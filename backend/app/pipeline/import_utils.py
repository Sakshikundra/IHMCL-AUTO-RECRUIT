import os
import re
import zipfile

import openpyxl
import pandas as pd


def _rows_from_xlsx(path: str) -> list[tuple]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    return list(ws.iter_rows(values_only=True))


def _rows_from_legacy_xls_or_csv(path: str) -> list[tuple]:
    """
    Handles legacy .xls (via the xlrd engine) and .csv files, which openpyxl
    cannot read. Returns the same [(row1_cells...), (row2_cells...)] shape
    that _rows_from_xlsx produces, header row included.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(path, header=None, dtype=object)
    else:
        df = pd.read_excel(path, header=None, dtype=object, engine="xlrd")
    df = df.where(pd.notnull(df), None)
    return [tuple(row) for row in df.values.tolist()]


def parse_candidate_excel(path: str) -> list[dict]:
    """
    Reads a recruiter-provided candidate sheet. Expected (case-insensitive, flexible)
    header names: Reference/Reference Number, Name/Candidate Name, Email.
    Any other columns are ignored gracefully. Supports modern .xlsx/.xlsm (openpyxl),
    legacy .xls (xlrd), and .csv files.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        rows = _rows_from_xlsx(path)
    elif ext in (".xls", ".csv"):
        rows = _rows_from_legacy_xls_or_csv(path)
    else:
        # Unknown extension - try modern format first, fall back to legacy
        try:
            rows = _rows_from_xlsx(path)
        except Exception:
            rows = _rows_from_legacy_xls_or_csv(path)

    if not rows:
        return []

    headers = [str(h).strip().lower() if h else "" for h in rows[0]]

    def find_col(*names):
        for name in names:
            for i, h in enumerate(headers):
                if name in h:
                    return i
        return None

    ref_col = find_col("reference", "ref no", "ref_no", "application id", "sno", "s.no")
    name_col = find_col("name")
    email_col = find_col("email")

    candidates = []
    for idx, row in enumerate(rows[1:], start=1):
        if row is None or all(c is None for c in row):
            continue
        ref = str(row[ref_col]).strip() if ref_col is not None and row[ref_col] is not None else f"APP{idx:04d}"
        name = str(row[name_col]).strip() if name_col is not None and row[name_col] is not None else ""
        email = str(row[email_col]).strip() if email_col is not None and row[email_col] is not None else ""
        candidates.append({"reference_number": ref, "candidate_name": name, "candidate_email": email})

    return candidates


def extract_zip(zip_path: str, dest_dir: str) -> list[str]:
    """Extracts a ZIP of candidate documents and returns the list of extracted file paths."""
    os.makedirs(dest_dir, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            target = os.path.join(dest_dir, os.path.basename(member))
            with zf.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
            extracted.append(target)
    return extracted


def match_resume_for_candidate(files: list[str], reference_number: str, candidate_name: str) -> str | None:
    """
    Best-effort match between a candidate and one of the extracted files, similar to
    the IHMCL naming convention '<id>_<Name>-Resume.pdf'. Prefers files whose name
    contains 'resume' or 'cv', then falls back to name/reference matching.
    """
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    ref_n = norm(reference_number)
    name_n = norm(candidate_name)
    name_tokens = [norm(t) for t in (candidate_name or "").split() if len(t) > 2]

    pdf_files = [f for f in files if f.lower().endswith(".pdf")]

    def score(fname: str) -> int:
        base = norm(os.path.basename(fname))
        s = 0
        if ref_n and ref_n in base:
            s += 5
        if name_n and name_n in base:
            s += 5
        s += sum(1 for t in name_tokens if t in base)
        if "resume" in base or "cv" in base:
            s += 2
        return s

    if not pdf_files:
        return None

    best = max(pdf_files, key=score)
    return best if score(best) > 0 else pdf_files[0]