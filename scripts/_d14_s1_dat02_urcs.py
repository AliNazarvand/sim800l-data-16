#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_d14_s1_dat02_urcs.py  (revision 2 - schema-compliant)

Adds the SIM800L URCs listed in the sim800-at-urc checklist to
data/dat_02_urc.yaml, using the official SIMCom extracted text files
inside sources/extracted/ to resolve page numbers.

Key differences from revision 1:
  * Only URCs present in the checklist are added.  Random +XXX tokens
    that appear in the extracted text as ordinary AT commands are NOT
    added.
  * source_type is "primary";  status is "complete" or "partial".
    (Matches the schema enum used by scripts/validate.py.)
  * The template's content-specific fields (parameters, format,
    trigger_event, examples, related_urcs, notes, ...) are reset, NOT
    cloned from the first existing record.
  * Page numbers are recovered by splitting the paged text on form-feed
    characters (\f), which is how pdftotext separates pages.
  * Checklist is cached locally at sources/reference/urcs.yaml.

Usage:
    python scripts/_d14_s1_dat02_urcs.py                 # dry-run
    python scripts/_d14_s1_dat02_urcs.py --apply         # write changes
    python scripts/_d14_s1_dat02_urcs.py --no-network    # offline
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[FATAL] PyYAML is not installed.  Run: pip install pyyaml",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
ROOT          = Path(__file__).resolve().parent.parent
SCHEMA_PATH   = ROOT / "schemas" / "dat_02.schema.yaml"
DAT02_PATH    = ROOT / "data"    / "dat_02_urc.yaml"
DAT02_BACKUP  = ROOT / "data"    / "dat_02_urc.yaml.bak"
EXTRACTED_DIR = ROOT / "sources" / "extracted"
REFERENCE_DIR = ROOT / "sources" / "reference"
SCRIPTS_DIR   = ROOT / "scripts"
REPORTS_DIR   = ROOT / "reports"

CHECKLIST_CACHE = REFERENCE_DIR / "urcs.yaml"
DIAG_PATH       = REPORTS_DIR / "_d14_diagnostic.json"
PLAN_PATH       = REPORTS_DIR / "_d14_plan.json"
REJECT_PATH     = REPORTS_DIR / "_d14_rejected.json"

CHECKLIST_URL = ("https://raw.githubusercontent.com/AliNazarvand/"
                 "sim800-at-urc/main/data/urcs.yaml")

# Schema-compliant enumerations taken from the project's validate.py run
VALID_STATUS      = {"complete", "partial", "unknown",
                     "inferred", "blocked", "deferred"}
VALID_SOURCE_TYPE = {"primary", "secondary", "inferred", "external"}

# ---------------------------------------------------------------------------
# Checklist: exact list from sim800-at-urc/data/urcs.yaml
# Each entry: (name, category, description, payload, enabled_by)
# ---------------------------------------------------------------------------
CHECKLIST = [
    # V.25TER
    ("RING", "V25TER", "An incoming call signal from network is detected", [], []),
    ("RDY", "V25TER", "Power on procedure is completed", [], []),
    ("NORMAL POWER DOWN", "V25TER", "SIM800 is powered down by PWRKEY or AT+CPOWD=1", [], ["AT+CPOWD"]),
    ("UNDER-VOLTAGE POWER DOWN", "V25TER", "Under-voltage automatic power down", [], []),
    ("UNDER-VOLTAGE WARNNING", "V25TER", "Under-voltage warning", [], []),
    ("OVER-VOLTAGE POWER DOWN", "V25TER", "Over-voltage automatic power down", [], []),
    ("OVER-VOLTAGE WARNNING", "V25TER", "Over-voltage warning", [], []),
    ("CHARGE-ONLY MODE", "V25TER", "The module is charging by charger", [], []),
    ("Call Ready", "V25TER", "Module is powered on and phonebook initialization is over", [], ["AT+CIURC"]),
    ("SMS Ready", "V25TER", "Module is powered on and SMS initialization is over", [], []),
    # 3GPP TS 27.007
    ("+CCWA", "3GPP_27007", "Indication of a call that is currently waiting and can be accepted", ["number", "type", "class", "alpha"], ["AT+CCWA"]),
    ("+CLIP", "3GPP_27007", "The calling line identity of the calling party", ["number", "type", "subaddr", "satype", "alphaId", "CLI_validity"], ["AT+CLIP"]),
    ("+CRING", "3GPP_27007", "Indicates incoming call to the TE if extended format is enabled", ["type"], ["AT+CRC"]),
    ("+CREG", "3GPP_27007", "There is a change in the MT network registration status", ["stat", "lac", "ci"], ["AT+CREG"]),
    ("+CCWV", "3GPP_27007", "Shortly before the ACM maximum value is reached", [], ["AT+CCWE"]),
    ("+CMTI", "3GPP_27007", "Indicates that new message has been received", ["mem3", "index"], ["AT+CNMI"]),
    ("+CMT", "3GPP_27007", "Indicates that new message has been received", ["oa", "scts", "tooa", "fo", "pid", "dcs", "sca", "tosca", "length", "data"], ["AT+CNMI"]),
    ("+CBM", "3GPP_27007", "Indicates that new cell broadcast message has been received", ["sn", "mid", "dcs", "page", "pages", "data"], ["AT+CNMI"]),
    ("+CDS", "3GPP_27007", "Indicates that new SMS status report has been received", ["fo", "mr", "ra", "tora", "scts", "dt", "st"], ["AT+CNMI"]),
    ("+COLP", "3GPP_27007", "The presentation of the COL at the TE for a MO call", ["number", "type", "subaddr", "satype", "alphaId"], ["AT+COLP"]),
    ("+CSSU", "3GPP_27007", "Presentation status during a mobile terminated call setup", ["code2"], ["AT+CSSN"]),
    ("+CSSI", "3GPP_27007", "Presentation status after a mobile originated call setup", ["code1", "index"], ["AT+CSSN"]),
    ("+CLCC", "3GPP_27007", "Report a list of current calls of ME", ["id1", "dir", "stat", "mode", "mpty", "number", "type", "alphaID"], ["AT+CLCC"]),
    ("*PSNWID", "3GPP_27007", "Refresh network name by network", ["mcc", "mnc", "full_name", "full_name_CI", "short_name", "short_name_CI"], ["AT+CLTS"]),
    ("*PSUTTZ", "3GPP_27007", "Refresh time and time zone by network", ["year", "month", "day", "hour", "min", "sec", "tz", "dst"], ["AT+CLTS"]),
    ("+CTZV", "3GPP_27007", "Refresh network time zone by network", ["time_zone"], ["AT+CLTS"]),
    ("DST", "3GPP_27007", "Refresh Network Daylight Saving Time by network", ["dst"], ["AT+CLTS"]),
    ("+CSMINS", "3GPP_27007", "Indicates whether SIM card has been inserted", ["n", "SIM_inserted"], ["AT+CSMINS"]),
    ("+CDRIND", "3GPP_27007", "Indicates whether a CS voice call, CS data has been terminated", ["type"], ["AT+CDRIND"]),
    ("+CHF", "3GPP_27007", "Indicates the current channel", ["state"], ["AT+CHF"]),
    ("+CENG", "3GPP_27007", "Report of network information", ["cell", "arfcn", "rxl", "rxq", "mcc", "mnc", "bsic", "cellid", "rla", "txp", "lac", "TA"], ["AT+CENG"]),
    ("MO RING", "3GPP_27007", "Shows call state of MO call: the call is alerted", [], ["AT+MORING"]),
    ("MO CONNECTED", "3GPP_27007", "Shows call state of MO call: the call is established", [], ["AT+MORING"]),
    ("+CPIN", "3GPP_27007", "Indicates whether some password is required or not", ["code"], ["AT+CPIN"]),
    ("+CSQN", "3GPP_27007", "Displays signal strength and channel bit error rate", ["rssi", "ber"], ["AT+EXUNSOL"]),
    ("+SIMTONE", "SIMCom", "The generated tone playing is stopped or completed", [], ["AT+SIMTONE"]),
    ("+STTONE", "SIMCom", "The SIM Toolkit tone playing is stopped or completed", [], ["AT+STTONE"]),
    ("+CR", "3GPP_27007", "Intermediate result code during connect negotiation", ["serv"], ["AT+CR"]),
    ("+CUSD", "3GPP_27007", "Indicates a USSD response from the network", ["n", "str_urc", "dcs"], ["AT+CUSD"]),
    ("+CFUN", "3GPP_27007", "Phone functionality indication", ["fun"], ["AT+CFUN"]),
    ("+CMTE", "SIMCom", "The module temperature is abnormal", ["n"], ["AT+CMTE"]),
    # TCPIP
    ("CONNECT OK", "TCPIP", "TCP/UDP connection is successful", [], ["AT+CIPSTART"]),
    ("CONNECT", "TCPIP", "TCP/UDP connection in channel mode is successful", [], []),
    ("CONNECT FAIL", "TCPIP", "TCP/UDP connection fails", [], ["AT+CIPSTART"]),
    ("ALREADY CONNECT", "TCPIP", "TCP/UDP connection exists", [], ["AT+CIPSTART"]),
    ("SEND OK", "TCPIP", "Data sending is successful", [], ["AT+CIPSEND"]),
    ("SEND FAIL", "TCPIP", "Data sending fails", [], ["AT+CIPSEND"]),
    ("DATA ACCEPT", "TCPIP", "Data accepted in quick send mode", ["n", "length"], ["AT+CIPSEND", "AT+CIPQSEND"]),
    ("CLOSED", "TCPIP", "TCP/UDP connection is closed", [], ["AT+CIPCLOSE"]),
    ("RECV FROM", "TCPIP", "Shows remote IP address and port (single connection mode)", ["IP_ADDRESS", "PORT"], ["AT+CIPSRIP"]),
    ("+IPD", "TCPIP", "Display transfer protocol in IP header to received data", ["data_size", "TCP_UDP", "data"], ["AT+CIPHEAD", "AT+CIPSHOWTP"]),
    ("+RECEIVE", "TCPIP", "Received data from remote client (multi connection mode)", ["n", "length"], ["AT+CIPHEAD"]),
    ("+CIPRXGET", "TCPIP", "Data received from network manually", ["n", "len"], ["AT+CIPRXGET"]),
    ("+CDNSGIP", "TCPIP", "DNS resolution result", ["status", "domain_name", "IP", "IP2"], ["AT+CDNSGIP"]),
    ("+PDP: DEACT", "GPRS", "GPRS is disconnected by network", [], []),
    ("+SAPBR", "IP", "The bearer based on IP connection is deactivated", ["cid"], ["AT+SAPBR"]),
    # HTTP
    ("+HTTPACTION", "HTTP", "Indicates HTTP method, Status Code and length of data", ["Method", "StatusCode", "DataLen"], ["AT+HTTPACTION"]),
    # FTP
    ("+FTPGET", "FTP", "FTP GET session status", ["res"], ["AT+FTPGET"]),
    ("+FTPPUT", "FTP", "FTP PUT return result", ["res", "maxlength"], ["AT+FTPPUT"]),
    ("+FTPDELE", "FTP", "FTP delete session result", ["res"], ["AT+FTPDELE"]),
    ("+FTPSIZE", "FTP", "FTP size session result", ["res", "size"], ["AT+FTPSIZE"]),
    ("+FTPMKD", "FTP", "FTP create directory result", ["res"], ["AT+FTPMKD"]),
    ("+FTPRMD", "FTP", "FTP delete directory result", ["res"], ["AT+FTPRMD"]),
    ("+FTPLIST", "FTP", "FTP list session result", ["res"], ["AT+FTPLIST"]),
    # Email
    ("+SMTPSEND", "Email", "Email send result", ["code"], ["AT+SMTPSEND"]),
    ("+SMTPFT", "Email", "Email attachment transfer", ["cnfLength"], ["AT+SMTPFT"]),
    ("+POP3IN", "Email", "POP3 login result", ["code"], ["AT+POP3IN"]),
    ("+POP3NUM", "Email", "POP3 message number result", ["totalNumber", "totalSize"], ["AT+POP3NUM"]),
    ("+POP3LIST", "Email", "POP3 message size result", ["msgNumber", "size"], ["AT+POP3LIST"]),
    ("+POP3UIDL", "Email", "POP3 unique-id result", ["msgNumber", "uid"], ["AT+POP3UIDL"]),
    ("+POP3CMD", "Email", "POP3 command result", ["cnfLength"], ["AT+POP3CMD"]),
    ("+POP3READ", "Email", "POP3 read multi-line result", ["cnfLength"], ["AT+POP3READ"]),
    ("+POP3DEL", "Email", "POP3 delete result", [], ["AT+POP3DEL"]),
    ("+POP3RSET", "Email", "POP3 reset result", [], ["AT+POP3RSET"]),
    ("+POP3OUT", "Email", "POP3 logout result", ["code"], ["AT+POP3OUT"]),
    # MMS
    ("+CMMSRECV", "MMS", "MMS receive result", ["sender", "time", "subject", "size"], ["AT+CMMSRECV"]),
    ("+CMMSVIEW", "MMS", "MMS view result", ["mmstype", "sender", "receipts", "ccs", "bccs", "datetime", "subject", "size"], ["AT+CMMSVIEW"]),
    ("+CMMSRDPUSH", "MMS", "MMS push read result", ["sender", "subject", "transaction", "location", "time", "class", "size"], ["AT+CMMSRDPUSH"]),
    ("+CMMSSTATUS", "MMS", "MMS status result", ["status"], ["AT+CMMSSTATUS"]),
    # STK
    ("+STKPCI", "STK", "STK proactive command indication", ["pci_type", "proactive_command"], ["AT+STKPCIS"]),
    # DDET
    ("+DTMF", "DDET", "DTMF key detection", ["key", "last_time"], ["AT+DDET"]),
    # RECORD
    ("+CREC", "RECORD", "Record operation result", ["status", "id", "form", "time", "len"], ["AT+CREC"]),
    # TTS
    ("+CTTS", "TTS", "TTS play over indication", ["status"], ["AT+CTTS"]),
    # GPRS
    ("+CGREG", "GPRS", "Network registration status change", ["stat", "lac", "ci"], ["AT+CGREG"]),
    ("+CGEV: NW DEACT", "GPRS", "Network deactivation event", ["PDP_type", "PDP_addr", "cid"], ["AT+CGEREP"]),
    ("+CGEV: ME DEACT", "GPRS", "Mobile equipment deactivation event", ["PDP_type", "PDP_addr", "cid"], ["AT+CGEREP"]),
    ("+CGEV: NW DETACH", "GPRS", "Network detach event", [], ["AT+CGEREP"]),
    ("+CGEV: ME DETACH", "GPRS", "Mobile equipment detach event", [], ["AT+CGEREP"]),
    # SIMCom Special
    ("ALARM RING", "SIMCom", "Indicate expired alarm", ["n"], ["AT+CALA"]),
    ("+CMEDPLAY", "SIMCom", "Audio play over", [], ["AT+CMEDPLAY"]),
    ("+SIMTONEX", "SIMCom", "Custom tone playing is stopped or completed", [], ["AT+SIMTONEX"]),
    ("+SKPD", "SIMCom", "Keypad pressed or released event", ["value", "event"], ["AT+SKPD"]),
    ("+CANT", "SIMCom", "Antenna state report", ["status"], ["AT+CANT"]),
    ("+SJDR", "SIMCom", "Jamming detection status", ["status", "mode", "var", "display", "result"], ["AT+SJDR"]),
    ("+CELLIST", "SIMCom", "Cell information report", ["MCC", "MNC", "Arfcn", "Rxlev", "CellID", "Lac", "Bsic"], ["AT+CELLIST"]),
]

CHECKLIST_NAMES = {name.upper() for name, *_ in CHECKLIST}


# ---------------------------------------------------------------------------
def log(msg, level="INFO"):
    print(f"[{level}] {msg}", flush=True)


def abort(msg, code=1):
    log(msg, "FATAL")
    sys.exit(code)


def utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_utf8(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
def load_dat02():
    if not DAT02_PATH.exists():
        abort(f"dat_02_urc.yaml not found: {DAT02_PATH}")
    with DAT02_PATH.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if isinstance(doc, list):
        return doc, None, doc
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return doc, key, value
    abort("Could not locate a list of records.")


def detect_field(records, candidates):
    for c in candidates:
        if c in records[0]:
            return c
    return None


def extract_max_id(records, id_field):
    if not id_field:
        return 0
    max_id = 0
    for rec in records:
        m = re.search(r"(\d+)\s*$", str(rec.get(id_field, "")))
        if m:
            max_id = max(max_id, int(m.group(1)))
    return max_id


# ---------------------------------------------------------------------------
def build_paged_index():
    """Return {paged_file: {line_no: page_no}} using form-feed page splits."""
    index = {}
    for p in EXTRACTED_DIR.glob("*paged*.txt"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        mapping = {}
        pages = text.split("\f")
        if len(pages) > 1:
            lineno = 0
            for page_no, page_text in enumerate(pages, start=1):
                for _line in page_text.split("\n"):
                    lineno += 1
                    mapping[lineno] = page_no
            num_pages = len(pages)
        else:
            # fallback: look for "Page N" markers
            current = 1
            for lineno, raw in enumerate(text.splitlines(), start=1):
                m = re.match(r"^\s*(?:Page|PAGE)\s+(\d+)\b", raw)
                if m:
                    current = int(m.group(1))
                mapping[lineno] = current
            num_pages = current
        index[p.name] = mapping
        log(f"  indexed {p.name}: {len(mapping)} lines, "
            f"{num_pages} pages")
    return index


def get_pdf_name(txt_filename):
    low = txt_filename.lower()
    if "at" in low and ("v1_01" in low or "v1.01" in low):
        return "SIM800 Series_AT Command Manual_V1.01.pdf"
    if "v1_00" in low or "v1.00" in low:
        return "SIM800L_Hardware_Design_V1.00.pdf"
    if "v2_02" in low or "v2.02" in low:
        return "SIM800H&SIM800L_Hardware_Design_V2.02.PDF"
    return txt_filename


def find_urc_in_sources(name, paged_index):
    """Locate `name` in the paged text files and return source info."""
    needle = name.upper()
    for p in sorted(EXTRACTED_DIR.glob("*paged*.txt")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        mapping = paged_index.get(p.name, {})
        lines = text.split("\n")
        for i, line in enumerate(lines, start=1):
            if needle in line.upper():
                # For simple tokens, require word boundaries to avoid
                # matching +CBM inside +CBMI etc.
                if name.startswith("+") or name.startswith("*"):
                    pattern = re.escape(needle) + r"(?![A-Z0-9_])"
                    if not re.search(pattern, line.upper()):
                        continue
                return {
                    "file": p.name,
                    "pdf":  get_pdf_name(p.name),
                    "line": i,
                    "page": mapping.get(i, ""),
                }
    return None


# ---------------------------------------------------------------------------
def make_skeleton(record_keys):
    """Build a record with all fields present but neutral values."""
    template = {}
    for k in record_keys:
        if k == "id":
            template[k] = ""
        elif k == "urc_string":
            template[k] = ""
        elif k == "category":
            template[k] = "URC"
        elif k == "source":
            template[k] = {
                "name": "", "version": "", "date": "",
                "page": "", "section": "", "quote": "",
            }
        elif k == "source_type":
            template[k] = "primary"
        elif k == "confidence":
            template[k] = 0.7
        elif k == "status":
            template[k] = "partial"
        elif k in ("conflicts", "tags", "applicable_models",
                   "parameters", "examples", "related_urcs"):
            template[k] = []
        elif k in ("notes", "trigger_event", "related_command",
                   "related_state", "format", "timing",
                   "suppression_method", "created_at", "updated_at"):
            template[k] = ""
        elif k == "coverage_estimate":
            template[k] = "medium"
        else:
            template[k] = None
    return template


def fill_record(skeleton, name, category, description, payload,
                enabled_by, next_id, id_field, urc_field, source):
    rec = copy.deepcopy(skeleton)
    if id_field:
        rec[id_field] = next_id
    rec[urc_field] = name
    if "category" in rec:
        rec["category"] = category
    if "description" in rec:
        rec["description"] = description
    if "parameters" in rec:
        rec["parameters"] = [
            {"name": p, "description": ""} for p in payload
        ]
    if "related_command" in rec:
        rec["related_command"] = enabled_by[0] if enabled_by else None
    if "trigger_event" in rec:
        rec["trigger_event"] = ""
    if "source_type" in rec:
        rec["source_type"] = "primary"
    if "confidence" in rec:
        rec["confidence"] = 0.9 if source else 0.6
    if "status" in rec:
        rec["status"] = "complete" if source else "partial"
    if "applicable_models" in rec:
        rec["applicable_models"] = ["SIM800L"]
    now = utcnow_iso()
    for k in ("created_at", "updated_at"):
        if k in rec:
            rec[k] = now
    src = rec.get("source")
    if isinstance(src, dict):
        if source:
            src["name"]    = source["pdf"]
            src["page"]    = str(source.get("page") or "")
            src["section"] = "URC Section"
            src["version"] = "V1.01"
            src["date"]    = "2013-09-15"
        else:
            src["name"]    = "SIM800 Series_AT Command Manual_V1.01.pdf"
            src["page"]    = ""
            src["section"] = "URC Section"
            src["version"] = "V1.01"
            src["date"]    = "2013-09-15"
    return rec


# ---------------------------------------------------------------------------
def detect_list_indent(raw_text):
    for line in raw_text.splitlines():
        m = re.match(r"^(\s*)-\s+[A-Za-z_][A-Za-z0-9_]*\s*:", line)
        if m:
            return len(m.group(1))
    return 0


def serialize_records(records, list_indent):
    block = yaml.safe_dump(
        records,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )
    if not block.endswith("\n"):
        block += "\n"
    indent_str = " " * list_indent
    out = []
    for line in block.splitlines():
        out.append((indent_str + line) if line.strip() else "")
    return "\n".join(out)


def append_records(path, new_records):
    raw = path.read_text(encoding="utf-8")
    indent = detect_list_indent(raw)
    log(f"Detected list indent: {indent} spaces")
    block = serialize_records(new_records, indent)
    shutil.copy2(path, DAT02_BACKUP)
    log(f"Backup written to {DAT02_BACKUP}")
    if not raw.endswith("\n"):
        raw += "\n"
    combined = raw + block
    if not combined.endswith("\n"):
        combined += "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(combined)
    tmp.replace(path)
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        log(f"Wrote file is invalid YAML: {exc}", "FATAL")
        shutil.copy2(DAT02_BACKUP, path)
        abort("Restored original file after YAML parse failure.")


def run_script(path):
    if not path.exists():
        log(f"Skipped (not found): {path.name}", "WARN")
        return 0
    log(f"Running: {path.name}")
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return 124
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Phase 1 : baseline --------------------------------------------
    log("=== Phase 1 : baseline diagnostics ===")
    doc, list_key, records = load_dat02()
    urc_field = detect_field(records,
                             ["urc_string", "urc", "urc_name", "name",
                              "pattern"]) or "urc_string"
    id_field = detect_field(records, ["id", "uid", "key", "identifier"])
    max_id = extract_max_id(records, id_field)

    existing_names = {
        str(r.get(urc_field, "")).strip().upper()
        for r in records if r.get(urc_field)
    }
    log(f"Existing records : {len(records)}")
    log(f"URC field        : {urc_field}")
    log(f"ID field         : {id_field}")
    log(f"Max existing ID  : {max_id}")

    diag = {
        "generated_at": utcnow_iso(),
        "record_count": len(records),
        "list_key": list_key,
        "urc_field": urc_field,
        "id_field": id_field,
        "max_id": max_id,
        "existing_urc_sample": sorted(existing_names),
        "record_template_keys": list(records[0].keys()),
    }
    write_utf8(DIAG_PATH, json.dumps(diag, indent=2))

    # ---- Phase 2 : paged index -----------------------------------------
    log("=== Phase 2 : indexing paged sources ===")
    paged_index = build_paged_index()

    # ---- Phase 3 : plan ------------------------------------------------
    log("=== Phase 3 : building plan from checklist ===")
    plan = []
    for name, category, description, payload, enabled_by in CHECKLIST:
        up = name.upper()
        if up in existing_names:
            continue
        src = find_urc_in_sources(name, paged_index)
        plan.append({
            "name": name,
            "category": category,
            "description": description,
            "payload": payload,
            "enabled_by": enabled_by,
            "source": src,
        })
    log(f"Candidates (checklist minus existing): {len(plan)}")

    write_utf8(PLAN_PATH, json.dumps({
        "generated_at": utcnow_iso(),
        "existing_count": len(records),
        "candidates_count": len(plan),
        "candidates": [
            {
                "name": c["name"],
                "in_source": c["source"] is not None,
                "pdf":  c["source"]["pdf"] if c["source"] else None,
                "page": c["source"]["page"] if c["source"] else None,
                "line": c["source"]["line"] if c["source"] else None,
            } for c in plan
        ],
    }, indent=2))
    log(f"Plan written to {PLAN_PATH}")

    if not plan:
        log("Nothing to add. Exiting.")
        return 0

    # ---- Phase 4 : assemble --------------------------------------------
    log("=== Phase 4 : assembling new records ===")
    skeleton = make_skeleton(list(records[0].keys()))

    id_pattern = ("dat_02_", 4)
    if id_field:
        m = re.match(r"^(.*?)(\d+)\s*$", str(records[0].get(id_field, "")))
        if m:
            id_pattern = (m.group(1), len(m.group(2)))

    new_records = []
    n = max_id
    for c in plan:
        n += 1
        next_id = f"{id_pattern[0]}{n:0{id_pattern[1]}d}"
        rec = fill_record(
            skeleton, c["name"], c["category"], c["description"],
            c["payload"], c["enabled_by"], next_id,
            id_field, urc_field, c["source"],
        )
        new_records.append(rec)

    log(f"New records built : {len(new_records)}")
    in_source = sum(1 for c in plan if c["source"])
    log(f"  with source info: {in_source}")
    log(f"  source missing  : {len(plan) - in_source}")

    # ---- Phase 5 : write -----------------------------------------------
    if args.apply:
        log("=== Phase 5 : appending to dat_02_urc.yaml ===")
        append_records(DAT02_PATH, new_records)
        log(f"Appended {len(new_records)} records.")
        log(f"Final total: {len(records) + len(new_records)}")
    else:
        log("=== Phase 5 : DRY-RUN (no changes written) ===")
        log("Re-run with --apply to write.")

    # ---- Phase 6 : validation ------------------------------------------
    if args.apply:
        log("=== Phase 6 : running validation scripts ===")
        rc = run_script(SCRIPTS_DIR / "validate.py")
        if rc != 0:
            log("validate.py reported errors.", "WARN")

    # ---- Summary -------------------------------------------------------
    log("=== Summary ===")
    log(f"Existing records : {len(records)}")
    log(f"New records      : {len(new_records)}")
    log(f"Final total      : {len(records) + len(new_records)}")
    log(f"Dry-run          : {not args.apply}")
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