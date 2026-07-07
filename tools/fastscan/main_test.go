package main

import (
	"os"
	"path/filepath"
	"testing"
)

func writeTempCSV(t *testing.T, content string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "sample.csv")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("failed to write temp csv: %v", err)
	}
	return path
}

func TestRunBasicCSV(t *testing.T) {
	path := writeTempCSV(t, "a,b,c\n1,2,3\n4,5,6\n\n")

	result, err := run(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Rows != 2 {
		t.Errorf("expected 2 rows, got %d", result.Rows)
	}
	if result.Columns != 3 {
		t.Errorf("expected 3 columns, got %d", result.Columns)
	}
	if result.Delimiter != "," {
		t.Errorf("expected ',' delimiter, got %q", result.Delimiter)
	}
}

func TestDetectDelimiterSemicolon(t *testing.T) {
	path := writeTempCSV(t, "a;b;c\n1;2;3\n")

	result, err := run(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Delimiter != ";" {
		t.Errorf("expected ';' delimiter, got %q", result.Delimiter)
	}
	if result.Columns != 3 {
		t.Errorf("expected 3 columns, got %d", result.Columns)
	}
}

func TestRunMissingFile(t *testing.T) {
	if _, err := run("/does/not/exist.csv"); err == nil {
		t.Error("expected error for missing file, got nil")
	}
}
