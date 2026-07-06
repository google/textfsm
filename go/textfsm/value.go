package textfsm

import (
	"fmt"
	"regexp"
	"strings"
)

// ValueOption defines the behavior of a Value (Required, Filldown, Fillup, Key, List).
type ValueOption interface {
	Name() string
	OnCreateOptions(val *Value)
	OnAssignVar(val *Value)
	OnClearVar(val *Value)
	OnClearAllVar(val *Value)
	OnGetValue(val *Value)
	OnSaveRecord(val *Value) error
}

// Value represents a template variable declaration.
type Value struct {
	Name          string
	Regex         string
	Template      string
	CompiledRegex *regexp.Regexp
	Options       []ValueOption
	CurrentValue  interface{} // string or []interface{} for List
	FSM           *FSM
	maxNameLen    int
}

// NewValue creates a new Value bound to an FSM.
func NewValue(fsm *FSM) *Value {
	return &Value{
		FSM:        fsm,
		maxNameLen: 48,
	}
}

// Parse parses a 'Value' declaration line from a template.
func (v *Value) Parse(line string) error {
	tokens := strings.Split(line, " ")
	if len(tokens) < 3 {
		return &TemplateError{Msg: "Expect at least 3 tokens on line"}
	}

	if !strings.HasPrefix(tokens[2], "(") {
		// Options are present
		for _, optName := range strings.Split(tokens[1], ",") {
			if err := v.AddOption(optName); err != nil {
				return err
			}
		}
		for _, opt := range v.Options {
			opt.OnCreateOptions(v)
		}
		v.Name = tokens[2]
		v.Regex = strings.Join(tokens[3:], " ")
	} else {
		v.Name = tokens[1]
		v.Regex = strings.Join(tokens[2:], " ")
	}

	if len(v.Name) > v.maxNameLen {
		return &TemplateError{Msg: fmt.Sprintf("Invalid Value name '%s' or name too long", v.Name)}
	}

	if len(v.Regex) < 2 || v.Regex[0] != '(' || v.Regex[len(v.Regex)-1] != ')' || (len(v.Regex) >= 2 && v.Regex[len(v.Regex)-2] == '\\') {
		return &TemplateError{Msg: fmt.Sprintf("Value '%s' must be contained within a '()' pair", v.Regex)}
	}

	re, err := regexp.Compile(v.Regex)
	if err != nil {
		return &TemplateError{Msg: err.Error()}
	}

	v.Template = strings.Replace(v.Regex, "(", fmt.Sprintf("(?P<%s>", v.Name), 1)

	if v.HasOption("List") {
		v.CompiledRegex = re
	}

	return nil
}

// AddOption adds a named option to the Value.
func (v *Value) AddOption(name string) error {
	if v.HasOption(name) {
		return &TemplateError{Msg: fmt.Sprintf("Duplicate option \"%s\"", name)}
	}
	var opt ValueOption
	switch name {
	case "Required":
		opt = &optRequired{}
	case "Filldown":
		opt = &optFilldown{}
	case "Fillup":
		opt = &optFillup{}
	case "Key":
		opt = &optKey{}
	case "List":
		opt = &optList{}
	default:
		return &TemplateError{Msg: fmt.Sprintf("Unknown option \"%s\"", name)}
	}
	v.Options = append(v.Options, opt)
	return nil
}

// HasOption checks if the Value has the given option name.
func (v *Value) HasOption(name string) bool {
	for _, opt := range v.Options {
		if opt.Name() == name {
			return true
		}
	}
	return false
}

// OptionNames returns a list of option names for this Value.
func (v *Value) OptionNames() []string {
	names := make([]string, len(v.Options))
	for i, opt := range v.Options {
		names[i] = opt.Name()
	}
	return names
}

// AssignVar assigns a value to this Value and triggers option callbacks.
func (v *Value) AssignVar(val interface{}) {
	v.CurrentValue = val
	for _, opt := range v.Options {
		opt.OnAssignVar(v)
	}
}

// ClearVar clears this Value and triggers option callbacks.
func (v *Value) ClearVar() {
	v.CurrentValue = nil
	for _, opt := range v.Options {
		opt.OnClearVar(v)
	}
}

// ClearAllVar clears this Value and triggers clear-all callbacks.
func (v *Value) ClearAllVar() {
	v.CurrentValue = nil
	for _, opt := range v.Options {
		opt.OnClearAllVar(v)
	}
}

// Header returns the header name of this Value.
func (v *Value) Header() string {
	for _, opt := range v.Options {
		opt.OnGetValue(v)
	}
	return v.Name
}

// OnSaveRecord is called just prior to a record being committed.
func (v *Value) OnSaveRecord() error {
	for _, opt := range v.Options {
		if err := opt.OnSaveRecord(v); err != nil {
			return err
		}
	}
	return nil
}

// String returns the string representation of the Value.
func (v *Value) String() string {
	if len(v.Options) > 0 {
		return fmt.Sprintf("Value %s %s %s", strings.Join(v.OptionNames(), ","), v.Name, v.Regex)
	}
	return fmt.Sprintf("Value %s %s", v.Name, v.Regex)
}

func isValueEmpty(val interface{}) bool {
	if val == nil {
		return true
	}
	switch x := val.(type) {
	case string:
		return x == ""
	case []interface{}:
		return len(x) == 0
	case []string:
		return len(x) == 0
	case []map[string]string:
		return len(x) == 0
	}
	return false
}

// optRequired implementation
type optRequired struct{}

func (o *optRequired) Name() string               { return "Required" }
func (o *optRequired) OnCreateOptions(val *Value) {}
func (o *optRequired) OnAssignVar(val *Value)     {}
func (o *optRequired) OnClearVar(val *Value)      {}
func (o *optRequired) OnClearAllVar(val *Value)   {}
func (o *optRequired) OnGetValue(val *Value)      {}
func (o *optRequired) OnSaveRecord(val *Value) error {
	if isValueEmpty(val.CurrentValue) {
		return ErrSkipRecord
	}
	return nil
}

// optFilldown implementation
type optFilldown struct {
	myvar interface{}
}

func (o *optFilldown) Name() string               { return "Filldown" }
func (o *optFilldown) OnCreateOptions(val *Value) { o.myvar = nil }
func (o *optFilldown) OnAssignVar(val *Value)     { o.myvar = val.CurrentValue }
func (o *optFilldown) OnClearVar(val *Value)      { val.CurrentValue = o.myvar }
func (o *optFilldown) OnClearAllVar(val *Value)   { o.myvar = nil }
func (o *optFilldown) OnGetValue(val *Value)      {}
func (o *optFilldown) OnSaveRecord(val *Value) error {
	return nil
}

// optFillup implementation
type optFillup struct{}

func (o *optFillup) Name() string               { return "Fillup" }
func (o *optFillup) OnCreateOptions(val *Value) {}
func (o *optFillup) OnAssignVar(val *Value) {
	if !isValueEmpty(val.CurrentValue) && val.FSM != nil {
		idx := -1
		for i, v := range val.FSM.Values {
			if v == val {
				idx = i
				break
			}
		}
		if idx != -1 {
			// Iterate backwards over FSM results
			for i := len(val.FSM.result) - 1; i >= 0; i-- {
				row := val.FSM.result[i]
				if idx < len(row) && row[idx] != "" && row[idx] != nil {
					break
				}
				if idx < len(row) {
					row[idx] = val.CurrentValue
				}
			}
		}
	}
}
func (o *optFillup) OnClearVar(val *Value)         {}
func (o *optFillup) OnClearAllVar(val *Value)      {}
func (o *optFillup) OnGetValue(val *Value)         {}
func (o *optFillup) OnSaveRecord(val *Value) error { return nil }

// optKey implementation
type optKey struct{}

func (o *optKey) Name() string                  { return "Key" }
func (o *optKey) OnCreateOptions(val *Value)    {}
func (o *optKey) OnAssignVar(val *Value)        {}
func (o *optKey) OnClearVar(val *Value)         {}
func (o *optKey) OnClearAllVar(val *Value)      {}
func (o *optKey) OnGetValue(val *Value)         {}
func (o *optKey) OnSaveRecord(val *Value) error { return nil }

// optList implementation
type optList struct {
	listVal []interface{}
}

func (o *optList) Name() string { return "List" }
func (o *optList) OnCreateOptions(val *Value) {
	o.OnClearAllVar(val)
}
func (o *optList) OnAssignVar(val *Value) {
	if val.CompiledRegex != nil && val.CompiledRegex.NumSubexp() > 1 {
		strVal, ok := val.CurrentValue.(string)
		if !ok {
			return
		}
		matches := val.CompiledRegex.FindStringSubmatch(strVal)
		if len(matches) > 0 {
			m := make(map[string]string)
			for i, name := range val.CompiledRegex.SubexpNames() {
				if i > 0 && name != "" && i < len(matches) {
					m[name] = matches[i]
				}
			}
			if len(m) > 0 {
				o.listVal = append(o.listVal, m)
				return
			}
		}
	}
	o.listVal = append(o.listVal, val.CurrentValue)
}
func (o *optList) OnClearVar(val *Value) {
	if !val.HasOption("Filldown") {
		o.listVal = nil
	}
}
func (o *optList) OnClearAllVar(val *Value) {
	o.listVal = nil
}
func (o *optList) OnGetValue(val *Value) {}
func (o *optList) OnSaveRecord(val *Value) error {
	val.CurrentValue = append([]interface{}(nil), o.listVal...)
	return nil
}
