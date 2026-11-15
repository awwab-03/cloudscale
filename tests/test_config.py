"""Unit tests for app/config.py caching and defaults. No AWS calls are made: boto3 clients are
replaced with stubs. Run from the repository root with:  python -m unittest discover tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import config  # noqa: E402


class CachedTests(unittest.TestCase):
    def setUp(self):
        config._cache.clear()

    def test_loader_runs_once_within_ttl(self):
        loader = mock.Mock(return_value="v")
        self.assertEqual(config._cached("k", 60, loader), "v")
        self.assertEqual(config._cached("k", 60, loader), "v")
        loader.assert_called_once()

    def test_loader_runs_again_after_ttl(self):
        loader = mock.Mock(side_effect=["a", "b"])
        with mock.patch("config.time.time", side_effect=[0, 100]):
            self.assertEqual(config._cached("k", 60, loader), "a")
            self.assertEqual(config._cached("k", 60, loader), "b")
        self.assertEqual(loader.call_count, 2)


class StressFlagTests(unittest.TestCase):
    def setUp(self):
        config._cache.clear()

    def _stub(self, value=None, error=None):
        client = mock.Mock()
        if error:
            client.get_parameter.side_effect = error
        else:
            client.get_parameter.return_value = {"Parameter": {"Value": value}}
        return mock.patch("config.boto3.client", return_value=client)

    def test_true_enables(self):
        with self._stub(" True "):
            self.assertTrue(config.stress_enabled())

    def test_false_disables(self):
        with self._stub("false"):
            self.assertFalse(config.stress_enabled())

    def test_ssm_failure_disables(self):
        with self._stub(error=RuntimeError("boom")):
            self.assertFalse(config.stress_enabled())


class ConstantsTests(unittest.TestCase):
    def test_upload_limit_is_5_mib(self):
        self.assertEqual(config.MAX_UPLOAD_BYTES, 5 * 1024 * 1024)

    def test_categories_unique_and_include_other(self):
        self.assertEqual(len(config.CATEGORIES), len(set(config.CATEGORIES)))
        self.assertIn("Other", config.CATEGORIES)


if __name__ == "__main__":
    unittest.main()
