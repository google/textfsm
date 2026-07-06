// Package clitable reads CLI output and parses it into tabular format using TextFSM templates and index files.
package clitable

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"github.com/google/textfsm/go/textfsm"
	"github.com/google/textfsm/go/texttable"
)

var (
	completionRe = regexp.MustCompile(`\[\[.+?\]\]`)
	indexCache   = make(map[string]*IndexTable)
	cacheLock    sync.Mutex
)

// IndexEntry represents a compiled row in the index table.
type IndexEntry struct {
	Template  string
	Compiled  map[string]*regexp.Regexp
	RawValues map[string]string
	RowNum    int
}

// IndexTable reads and stores template index mappings.
type IndexTable struct {
	Index    *texttable.Table
	Entries  []*IndexEntry
	FilePath string
}

// NewIndexTable reads an index file and compiles regexes for each field.
func NewIndexTable(filePath string) (*IndexTable, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open index file %s: %v", filePath, err)
	}
	defer f.Close()

	return NewIndexTableFromReader(f, filePath)
}

// NewIndexTableFromReader creates an IndexTable from an io.Reader.
func NewIndexTableFromReader(r io.Reader, filePath string) (*IndexTable, error) {
	tbl := texttable.NewTable()
	if err := tbl.CsvToTable(r); err != nil {
		return nil, fmt.Errorf("failed to parse index CSV: %v", err)
	}

	hasTemplate := false
	for _, col := range tbl.Header {
		if col == "Template" {
			hasTemplate = true
			break
		}
	}
	if !hasTemplate {
		return nil, fmt.Errorf("index file does not have 'Template' column")
	}

	it := &IndexTable{
		Index:    tbl,
		FilePath: filePath,
	}

	for _, row := range tbl.Rows {
		entry := &IndexEntry{
			Compiled:  make(map[string]*regexp.Regexp),
			RawValues: row.Map(),
			RowNum:    row.RowNum,
		}

		for _, col := range tbl.Header {
			val, _ := row.Get(col)
			if col == "Command" {
				val = expandCompletion(val)
			}
			if col == "Template" {
				entry.Template = val
			} else if val != "" {
				re, err := regexp.Compile(val)
				if err != nil {
					return nil, fmt.Errorf("row %d col %s invalid regex %q: %v", row.RowNum, col, val, err)
				}
				entry.Compiled[col] = re
			}
		}
		it.Entries = append(it.Entries, entry)
	}

	return it, nil
}

// GetRowMatch returns the matching IndexEntry for the given attributes.
func (it *IndexTable) GetRowMatch(attributes map[string]string) *IndexEntry {
	for _, entry := range it.Entries {
		match := true
		for k, attrVal := range attributes {
			re, ok := entry.Compiled[k]
			if ok && re != nil {
				loc := re.FindStringIndex(attrVal)
				if loc == nil || loc[0] != 0 {
					match = false
					break
				}
			}
		}
		if match {
			return entry
		}
	}
	return nil
}

func expandCompletion(val string) string {
	return completionRe.ReplaceAllStringFunc(val, func(m string) string {
		word := m[2 : len(m)-2]
		if len(word) == 0 {
			return ""
		}
		var sb strings.Builder
		sb.WriteString("(")
		for i := 0; i < len(word); i++ {
			if i > 0 {
				sb.WriteString("(")
			}
			sb.WriteByte(word[i])
		}
		for i := 0; i < len(word); i++ {
			sb.WriteString(")?")
		}
		return sb.String()
	})
}

// CliTable reads CLI output and parses it into tabular format using an index table and TextFSM.
type CliTable struct {
	*texttable.Table
	Raw         string
	IndexFile   string
	TemplateDir string
	Index       *IndexTable
	keys        map[string]bool
}

// NewCliTable creates a new CliTable.
func NewCliTable(indexFile, templateDir string) (*CliTable, error) {
	ct := &CliTable{
		Table:       texttable.NewTable(),
		IndexFile:   indexFile,
		TemplateDir: templateDir,
		keys:        make(map[string]bool),
	}
	if indexFile != "" && templateDir != "" {
		if err := ct.ReadIndex(indexFile); err != nil {
			return nil, err
		}
	}
	return ct, nil
}

// ReadIndex reads and caches the template index file.
func (ct *CliTable) ReadIndex(indexFile string) error {
	if indexFile != "" {
		ct.IndexFile = indexFile
	}
	fullPath := filepath.Join(ct.TemplateDir, ct.IndexFile)

	cacheLock.Lock()
	defer cacheLock.Unlock()

	if idx, ok := indexCache[fullPath]; ok {
		ct.Index = idx
		return nil
	}

	idx, err := NewIndexTable(fullPath)
	if err != nil {
		return err
	}
	indexCache[fullPath] = idx
	ct.Index = idx
	return nil
}

// ParseCmd creates a texttable of values from command input string and matching attributes.
func (ct *CliTable) ParseCmd(cmdInput string, attributes map[string]string, templates string) error {
	ct.Raw = cmdInput

	if templates == "" {
		if ct.Index == nil {
			return fmt.Errorf("no index table loaded and no templates specified")
		}
		entry := ct.Index.GetRowMatch(attributes)
		if entry == nil {
			return fmt.Errorf("no template found for attributes: %v", attributes)
		}
		templates = entry.Template
	}

	tmpltNames := strings.Split(templates, ":")
	if len(tmpltNames) == 0 {
		return fmt.Errorf("empty template list")
	}

	ct.Reset()
	ct.keys = make(map[string]bool)

	// Parse first template
	firstFile := filepath.Join(ct.TemplateDir, tmpltNames[0])
	f, err := os.Open(firstFile)
	if err != nil {
		return fmt.Errorf("failed to open template %s: %v", firstFile, err)
	}
	defer f.Close()

	fsm, err := textfsm.NewFSM(f)
	if err != nil {
		return fmt.Errorf("failed to parse template %s: %v", firstFile, err)
	}

	for _, k := range fsm.GetValuesByAttrib("Key") {
		ct.keys[k] = true
	}

	ct.SetHeader(fsm.Header)
	records, err := fsm.ParseText(cmdInput, true)
	if err != nil {
		return err
	}

	// records[0] is header, rows start at 1
	for i := 1; i < len(records); i++ {
		if err := ct.Append(records[i]); err != nil {
			return err
		}
	}

	// Parse additional templates and extend
	for _, tmpltName := range tmpltNames[1:] {
		nextFile := filepath.Join(ct.TemplateDir, tmpltName)
		nf, err := os.Open(nextFile)
		if err != nil {
			return fmt.Errorf("failed to open additional template %s: %v", nextFile, err)
		}
		nextFSM, err := textfsm.NewFSM(nf)
		nf.Close()
		if err != nil {
			return fmt.Errorf("failed to parse additional template %s: %v", nextFile, err)
		}

		nextTable := texttable.NewTable()
		nextTable.SetHeader(nextFSM.Header)
		nextRecords, err := nextFSM.ParseText(cmdInput, true)
		if err != nil {
			return err
		}
		for i := 1; i < len(nextRecords); i++ {
			_ = nextTable.Append(nextRecords[i])
		}

		var keyList []string
		for k := range ct.keys {
			keyList = append(keyList, k)
		}
		if err := ct.Extend(nextTable, keyList); err != nil {
			return fmt.Errorf("failed to extend table with %s: %v", tmpltName, err)
		}
	}

	return nil
}

// AddKeys marks additional columns as being part of the superkey.
func (ct *CliTable) AddKeys(keyList []string) error {
	for _, k := range keyList {
		found := false
		for _, h := range ct.Header {
			if h == k {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("key %q not found in table header", k)
		}
		ct.keys[k] = true
	}
	return nil
}

// SuperKey returns the list of column names that constitute the superkey.
func (ct *CliTable) SuperKey() []string {
	var sk []string
	for _, h := range ct.Header {
		if ct.keys[h] {
			sk = append(sk, h)
		}
	}
	return sk
}
