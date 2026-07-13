"""
Thin wrapper around the Gemini API used by every stage of the recruitment
pipeline. Centralising it here means:
  - one place to swap models / retry / handle rate limits
  - one place that enforces "always return JSON" behaviour
  - pipeline stages stay easy to read / unit test
"""
import json
import re
import logging

try:
    import google.generativeai as genai
except Exception as exc:  # pragma: no cover - import may fail in stripped environments
    genai = None
    _GENAI_IMPORT_ERROR = exc
else:
    _GENAI_IMPORT_ERROR = None

from app.config import settings

logger = logging.getLogger("gemini_client")

_configured = False


def _ensure_configured() -> bool:
    global _configured
    if _configured:
        return True

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set; using empty fallback JSON for pipeline stages.")
        _configured = True
        return False

    if genai is None:
        logger.warning("google-generativeai is unavailable (%s); using empty fallback JSON.", _GENAI_IMPORT_ERROR)
        _configured = True
        return False

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Could not configure Gemini client: %s", exc)
        _configured = True
        return False

    _configured = True
    return True


def _extract_json(text: str):
    """Gemini sometimes wraps JSON in ```json fences or adds stray prose. Strip it."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    # Fallback: grab the first {...} or [...] block
    if not (text.startswith("{") or text.startswith("[")):
        obj_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if obj_match:
            text = obj_match.group(1)
    return json.loads(text)


def generate_json(system_instruction: str, user_prompt: str, max_retries: int = 2) -> dict:
    """
    Calls Gemini with a system instruction + user prompt and expects a JSON object
    back. Retries on parse failure by asking the model to fix its own output.
    """
    if not _ensure_configured():
        return {}

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config={"response_mime_type": "application/json", "temperature": 0.1},
    )

    last_err = None
    prompt = user_prompt
    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(prompt)
            raw = response.text or ""
            return _extract_json(raw)
        except Exception as exc:  # noqa: BLE001 - want to catch parse + API errors alike
            last_err = exc
            logger.warning("Gemini call failed (attempt %s): %s", attempt + 1, exc)
            prompt = (
                user_prompt
                + "\n\nIMPORTANT: Your previous response could not be parsed as valid JSON. "
                  "Return ONLY a single valid JSON object/array, with no markdown fences and no commentary."
            )

    logger.warning("Gemini did not return parseable JSON after retries; falling back to empty data: %s", last_err)
    return {}
