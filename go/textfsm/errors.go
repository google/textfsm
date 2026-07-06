// Package textfsm implements a template based text parser.
package textfsm

import "fmt"

// ErrSkipRecord is raised by Value options (like Required) to indicate a record should be skipped.
var ErrSkipRecord = fmt.Errorf("skip record")

// ErrSkipValue is raised by Value options to indicate a value should be skipped.
var ErrSkipValue = fmt.Errorf("skip value")

// TemplateError represents an error in template syntax or FSM construction.
type TemplateError struct {
	Msg     string
	LineNum int
}

func (e *TemplateError) Error() string {
	if e.LineNum > 0 {
		return fmt.Sprintf("%s Line: %d.", e.Msg, e.LineNum)
	}
	return e.Msg
}

// FSMError represents a runtime error during state machine execution.
type FSMError struct {
	Msg     string
	LineNum int
	Input   string
}

func (e *FSMError) Error() string {
	if e.LineNum > 0 {
		return fmt.Sprintf("%s Rule Line: %d. Input Line: %s.", e.Msg, e.LineNum, e.Input)
	}
	return e.Msg
}
