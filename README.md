TextFSM
=======

Python module which implements a template based state machine for parsing
semi-formatted text. Originally developed to allow programmatic access to
information returned from the command line interface (CLI) of networking
devices.

The engine takes two inputs - a template file, and text input (such as command
responses from the CLI of a device) and returns a list of records that contains
the data parsed from the text.

A template file is needed for each uniquely structured text input. Some examples
are provided with the code and users are encouraged to develop their own.

By developing a pool of template files, scripts can call TextFSM to parse useful
information from a variety of sources. It is also possible to use different
templates on the same data in order to create different tables (or views).

TextFSM was developed internally at Google and released under the Apache 2.0
licence for the benefit of the wider community.

[**See documentation for more details.**](https://github.com/google/textfsm/wiki/TextFSM)

Go Version (Golang)
-------------------
An idiomatic Golang port of TextFSM is available in the `go/` directory, mirroring the core functionality of the Python library (`textfsm`, `clitable`, `texttable`, and `terminal`).

### Proposed Usage

To use the Go implementation as a library in your project:

```bash
go get github.com/google/textfsm/go@latest
```

Example usage in Go:

```go
package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/google/textfsm/go/textfsm"
)

func main() {
	tmpl := `Value Required Interface (\S+)
Value Status (up|down)

Start
  ^${Interface} is ${Status} -> Record
`
	fsm, err := textfsm.NewFSM(strings.NewReader(tmpl))
	if err != nil {
		panic(err)
	}

	input := "GigabitEthernet0/0 is up\nGigabitEthernet0/1 is down"
	records, err := fsm.ParseText(input, true)
	if err != nil {
		panic(err)
	}

	for _, row := range records {
		fmt.Printf("%v\n", row)
	}
}
```

A CLI utility mirroring `textfsm/parser.py` is also provided under `go/cmd/textfsm`:

```bash
go run ./go/cmd/textfsm <template_file> [input_file [reference_file]]
```

Before contributing
-------------------
If you are not a Google employee, our lawyers insist that you sign a Contributor
Licence Agreement (CLA).

If you are an individual writing original source code and you're sure you own
the intellectual property, then you'll need to sign an
[individual CLA](https://cla.developers.google.com/about/google-individual).
Individual CLAs can be signed electronically. If you work for a company that
wants to allow you to contribute your work, then you'll need to sign a
[corporate CLA](https://cla.developers.google.com/clas).
The Google CLA is based on Apache's. Note that unlike some projects
(notably GNU projects), we do not require a transfer of copyright. You still own
the patch.

Sadly, even the smallest patch needs a CLA.
