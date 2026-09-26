#!/usr/bin/env python3
"""Validate the compenclaude skill and plugin manifests.

Checks the SKILL.md frontmatter against the Agent Skills rules, confirms every
file SKILL.md points to exists, and checks the plugin JSON files.
Uses PyYAML when installed (pip install pyyaml) and a small built-in parser otherwise.
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # minimal fallback for flat "key: value" frontmatter
    yaml = None


def load_frontmatter(text):
    if yaml:
        return yaml.safe_load(text)
    meta, parent = {}, None
    for line in text.splitlines():
        if not line.strip():
            continue
        key, _, value = line.strip().partition(":")
        value = value.strip().strip('"')
        if line.startswith((" ", "\t")) and parent:
            meta[parent][key] = value
        elif value:
            meta[key], parent = value, None
        else:
            meta[key], parent = {}, key
    return meta

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "compenclaude"
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def validate_skill():
    skill_md = SKILL_DIR / "SKILL.md"
    check(skill_md.exists(), "SKILL.md is missing")
    if not skill_md.exists():
        return
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    check(match is not None, "SKILL.md must start with YAML frontmatter between --- lines")
    if not match:
        return
    meta = load_frontmatter(match.group(1))
    check(isinstance(meta, dict), "frontmatter must be a YAML mapping")
    if not isinstance(meta, dict):
        return

    check(not (set(meta) - ALLOWED_KEYS), f"unexpected frontmatter keys: {set(meta) - ALLOWED_KEYS}")
    name = meta.get("name", "")
    check(isinstance(name, str) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or ""),
          "name must be lowercase letters, digits, and single hyphens")
    check(len(name) <= 64, "name must be 64 characters or fewer")
    check(name == SKILL_DIR.name, f"name '{name}' must match folder name '{SKILL_DIR.name}'")
    desc = meta.get("description", "")
    check(isinstance(desc, str) and desc.strip(), "description is required")
    check(len(desc) <= 1024, f"description is {len(desc)} characters; the limit is 1024")
    check("<" not in desc and ">" not in desc, "description cannot contain angle brackets")

    body_lines = text[match.end():].count("\n")
    check(body_lines < 500, f"SKILL.md body is {body_lines} lines; keep it under 500")

    skill_md_count = len(list(SKILL_DIR.rglob("SKILL.md")))
    check(skill_md_count == 1, f"found {skill_md_count} SKILL.md files; a skill must have exactly one")

    # Every references/, assets/, scripts/ path mentioned in SKILL.md must exist.
    for rel in sorted(set(re.findall(r"`((?:references|assets|scripts)/[^`\s]+)`", text))):
        target = SKILL_DIR / rel
        check(target.exists(), f"SKILL.md mentions {rel} but it does not exist")
    for rel in sorted(set(re.findall(r"`([a-z-]+\.(?:md|csv))`", text))):
        hits = list(SKILL_DIR.rglob(rel))
        check(hits, f"SKILL.md mentions {rel} but no such file exists in the skill")


def validate_plugin():
    plugin = ROOT / ".claude-plugin" / "plugin.json"
    market = ROOT / ".claude-plugin" / "marketplace.json"
    for path in (plugin, market):
        check(path.exists(), f"{path.relative_to(ROOT)} is missing")
    if not (plugin.exists() and market.exists()):
        return
    p = json.loads(plugin.read_text(encoding="utf-8"))
    m = json.loads(market.read_text(encoding="utf-8"))
    check(p.get("name") == "compenclaude", "plugin.json name must be 'compenclaude'")
    check(m.get("name"), "marketplace.json needs a name")
    check(isinstance(m.get("owner"), dict) and m["owner"].get("name"), "marketplace.json needs owner.name")
    names = [entry.get("name") for entry in m.get("plugins", [])]
    check("compenclaude" in names, "marketplace.json must list the compenclaude plugin")


def main():
    validate_skill()
    validate_plugin()
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("OK: skill and plugin manifests are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
