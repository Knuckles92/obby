#!/usr/bin/env python3
"""
Test script to analyze when difflib.unified_diff produces +0/-0 results.

This script tests the same logic used in ContentDiffModel.generate_diff() to understand
edge cases that result in zero added and zero removed lines.
"""

import difflib
from typing import Tuple, List


def generate_diff(old_content: str, new_content: str) -> Tuple[str, int, int]:
    """
    Generate diff content and calculate line changes.
    This is identical to ContentDiffModel.generate_diff() method.
    """
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []
    
    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile='old', tofile='new',
        lineterm=''
    ))
    diff_content = '\n'.join(diff_lines)
    
    # Count added/removed lines
    lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
    
    return diff_content, lines_added, lines_removed


def test_scenario(name: str, old_content: str, new_content: str) -> dict:
    """Test a single diff scenario and return results."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    diff_content, lines_added, lines_removed = generate_diff(old_content, new_content)
    
    print(f"Old content: {repr(old_content)}")
    print(f"New content: {repr(new_content)}")
    print(f"Lines added: {lines_added}")
    print(f"Lines removed: {lines_removed}")
    print(f"Diff content length: {len(diff_content)}")
    
    if diff_content:
        print(f"Diff content:\n{diff_content}")
    else:
        print("Diff content: <empty>")
    
    # Analyze diff lines for debugging
    if diff_content:
        diff_lines = diff_content.split('\n')
        print(f"\nDiff line analysis:")
        for i, line in enumerate(diff_lines):
            if line.startswith('+++') or line.startswith('---'):
                print(f"  {i}: HEADER: {repr(line)}")
            elif line.startswith('+'):
                print(f"  {i}: ADDED: {repr(line)}")
            elif line.startswith('-'):
                print(f"  {i}: REMOVED: {repr(line)}")
            elif line.startswith('@@'):
                print(f"  {i}: CONTEXT: {repr(line)}")
            else:
                print(f"  {i}: OTHER: {repr(line)}")
    
    is_zero_zero = lines_added == 0 and lines_removed == 0
    print(f"\nResult: +{lines_added}/-{lines_removed} ({'ZERO-ZERO' if is_zero_zero else 'NON-ZERO'})")
    
    return {
        'name': name,
        'old_content': old_content,
        'new_content': new_content,
        'lines_added': lines_added,
        'lines_removed': lines_removed,
        'diff_content': diff_content,
        'is_zero_zero': is_zero_zero
    }


def main():
    """Run comprehensive diff analysis tests."""
    print("DIFF ANALYSIS: Testing scenarios that might produce +0/-0 results")
    print("This uses the same logic as ContentDiffModel.generate_diff()")
    
    test_results = []
    
    # Test Case 1: Empty content vs empty content
    test_results.append(test_scenario(
        "Empty vs Empty",
        "", ""
    ))
    
    # Test Case 2: None vs None (handled as empty)
    test_results.append(test_scenario(
        "None vs None (as empty strings)",
        "", ""
    ))
    
    # Test Case 3: Identical single line content
    test_results.append(test_scenario(
        "Identical single line",
        "hello world", "hello world"
    ))
    
    # Test Case 4: Identical multi-line content
    test_results.append(test_scenario(
        "Identical multi-line",
        "line 1\nline 2\nline 3", "line 1\nline 2\nline 3"
    ))
    
    # Test Case 5: Empty vs non-empty
    test_results.append(test_scenario(
        "Empty vs Non-empty",
        "", "hello world"
    ))
    
    # Test Case 6: Non-empty vs empty
    test_results.append(test_scenario(
        "Non-empty vs Empty",
        "hello world", ""
    ))
    
    # Test Case 7: Whitespace only content
    test_results.append(test_scenario(
        "Whitespace only (identical)",
        "   \n  \n   ", "   \n  \n   "
    ))
    
    # Test Case 8: Different whitespace
    test_results.append(test_scenario(
        "Different whitespace",
        "   \n  \n   ", "  \n   \n  "
    ))
    
    # Test Case 9: Newline differences
    test_results.append(test_scenario(
        "Newline at end vs no newline",
        "hello", "hello\n"
    ))
    
    # Test Case 10: Multiple newlines
    test_results.append(test_scenario(
        "Single vs double newline",
        "hello\n", "hello\n\n"
    ))
    
    # Test Case 11: Content with only newlines
    test_results.append(test_scenario(
        "Only newlines (identical)",
        "\n\n\n", "\n\n\n"
    ))
    
    # Test Case 12: Different newline counts
    test_results.append(test_scenario(
        "Different newline counts",
        "\n\n", "\n\n\n"
    ))
    
    # Test Case 13: Invisible characters
    test_results.append(test_scenario(
        "Tabs vs spaces",
        "hello\tworld", "hello    world"
    ))
    
    # Test Case 14: Windows vs Unix line endings
    test_results.append(test_scenario(
        "Windows vs Unix line endings",
        "line1\r\nline2\r\n", "line1\nline2\n"
    ))
    
    # Test Case 15: Content replacement (same length)
    test_results.append(test_scenario(
        "Content replacement (same length)",
        "aaaa", "bbbb"
    ))
    
    # Test Case 16: Case change only
    test_results.append(test_scenario(
        "Case change only",
        "Hello World", "hello world"
    ))
    
    # Test Case 17: Leading/trailing whitespace
    test_results.append(test_scenario(
        "Leading/trailing whitespace",
        "hello", " hello "
    ))
    
    # Summary analysis
    print(f"\n{'='*80}")
    print("SUMMARY ANALYSIS")
    print(f"{'='*80}")
    
    zero_zero_cases = [r for r in test_results if r['is_zero_zero']]
    non_zero_cases = [r for r in test_results if not r['is_zero_zero']]
    
    print(f"Total test cases: {len(test_results)}")
    print(f"Zero-zero cases (+0/-0): {len(zero_zero_cases)}")
    print(f"Non-zero cases: {len(non_zero_cases)}")
    
    if zero_zero_cases:
        print(f"\nCases that produce +0/-0:")
        for case in zero_zero_cases:
            print(f"  - {case['name']}")
            print(f"    Old: {repr(case['old_content'])}")
            print(f"    New: {repr(case['new_content'])}")
            if case['diff_content']:
                print(f"    Diff length: {len(case['diff_content'])} chars")
            else:
                print(f"    Diff: <empty>")
    
    print(f"\n{'='*80}")
    print("KEY FINDINGS")
    print(f"{'='*80}")
    
    print("Scenarios that produce +0/-0 diffs:")
    print("1. Empty content compared to empty content")
    print("2. Identical content (any length)")
    print("3. Content that is byte-for-byte identical")
    
    print("\nScenarios that do NOT produce +0/-0:")
    print("1. Any actual content change")
    print("2. Whitespace-only changes")
    print("3. Newline differences")
    print("4. Line ending differences (CRLF vs LF)")
    print("5. Case changes")
    print("6. Adding/removing content")
    
    print("\nConclusion:")
    print("The +0/-0 diff entries in the database likely indicate:")
    print("- File monitoring events triggered but content didn't actually change")
    print("- Duplicate processing of identical content")
    print("- File system events (like timestamps) without content changes")
    print("- Race conditions where file is read before write completes")


if __name__ == "__main__":
    main()