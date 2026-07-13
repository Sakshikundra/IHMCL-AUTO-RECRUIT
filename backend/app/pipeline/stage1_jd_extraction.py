"""
STAGE 1 — Job Description Extraction
Input:  raw text of an uploaded JD PDF (e.g. an IHMCL recruitment advertisement)
Output: structured criteria matching the shape the frontend's CriteriaEditor expects:
        { criteria: { title, department, minExp, maxExp, skills, educationReqs,
                       location, customRules }, confidence, warnings }
"""
import re

from app.gemini_client import generate_json

SYSTEM_INSTRUCTION = """You are a meticulous HR analyst for Indian Highways Management Company \
Limited (IHMCL), a public-sector highway tolling & ITS company. You read Job Description / \
recruitment-advertisement documents (often containing MULTIPLE posts in one PDF, as IHMCL \
advertisements typically do) and extract clean, structured hiring criteria for ONE specific post \
at a time as valid JSON. Never invent facts that are not in the text. If a field cannot be \
determined, use a sensible empty value (0, "", [] as appropriate) and add a note to `warnings`."""

PROMPT_TEMPLATE = """Below is the extracted text of a job advertisement PDF (page markers included).
It may list several posts/designations in one document.

TARGET POST HINT (may be blank if the caller doesn't know yet): "{post_hint}"

Extract hiring criteria and return ONLY this JSON shape:
{{
  "criteria": {{
    "title": "<designation/post name>",
    "department": "<company / department / grade, short>",
    "minExp": <integer years, essential/minimum experience>,
    "maxExp": <integer years, 0 if no explicit maximum is stated>,
    "skills": [{{"name": "<skill or domain expertise>", "mandatory": true|false}}],
    "educationReqs": [{{"degree": "<degree>", "field": "<field/branch>", "mandatory": true|false}}],
    "location": "<location requirement, empty string if all-India / not specified>",
    "customRules": [{{"fieldName": "<e.g. Age Limit, Pay Scale, Method of Recruitment>", "condition": "equals|lte|gte|range", "value": "<value>"}}]
  }},
  "confidence": <integer 0-100, your confidence that this extraction is accurate>,
  "warnings": ["<short string, e.g. 'Document contains multiple posts, extracted the closest match'>"]
}}

Rules:
- If the document lists multiple posts and TARGET POST HINT matches one of them (by title or partial
  text), extract that post's criteria only. Otherwise extract the FIRST/primary post and say so in warnings.
- Essential experience -> minExp/mandatory skills. Preferred/desirable experience -> skills with mandatory:false.
- Age limit, pay scale, recruitment mode etc. belong in customRules, not skills/education.
- Output strictly valid JSON, no markdown fences, no commentary.

DOCUMENT TEXT:
---
{document_text}
---
"""


def _heuristic_extract(document_text: str, post_hint: str = "") -> dict:
    text = (document_text or "").strip()
    title = ""
    if post_hint:
        title = post_hint.strip()
    else:
        match = re.search(r"(?:position|designation|post)\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()

    department = ""
    match = re.search(r"(?:department|division|branch)\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        department = match.group(1).strip()

    min_exp = 0
    max_exp = 0
    exp_match = re.search(r"experience\s*[:\-]\s*(\d+)\s*(?:to|-)\s*(\d+)\s*years", text, re.IGNORECASE)
    if exp_match:
        min_exp = int(exp_match.group(1))
        max_exp = int(exp_match.group(2))
    else:
        single_match = re.search(r"experience\s*[:\-]\s*(\d+)\s*years", text, re.IGNORECASE)
        if single_match:
            min_exp = int(single_match.group(1))
            max_exp = int(single_match.group(1))

    skills = []
    skills_match = re.search(r"skills\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if skills_match:
        skill_text = skills_match.group(1).strip()
        for raw_skill in re.split(r"[,;]+", skill_text):
            skill = raw_skill.strip()
            if skill:
                skills.append({"name": skill, "mandatory": True})

    education = []
    edu_match = re.search(r"qualification\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if edu_match:
        education.append({"degree": edu_match.group(1).strip(), "field": "", "mandatory": True})

    location = ""
    loc_match = re.search(r"location\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(1).strip()

    custom_rules = []
    age_match = re.search(r"age\s*limit\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if age_match:
        custom_rules.append({"fieldName": "Age Limit", "condition": "equals", "value": age_match.group(1).strip()})

    return {
        "criteria": {
            "title": title,
            "department": department,
            "minExp": min_exp,
            "maxExp": max_exp,
            "skills": skills,
            "educationReqs": education,
            "location": location,
            "customRules": custom_rules,
        },
        "confidence": 55,
        "warnings": ["Used heuristic extraction because the AI service did not return structured JSON."],
    }


def run(document_text: str, post_hint: str = "") -> dict:
    prompt = PROMPT_TEMPLATE.format(
        post_hint=post_hint or "(none given — pick the primary/first post)",
        document_text=document_text[:120000],  # keep prompt bounded
    )
    result = generate_json(SYSTEM_INSTRUCTION, prompt)

    if isinstance(result, dict) and result.get("criteria"):
        criteria = result.get("criteria", {})
        criteria.setdefault("title", "")
        criteria.setdefault("department", "")
        criteria.setdefault("minExp", 0)
        criteria.setdefault("maxExp", 0)
        criteria.setdefault("skills", [])
        criteria.setdefault("educationReqs", [])
        criteria.setdefault("location", "")
        criteria.setdefault("customRules", [])

        return {
            "criteria": criteria,
            "confidence": result.get("confidence", 60) if isinstance(result, dict) else 50,
            "warnings": result.get("warnings", []) if isinstance(result, dict) else [],
        }

    return _heuristic_extract(document_text, post_hint=post_hint)
