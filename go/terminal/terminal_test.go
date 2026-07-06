package terminal

import (
	"testing"
)

func TestAnsiCmd(t *testing.T) {
	tests := []struct {
		name    string
		cmds    []string
		want    string
		wantErr bool
	}{
		{
			name:    "single reset",
			cmds:    []string{"reset"},
			want:    "\033[0m",
			wantErr: false,
		},
		{
			name:    "multiple colors",
			cmds:    []string{"bold", "red", "bg_white"},
			want:    "\033[1;31;47m",
			wantErr: false,
		},
		{
			name:    "case insensitive",
			cmds:    []string{"BLUE", "Bg_Yellow"},
			want:    "\033[34;43m",
			wantErr: false,
		},
		{
			name:    "invalid color",
			cmds:    []string{"super_red"},
			want:    "",
			wantErr: true,
		},
		{
			name:    "empty list",
			cmds:    []string{},
			want:    "",
			wantErr: false,
		},
	}

	for _, tc := range tests {
		got, err := AnsiCmd(tc.cmds)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] AnsiCmd(%v) error = %v, wantErr %v", tc.name, tc.cmds, err, tc.wantErr)
			continue
		}
		if got != tc.want {
			t.Errorf("[%s] AnsiCmd(%v) = %q, want %q", tc.name, tc.cmds, got, tc.want)
		}
	}
}

func TestAnsiText(t *testing.T) {
	tests := []struct {
		name    string
		text    string
		cmds    []string
		reset   bool
		want    string
		wantErr bool
	}{
		{
			name:    "with reset",
			text:    "hello",
			cmds:    []string{"green"},
			reset:   true,
			want:    "\033[32mhello\033[0m",
			wantErr: false,
		},
		{
			name:    "without reset",
			text:    "world",
			cmds:    []string{"bold", "blue"},
			reset:   false,
			want:    "\033[1;34mworld",
			wantErr: false,
		},
		{
			name:    "default reset command when empty",
			text:    "test",
			cmds:    nil,
			reset:   true,
			want:    "\033[0mtest\033[0m",
			wantErr: false,
		},
	}

	for _, tc := range tests {
		got, err := AnsiText(tc.text, tc.cmds, tc.reset)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] AnsiText(%q, %v, %v) error = %v, wantErr %v", tc.name, tc.text, tc.cmds, tc.reset, err, tc.wantErr)
			continue
		}
		if got != tc.want {
			t.Errorf("[%s] AnsiText(%q, %v, %v) = %q, want %q", tc.name, tc.text, tc.cmds, tc.reset, got, tc.want)
		}
	}
}

func TestStripAnsiText(t *testing.T) {
	tests := []struct {
		name string
		text string
		want string
	}{
		{
			name: "no ansi",
			text: "plain text",
			want: "plain text",
		},
		{
			name: "with ansi",
			text: "\033[31mred text\033[0m and \033[1;32mgreen text\033[0m",
			want: "red text and green text",
		},
		{
			name: "with enclosed ansi",
			text: "\001\033[34m\002blue\001\033[0m\002",
			want: "blue",
		},
	}

	for _, tc := range tests {
		got := StripAnsiText(tc.text)
		if got != tc.want {
			t.Errorf("[%s] StripAnsiText(%q) = %q, want %q", tc.name, tc.text, got, tc.want)
		}
	}
}

func TestEncloseAnsiText(t *testing.T) {
	tests := []struct {
		name string
		text string
		want string
	}{
		{
			name: "simple ansi",
			text: "\033[31mred\033[0m",
			want: "\001\033[31m\002red\001\033[0m\002",
		},
		{
			name: "already enclosed",
			text: "\001\033[31m\002red\001\033[0m\002",
			want: "\001\033[31m\002red\001\033[0m\002",
		},
		{
			name: "no ansi",
			text: "normal string",
			want: "normal string",
		},
	}

	for _, tc := range tests {
		got := EncloseAnsiText(tc.text)
		if got != tc.want {
			t.Errorf("[%s] EncloseAnsiText(%q) = %q, want %q", tc.name, tc.text, got, tc.want)
		}
	}
}

func TestLineWrap(t *testing.T) {
	tests := []struct {
		name    string
		text    string
		omitSGR bool
		width   int
		want    string
	}{
		{
			name:    "short line no wrap",
			text:    "hello world",
			omitSGR: false,
			width:   20,
			want:    "hello world",
		},
		{
			name:    "long line wrap without sgr",
			text:    "abcdefghijklmnopqrstuvwxyz",
			omitSGR: false,
			width:   10,
			want:    "abcdefghij\nklmnopqrst\nuvwxyz",
		},
		{
			name:    "wrap with sgr ignored in length",
			text:    "\033[31mabcdefghij\033[0mklmnopqrstuvwxyz",
			omitSGR: true,
			width:   10,
			want:    "\033[31mabcdefghij\033[0m\nklmnopqrst\nuvwxyz",
		},
	}

	for _, tc := range tests {
		got := LineWrap(tc.text, tc.omitSGR, tc.width)
		if got != tc.want {
			t.Errorf("[%s] LineWrap(%q, %v, %d) = %q, want %q", tc.name, tc.text, tc.omitSGR, tc.width, got, tc.want)
		}
	}
}
