#!/usr/bin/env python3
"""Build the combined COMPENclaude document.

Writes docs/COMPENclaude.md (one Markdown file) and docs/COMPENclaude.html
(print-ready). With --pdf, also prints docs/COMPENclaude.pdf using a local
Chrome or Chromium in headless mode.

    python3 tools/build_docs.py --pdf
"""
import argparse
import html
import shutil
import subprocess
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "compenclaude"
OUT = ROOT / "docs"

REFS = [
    ("digital-logic.md", "Digital Logic and HDL"),
    ("computer-architecture.md", "Computer Architecture"),
    ("low-level-programming.md", "Low-Level Programming"),
    ("embedded-systems.md", "Embedded Systems"),
    ("operating-systems.md", "Operating Systems"),
    ("networking.md", "Networking"),
    ("circuits-electronics.md", "Circuits and Electronics"),
]


def body_without_title(text: str) -> str:
    """Drop front matter and the first H1; demote remaining headings one level."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"\A\s*# .*\n", "", text)
    out, fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and re.match(r"#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out).strip()


def readme_overview() -> str:
    return body_without_title((ROOT / "README.md").read_text())


sections = [("Overview", readme_overview()),
            ("The Skill (SKILL.md)", body_without_title((SKILL / "SKILL.md").read_text()))]
for fname, title in REFS:
    sections.append((f"Reference: {title}", body_without_title((SKILL / "references" / fname).read_text())))
tpl = []
for f in sorted((SKILL / "assets" / "templates").iterdir()):
    lang = "systemverilog" if f.suffix == ".sv" else "markdown"
    tpl.append(f"### {f.name}\n\n```{lang}\n{f.read_text().rstrip()}\n```")
sections.append(("Templates", "Files in `assets/templates/`.\n\n" + "\n\n".join(tpl)))
src = (SKILL / "scripts" / "cecalc.py").read_text()
sections.append(("Appendix: cecalc.py Source", "The complete calculator. Save it as `compenclaude/scripts/cecalc.py`.\n\n```python\n" + src.rstrip() + "\n```"))

# ------------------------------------------------------------------ markdown
md = ["# COMPENclaude", "",
      "A computer engineering skill for Claude: digital logic, computer architecture, embedded systems, "
      "low-level C and assembly, operating systems, networking, and circuits.", "",
      "## Contents", ""]
md += [f"{i}. {t}" for i, (t, _) in enumerate(sections, 1)]
for i, (t, body) in enumerate(sections, 1):
    md += ["", "---", "", f"## {i}. {t}", "", body]
(OUT / "COMPENclaude.md").write_text("\n".join(md) + "\n")


# ------------------------------------------------------------------ minimal markdown -> html
def inline(s: str) -> str:
    parts = re.split(r"(`[^`]+`)", s)
    res = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            res.append(f"<code>{html.escape(p[1:-1])}</code>")
            continue
        p = html.escape(p, quote=False).replace("**", "\x00")
        p = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", p)
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: m.group(1) if not m.group(2).startswith("http")
                   else f'<a href="{m.group(2)}">{m.group(1)}</a>', p)
        res.append(p)
    joined = re.sub("\x00(.+?)\x00", r"<strong>\1</strong>", "".join(res))
    return joined.replace("\\|", "|")


def split_row(line: str) -> list:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip() for c in cells]


def to_html(text: str) -> str:
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            cls = ' class="src"' if lang == "python" and len(code) > 100 else ""
            out.append(f"<pre{cls}><code>{html.escape(chr(10).join(code))}</code></pre>")
            i += 1
            continue
        m = re.match(r"(#{1,6}) (.*)", line)
        if m:
            lvl, title = len(m.group(1)), m.group(2)
            anchor = ""
            if lvl == 2 and re.match(r"\d+\. ", title):
                anchor = f' id="s{title.split(".")[0]}"'
            out.append(f"<h{lvl}{anchor}>{inline(title)}</h{lvl}>")
            i += 1
            continue
        if line.strip() == "---":
            out.append('<div class="pagebreak"></div>')
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            head = split_row(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(t + "</tbody></table>")
            continue
        if re.match(r"^\s*([-*]|\d+\.) ", line):
            ordered = bool(re.match(r"^\s*\d+\. ", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.) ", lines[i]) or
                                      (lines[i].startswith("   ") and lines[i].strip() and items)):
                l = lines[i]
                if re.match(r"^\s*([-*]|\d+\.) ", l):
                    nested = l.startswith("  ")
                    content = re.sub(r"^\s*([-*]|\d+\.) ", "", l)
                    items.append([nested, content])
                else:
                    if l.strip().startswith("```"):
                        # fenced block inside a list item
                        code = []
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith("```"):
                            code.append(lines[i].strip())
                            i += 1
                        items[-1][1] += f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>"
                    else:
                        items[-1][1] += " " + l.strip()
                i += 1
            h = [f"<{tag}>"]
            for nested, content in items:
                c = content if "<pre>" in content else inline(content)
                if "<pre>" in content:
                    pre_at = content.index("<pre>")
                    c = inline(content[:pre_at]) + content[pre_at:]
                h.append(f'<li class="nested">{c}</li>' if nested else f"<li>{c}</li>")
            h.append(f"</{tag}>")
            out.append("".join(h))
            continue
        if not line.strip():
            i += 1
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|```|\||\s*[-*] |\s*\d+\. |---)", lines[i]):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


toc = "".join(f'<li><a href="#s{i}">{html.escape(t)}</a></li>' for i, (t, _) in enumerate(sections, 1))
content = "\n".join(f'<section><h2 id="s{i}"><span class="num">{i:02d}</span>{html.escape(t)}</h2>\n{to_html(b)}</section>'
                    for i, (t, b) in enumerate(sections, 1))

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>COMPENclaude</title>
<style>
@page {{ size: A4; margin: 18mm 16mm 20mm; }}
:root {{ --ink:#1b1f24; --muted:#5b6470; --accent:#c2562f; --rule:#e3e6ea; --code:#f5f6f8; }}
* {{ box-sizing: border-box; }}
body {{ font: 10pt/1.5 -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; color: var(--ink); margin: 0; background:#fff; }}
.cover {{ height: 255mm; display:flex; flex-direction:column; justify-content:center; page-break-after: always; }}
.cover .kicker {{ color: var(--accent); font-weight:600; letter-spacing:.12em; text-transform:uppercase; font-size:9pt; }}
.cover h1 {{ font-size: 48pt; margin: 6mm 0 4mm; letter-spacing:-.02em; line-height:1; }}
.cover p {{ font-size: 13pt; color: var(--muted); max-width: 140mm; margin:0; }}
.cover .tags {{ margin-top: 12mm; display:flex; flex-wrap:wrap; gap:2mm; }}
.cover .tags span {{ border:1px solid var(--rule); border-radius: 99px; padding: 1mm 3.5mm; font-size:9pt; color:var(--muted); }}
.cover .foot {{ margin-top:auto; font-size:9pt; color:var(--muted); border-top:1px solid var(--rule); padding-top:3mm; }}
.toc {{ page-break-after: always; }}
.toc h2 {{ font-size: 20pt; }}
.toc ol {{ list-style:none; padding:0; counter-reset:t; }}
.toc li {{ counter-increment:t; padding: 2.2mm 0; border-bottom:1px solid var(--rule); font-size:11.5pt; }}
.toc li::before {{ content: counter(t, decimal-leading-zero); color: var(--accent); font-weight:600; margin-right:5mm; font-variant-numeric: tabular-nums; }}
.toc a {{ color: inherit; text-decoration:none; }}
section {{ page-break-before: always; }}
section > h2 {{ font-size: 20pt; margin: 0 0 5mm; padding-bottom: 3mm; border-bottom: 2px solid var(--ink); letter-spacing:-.01em; }}
section > h2 .num {{ color: var(--accent); margin-right: 4mm; font-variant-numeric: tabular-nums; }}
h3 {{ font-size: 13pt; margin: 7mm 0 2mm; page-break-after: avoid; }}
h4 {{ font-size: 11pt; margin: 5mm 0 1.5mm; color: #2d333b; page-break-after: avoid; }}
p {{ margin: 0 0 2.5mm; }}
ul, ol {{ margin: 0 0 3mm; padding-left: 6mm; }}
li {{ margin: .6mm 0; }}
li.nested {{ margin-left: 5mm; list-style-type: circle; }}
code {{ font: 8.8pt/1.4 "SF Mono", Menlo, Consolas, monospace; background: var(--code); padding: .2mm 1mm; border-radius: 2px; }}
pre {{ background: var(--code); border: 1px solid var(--rule); border-left: 3px solid var(--accent); border-radius: 3px; padding: 3mm 4mm; margin: 2mm 0 4mm; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }}
pre code {{ background:none; padding:0; font-size: 8.3pt; }}
pre.src {{ page-break-inside: auto; }}
pre.src code {{ font-size: 7.4pt; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 8.8pt; page-break-inside: avoid; }}
th, td {{ border: 1px solid var(--rule); padding: 1.4mm 2mm; text-align: left; vertical-align: top; }}
th {{ background: #f0f2f4; font-weight: 600; }}
tr:nth-child(even) td {{ background: #fafbfc; }}
a {{ color: var(--accent); }}
strong {{ font-weight: 650; }}
.pagebreak {{ display:none; }}
</style></head><body>
<div class="cover">
  <div class="kicker">Claude Skill · Computer Engineering</div>
  <h1>COMPENclaude</h1>
  <p>A working method, seven reference guides, and an exact calculator that make Claude precise on computer engineering problems.</p>
  <div class="tags"><span>Digital logic &amp; HDL</span><span>Computer architecture</span><span>Low-level C &amp; assembly</span><span>Embedded systems</span><span>Operating systems</span><span>Networking</span><span>Circuits</span></div>
  <div class="foot">Complete documentation · skill instructions · references · calculator source · MIT License</div>
</div>
<div class="toc"><h2>Contents</h2><ol>{toc}</ol></div>
{content}
</body></html>"""

(OUT / "COMPENclaude.html").write_text(page)
print(f"wrote {len(sections)} sections to docs/COMPENclaude.md and docs/COMPENclaude.html")

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
]


def print_pdf() -> None:
    chrome = next((c for c in CHROME_CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    if not chrome:
        sys.exit("no Chrome/Chromium found; open docs/COMPENclaude.html and print to PDF instead")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT / 'COMPENclaude.pdf'}", (OUT / "COMPENclaude.html").as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote docs/COMPENclaude.pdf")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", action="store_true", help="also print a PDF with headless Chrome")
    if ap.parse_args().pdf:
        print_pdf()
