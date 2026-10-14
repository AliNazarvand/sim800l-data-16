#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_d15_fix_pages.py

Repairs the `source.page` value of the records dat_02_0006..dat_02_0095
inside data/dat_02_urc.yaml.  The page numbers were originally written as
'1' or '' because the page-marker detection in the previous script used
form-feed (\f) splitting which does not match the format of the paged
files in this repository.

This script:

  1. Tries several page-marker patterns on each file in sources/extracted/
     whose name contains 'paged'.
  2. Picks the pattern that yields the most distinct page numbers.
  3. Uses reports/_d14_plan.json (which lists, for each candidate URC, the
     paged file and line where it was found) to derive the real page.
  4. Rewrites data/dat_02_urc.yaml with the corrected pages.  Only the
     records between dat_02_0006 and dat_02_0095 have their `page:` line
     touched; everything else is preserved verbatim (comments, key order,
     spacing, quoting).

If no page marker pattern matches, the script prints the first 80 lines
of one paged file and exits, so you can send them for inspection.

Backup: data/dat_02_urc.yaml.pagebak

Usage:
    python scripts/_d15_fix_pages.py             # apply the fix
    python scripts/_d15_fix_pages.py --dry-run   # show counts, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[FATAL] PyYAML is not installed.  Run: pip install pyyaml",
          file=sys.stderr)
    sys.exit(1)


ROOT          = Path(__file__).resolve().parent.parent
DAT02_PATH    = ROOT / "data"    / "dat_02_urc.yaml"
DAT02_BACKUP  = ROOT / "data"    / "dat_02_urc.yaml.pagebak"
EXTRACTED_DIR = ROOT / "sources" / "extracted"
PLAN_PATH     = ROOT / "reports" / "_d14_plan.json"

# ---------------------------------------------------------------------------
# Page-marker patterns, tried in order.  Each pattern must have exactly one
# capturing group with the page number.
# ---------------------------------------------------------------------------
PAGE_PATTERNS = [
    ("--- Page N ---",
     re.compile(r"^\s*-{3,}\s*[Pp]age\s+(\d+)\s*-{3,}\s*$", re.MULTILINE)),
    ("=== Page N ===",
     re.compile(r"^\s*={3,}\s*[Pp]age\s+(\d+)\s*={3,}\s*$", re.MULTILINE)),
    ("*** Page N ***",
     re.compile(r"^\s*\*{3,}\s*[Pp]age\s+(\d+)\s*\*{3,}\s*$", re.MULTILINE)),
    ("[Page N]",
     re.compile(r"^\s*\[\s*[Pp]age\s+(\d+)\s*\]\s*$", re.MULTILINE)),
    ("<Page N>",
     re.compile(r"^\s*<\s*[Pp]age\s+(\d+)\s*>\s*$", re.MULTILINE)),
    ("# Page N",
     re.compile(r"^\s*#{2,}\s*[Pp]age\s+(\d+)\s*$", re.MULTILINE)),
    ("Page N of M",
     re.compile(r"^\s*[Pp]age\s+(\d+)\s+of\s+\d+\s*$", re.MULTILINE)),
    ("<<<PAGE N>>>",
     re.compile(r"^\s*<<<\s*[Pp][Aa][Gg][Ee]\s+(\d+)\s*>>>\s*$", re.MULTILINE)),
    ("Page N (standalone)",
     re.compile(r"^\s*[Pp]age\s+(\d+)\s*$", re.MULTILINE)),
]


# Map plan's "pdf" field -> paged .txt filename used in paged_maps
PDF_TO_TXT = {
    "SIM800 Series_AT Command Manual_V1.01.pdf": "at_manual_v1_01_paged.txt",
    "SIM800L_Hardware_Design_V1.00.pdf":         "v1_00_paged.txt",
    "SIM800H&SIM800L_Hardware_Design_V2.02.PDF": "v2_02_paged.txt",
}

def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}", flush=True)


def abort(msg: str, code: int = 1) -> None:
    log(msg, "FATAL")
    sys.exit(code)


# ---------------------------------------------------------------------------
def build_line_to_page(text: str, pattern: re.Pattern) -> dict | None:
    markers = []
    for m in pattern.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        try:
            pg = int(m.group(1))
        except (IndexError, ValueError):
            continue
        markers.append((ln, pg))
    if not markers:
        return None
    markers.sort()
    total = text.count("\n") + 1
    mapping = {}
    for i, (start, pg) in enumerate(markers):
        end = markers[i + 1][0] - 1 if i + 1 < len(markers) else total
        for ln in range(start, end + 1):
            mapping[ln] = pg
    return mapping


def try_form_feed(text: str) -> dict | None:
    parts = text.split("\f")
    if len(parts) <= 1:
        return None
    mapping = {}
    ln = 0
    for pg, part in enumerate(parts, start=1):
        for _line in part.split("\n"):
            ln += 1
            mapping[ln] = pg
    return mapping


def find_best_mapping(text: str):
    candidates = []
    ff = try_form_feed(text)
    if ff:
        candidates.append(("form-feed", ff))
    for name, pattern in PAGE_PATTERNS:
        m = build_line_to_page(text, pattern)
        if m:
            candidates.append((name, m))
    if not candidates:
        return None
    return max(candidates, key=lambda x: len(set(x[1].values())))


# ---------------------------------------------------------------------------
def fix_record_block(block: str, page: int) -> tuple[str, bool]:
    """Return (new_block, changed).  Only touches the first `page:` line."""
    m = re.search(r"^(\s*)page:\s*(.*?)\s*$", block, re.MULTILINE)
    if not m:
        return block, False
    current_raw = m.group(2).strip().strip("'\"")
    if current_raw == str(page):
        return block, False
    new_block, n = re.subn(
        r"^(\s*)page:\s*.*?$",
        lambda mm: f"{mm.group(1)}page: '{page}'",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    return new_block, n > 0


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be done; write nothing.")
    args = parser.parse_args()

    if not DAT02_PATH.exists():
        abort(f"dat_02_urc.yaml not found: {DAT02_PATH}")
    if not PLAN_PATH.exists():
        abort(f"_d14_plan.json not found: {PLAN_PATH}")

    # ---- Load plan ------------------------------------------------------
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    candidates = plan.get("candidates", [])
    log(f"Loaded plan: {len(candidates)} candidates")

    # ---- Build page maps for every paged file --------------------------
    log("Scanning paged sources for page markers ...")
    paged_maps: dict[str, dict] = {}
    detected_patterns: dict[str, str] = {}
    for p in sorted(EXTRACTED_DIR.glob("*paged*.txt")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        best = find_best_mapping(text)
        if best is None:
            log(f"  no page marker found in {p.name}", "WARN")
            continue
        name, mapping = best
        distinct = len(set(mapping.values()))
        log(f"  {p.name}: pattern='{name}' pages={distinct} "
            f"lines={len(mapping)}")
        paged_maps[p.name] = mapping
        detected_patterns[p.name] = name

    if not paged_maps:
        # Nothing worked — dump diagnostics so the user can report back.
        log("No page markers detected. Printing first 80 lines of one "
            "paged file for inspection:", "WARN")
        for p in sorted(EXTRACTED_DIR.glob("*paged*.txt"))[:1]:
            log(f"--- {p.name} (first 80 lines) ---")
            for i, line in enumerate(p.read_text(encoding="utf-8",
                                                errors="ignore").splitlines()[:80],
                                     start=1):
                print(f"  {i:4d}|{line}")
        abort("Cannot proceed without page markers.")

    # ---- Re-search each URC with strict word boundaries, take LAST hit --
    paged_texts = {}
    for p in sorted(EXTRACTED_DIR.glob("*paged*.txt")):
        paged_texts[p.name] = p.read_text(encoding="utf-8", errors="ignore")

    def find_page_for(name: str, txt: str, mapping: dict):
        if name.startswith("+") or name.startswith("*"):
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) +
                             r"(?![A-Z0-9_])")
        else:
            pat = re.compile(r"\b" + re.escape(name) + r"\b",
                             re.IGNORECASE)
        matches = list(pat.finditer(txt))
        if not matches:
            return None, 0
        last = matches[-1]
        ln = txt.count("\n", 0, last.start()) + 1
        return mapping.get(ln), len(matches)

    urc_to_page = {}
    for c in candidates:
        name  = c.get("name")
        fname = c.get("file") or PDF_TO_TXT.get(c.get("pdf", ""))
        if not name or not fname:
            continue
        txt = paged_texts.get(fname)
        mapping = paged_maps.get(fname)
        if not txt or not mapping:
            continue
        page, n_hits = find_page_for(name, txt, mapping)
        if page is not None:
            urc_to_page[name.upper()] = page
            log(f"  {name}: page={page} ({n_hits} hits, last used)")

    log(f"Resolved page for {len(urc_to_page)} URCs.")

    # ---- Update dat_02_urc.yaml in place -------------------------------
    raw = DAT02_PATH.read_text(encoding="utf-8")

    blocks = re.split(r"(?=\n- id: dat_02_)", raw)

    new_blocks: list[str] = []
    changed = 0
    skipped_missing_urc = 0
    skipped_missing_page = 0

    for block in blocks:
        m = re.search(r"^\s*-\s+id:\s*dat_02_(\d+)", block, re.MULTILINE)
        if not m:
            new_blocks.append(block)
            continue
        num = int(m.group(1))
        if num < 6 or num > 95:
            new_blocks.append(block)
            continue
        um = re.search(r"^\s*urc_string:\s*['\"]?(.*?)['\"]?\s*$",
                       block, re.MULTILINE)
        if not um:
            skipped_missing_urc += 1
            new_blocks.append(block)
            continue
        urc = um.group(1).strip().strip("'\"")
        page = urc_to_page.get(urc.upper())
        if page is None:
            skipped_missing_page += 1
            new_blocks.append(block)
            continue
        new_block, did = fix_record_block(block, page)
        if did:
            changed += 1
        new_blocks.append(new_block)

    out = "".join(new_blocks)

    # Verify still parses as YAML
    try:
        yaml.safe_load(out)
    except yaml.YAMLError as exc:
        abort(f"Resulting YAML is invalid: {exc}")

    if args.dry_run:
        log("DRY-RUN: no changes written.")
        log(f"  Would change : {changed} records")
        log(f"  No URC name  : {skipped_missing_urc}")
        log(f"  No page      : {skipped_missing_page}")
        return 0

    shutil.copy2(DAT02_PATH, DAT02_BACKUP)
    log(f"Backup written to {DAT02_BACKUP}")

    DAT02_PATH.write_text(out, encoding="utf-8", newline="\n")
    log(f"Updated {changed} records.")
    if skipped_missing_urc:
        log(f"  Skipped (no urc_string) : {skipped_missing_urc}", "WARN")
    if skipped_missing_page:
        log(f"  Skipped (no page in plan): {skipped_missing_page}", "WARN")
    log("Done.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Interrupted.", "WARN")
        sys.exit(130)
    except Exception as exc:
        log(f"Unhandled exception: {exc}", "FATAL")
        import traceback
        traceback.print_exc()
        sys.exit(1)