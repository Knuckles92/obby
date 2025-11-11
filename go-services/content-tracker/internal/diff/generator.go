package diff

import (
	"strings"

	"github.com/sergi/go-diff/diffmatchpatch"
)

// Generator generates unified diffs
type Generator struct {
	dmp *diffmatchpatch.DiffMatchPatch
}

// NewDiffGenerator creates a new diff generator
func NewDiffGenerator() *Generator {
	return &Generator{
		dmp: diffmatchpatch.New(),
	}
}

// GenerateUnifiedDiff is a package-level function for convenience
func GenerateUnifiedDiff(oldContent, newContent, oldPath, newPath string) (string, int, int, error) {
	gen := NewDiffGenerator()
	return gen.GenerateUnifiedDiff(oldContent, newContent, oldPath, newPath)
}

// GenerateUnifiedDiff generates a unified diff between old and new content
func (dg *Generator) GenerateUnifiedDiff(oldContent, newContent, oldPath, newPath string) (string, int, int, error) {
	diffs := dg.dmp.DiffMain(oldContent, newContent, false)

	// Convert to unified diff format
	patches := dg.dmp.PatchMake(oldContent, diffs)
	diffText := dg.dmp.PatchToText(patches)

	// Calculate lines added/removed
	linesAdded := 0
	linesRemoved := 0

	oldLines := strings.Split(oldContent, "\n")
	newLines := strings.Split(newContent, "\n")

	// Simple line count (can be improved with proper diff analysis)
	if len(newLines) > len(oldLines) {
		linesAdded = len(newLines) - len(oldLines)
	} else {
		linesRemoved = len(oldLines) - len(newLines)
	}

	return diffText, linesAdded, linesRemoved, nil
}

