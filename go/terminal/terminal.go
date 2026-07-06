// Package terminal provides simple terminal related routines such as ANSI/SGR
// escape sequence manipulation and line wrapping.
package terminal

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// SGR maps Select Graphic Rendition names to their ANSI code values.
var SGR = map[string]int{
	"reset":         0,
	"bold":          1,
	"underline":     4,
	"blink":         5,
	"negative":      7,
	"underline_off": 24,
	"blink_off":     25,
	"positive":      27,
	"black":         30,
	"red":           31,
	"green":         32,
	"yellow":        33,
	"blue":          34,
	"magenta":       35,
	"cyan":          36,
	"white":         37,
	"fg_reset":      39,
	"bg_black":      40,
	"bg_red":        41,
	"bg_green":      42,
	"bg_yellow":     43,
	"bg_blue":       44,
	"bg_magenta":    45,
	"bg_cyan":       46,
	"bg_white":      47,
	"bg_reset":      49,
}

// FGColorWords maps familiar descriptive color words to SGR sequence lists.
var FGColorWords = map[string][]string{
	"black":        {"black"},
	"dark_gray":    {"bold", "black"},
	"blue":         {"blue"},
	"light_blue":   {"bold", "blue"},
	"green":        {"green"},
	"light_green":  {"bold", "green"},
	"cyan":         {"cyan"},
	"light_cyan":   {"bold", "cyan"},
	"red":          {"red"},
	"light_red":    {"bold", "red"},
	"purple":       {"magenta"},
	"light_purple": {"bold", "magenta"},
	"brown":        {"yellow"},
	"yellow":       {"bold", "yellow"},
	"light_gray":   {"white"},
	"white":        {"bold", "white"},
}

// BGColorWords maps familiar descriptive background color words to SGR sequence lists.
var BGColorWords = map[string][]string{
	"black":      {"bg_black"},
	"red":        {"bg_red"},
	"green":      {"bg_green"},
	"yellow":     {"bg_yellow"},
	"dark_blue":  {"bg_blue"},
	"purple":     {"bg_magenta"},
	"light_blue": {"bg_cyan"},
	"grey":       {"bg_white"},
}

const (
	// AnsiStart is the character inserted at start of ANSI strings for readline hinting.
	AnsiStart = "\001"
	// AnsiEnd is the character inserted at end of ANSI strings for readline hinting.
	AnsiEnd = "\002"
)

// sgrRe matches ANSI/SGR escape sequences, optionally enclosed in AnsiStart/AnsiEnd.
var sgrRe = regexp.MustCompile(`(` + AnsiStart + `?\033\[\d+(?:;\d+)*m` + AnsiEnd + `?)`)

// AnsiCmd takes a list of SGR values and formats them as an ANSI escape sequence.
func AnsiCmd(commandList []string) (string, error) {
	if len(commandList) == 0 {
		return "", nil
	}
	var codes []string
	for _, sgr := range commandList {
		val, ok := SGR[strings.ToLower(sgr)]
		if !ok {
			return "", fmt.Errorf("invalid or unsupported SGR name: %s", sgr)
		}
		codes = append(codes, strconv.Itoa(val))
	}
	return fmt.Sprintf("\033[%sm", strings.Join(codes, ";")), nil
}

// AnsiText wraps text in ANSI/SGR escape codes.
func AnsiText(text string, commandList []string, reset bool) (string, error) {
	if len(commandList) == 0 {
		commandList = []string{"reset"}
	}
	prefix, err := AnsiCmd(commandList)
	if err != nil {
		return "", err
	}
	if reset {
		suffix, _ := AnsiCmd([]string{"reset"})
		return prefix + text + suffix, nil
	}
	return prefix + text, nil
}

// StripAnsiText strips ANSI/SGR escape sequences from text.
func StripAnsiText(text string) string {
	return sgrRe.ReplaceAllString(text, "")
}

// EncloseAnsiText encloses ANSI/SGR escape sequences with AnsiStart and AnsiEnd.
func EncloseAnsiText(text string) string {
	return sgrRe.ReplaceAllStringFunc(text, func(match string) string {
		// If already enclosed, strip first to avoid double enclosing
		clean := strings.TrimPrefix(match, AnsiStart)
		clean = strings.TrimSuffix(clean, AnsiEnd)
		return AnsiStart + clean + AnsiEnd
	})
}

// LineWrap breaks text to fit terminal/screen width, optionally ignoring SGR sequences in length calculation.
// If width <= 0, it defaults to 80 columns.
func LineWrap(text string, omitSGR bool, width int) string {
	if width <= 0 {
		width = 80
	}

	lines := strings.Split(text, "\n")
	var multiline []string

	for _, line := range lines {
		if line == "" {
			multiline = append(multiline, "")
			continue
		}

		for (omitSGR && len(StripAnsiText(line)) > width) || (!omitSGR && len(line) > width) {
			if !omitSGR {
				multiline = append(multiline, line[:width])
				line = line[width:]
			} else {
				wrapped, rem := splitWithSGR(line, width)
				multiline = append(multiline, wrapped)
				line = rem
				if line == "" {
					break
				}
			}
		}
		if line != "" {
			multiline = append(multiline, line)
		}
	}
	return strings.Join(multiline, "\n")
}

func splitWithSGR(line string, width int) (string, string) {
	// Find all SGR sequences and text between them
	locs := sgrRe.FindAllStringIndex(line, -1)
	if len(locs) == 0 {
		if len(line) <= width {
			return line, ""
		}
		return line[:width], line[width:]
	}

	var wrapped strings.Builder
	currLen := 0
	lastIdx := 0

	for _, loc := range locs {
		// Text before this SGR token
		textPart := line[lastIdx:loc[0]]
		if currLen+len(textPart) <= width {
			wrapped.WriteString(textPart)
			currLen += len(textPart)
		} else {
			// Split in textPart
			remWidth := width - currLen
			wrapped.WriteString(textPart[:remWidth])
			remLine := textPart[remWidth:] + line[loc[0]:]
			return wrapped.String(), remLine
		}

		// Append the SGR token itself (0 length contribution)
		sgrToken := line[loc[0]:loc[1]]
		wrapped.WriteString(sgrToken)
		lastIdx = loc[1]
	}

	// Remaining text after last SGR token
	remText := line[lastIdx:]
	if currLen+len(remText) <= width {
		wrapped.WriteString(remText)
		return wrapped.String(), ""
	}

	remWidth := width - currLen
	wrapped.WriteString(remText[:remWidth])
	return wrapped.String(), remText[remWidth:]
}
