import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from workflow.github import GitHub, repo_slug


class RecordingRunner:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.calls: list[list[str]] = []
        self.result = SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        return self.result


class GitHubClientTest(unittest.TestCase):
    def test_list_calls_paginate(self):
        runner = RecordingRunner('[[{"number":1}],[{"number":2,"pull_request":{}}]]')
        self.assertEqual(GitHub("o/r", runner).issues("task"), [{"number": 1}])
        args = runner.calls[0]
        self.assertEqual(args[:2], ["gh", "api"])
        self.assertIn("--paginate", args)
        self.assertIn("--slurp", args)
        self.assertIn("repos/o/r/issues?labels=task&state=all&per_page=100", args)

    def test_timeline_and_sub_issues_flatten_pages(self):
        runner = RecordingRunner('[[{"event":"labeled"}],[{"event":"closed"}]]')
        gh = GitHub("o/r", runner)
        self.assertEqual(gh.timeline(5), [{"event": "labeled"}, {"event": "closed"}])
        self.assertIn("repos/o/r/issues/5/timeline?per_page=100", runner.calls[0])
        gh.sub_issues(42)
        self.assertIn("repos/o/r/issues/42/sub_issues?per_page=100", runner.calls[1])
        self.assertIn("--paginate", runner.calls[1])

    def test_single_issue(self):
        runner = RecordingRunner('{"number": 7}')
        self.assertEqual(GitHub("o/r", runner).issue(7), {"number": 7})
        self.assertEqual(runner.calls[0], ["gh", "api", "repos/o/r/issues/7"])

    def test_error_raises(self):
        runner = RecordingRunner(returncode=1, stderr="boom")
        with self.assertRaisesRegex(RuntimeError, "boom"):
            GitHub("o/r", runner).issue(1)


class RepoSlugTest(unittest.TestCase):
    def _repo_with_remote(self, url: str) -> Path:
        tmp = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", tmp], check=True)
        subprocess.run(["git", "-C", tmp, "remote", "add", "origin", url], check=True)
        return Path(tmp)

    def test_repo_slug_forms(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_REPOSITORY", None)
            for url in ("https://github.com/aholt21754/job-search.git",
                        "https://github.com/aholt21754/job-search",
                        "git@github.com:aholt21754/job-search.git",
                        "http://local_proxy@127.0.0.1:1234/git/aholt21754/job-search"):
                with self.subTest(url=url):
                    self.assertEqual(repo_slug(self._repo_with_remote(url)), "aholt21754/job-search")

    def test_env_takes_precedence(self):
        root = self._repo_with_remote("https://github.com/aholt21754/job-search.git")
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "other/repo"}):
            self.assertEqual(repo_slug(root), "other/repo")


if __name__ == "__main__":
    unittest.main()
