import re
import unittest
from pathlib import Path

CI = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def permissions_block(text: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index("permissions:")
    block = []
    for line in lines[start + 1:]:
        if not line.startswith("  "):
            break
        block.append(line.strip())
    return block


class CiWorkflowTest(unittest.TestCase):
    def test_ci_permissions_read_only(self):
        text = CI.read_text()
        block = permissions_block(text)
        self.assertTrue(block, "top-level permissions block is empty")
        for line in block:
            self.assertTrue(line.endswith("read"), line)
        for forbidden in ("write", "pull_request_target", "secrets."):
            self.assertNotIn(forbidden, text)

    def test_ci_job_id(self):
        self.assertRegex(CI.read_text(), re.compile(r"^  checks:$", re.M))


if __name__ == "__main__":
    unittest.main()
