package clitable

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestExpandCompletion(t *testing.T) {
	tests := []struct {
		name string
		val  string
		want string
	}{
		{
			name: "simple completion",
			val:  "sh[[ow]]",
			want: "sh(o(w)?)?",
		},
		{
			name: "no completion",
			val:  "show version",
			want: "show version",
		},
		{
			name: "multiple completions",
			val:  "sh[[ow]] ver[[sion]]",
			want: "sh(o(w)?)? ver(s(i(o(n)?)?)?)?",
		},
	}

	for _, tc := range tests {
		got := expandCompletion(tc.val)
		if got != tc.want {
			t.Errorf("[%s] expandCompletion(%q) = %q, want %q", tc.name, tc.val, got, tc.want)
		}
	}
}

func TestIndexTableMatch(t *testing.T) {
	indexCSV := `Template,Hostname,Vendor,Command
cisco_version.tmpl,.*,cisco,sh[[ow]] ver[[sion]]
juniper_version.tmpl,.*,juniper,show version
`

	tests := []struct {
		name         string
		attrs        map[string]string
		wantTemplate string
		wantMatch    bool
	}{
		{
			name: "match cisco abbreviated command",
			attrs: map[string]string{
				"Vendor":  "cisco",
				"Command": "sho ver",
			},
			wantTemplate: "cisco_version.tmpl",
			wantMatch:    true,
		},
		{
			name: "match cisco full command",
			attrs: map[string]string{
				"Vendor":  "cisco",
				"Command": "show version",
			},
			wantTemplate: "cisco_version.tmpl",
			wantMatch:    true,
		},
		{
			name: "no match wrong vendor",
			attrs: map[string]string{
				"Vendor":  "hp",
				"Command": "show version",
			},
			wantTemplate: "",
			wantMatch:    false,
		},
	}

	idx, err := NewIndexTableFromReader(strings.NewReader(indexCSV), "test_index")
	if err != nil {
		t.Fatalf("NewIndexTableFromReader() error = %v", err)
	}

	for _, tc := range tests {
		entry := idx.GetRowMatch(tc.attrs)
		if tc.wantMatch && entry == nil {
			t.Errorf("[%s] GetRowMatch(%v) returned nil, want %q", tc.name, tc.attrs, tc.wantTemplate)
			continue
		}
		if !tc.wantMatch && entry != nil {
			t.Errorf("[%s] GetRowMatch(%v) returned %q, want nil", tc.name, tc.attrs, entry.Template)
			continue
		}
		if tc.wantMatch && entry.Template != tc.wantTemplate {
			t.Errorf("[%s] Template = %q, want %q", tc.name, entry.Template, tc.wantTemplate)
		}
	}
}

func TestCliTableParseCmd(t *testing.T) {
	// Create temporary directory for templates and index
	tmpDir := t.TempDir()

	indexContent := `Template,Hostname,Vendor,Command
test_template.tmpl,.*,cisco,sh[[ow]] ver[[sion]]
`
	if err := os.WriteFile(filepath.Join(tmpDir, "index"), []byte(indexContent), 0644); err != nil {
		t.Fatalf("failed to write index file: %v", err)
	}

	templateContent := `Value Key Version (\d+\.\d+)
Value Uptime (\d+)

Start
  ^Version:\s+${Version},\s+uptime:\s+${Uptime} -> Record
`
	if err := os.WriteFile(filepath.Join(tmpDir, "test_template.tmpl"), []byte(templateContent), 0644); err != nil {
		t.Fatalf("failed to write template file: %v", err)
	}

	cmdOutput := `Version: 15.2, uptime: 100
Version: 16.1, uptime: 200`

	tests := []struct {
		name     string
		attrs    map[string]string
		wantHead []string
		wantRows [][]string
		wantKey  []string
		wantErr  bool
	}{
		{
			name: "parse valid cisco show version",
			attrs: map[string]string{
				"Vendor":  "cisco",
				"Command": "sho ver",
			},
			wantHead: []string{"Version", "Uptime"},
			wantRows: [][]string{
				{"15.2", "100"},
				{"16.1", "200"},
			},
			wantKey: []string{"Version"},
			wantErr: false,
		},
		{
			name: "parse invalid attribute combination",
			attrs: map[string]string{
				"Vendor":  "juniper",
				"Command": "show version",
			},
			wantErr: true,
		},
	}

	for _, tc := range tests {
		ct, err := NewCliTable("index", tmpDir)
		if err != nil {
			t.Fatalf("[%s] NewCliTable() error = %v", tc.name, err)
		}

		err = ct.ParseCmd(cmdOutput, tc.attrs, "")
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] ParseCmd() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if tc.wantErr {
			continue
		}

		if !reflect.DeepEqual(ct.Header, tc.wantHead) {
			t.Errorf("[%s] Header = %v, want %v", tc.name, ct.Header, tc.wantHead)
		}

		if ct.Size() != len(tc.wantRows) {
			t.Errorf("[%s] Size() = %d, want %d", tc.name, ct.Size(), len(tc.wantRows))
			continue
		}

		for i, row := range ct.Rows {
			if !reflect.DeepEqual(row.Values, tc.wantRows[i]) {
				t.Errorf("[%s] Row[%d] = %v, want %v", tc.name, i, row.Values, tc.wantRows[i])
			}
		}

		if !reflect.DeepEqual(ct.SuperKey(), tc.wantKey) {
			t.Errorf("[%s] SuperKey() = %v, want %v", tc.name, ct.SuperKey(), tc.wantKey)
		}
	}
}
