import unittest

from check_personal_data import find_violations


class FindViolationsTest(unittest.TestCase):
    def test_blocks_documents_and_data(self):
        paths = ["Resume_2026.pdf", "data/jobs.json", "notes/cover-letter.md", "export.csv", ".env", "src/CV.txt"]
        self.assertEqual(len(find_violations(paths)), 6, find_violations(paths))

    def test_allows_safe_paths(self):
        paths = ["tests/fixtures/sample_resume.pdf", ".env.example", "scripts/csv_utils.py",
                 "docs/adr/0003-personal-data-outside-repo.md", "src/metadata.py"]
        self.assertEqual(find_violations(paths), [])

    def test_more_blocked_forms(self):
        for path in ["résumé.md", "my_cv.md", "CoverLetter.docx", "x/job-search-data/a.json",
                     ".env.local", "offer.xlsx", "letter.odt", "notes.rtf", "notes.pages", "a.doc", "b.xls"]:
            with self.subTest(path=path):
                self.assertEqual(len(find_violations([path])), 1)

    def test_more_allowed_forms(self):
        for path in ["scripts/check_personal_data.py", "docs/curve.md", "src/cvss_score.py", "src/database.py",
                     "src/datastore/x.py", ".github/workflows/ci.yml", "tests/fixtures/data/jobs.csv"]:
            with self.subTest(path=path):
                self.assertEqual(find_violations([path]), [])


if __name__ == "__main__":
    unittest.main()


import contextlib  # noqa: E402
import io  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

from check_personal_data import main  # noqa: E402


class RealGitOutputTest(unittest.TestCase):
    """Run main() against a real git repo, so git's own output format is exercised."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        subprocess.run(["git", "init", "-q", self.root], check=True)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.root)

    def stage(self, name: str) -> None:
        open(name, "w").close()
        subprocess.run(["git", "add", "-f", name], check=True)

    def run_main(self, *argv) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return main(list(argv))

    def test_non_ascii_names_blocked_when_staged(self):
        self.stage("résumé.md")
        self.assertEqual(self.run_main("--staged"), 1)

    def test_non_ascii_names_blocked_in_tracked_files(self):
        self.stage("Lebenslauf_Café.pdf")
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x",
                        "--no-verify"], check=True)
        self.assertEqual(self.run_main(), 1)

    def test_clean_repo_passes(self):
        self.stage("notes.md")
        self.assertEqual(self.run_main("--staged"), 0)


class ResumeNameFormsTest(unittest.TestCase):
    def test_camel_case_and_digits(self):
        for path in ["MyResume.md", "Resume2026.md", "JaneDoe_CV2026.txt", "myCoverLetter.md", "CV.md"]:
            with self.subTest(path=path):
                self.assertEqual(len(find_violations([path])), 1)

    def test_lookalikes_still_allowed(self):
        for path in ["scripts/csv_utils.py", "src/cvss_score.py", "docs/curve.md", "src/recover.py"]:
            with self.subTest(path=path):
                self.assertEqual(find_violations([path]), [])


class DecomposedUnicodeTest(unittest.TestCase):
    def test_macos_decomposed_accents(self):
        import unicodedata
        self.assertEqual(len(find_violations([unicodedata.normalize("NFD", "résumé.md")])), 1)
