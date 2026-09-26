# Contributing to COMPENclaude

Thanks for helping make Claude better at computer engineering.

## Good contributions

- A mistake you've seen Claude make that the trap list in `SKILL.md` should cover
- New or improved reference material in `skills/compenclaude/references/`
- New calculator commands in `scripts/cecalc.py`, each with a known-answer test
- New templates in `skills/compenclaude/assets/templates/`
- Fixes to factual errors

## Guidelines

- **Keep `SKILL.md` short** (under 500 lines). Put detail in `references/` and link to it from the routing table in section 1 of `SKILL.md`.
- **Explain why.** Instructions that give reasons work better than bare rules.
- **Be accurate.** Cite a source in your pull request for any formula or fact you add. For part-specific details (register names, electrical limits), point readers to the datasheet instead of hard-coding values.
- **Test every number.** A new calculator command needs at least one test in `tests/test_cecalc.py` with an answer checked against a textbook or datasheet.
- **Match the style:** plain language, short sections, a contents list at the top of each reference file.

## Before opening a pull request

```bash
python3 -m unittest discover tests
```

```bash
pip install pyyaml && python3 tools/validate_skill.py
```

Rebuild the docs with `python3 tools/build_docs.py --pdf` so `docs/` matches the skill.

If you changed how the skill answers, try a few prompts from `evals/evals.json` and describe the before and after in your pull request.
