// fastscan is a small, dependency-free CSV pre-scanner.
//
// Pandas has to fully parse and type-infer a CSV before Data Detective's
// Python profiling engine can report anything. On large files that first
// pass can take seconds. fastscan gives the caller near-instant metadata
// (row/column counts, delimiter, file size) by streaming the file once with
// a buffered scanner, so the API can return a "quick" result immediately
// while the full statistical profile is computed.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
)

// maxLineSize bounds how long a single CSV line/cell can be before fastscan
// gives up, protecting against pathological/malicious input.
const maxLineSize = 10 * 1024 * 1024 // 10 MB per line

type quickScan struct {
	Rows       int     `json:"rows"`
	Columns    int     `json:"columns"`
	Delimiter  string  `json:"delimiter"`
	FileSizeKB float64 `json:"file_size_kb"`
	ScanMs     int64   `json:"scan_ms"`
}

// detectDelimiter picks the delimiter that splits the header line into the
// most fields, among the common candidates.
func detectDelimiter(headerLine string) string {
	candidates := []string{",", ";", "\t", "|"}
	best := ","
	bestCount := -1
	for _, d := range candidates {
		if c := strings.Count(headerLine, d); c > bestCount {
			bestCount = c
			best = d
		}
	}
	return best
}

func run(path string) (quickScan, error) {
	start := time.Now()

	f, err := os.Open(path)
	if err != nil {
		return quickScan{}, err
	}
	defer f.Close()

	info, err := f.Stat()
	if err != nil {
		return quickScan{}, err
	}

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 64*1024), maxLineSize)

	rows := 0
	columns := 0
	delimiter := ","
	header := true

	for scanner.Scan() {
		line := scanner.Text()
		if header {
			delimiter = detectDelimiter(line)
			columns = len(strings.Split(line, delimiter))
			header = false
			continue
		}
		if strings.TrimSpace(line) == "" {
			continue
		}
		rows++
	}
	if err := scanner.Err(); err != nil {
		return quickScan{}, err
	}

	return quickScan{
		Rows:       rows,
		Columns:    columns,
		Delimiter:  delimiter,
		FileSizeKB: float64(info.Size()) / 1024.0,
		ScanMs:     time.Since(start).Milliseconds(),
	}, nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: fastscan <path-to-csv>")
		os.Exit(1)
	}

	result, err := run(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "fastscan error:", err)
		os.Exit(1)
	}

	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		fmt.Fprintln(os.Stderr, "fastscan encode error:", err)
		os.Exit(1)
	}
}
