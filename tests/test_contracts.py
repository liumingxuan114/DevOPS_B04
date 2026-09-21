import unittest
from pathlib import Path

from jsonschema.exceptions import ValidationError

import validate


class ContractTests(unittest.TestCase):
    def test_four_valid_requests(self):
        paths = sorted(validate.REQUEST_DIR.glob("*.json"))
        self.assertEqual(4, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                validate.validate_request(path)

    def test_four_successful_job_responses(self):
        paths = sorted(validate.RESPONSE_DIR.glob("*-succeeded.json"))
        self.assertEqual(4, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                validate.validate_job(path)

    def test_schema_invalid_examples_are_rejected(self):
        for name in ["bad-job-type.json", "incremental-missing-baseline.json"]:
            with self.subTest(path=name), self.assertRaises(ValidationError):
                validate.validate_request(validate.INVALID_DIR / name)

    def test_semantic_invalid_examples_are_rejected(self):
        for name in [
            "incremental-baseline-mismatch.json",
            "repair-with-redundant-finding.json",
        ]:
            with self.subTest(path=name), self.assertRaises(ValueError):
                validate.validate_request(validate.INVALID_DIR / name)

    def test_no_example_uses_short_commit(self):
        for path in Path(validate.ROOT / "examples").rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn('"commit": "1111111"', text, path)


if __name__ == "__main__":
    unittest.main()
