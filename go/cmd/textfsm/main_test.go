package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCLI(t *testing.T) {
	tmpDir := t.TempDir()

	tmplPath := filepath.Join(tmpDir, "test.tmpl")
	inPath := filepath.Join(tmpDir, "test.in")
	refPath := filepath.Join(tmpDir, "test.ref")

	tmplData := `Value Key Version (\d+\.\d+)

Start
  ^Version:\s+${Version} -> Record
`
	inData := `Version: 1.0
Version: 2.5`
	refData := `["Version"]
["1.0"]
["2.5"]
`

	_ = os.WriteFile(tmplPath, []byte(tmplData), 0644)
	_ = os.WriteFile(inPath, []byte(inData), 0644)
	_ = os.WriteFile(refPath, []byte(refData), 0644)

	tests := []struct {
		name       string
		args       []string
		wantExit   int
		wantStdout string
	}{
		{
			name:       "help flag",
			args:       []string{"--help"},
			wantExit:   0,
			wantStdout: "textfsm [--help] template [input_file [output_file]]",
		},
		{
			name:       "template only",
			args:       []string{tmplPath},
			wantExit:   0,
			wantStdout: "FSM Template:",
		},
		{
			name:       "template and input",
			args:       []string{tmplPath, inPath},
			wantExit:   0,
			wantStdout: "FSM Table:\n[\"Version\"]\n[\"1.0\"]\n[\"2.5\"]",
		},
		{
			name:       "template input and matching ref",
			args:       []string{tmplPath, inPath, refPath},
			wantExit:   0,
			wantStdout: "Data match!",
		},
		{
			name:     "missing args",
			args:     []string{},
			wantExit: 2,
		},
	}

	for _, tc := range tests {
		var stdout, stderr bytes.Buffer
		exitCode := run(tc.args, &stdout, &stderr)
		if exitCode != tc.wantExit {
			t.Errorf("[%s] run(%v) exitCode = %d, want %d", tc.name, tc.args, exitCode, tc.wantExit)
			continue
		}
		if tc.wantStdout != "" && !strings.Contains(stdout.String(), tc.wantStdout) {
			t.Errorf("[%s] stdout = %q, want substring %q", tc.name, stdout.String(), tc.wantStdout)
		}
	}
}
