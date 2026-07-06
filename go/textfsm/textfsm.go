package textfsm

import (
	"bufio"
	"fmt"
	"io"
	"regexp"
	"strings"
)

var commentRe = regexp.MustCompile(`^\s*#`)

// FSM parses a template and executes the state machine against input text.
type FSM struct {
	States       map[string][]*Rule
	StateList    []string
	Values       []*Value
	ValueMap     map[string]string
	Header       []string
	curState     []*Rule
	curStateName string
	result       [][]interface{}
	lineNum      int
}

// NewFSM parses a template file/reader and initializes a new FSM.
func NewFSM(r io.Reader) (*FSM, error) {
	fsm := &FSM{
		States:   make(map[string][]*Rule),
		ValueMap: make(map[string]string),
	}

	scanner := bufio.NewScanner(r)
	if err := fsm.parse(scanner); err != nil {
		return nil, err
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	fsm.Reset()
	return fsm, nil
}

// Reset preserves the FSM but resets starting state and current record.
func (fsm *FSM) Reset() {
	fsm.curState = fsm.States["Start"]
	fsm.curStateName = "Start"
	fsm.result = nil
	fsm.clearAllRecord()
}

func (fsm *FSM) parse(scanner *bufio.Scanner) error {
	if err := fsm.parseFSMVariables(scanner); err != nil {
		return err
	}

	for {
		stateName, err := fsm.parseFSMState(scanner)
		if err != nil {
			return err
		}
		if stateName == "" {
			break
		}
	}

	return fsm.validateFSM()
}

func (fsm *FSM) parseFSMVariables(scanner *bufio.Scanner) error {
	fsm.Values = nil
	for scanner.Scan() {
		fsm.lineNum++
		line := strings.TrimRight(scanner.Text(), "\r\n\t ")

		if line == "" {
			return nil
		}
		if commentRe.MatchString(line) {
			continue
		}

		if strings.HasPrefix(line, "Value ") {
			val := NewValue(fsm)
			if err := val.Parse(line); err != nil {
				return &TemplateError{Msg: fmt.Sprintf("%v Line %d.", err, fsm.lineNum), LineNum: fsm.lineNum}
			}

			for _, existing := range fsm.Values {
				if existing.Name == val.Name {
					return &TemplateError{
						Msg:     fmt.Sprintf("Duplicate declarations for Value '%s'. Line: %d.", val.Name, fsm.lineNum),
						LineNum: fsm.lineNum,
					}
				}
			}

			fsm.Values = append(fsm.Values, val)
			fsm.ValueMap[val.Name] = val.Template
		} else if len(fsm.Values) == 0 {
			return &TemplateError{Msg: "No Value definitions found"}
		} else {
			return &TemplateError{
				Msg:     fmt.Sprintf("Expected blank line after last Value entry. Line: %d.", fsm.lineNum),
				LineNum: fsm.lineNum,
			}
		}
	}
	return nil
}

func (fsm *FSM) parseFSMState(scanner *bufio.Scanner) (string, error) {
	stateName := ""
	for scanner.Scan() {
		fsm.lineNum++
		line := strings.TrimRight(scanner.Text(), "\r\n\t ")
		if line != "" && !commentRe.MatchString(line) {
			if !stateNameRe.MatchString(line) || len(line) > 48 || validLineOps[line] || validRecordOps[line] {
				return "", &TemplateError{
					Msg:     fmt.Sprintf("Invalid state name: '%s'. Line: %d", line, fsm.lineNum),
					LineNum: fsm.lineNum,
				}
			}
			stateName = line
			if _, exists := fsm.States[stateName]; exists {
				return "", &TemplateError{
					Msg:     fmt.Sprintf("Duplicate state name: '%s'. Line: %d", line, fsm.lineNum),
					LineNum: fsm.lineNum,
				}
			}
			fsm.States[stateName] = []*Rule{}
			fsm.StateList = append(fsm.StateList, stateName)
			break
		}
	}

	if stateName == "" {
		return "", nil
	}

	for scanner.Scan() {
		fsm.lineNum++
		line := strings.TrimRight(scanner.Text(), "\r\n\t ")
		if line == "" {
			break
		}
		if commentRe.MatchString(line) {
			continue
		}
		if !strings.HasPrefix(line, " ^") && !strings.HasPrefix(line, "  ^") && !strings.HasPrefix(line, "\t^") {
			return "", &TemplateError{
				Msg:     fmt.Sprintf("Missing white space or carat ('^') before rule. Line: %d", fsm.lineNum),
				LineNum: fsm.lineNum,
			}
		}

		rule, err := NewRule(line, fsm.lineNum, fsm.ValueMap)
		if err != nil {
			return "", err
		}
		fsm.States[stateName] = append(fsm.States[stateName], rule)
	}

	return stateName, nil
}

func (fsm *FSM) validateFSM() error {
	if _, ok := fsm.States["Start"]; !ok {
		return &TemplateError{Msg: "Missing state 'Start'"}
	}
	if len(fsm.States["End"]) > 0 {
		return &TemplateError{Msg: "Non-Empty 'End' state"}
	}
	if len(fsm.States["EOF"]) > 0 {
		return &TemplateError{Msg: "Non-Empty 'EOF' state"}
	}
	if _, ok := fsm.States["End"]; ok {
		delete(fsm.States, "End")
		for i, s := range fsm.StateList {
			if s == "End" {
				fsm.StateList = append(fsm.StateList[:i], fsm.StateList[i+1:]...)
				break
			}
		}
	}

	for state, rules := range fsm.States {
		for _, r := range rules {
			if r.LineOp == "Error" || r.NewState == "" || r.NewState == "End" || r.NewState == "EOF" {
				continue
			}
			if _, ok := fsm.States[r.NewState]; !ok {
				return &TemplateError{
					Msg: fmt.Sprintf("State '%s' not found, referenced in state '%s'", r.NewState, state),
				}
			}
		}
	}

	fsm.Header = make([]string, 0, len(fsm.Values))
	for _, val := range fsm.Values {
		fsm.Header = append(fsm.Header, val.Header())
	}

	return nil
}

// GetValuesByAttrib returns a list of value names that have a particular attribute/option.
func (fsm *FSM) GetValuesByAttrib(attribute string) []string {
	var result []string
	for _, val := range fsm.Values {
		if val.HasOption(attribute) {
			result = append(result, val.Name)
		}
	}
	return result
}

// ParseText passes CLI output through the FSM and returns a 2D slice of values.
// The first row is always the header.
func (fsm *FSM) ParseText(text string, eof bool) ([][]interface{}, error) {
	lines := strings.Split(text, "\n")
	for _, line := range lines {
		line = strings.TrimRight(line, "\r")
		if err := fsm.checkLine(line); err != nil {
			return nil, err
		}
		if fsm.curStateName == "End" || fsm.curStateName == "EOF" {
			break
		}
	}

	if fsm.curStateName != "End" && fsm.States["EOF"] == nil && eof {
		fsm.appendRecord()
	}

	out := make([][]interface{}, 0, len(fsm.result)+1)
	headerRow := make([]interface{}, len(fsm.Header))
	for i, h := range fsm.Header {
		headerRow[i] = h
	}
	out = append(out, headerRow)
	out = append(out, fsm.result...)
	return out, nil
}

// ParseTextToDicts parses CLI output and returns a slice of maps (column header -> value).
func (fsm *FSM) ParseTextToDicts(text string, eof bool) ([]map[string]interface{}, error) {
	rows, err := fsm.ParseText(text, eof)
	if err != nil {
		return nil, err
	}
	if len(rows) <= 1 {
		return nil, nil
	}

	result := make([]map[string]interface{}, 0, len(rows)-1)
	for i := 1; i < len(rows); i++ {
		m := make(map[string]interface{}, len(fsm.Header))
		for j, col := range fsm.Header {
			if j < len(rows[i]) {
				m[col] = rows[i][j]
			}
		}
		result = append(result, m)
	}
	return result, nil
}

func (fsm *FSM) checkLine(line string) error {
	for _, rule := range fsm.curState {
		indices := rule.RegexObj.FindStringSubmatchIndex(line)
		if indices != nil {
			for i, name := range rule.RegexObj.SubexpNames() {
				if i > 0 && name != "" {
					start := indices[2*i]
					end := indices[2*i+1]
					var val interface{}
					if start != -1 && end != -1 {
						val = line[start:end]
					} else {
						val = nil
					}
					fsm.assignVar(name, val)
				}
			}

			if err := fsm.operations(rule, line); err != nil {
				return err
			}

			if rule.LineOp != "Continue" {
				if rule.NewState != "" {
					if rule.NewState != "End" && rule.NewState != "EOF" {
						fsm.curState = fsm.States[rule.NewState]
					}
					fsm.curStateName = rule.NewState
				}
				break
			}
		}
	}
	return nil
}

func (fsm *FSM) assignVar(name string, val interface{}) {
	for _, v := range fsm.Values {
		if v.Name == name {
			v.AssignVar(val)
			break
		}
	}
}

func (fsm *FSM) operations(rule *Rule, line string) error {
	switch rule.RecordOp {
	case "Record":
		fsm.appendRecord()
	case "Clear":
		fsm.clearRecord()
	case "Clearall":
		fsm.clearAllRecord()
	}

	if rule.LineOp == "Error" {
		if rule.NewState != "" {
			return &FSMError{Msg: fmt.Sprintf("Error: %s", rule.NewState), LineNum: rule.LineNum, Input: line}
		}
		return &FSMError{Msg: "State Error raised", LineNum: rule.LineNum, Input: line}
	}

	return nil
}

func (fsm *FSM) appendRecord() {
	if len(fsm.Values) == 0 {
		return
	}

	curRecord := make([]interface{}, 0, len(fsm.Values))
	for _, val := range fsm.Values {
		if err := val.OnSaveRecord(); err == ErrSkipRecord {
			fsm.clearRecord()
			return
		}
		curRecord = append(curRecord, val.CurrentValue)
	}

	emptyCount := 0
	for _, v := range curRecord {
		if isValueEmpty(v) {
			emptyCount++
		}
	}
	if emptyCount == len(curRecord) {
		return
	}

	for i, v := range curRecord {
		if v == nil {
			curRecord[i] = ""
		}
	}

	fsm.result = append(fsm.result, curRecord)
	fsm.clearRecord()
}

func (fsm *FSM) clearRecord() {
	for _, v := range fsm.Values {
		v.ClearVar()
	}
}

func (fsm *FSM) clearAllRecord() {
	for _, v := range fsm.Values {
		v.ClearAllVar()
	}
}

// String returns the FSM template representation.
func (fsm *FSM) String() string {
	var sb strings.Builder
	for _, v := range fsm.Values {
		sb.WriteString(v.String())
		sb.WriteString("\n")
	}
	sb.WriteString("\n")
	for _, state := range fsm.StateList {
		sb.WriteString("\n" + state + "\n")
		for _, r := range fsm.States[state] {
			sb.WriteString(r.String())
			sb.WriteString("\n")
		}
	}
	return sb.String()
}
