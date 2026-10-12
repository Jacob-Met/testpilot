"""Focused public recheck timeout admission and error-boundary regressions."""
import sys
import unittest
from unittest.mock import patch

from testpilot import recheck


class RecheckTimeoutOverflowTests(unittest.TestCase):
    def assert_refused_before_admission(self, value):
        with (
            patch.object(recheck.Path, "resolve", side_effect=AssertionError("repository admission reached")) as resolve,
            patch.object(recheck, "read_saved_tests", side_effect=AssertionError("report read reached")) as read,
            patch.object(recheck, "run_pytest", side_effect=AssertionError("pytest reached")) as run,
        ):
            with self.assertRaises(recheck.RecheckError) as caught:
                recheck.recheck_report("unused-project", "unused-report.json", timeout_s=value)
            self.assertEqual(str(caught.exception), "timeout must be a positive finite number of seconds")
            resolve.assert_not_called()
            read.assert_not_called()
            run.assert_not_called()

    def test_unrepresentable_integers_use_the_recheck_error(self):
        for value in (10**400, -(10**400)):
            with self.subTest(positive=value > 0):
                self.assert_refused_before_admission(value)

    def test_existing_invalid_timeout_refusals_are_preserved(self):
        for value in (True, False, None, "60", [], 0, -1, -0.25,
                      float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value):
                self.assert_refused_before_admission(value)

    def test_positive_representable_numbers_reach_repository_admission(self):
        for value in (1, 0.25, 60.0, 10**100, 2**1023, sys.float_info.max):
            with self.subTest(value=value):
                admitted = RuntimeError("repository admission boundary")
                with (
                    patch.object(recheck.Path, "resolve", side_effect=admitted) as resolve,
                    patch.object(recheck, "read_saved_tests") as read,
                    patch.object(recheck, "run_pytest") as run,
                ):
                    with self.assertRaises(RuntimeError) as caught:
                        recheck.recheck_report("unused-project", "unused-report.json", timeout_s=value)
                    self.assertIs(caught.exception, admitted)
                    resolve.assert_called_once_with(strict=True)
                    read.assert_not_called()
                    run.assert_not_called()

    def test_admitted_float_subclass_keeps_its_existing_comparison_protocol(self):
        class PositiveFloat(float):
            def __gt__(self, other):
                raise RuntimeError("unexpected greater-than comparison")

        admitted = RuntimeError("repository admission boundary")
        with (
            patch.object(recheck.Path, "resolve", side_effect=admitted) as resolve,
            patch.object(recheck, "read_saved_tests") as read,
            patch.object(recheck, "run_pytest") as run,
        ):
            with self.assertRaises(RuntimeError) as caught:
                recheck.recheck_report("unused-project", "unused-report.json",
                                       timeout_s=PositiveFloat(0.125))
            self.assertIs(caught.exception, admitted)
            resolve.assert_called_once_with(strict=True)
            read.assert_not_called()
            run.assert_not_called()

    def test_later_overflow_is_not_reclassified_as_invalid_timeout(self):
        later_error = OverflowError("repository admission overflow")
        with (
            patch.object(recheck.Path, "resolve", side_effect=later_error),
            patch.object(recheck, "read_saved_tests") as read,
            patch.object(recheck, "run_pytest") as run,
        ):
            with self.assertRaises(OverflowError) as caught:
                recheck.recheck_report("unused-project", "unused-report.json", timeout_s=60)
            self.assertIs(caught.exception, later_error)
            read.assert_not_called()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
