# Contributing to YSFC Forge

Thanks for your interest in contributing. This guide explains how to report bugs, submit reverse engineering findings, and propose improvements.

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Bug Reports](#bug-reports)
- [Reverse Engineering Contributions](#reverse-engineering-contributions)
- [Pull Requests](#pull-requests)
- [Code Style](#code-style)
- [What's Most Needed](#whats-most-needed)

---

## Ways to Contribute

### Most welcome

- **Test files for unmapped areas** — Smart Morph, Scene snapshots, FM-X 2nd LFO matrix
- **Verification on Montage M hardware** — we assume format compatibility but lack hardware verification
- **Bug reports** for the Forge Librarian tool (the production tool)
- **Documentation improvements** — clarifications, typo fixes, additional examples

### Provided as-is

The Performance Editor, translators, and utilities are experimental and provided without active support. Feature requests are appreciated but may not be implemented quickly. Forks and independent development are encouraged.

---

## Bug Reports

Please use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- **The specific file(s)** that exhibit the bug (or steps to reproduce without the file)
- **Browser and version** you're using
- **Hardware tested on** (MODX M, ESP plugin, Montage M)
- **Expected vs actual behavior**

If the bug involves a corrupt or unusual `.Y2L` / `.Y2U` file, attaching the file (or a minimal reproduction file) helps enormously.

---

## Reverse Engineering Contributions

Reverse engineering contributions are highly valued. We use a strict binary-diff methodology to ensure every documented offset has concrete evidence.

### Methodology

1. **Set up a baseline performance** on hardware. We use a stripped-down "Init Voice" with one part — simple defaults, no modulation routing.
2. **Change exactly ONE parameter** via the UI. For example: set OSC1 Pitch to +50 cents, leave everything else untouched.
3. **Export the file** with a descriptive name: `Test-{Engine}_{Section}_{Parameter}_{Value}.Y2L`. Example: `Test-ANX_OSC1_Pitch_+50.Y2L`.
4. **Run a binary diff** against the baseline. Any hex-diff tool works (`cmp -l`, `xxd | diff`, HxD, etc.)
5. **Document the finding**:
   - File offset (or audit offset, if you know the conversion)
   - Before/after values
   - UI parameter name and section
   - Encoding (direct u8, center=64, u16le, etc.)
6. **Filter out save-counter noise**. These bytes change on every save regardless of edits:
   ```
   abs 22-24, 60-63, 66, 232, 234, 358, 376, 396-399, 488, 654,
   abs 6715-6716, 6721, 6724-6725, 7167-7168, 7419
   ```

### Submission format

Submit findings either as:

- **An issue** with the test file attached and a description of the parameter mapping, or
- **A pull request** updating `serializer/ysfc_serializer.py` with the new field

### Ambiguous results

For changes across multiple bytes, or no changes at all for a UI control, it helps to test variations:

- Same parameter at min/mid/max values
- Toggling on/off (for boolean parameters)
- Small step changes (e.g., +1, +5, +10) to detect encoding

For multi-byte fields, look for patterns: little-endian u16 with low byte changing first, center-offset encodings (raw = value + 64 or + 128), etc.

### Star ratings

Use the verification level system when documenting findings:

- **★★★★★** — Binary-verified with one or more test files (direct A/B diff evidence)
- **★★★★☆** — Derived from official source data, highly confident
- **★★★☆☆** — Likely correct, not binary-verified
- **★★☆☆☆** — Uncertain
- **[INTERN]** — MODX-internal firmware constant, not user-editable

---

## Pull Requests

### General guidelines

- Keep tool changes focused on **Forge Librarian** unless coordinated with maintainers
- For serializer changes, include the test file name(s) as evidence in the comment
- Update both `serializer/ysfc_serializer.py` AND `docs/YSFC_FORGE_REFERENCE.md` to stay consistent
- Preserve the star rating system

### Commit messages

Use clear, descriptive commit messages:

- `Add: AN-X OSC1 Connect field (audit 12670)`
- `Fix: FM-X Algorithm encoding off-by-one`
- `Docs: clarify Drum filoffset convention (+669)`
- `Verify: AWM2 element 1-8 stride 313 with 8 new test files`

### Code review

- All PRs are reviewed before merging
- For serializer changes, expect questions about test file evidence
- For tool changes, expect questions about browser compatibility

---

## Code Style

### HTML tools

- Vanilla JavaScript, no build step, single-file
- CSS inline or in a single `<style>` block
- No frameworks (no React, no Vue, no jQuery)
- ES6+ features OK (`const`/`let`, arrow functions, template literals)

### Python

- Python 3.8+
- Standard library only (no external dependencies)
- Type hints encouraged but not mandatory
- Follow PEP 8 for general style

### Markdown documentation

- GitHub-flavored Markdown
- Tables for parameter listings
- Code blocks for binary examples (hex, byte offsets)
- Preserve the star rating system across all documents

---

## What's Most Needed

If you want to contribute but aren't sure where to start, these areas have the most value:

### Test files

- **Smart Morph** — completely unmapped area
- **Scene snapshots** — structure verified, field-level mapping incomplete
- **FM-X 2nd LFO matrix** — partial mapping needs verification
- **Montage M hardware** — verify that the format is identical to MODX M

### Tool development

- **Performance Editor multi-part support** — currently only shows Part 1
- **Drum parameter editor UI** — structure is mapped, UI is not yet exposed
- **Undo/redo** in Performance Editor

### Documentation

- Translation of `docs/REVERSE_ENGINEERING.md` to other languages
- Improvements to parameter encoding documentation
- More real-world examples of binary diff workflows

---

## Questions?

Open an issue with the `question` label, or start a discussion in the GitHub Discussions tab.
