package textfsm

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	matchActionRe = regexp.MustCompile(`^(.*?)(\s+->\s*(.*))$`)
	varSubRe      = regexp.MustCompile(`\$(?:\{(\w+)\}|(\w+))`)
	stateNameRe   = regexp.MustCompile(`^\w+$`)
)

var (
	validLineOps   = map[string]bool{"Continue": true, "Next": true, "Error": true}
	validRecordOps = map[string]bool{"Clear": true, "Clearall": true, "Record": true, "NoRecord": true}
)

// Rule represents a transition rule in an FSM state.
type Rule struct {
	Match    string
	Regex    string
	RegexObj *regexp.Regexp
	LineOp   string // "Next", "Continue", "Error"
	RecordOp string // "NoRecord", "Record", "Clear", "Clearall"
	NewState string
	LineNum  int
}

// NewRule creates and parses a new Rule from a template line.
func NewRule(line string, lineNum int, varMap map[string]string) (*Rule, error) {
	r := &Rule{
		LineNum: lineNum,
	}

	trimmed := strings.TrimSpace(line)
	if trimmed == "" {
		return nil, &TemplateError{Msg: fmt.Sprintf("Null data in FSMRule. Line: %d", lineNum), LineNum: lineNum}
	}

	// Check for '->' action
	matchAction := matchActionRe.FindStringSubmatch(trimmed)
	if len(matchAction) > 0 {
		r.Match = matchAction[1]
	} else {
		r.Match = trimmed
	}

	// Variable substitution ${var} or $var
	var errVarSub error
	r.Regex = varSubRe.ReplaceAllStringFunc(r.Match, func(s string) string {
		m := varSubRe.FindStringSubmatch(s)
		name := m[1]
		if name == "" {
			name = m[2]
		}
		tmpl, ok := varMap[name]
		if !ok {
			errVarSub = &TemplateError{
				Msg:     fmt.Sprintf("Duplicate or invalid variable substitution: '%s'. Line: %d.", r.Match, lineNum),
				LineNum: lineNum,
			}
			return s
		}
		return tmpl
	})
	if errVarSub != nil {
		return nil, errVarSub
	}

	re, err := regexp.Compile(r.Regex)
	if err != nil {
		return nil, &TemplateError{
			Msg:     fmt.Sprintf("Invalid regular expression: '%s'. Line: %d.", r.Regex, lineNum),
			LineNum: lineNum,
		}
	}
	r.RegexObj = re

	if len(matchAction) == 0 {
		return r, nil
	}

	actionStr := strings.TrimSpace(matchAction[3])
	if err := r.parseAction(actionStr, trimmed); err != nil {
		return nil, err
	}

	return r, nil
}

func (r *Rule) parseAction(actionStr, origLine string) error {
	parts := strings.Fields(actionStr)
	if len(parts) == 0 {
		return &TemplateError{Msg: fmt.Sprintf("Badly formatted rule '%s'. Line: %d.", origLine, r.LineNum), LineNum: r.LineNum}
	}

	firstToken := parts[0]
	isOp := false

	if strings.Contains(firstToken, ".") {
		opParts := strings.Split(firstToken, ".")
		if len(opParts) != 2 {
			return &TemplateError{Msg: fmt.Sprintf("Badly formatted rule '%s'. Line: %d.", origLine, r.LineNum), LineNum: r.LineNum}
		}
		op1, op2 := opParts[0], opParts[1]
		if validLineOps[op1] && validRecordOps[op2] {
			r.LineOp = op1
			r.RecordOp = op2
			isOp = true
		} else if validRecordOps[op1] && validLineOps[op2] {
			// In Python, Record.Next is rejected as badly formatted
			return &TemplateError{Msg: fmt.Sprintf("Badly formatted rule '%s'. Line: %d.", origLine, r.LineNum), LineNum: r.LineNum}
		} else {
			return &TemplateError{Msg: fmt.Sprintf("Badly formatted rule '%s'. Line: %d.", origLine, r.LineNum), LineNum: r.LineNum}
		}
	} else if validLineOps[firstToken] {
		r.LineOp = firstToken
		isOp = true
	} else if validRecordOps[firstToken] {
		r.RecordOp = firstToken
		isOp = true
	}

	if isOp {
		if len(parts) > 1 {
			r.NewState = strings.TrimSpace(actionStr[len(firstToken):])
		}
	} else {
		// No operator matched, so the whole actionStr is treated as NewState
		r.NewState = actionStr
	}

	if r.LineOp == "Continue" && r.NewState != "" {
		return &TemplateError{
			Msg:     fmt.Sprintf("Action '%s' with new state %s specified. Line: %d.", r.LineOp, r.NewState, r.LineNum),
			LineNum: r.LineNum,
		}
	}

	if r.LineOp != "Error" && r.NewState != "" {
		if len(strings.Fields(r.NewState)) > 1 || !stateNameRe.MatchString(r.NewState) {
			if !isOp {
				return &TemplateError{Msg: fmt.Sprintf("Badly formatted rule '%s'. Line: %d.", origLine, r.LineNum), LineNum: r.LineNum}
			}
			return &TemplateError{
				Msg:     fmt.Sprintf("Alphanumeric characters only in state names. Line: %d.", r.LineNum),
				LineNum: r.LineNum,
			}
		}
	}

	return nil
}

// String returns the string representation of the Rule.
func (r *Rule) String() string {
	op := ""
	if r.LineOp != "" && r.RecordOp != "" {
		op = r.LineOp + "." + r.RecordOp
	} else {
		op = r.LineOp + r.RecordOp
	}

	newState := r.NewState
	if op != "" && newState != "" {
		newState = " " + newState
	}

	if op == "" && newState == "" {
		return "  " + r.Match
	}
	return "  " + r.Match + " -> " + op + newState
}
