package textfsm

import (
	"reflect"
	"strings"
	"testing"
)

func TestValueParse(t *testing.T) {
	tests := []struct {
		name        string
		line        string
		wantName    string
		wantRegex   string
		wantOptions []string
		wantErr     bool
	}{
		{
			name:        "simple value",
			line:        "Value beer (\\S+)",
			wantName:    "beer",
			wantRegex:   "(\\S+)",
			wantOptions: []string{},
			wantErr:     false,
		},
		{
			name:        "value with options",
			line:        "Value Filldown,Required beer (\\S+)",
			wantName:    "beer",
			wantRegex:   "(\\S+)",
			wantOptions: []string{"Filldown", "Required"},
			wantErr:     false,
		},
		{
			name:        "multiple parenthesis",
			line:        "Value Required beer (boo(hoo))",
			wantName:    "beer",
			wantRegex:   "(boo(hoo))",
			wantOptions: []string{"Required"},
			wantErr:     false,
		},
		{
			name:    "unbalanced parenthesis",
			line:    "Value beer (boo(hoo)))boo",
			wantErr: true,
		},
		{
			name:        "escaped parenthesis",
			line:        "Value beer (boo\\)hoo)",
			wantName:    "beer",
			wantRegex:   "(boo\\)hoo)",
			wantOptions: []string{},
			wantErr:     false,
		},
		{
			name:    "too few tokens",
			line:    "Value beer",
			wantErr: true,
		},
		{
			name:    "unknown option",
			line:    "Value SuperOption beer (.*)",
			wantErr: true,
		},
	}

	for _, tc := range tests {
		fsm := &FSM{}
		v := NewValue(fsm)
		err := v.Parse(tc.line)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] Parse() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if tc.wantErr {
			continue
		}
		if v.Name != tc.wantName {
			t.Errorf("[%s] Name = %q, want %q", tc.name, v.Name, tc.wantName)
		}
		if v.Regex != tc.wantRegex {
			t.Errorf("[%s] Regex = %q, want %q", tc.name, v.Regex, tc.wantRegex)
		}
		if !reflect.DeepEqual(v.OptionNames(), tc.wantOptions) {
			t.Errorf("[%s] OptionNames() = %v, want %v", tc.name, v.OptionNames(), tc.wantOptions)
		}
	}
}

func TestRuleParse(t *testing.T) {
	varMap := map[string]string{
		"beer": "(?P<beer>\\S+)",
	}

	tests := []struct {
		name         string
		line         string
		wantMatch    string
		wantLineOp   string
		wantRecordOp string
		wantNewState string
		wantErr      bool
	}{
		{
			name:         "basic line no action",
			line:         "  ^A beer called ${beer}",
			wantMatch:    "^A beer called ${beer}",
			wantLineOp:   "",
			wantRecordOp: "",
			wantNewState: "",
			wantErr:      false,
		},
		{
			name:         "line with next action",
			line:         "  ^A beer called ${beer} -> Next",
			wantMatch:    "^A beer called ${beer}",
			wantLineOp:   "Next",
			wantRecordOp: "",
			wantNewState: "",
			wantErr:      false,
		},
		{
			name:         "line with continue record",
			line:         "  ^A beer called ${beer} -> Continue.Record",
			wantMatch:    "^A beer called ${beer}",
			wantLineOp:   "Continue",
			wantRecordOp: "Record",
			wantNewState: "",
			wantErr:      false,
		},
		{
			name:         "line with new state and record op",
			line:         "  ^A beer called ${beer} -> Next.NoRecord End",
			wantMatch:    "^A beer called ${beer}",
			wantLineOp:   "Next",
			wantRecordOp: "NoRecord",
			wantNewState: "End",
			wantErr:      false,
		},
		{
			name:    "bad syntax multiple next",
			line:    "  ^A beer called ${beer} -> Next Next Next",
			wantErr: true,
		},
		{
			name:    "continue with new state is invalid",
			line:    "  ^A beer called ${beer} -> Continue End",
			wantErr: true,
		},
		{
			name:    "unknown variable substitution",
			line:    "  ^A beer called ${wine}",
			wantErr: true,
		},
	}

	for _, tc := range tests {
		r, err := NewRule(tc.line, 1, varMap)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] NewRule() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if tc.wantErr {
			continue
		}
		if r.Match != tc.wantMatch {
			t.Errorf("[%s] Match = %q, want %q", tc.name, r.Match, tc.wantMatch)
		}
		if r.LineOp != tc.wantLineOp {
			t.Errorf("[%s] LineOp = %q, want %q", tc.name, r.LineOp, tc.wantLineOp)
		}
		if r.RecordOp != tc.wantRecordOp {
			t.Errorf("[%s] RecordOp = %q, want %q", tc.name, r.RecordOp, tc.wantRecordOp)
		}
		if r.NewState != tc.wantNewState {
			t.Errorf("[%s] NewState = %q, want %q", tc.name, r.NewState, tc.wantNewState)
		}
	}
}

func TestFSMParseAndExecute(t *testing.T) {
	tests := []struct {
		name     string
		template string
		input    string
		wantHead []string
		wantRows [][]interface{}
		wantErr  bool
	}{
		{
			name: "simple interface parsing",
			template: `Value Required Interface (\S+)
Value Status (up|down)
Value Protocol (up|down)

Start
  ^${Interface}\s+is\s+${Status},\s+line\s+protocol\s+is\s+${Protocol} -> Record
`,
			input: `GigabitEthernet0/0 is up, line protocol is up
GigabitEthernet0/1 is down, line protocol is down
Loopback0 is up, line protocol is up`,
			wantHead: []string{"Interface", "Status", "Protocol"},
			wantRows: [][]interface{}{
				{"GigabitEthernet0/0", "up", "up"},
				{"GigabitEthernet0/1", "down", "down"},
				{"Loopback0", "up", "up"},
			},
			wantErr: false,
		},
		{
			name: "filldown and required options",
			template: `Value Filldown Router (\S+)
Value Required Interface (\S+)
Value Status (up|down)

Start
  ^Router:\s+${Router}
  ^Interface\s+${Interface}\s+is\s+${Status} -> Record
`,
			input: `Router: R1
Interface Eth0 is up
Interface Eth1 is down
Router: R2
Interface Eth0 is up`,
			wantHead: []string{"Router", "Interface", "Status"},
			wantRows: [][]interface{}{
				{"R1", "Eth0", "up"},
				{"R1", "Eth1", "down"},
				{"R2", "Eth0", "up"},
			},
			wantErr: false,
		},
		{
			name: "list option",
			template: `Value List IP (\d+\.\d+\.\d+\.\d+)

Start
  ^IP:\s+${IP}
  ^End -> Record
`,
			input: `IP: 1.1.1.1
IP: 2.2.2.2
End`,
			wantHead: []string{"IP"},
			wantRows: [][]interface{}{
				{[]interface{}{"1.1.1.1", "2.2.2.2"}},
			},
			wantErr: false,
		},
		{
			name: "state transitions",
			template: `Value Filldown Section (\S+)
Value Item (\S+)

Start
  ^Section:\s+${Section} -> InSection

InSection
  ^Item:\s+${Item} -> Record
  ^EndSection -> Start
`,
			input: `Section: A
Item: 1
Item: 2
EndSection
Section: B
Item: 3`,
			wantHead: []string{"Section", "Item"},
			wantRows: [][]interface{}{
				{"A", "1"},
				{"A", "2"},
				{"B", "3"},
				{"B", ""},
			},
			wantErr: false,
		},
		{
			name: "error line op",
			template: `Value Val (\d+)

Start
  ^FATAL -> Error "Fatal error occurred"
  ^Val:\s+${Val} -> Record
`,
			input:   `Val: 100` + "\n" + `FATAL`,
			wantErr: true,
		},
	}

	for _, tc := range tests {
		fsm, err := NewFSM(strings.NewReader(tc.template))
		if err != nil {
			if !tc.wantErr {
				t.Errorf("[%s] NewFSM() unexpected error = %v", tc.name, err)
			}
			continue
		}

		got, err := fsm.ParseText(tc.input, true)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] ParseText() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if tc.wantErr {
			continue
		}

		if len(got) == 0 {
			t.Errorf("[%s] ParseText() returned empty slice", tc.name)
			continue
		}

		// Check header
		gotHead := make([]string, len(got[0]))
		for i, h := range got[0] {
			gotHead[i] = h.(string)
		}
		if !reflect.DeepEqual(gotHead, tc.wantHead) {
			t.Errorf("[%s] Header = %v, want %v", tc.name, gotHead, tc.wantHead)
		}

		// Check rows
		gotRows := got[1:]
		if len(gotRows) != len(tc.wantRows) {
			t.Errorf("[%s] len(rows) = %d, want %d", tc.name, len(gotRows), len(tc.wantRows))
			continue
		}
		for i, row := range gotRows {
			if !reflect.DeepEqual(row, tc.wantRows[i]) {
				t.Errorf("[%s] Row[%d] = %v, want %v", tc.name, i, row, tc.wantRows[i])
			}
		}
	}
}
