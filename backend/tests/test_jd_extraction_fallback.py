import unittest

from app.pipeline import stage1_jd_extraction


class JDExtractionFallbackTests(unittest.TestCase):
    def test_heuristic_fallback_extracts_basic_fields(self):
        document_text = """
        IHMCL Recruitment Notice

        Position: Senior Software Engineer
        Department: ITS / Digital Solutions
        Experience: 3 to 5 years
        Skills: Python, SQL, FastAPI
        Qualification: B.Tech in Computer Science
        Location: Mumbai
        Age Limit: 35 years
        """

        result = stage1_jd_extraction.run(document_text)
        self.assertEqual(result["criteria"]["title"], "Senior Software Engineer")
        self.assertEqual(result["criteria"]["department"], "ITS / Digital Solutions")
        self.assertEqual(result["criteria"]["minExp"], 3)
        self.assertEqual(result["criteria"]["maxExp"], 5)
        self.assertEqual(result["criteria"]["skills"][0]["name"], "Python")
        self.assertEqual(result["criteria"]["location"], "Mumbai")


if __name__ == "__main__":
    unittest.main()
