// Package texttable represents and manipulates tabular text data.
package texttable

import (
	"encoding/csv"
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/google/textfsm/go/terminal"
)

// Row represents a row of tabular data with header mappings.
type Row struct {
	Header []string
	Values []string
	RowNum int
	Table  *Table
	Color  []string
	index  map[string]int
}

// NewRow creates a new Row with the given header and values.
func NewRow(header, values []string) (*Row, error) {
	if len(header) != len(values) {
		return nil, fmt.Errorf("header length (%d) does not match values length (%d)", len(header), len(values))
	}
	r := &Row{
		Header: append([]string(nil), header...),
		Values: append([]string(nil), values...),
		index:  make(map[string]int, len(header)),
	}
	r.buildIndex()
	return r, nil
}

func (r *Row) buildIndex() {
	r.index = make(map[string]int, len(r.Header))
	for i, col := range r.Header {
		r.index[col] = i
	}
}

// Get retrieves a value by column name. Returns empty string and false if not found.
func (r *Row) Get(col string) (string, bool) {
	idx, ok := r.index[col]
	if !ok || idx >= len(r.Values) {
		return "", false
	}
	return r.Values[idx], true
}

// Set sets a value by column name. If column does not exist, it appends it to the header and values.
func (r *Row) Set(col, val string) {
	idx, ok := r.index[col]
	if ok && idx < len(r.Values) {
		r.Values[idx] = val
		return
	}
	r.Header = append(r.Header, col)
	r.Values = append(r.Values, val)
	r.buildIndex()
	if r.Table != nil && len(r.Header) > len(r.Table.Header) {
		r.Table.Header = append([]string(nil), r.Header...)
	}
}

// Map returns the row values as a map of column name to value.
func (r *Row) Map() map[string]string {
	m := make(map[string]string, len(r.Header))
	for i, col := range r.Header {
		if i < len(r.Values) {
			m[col] = r.Values[i]
		}
	}
	return m
}

// String returns a formatted string representation of the row.
func (r *Row) String() string {
	var sb strings.Builder
	for _, v := range r.Values {
		sb.WriteString(fmt.Sprintf("%12s  ", v))
	}
	sb.WriteString("\n")
	return sb.String()
}

// Table provides data methods on a tabular format.
type Table struct {
	Header    []string
	Rows      []*Row
	Separator string
}

// NewTable creates a new empty Table.
func NewTable() *Table {
	return &Table{
		Separator: ", ",
	}
}

// Reset clears all data rows from the table and resets the header.
func (t *Table) Reset() {
	t.Header = nil
	t.Rows = nil
}

// Size returns the number of data rows in the table.
func (t *Table) Size() int {
	return len(t.Rows)
}

// SetHeader sets the table header.
func (t *Table) SetHeader(header []string) {
	t.Header = append([]string(nil), header...)
}

// Append adds a new row to the table. Accepts *Row, []string, or map[string]string.
func (t *Table) Append(data interface{}) error {
	var newRow *Row
	var err error

	switch v := data.(type) {
	case *Row:
		if len(t.Header) != 0 && !equalSlices(t.Header, v.Header) {
			return fmt.Errorf("attempt to append row with mismatched header")
		}
		if len(t.Header) == 0 {
			t.SetHeader(v.Header)
		}
		newRow, err = NewRow(t.Header, v.Values)
	case []string:
		if len(t.Header) == 0 {
			return fmt.Errorf("cannot append slice to table without header")
		}
		if len(v) != len(t.Header) {
			return fmt.Errorf("slice length (%d) does not match header length (%d)", len(v), len(t.Header))
		}
		newRow, err = NewRow(t.Header, v)
	case []interface{}:
		if len(t.Header) == 0 {
			return fmt.Errorf("cannot append slice to table without header")
		}
		if len(v) != len(t.Header) {
			return fmt.Errorf("slice length (%d) does not match header length (%d)", len(v), len(t.Header))
		}
		vals := make([]string, len(v))
		for i, item := range v {
			if item == nil {
				vals[i] = ""
			} else if s, ok := item.(string); ok {
				vals[i] = s
			} else {
				vals[i] = fmt.Sprintf("%v", item)
			}
		}
		newRow, err = NewRow(t.Header, vals)
	case map[string]string:
		if len(t.Header) == 0 {
			return fmt.Errorf("cannot append map to table without header")
		}
		vals := make([]string, len(t.Header))
		for i, col := range t.Header {
			val, ok := v[col]
			if !ok {
				return fmt.Errorf("map missing required column: %s", col)
			}
			vals[i] = val
		}
		newRow, err = NewRow(t.Header, vals)
	default:
		return fmt.Errorf("unsupported type for Append: %T", data)
	}

	if err != nil {
		return err
	}

	newRow.RowNum = len(t.Rows) + 1
	newRow.Table = t
	t.Rows = append(t.Rows, newRow)
	return nil
}

// CsvToTable populates the table from a CSV reader. The first row is treated as the header.
func (t *Table) CsvToTable(r io.Reader) error {
	t.Reset()
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1 // Allow variable fields, or let header dictate

	records, err := cr.ReadAll()
	if err != nil {
		return err
	}
	if len(records) == 0 {
		return nil
	}

	t.SetHeader(records[0])
	for i := 1; i < len(records); i++ {
		// Pad or trim record to match header length if needed
		rec := records[i]
		if len(rec) < len(t.Header) {
			padded := make([]string, len(t.Header))
			copy(padded, rec)
			rec = padded
		} else if len(rec) > len(t.Header) {
			rec = rec[:len(t.Header)]
		}
		if err := t.Append(rec); err != nil {
			return fmt.Errorf("row %d: %v", i, err)
		}
	}
	return nil
}

// Filter returns a new Table containing only rows for which fn returns true.
func (t *Table) Filter(fn func(r *Row) bool) *Table {
	if fn == nil {
		fn = func(r *Row) bool {
			for _, v := range r.Values {
				if v != "" {
					return true
				}
			}
			return false
		}
	}

	nt := NewTable()
	nt.Separator = t.Separator
	nt.SetHeader(t.Header)
	for _, r := range t.Rows {
		if fn(r) {
			_ = nt.Append(r.Values)
		}
	}
	return nt
}

// Map returns a new Table where each row has been transformed by fn.
func (t *Table) Map(fn func(r *Row) *Row) *Table {
	nt := NewTable()
	nt.Separator = t.Separator
	nt.SetHeader(t.Header)
	for _, r := range t.Rows {
		nr := fn(r)
		if nr != nil {
			_ = nt.Append(nr.Values)
		}
	}
	return nt
}

// Sort sorts the rows using a custom comparison function.
func (t *Table) Sort(less func(r1, r2 *Row) bool) {
	sort.SliceStable(t.Rows, func(i, j int) bool {
		return less(t.Rows[i], t.Rows[j])
	})
	for i, r := range t.Rows {
		r.RowNum = i + 1
	}
}

// SortByKey sorts the rows by comparing values generated by keyFn.
func (t *Table) SortByKey(keyFn func(r *Row) []string, reverse bool) {
	t.Sort(func(r1, r2 *Row) bool {
		k1 := keyFn(r1)
		k2 := keyFn(r2)
		minLen := len(k1)
		if len(k2) < minLen {
			minLen = len(k2)
		}
		for i := 0; i < minLen; i++ {
			if k1[i] != k2[i] {
				if reverse {
					return k1[i] > k2[i]
				}
				return k1[i] < k2[i]
			}
		}
		if reverse {
			return len(k1) > len(k2)
		}
		return len(k1) < len(k2)
	})
}

// Extend merges new columns from another table into this table.
func (t *Table) Extend(other *Table, keys []string) error {
	if len(keys) > 0 {
		for _, k := range keys {
			if !containsString(t.Header, k) {
				return fmt.Errorf("unknown key: %s", k)
			}
		}
	}

	var extendWith []string
	for _, col := range other.Header {
		if !containsString(t.Header, col) {
			extendWith = append(extendWith, col)
		}
	}
	if len(extendWith) == 0 {
		return nil
	}

	for _, col := range extendWith {
		t.Header = append(t.Header, col)
	}

	if len(keys) == 0 {
		for i, r1 := range t.Rows {
			for _, col := range extendWith {
				val := ""
				if i < len(other.Rows) {
					if v, ok := other.Rows[i].Get(col); ok {
						val = v
					}
				}
				r1.Set(col, val)
			}
		}
		return nil
	}

	for _, r1 := range t.Rows {
		for _, r2 := range other.Rows {
			match := true
			for _, k := range keys {
				v1, _ := r1.Get(k)
				v2, _ := r2.Get(k)
				if v1 != v2 {
					match = false
					break
				}
			}
			if match {
				for _, col := range extendWith {
					val, _ := r2.Get(col)
					r1.Set(col, val)
				}
				break
			}
		}
		// Ensure column exists even if no match found
		for _, col := range extendWith {
			if _, ok := r1.Get(col); !ok {
				r1.Set(col, "")
			}
		}
	}
	return nil
}

// Remove deletes a row by its 1-indexed row number.
func (t *Table) Remove(rowNum int) error {
	if rowNum <= 0 || rowNum > len(t.Rows) {
		return fmt.Errorf("attempt to remove non-existent row %d", rowNum)
	}
	idx := rowNum - 1
	t.Rows = append(t.Rows[:idx], t.Rows[idx+1:]...)
	for i := idx; i < len(t.Rows); i++ {
		t.Rows[i].RowNum = i + 1
	}
	return nil
}

// String returns the CSV/separated string representation of the table.
func (t *Table) String() string {
	var sb strings.Builder
	if len(t.Header) > 0 {
		sb.WriteString(strings.Join(t.Header, t.Separator))
		sb.WriteString("\n")
	}
	for _, r := range t.Rows {
		sb.WriteString(strings.Join(r.Values, t.Separator))
		sb.WriteString("\n")
	}
	return sb.String()
}

// FormattedTable returns a whitespace-padded, formatted string representation of the table.
func (t *Table) FormattedTable(width int, forceDisplay bool, columns []string) (string, error) {
	if width <= 0 {
		width = 80
	}
	cols := columns
	if len(cols) == 0 {
		cols = t.Header
	}

	colWidths := make(map[string]int, len(cols))
	for _, col := range cols {
		colWidths[col] = len(col)
	}

	for _, r := range t.Rows {
		for _, col := range cols {
			val, _ := r.Get(col)
			stripped := terminal.StripAnsiText(val)
			if len(stripped) > colWidths[col] {
				colWidths[col] = len(stripped)
			}
		}
	}

	totalWidth := 0
	for _, col := range cols {
		colWidths[col] += 2 // 1 space padding on each side
		totalWidth += colWidths[col]
	}

	if totalWidth > width && !forceDisplay {
		return "", fmt.Errorf("width %d too narrow to display table (minimum %d)", width, totalWidth)
	}

	var sb strings.Builder
	// Header
	for _, col := range cols {
		sb.WriteString(fmt.Sprintf(" %-*s", colWidths[col]-1, col))
	}
	sb.WriteString("\n")

	// Rows
	for _, r := range t.Rows {
		for _, col := range cols {
			val, _ := r.Get(col)
			strippedLen := len(terminal.StripAnsiText(val))
			ansiAdds := len(val) - strippedLen
			sb.WriteString(fmt.Sprintf(" %-*s", colWidths[col]-1+ansiAdds, val))
		}
		sb.WriteString("\n")
	}

	return sb.String(), nil
}

func equalSlices(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func containsString(slice []string, val string) bool {
	for _, item := range slice {
		if item == val {
			return true
		}
	}
	return false
}
