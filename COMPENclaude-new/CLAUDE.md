# CLAUDE.md

Instructions for Claude Code when working in this repository.

## What this repo is

COMPENclaude is a Claude Agent Skill for computer engineering, packaged as a Claude Code plugin. The skill lives in `skills/compenclaude/`. Everything else supports it: plugin manifests, tests, a validator, evals, and generated documentation.

## Layout

| Path | Purpose |
|---|---|
| `skills/compenclaude/SKILL.md` | The skill: frontmatter, method, routing table, trap checklist, modes, templates list |
| `skills/compenclaude/references/*.md` | Topic guides, loaded on demand. One per area |
| `skills/compenclaude/assets/templates/*.md` | Fill-in templates the skill offers to users |
| `skills/compenclaude/scripts/cecalc.py` | Exact calculators. Standard library only, Python 3.9+ |
| `.claude-plugin/plugin.json`, `marketplace.json` | Claude Code plugin install |
| `tests/test_cecalc.py` | Known-answer tests for every calculator command |
| `tools/validate_skill.py` | Checks frontmatter, file references, and manifests |
| `tools/build_docs.py` | Regenerates `docs/` from the skill files |
| `docs/` | Generated. Never edit by hand |
| `evals/evals.json` | Behavior test prompts with expected answers |

## Commands

```bash
python3 -m unittest discover tests          # run calculator tests
python3 tools/validate_skill.py             # validate skill + manifests (uses PyYAML if installed)
python3 tools/build_docs.py --pdf           # rebuild docs/ (PDF needs Chrome or Chromium)
python3 skills/compenclaude/scripts/cecalc.py <command> -h
```

Run the tests and the validator after every change. Rebuild the docs after any change inside `skills/` or to `README.md`.

## Rules for SKILL.md

- Frontmatter keys: `name`, `description`, `license`, `metadata` only.
- `name` must be `compenclaude`: lowercase, matches the folder name.
- `description` stays under 1024 characters, has no angle brackets, and has no `": "` (colon followed by a space). A colon-space breaks YAML parsing and the skill will fail to load.
- Keep the body under 500 lines. Put detail in `references/` and add it to the routing table in section 1.
- Every `references/`, `assets/`, or `scripts/` path mentioned in backticks must exist. The validator checks this.

## Rules for content

- **Accuracy first.** Every formula and fact must be correct. Verify numbers with `cecalc.py` before writing them into a reference or eval. When unsure, leave it out.
- Part-specific details (register names, pin limits) vary by chip. Describe the mechanism and tell the reader to confirm in the datasheet.
- Each reference file starts with a title, a one-line summary, and a `## Contents` list matching its `##` headings.
- End each reference with a "Common mistakes" section.
- Plain language, short sections, active voice. No filler.

## Adding a calculator command

1. Add a `cmd_<name>(a)` function in `cecalc.py` that prints its working, then register a subparser in `main()`.
2. Standard library only. Validate inputs and exit with `die("...")` on bad input.
3. Add a known-answer test in `tests/test_cecalc.py`, with the expected value checked against a textbook or datasheet.
4. List the command in the module docstring, in section 2 of `SKILL.md`, and in the README table.

## Releasing

1. Bump the version in `skills/compenclaude/SKILL.md` (`metadata.version`), `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`.
2. Add an entry to `CHANGELOG.md`.
3. Run tests, the validator, and `tools/build_docs.py --pdf`.
4. Build the upload zip for GitHub Releases (zips are gitignored, never commit them):
   ```bash
   cd skills && zip -r ../compenclaude.zip compenclaude -x '*/__pycache__/*' '*.DS_Store'
   ```

## Don't

- Don't commit `*.zip`, `__pycache__/`, or `.DS_Store`.
- Don't add third-party dependencies to `cecalc.py`.
- Don't hand-edit files in `docs/`.
- Don't rename the skill folder without updating `name`, the validator, and both manifests.
