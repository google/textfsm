package texttable

import (
	"strings"
	"testing"
)

func TestTableAppend(t *testing.T) {
	tests := []struct {
		name     string
		header   []string
		appends  []interface{}
		wantSize int
		wantErr  bool
	}{
		{
			name:   "append slice to empty table with header",
			header: []string{"Name", "Age"},
			appends: []interface{}{
				[]string{"Alice", "30"},
				[]string{"Bob", "25"},
			},
			wantSize: 2,
			wantErr:  false,
		},
		{
			name:   "append map",
			header: []string{"City", "Country"},
			appends: []interface{}{
				map[string]string{"City": "Paris", "Country": "France"},
			},
			wantSize: 1,
			wantErr:  false,
		},
		{
			name:   "append mismatched slice length",
			header: []string{"A", "B"},
			appends: []interface{}{
				[]string{"OnlyOne"},
			},
			wantSize: 0,
			wantErr:  true,
		},
	}

	for _, tc := range tests {
		tbl := NewTable()
		if len(tc.header) > 0 {
			tbl.SetHeader(tc.header)
		}
		var err error
		for _, item := range tc.appends {
			err = tbl.Append(item)
			if err != nil {
				break
			}
		}
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] Append() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if !tc.wantErr && tbl.Size() != tc.wantSize {
			t.Errorf("[%s] Size() = %d, want %d", tc.name, tbl.Size(), tc.wantSize)
		}
	}
}

func TestCsvToTable(t *testing.T) {
	tests := []struct {
		name     string
		csvData  string
		wantHead []string
		wantRows [][]string
		wantErr  bool
	}{
		{
			name:     "simple csv",
			csvData:  "Col1,Col2\nVal1,Val2\nVal3,Val4",
			wantHead: []string{"Col1", "Col2"},
			wantRows: [][]string{
				{"Val1", "Val2"},
				{"Val3", "Val4"},
			},
			wantErr: false,
		},
		{
			name:     "csv with uneven rows",
			csvData:  "A,B,C\n1,2\n3,4,5,6",
			wantHead: []string{"A", "B", "C"},
			wantRows: [][]string{
				{"1", "2", ""},
				{"3", "4", "5"},
			},
			wantErr: false,
		},
	}

	for _, tc := range tests {
		tbl := NewTable()
		err := tbl.CsvToTable(strings.NewReader(tc.csvData))
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] CsvToTable() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if tc.wantErr {
			continue
		}
		if !equalSlices(tbl.Header, tc.wantHead) {
			t.Errorf("[%s] Header = %v, want %v", tc.name, tbl.Header, tc.wantHead)
		}
		if tbl.Size() != len(tc.wantRows) {
			t.Errorf("[%s] Size() = %d, want %d", tc.name, tbl.Size(), len(tc.wantRows))
			continue
		}
		for i, row := range tbl.Rows {
			if !equalSlices(row.Values, tc.wantRows[i]) {
				t.Errorf("[%s] Row[%d] = %v, want %v", tc.name, i, row.Values, tc.wantRows[i])
			}
		}
	}
}

func TestTableFilter(t *testing.T) {
	tests := []struct {
		name     string
		header   []string
		rows     [][]string
		filterFn func(r *Row) bool
		wantSize int
	}{
		{
			name:   "default filter removes empty rows",
			header: []string{"X"},
			rows: [][]string{
				{"hello"},
				{""},
				{"world"},
			},
			filterFn: nil,
			wantSize: 2,
		},
		{
			name:   "custom filter",
			header: []string{"Num"},
			rows: [][]string{
				{"10"},
				{"20"},
				{"30"},
			},
			filterFn: func(r *Row) bool {
				v, _ := r.Get("Num")
				return v == "20"
			},
			wantSize: 1,
		},
	}

	for _, tc := range tests {
		tbl := NewTable()
		tbl.SetHeader(tc.header)
		for _, r := range tc.rows {
			_ = tbl.Append(r)
		}
		filtered := tbl.Filter(tc.filterFn)
		if filtered.Size() != tc.wantSize {
			t.Errorf("[%s] Filter().Size() = %d, want %d", tc.name, filtered.Size(), tc.wantSize)
		}
	}
}

func TestTableSortByKey(t *testing.T) {
	tests := []struct {
		name    string
		header  []string
		rows    [][]string
		col     string
		reverse bool
		want    []string
	}{
		{
			name:    "ascending sort",
			header:  []string{"Letter"},
			rows:    [][]string{{"C"}, {"A"}, {"B"}},
			col:     "Letter",
			reverse: false,
			want:    []string{"A", "B", "C"},
		},
		{
			name:    "descending sort",
			header:  []string{"Letter"},
			rows:    [][]string{{"C"}, {"A"}, {"B"}},
			col:     "Letter",
			reverse: true,
			want:    []string{"C", "B", "A"},
		},
	}

	for _, tc := range tests {
		tbl := NewTable()
		tbl.SetHeader(tc.header)
		for _, r := range tc.rows {
			_ = tbl.Append(r)
		}
		tbl.SortByKey(func(r *Row) []string {
			v, _ := r.Get(tc.col)
			return []string{v}
		}, tc.reverse)

		var got []string
		for _, r := range tbl.Rows {
			v, _ := r.Get(tc.col)
			got = append(got, v)
		}
		if !equalSlices(got, tc.want) {
			t.Errorf("[%s] SortByKey() = %v, want %v", tc.name, got, tc.want)
		}
	}
}

func TestTableExtend(t *testing.T) {
	tests := []struct {
		name     string
		t1Head   []string
		t1Rows   [][]string
		t2Head   []string
		t2Rows   [][]string
		keys     []string
		wantHead []string
		wantRow0 map[string]string
	}{
		{
			name:     "extend without keys (positional)",
			t1Head:   []string{"ID", "Name"},
			t1Rows:   [][]string{{"1", "Alice"}},
			t2Head:   []string{"ID", "Role"},
			t2Rows:   [][]string{{"1", "Admin"}},
			keys:     nil,
			wantHead: []string{"ID", "Name", "Role"},
			wantRow0: map[string]string{"ID": "1", "Name": "Alice", "Role": "Admin"},
		},
		{
			name:     "extend with keys match",
			t1Head:   []string{"Host", "IP"},
			t1Rows:   [][]string{{"router1", "10.0.0.1"}, {"router2", "10.0.0.2"}},
			t2Head:   []string{"Host", "OS"},
			t2Rows:   [][]string{{"router2", "IOS"}, {"router1", "NXOS"}},
			keys:     []string{"Host"},
			wantHead: []string{"Host", "IP", "OS"},
			wantRow0: map[string]string{"Host": "router1", "IP": "10.0.0.1", "OS": "NXOS"},
		},
	}

	for _, tc := range tests {
		t1 := NewTable()
		t1.SetHeader(tc.t1Head)
		for _, r := range tc.t1Rows {
			_ = t1.Append(r)
		}

		t2 := NewTable()
		t2.SetHeader(tc.t2Head)
		for _, r := range tc.t2Rows {
			_ = t2.Append(r)
		}

		err := t1.Extend(t2, tc.keys)
		if err != nil {
			t.Errorf("[%s] Extend() unexpected error = %v", tc.name, err)
			continue
		}
		if !equalSlices(t1.Header, tc.wantHead) {
			t.Errorf("[%s] Header = %v, want %v", tc.name, t1.Header, tc.wantHead)
		}
		for k, wantVal := range tc.wantRow0 {
			gotVal, _ := t1.Rows[0].Get(k)
			if gotVal != wantVal {
				t.Errorf("[%s] Row[0].Get(%q) = %q, want %q", tc.name, k, gotVal, wantVal)
			}
		}
	}
}

func TestFormattedTable(t *testing.T) {
	tests := []struct {
		name       string
		header     []string
		rows       [][]string
		width      int
		wantSubstr string
		wantErr    bool
	}{
		{
			name:       "normal display",
			header:     []string{"Col1", "Col2"},
			rows:       [][]string{{"A", "B"}},
			width:      80,
			wantSubstr: "Col1",
			wantErr:    false,
		},
		{
			name:    "width too small without force",
			header:  []string{"VeryLongColumnHeader"},
			rows:    [][]string{{"Value"}},
			width:   5,
			wantErr: true,
		},
	}

	for _, tc := range tests {
		tbl := NewTable()
		tbl.SetHeader(tc.header)
		for _, r := range tc.rows {
			_ = tbl.Append(r)
		}
		got, err := tbl.FormattedTable(tc.width, false, nil)
		if (err != nil) != tc.wantErr {
			t.Errorf("[%s] FormattedTable() error = %v, wantErr %v", tc.name, err, tc.wantErr)
			continue
		}
		if !tc.wantErr && !strings.Contains(got, tc.wantSubstr) {
			t.Errorf("[%s] FormattedTable() = %q, want substring %q", tc.name, got, tc.wantSubstr)
		}
	}
}
