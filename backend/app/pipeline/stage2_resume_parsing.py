"""
STAGE 2 — Candidate Document Parsing
Input:  resume/CV text (with [PAGE n] markers) for one candidate, plus whatever
        row data came from the recruiter's Excel sheet.
Output: normalized parsedFormData used by the frontend candidate cards:
        { dob, education, highest_degree, experience_years, skills, idNumber }
"""
from app.gemini_client import generate_json

SYSTEM_INSTRUCTION = """You are an information-extraction engine for an HR screening system. You \
read a candidate's resume/CV (and any supporting documents) and pull out clean, structured fields \
as JSON. Only use what is stated or clearly inferable from the text — never fabricate numbers or \
dates. If something is missing, use null or an empty value."""

PROMPT_TEMPLATE = """Candidate reference: {reference_number}
Name (from application sheet, may be blank): {candidate_name}

Extract the candidate's profile and return ONLY this JSON shape:
{{
  "dob": "<DD-MM-YYYY or null>",
  "education": "<one-line summary, e.g. 'B.Tech Computer Science, XYZ University'>",
  "highest_degree": "<e.g. B.Tech, M.Tech, MBA, CA>",
  "experience_years": <number, total years of relevant professional experience, best estimate>,
  "skills": ["<skill1>", "<skill2>", "..."],
  "idNumber": "<any government/roll/registration ID number found, e.g. ICAI membership no, or null>"
}}

Output strictly valid JSON, no markdown fences, no commentary.

RESUME / DOCUMENT TEXT:
---
{document_text}
---
"""


def run(reference_number: str, candidate_name: str, document_text: str) -> dict:
    if not document_text.strip():
        return {
            "dob": None, "education": None, "highest_degree": None,
            "experience_years": 0, "skills": [], "idNumber": None,
        }

    prompt = PROMPT_TEMPLATE.format(
        reference_number=reference_number,
        candidate_name=candidate_name or "(unknown)",
        document_text=document_text[:120000],
    )
    result = generate_json(SYSTEM_INSTRUCTION, prompt)
    if not isinstance(result, dict):
        result = {}

    result.setdefault("dob", None)
    result.setdefault("education", None)
    result.setdefault("highest_degree", None)
    result.setdefault("experience_years", 0)
    result.setdefault("skills", [])
    result.setdefault("idNumber", None)
    return result
