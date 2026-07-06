// Command textfsm validates templates and parses CLI text via command line.
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/google/textfsm/go/textfsm"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("textfsm", flag.ContinueOnError)
	fs.SetOutput(stderr)
	help := fs.Bool("help", false, "show help")
	h := fs.Bool("h", false, "show help")

	if err := fs.Parse(args); err != nil {
		fmt.Fprintf(stderr, "For help use --help\n")
		return 2
	}

	if *help || *h {
		printHelp(stdout)
		return 0
	}

	posArgs := fs.Args()
	if len(posArgs) == 0 || len(posArgs) > 3 {
		fmt.Fprintf(stderr, "Invalid arguments.\nFor help use --help\n")
		return 2
	}

	tmplFile, err := os.Open(posArgs[0])
	if err != nil {
		fmt.Fprintf(stderr, "Error opening template: %v\n", err)
		return 2
	}
	defer tmplFile.Close()

	fsm, err := textfsm.NewFSM(tmplFile)
	if err != nil {
		fmt.Fprintf(stderr, "Error parsing template: %v\n", err)
		return 2
	}

	fmt.Fprintf(stdout, "FSM Template:\n%s\n", fsm.String())

	if len(posArgs) == 1 {
		return 0
	}

	inputBytes, err := os.ReadFile(posArgs[1])
	if err != nil {
		fmt.Fprintf(stderr, "Error reading input file: %v\n", err)
		return 2
	}

	table, err := fsm.ParseText(string(inputBytes), true)
	if err != nil {
		fmt.Fprintf(stderr, "Error executing FSM: %v\n", err)
		return 2
	}

	fmt.Fprintf(stdout, "FSM Table:\n")
	var sb strings.Builder
	for _, row := range table {
		sb.WriteString(formatSlice(row))
		sb.WriteString("\n")
	}
	resultStr := sb.String()
	fmt.Fprint(stdout, resultStr)

	if len(posArgs) > 2 {
		refBytes, err := os.ReadFile(posArgs[2])
		if err != nil {
			fmt.Fprintf(stderr, "Error reading reference file: %v\n", err)
			return 2
		}
		if string(refBytes) != resultStr {
			fmt.Fprintf(stdout, "Data mis-match!\n")
			return 1
		}
		fmt.Fprintf(stdout, "Data match!\n")
	}

	return 0
}

func formatSlice(row []interface{}) string {
	var parts []string
	for _, item := range row {
		if s, ok := item.(string); ok {
			parts = append(parts, fmt.Sprintf("%q", s))
		} else {
			parts = append(parts, fmt.Sprintf("%v", item))
		}
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func printHelp(w io.Writer) {
	fmt.Fprintf(w, "textfsm [--help] template [input_file [output_file]]\n\n")
	fmt.Fprintf(w, "Validate text parsed with FSM or validate an FSM via command line.\n")
}
