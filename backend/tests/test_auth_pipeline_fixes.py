import unittest
from unittest.mock import patch

from app import gemini_client


class GeminiClientFallbackTests(unittest.TestCase):
    def test_generate_json_returns_empty_object_without_gemini_key(self):
        with patch.object(gemini_client.settings, "GEMINI_API_KEY", ""), patch.object(gemini_client, "_configured", False):
            result = gemini_client.generate_json("system instruction", "user prompt")

        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
