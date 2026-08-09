import argparse
import contextlib
import io
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import run_eval_litellm
from run_eval_litellm import ask, parse_header


class RecordingCompletion:
    def __init__(self, contents=None):
        self.calls = []
        self.contents = iter(contents or [" 2 \n"])

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        content = next(self.contents)
        message = (content if isinstance(content, SimpleNamespace)
                   else SimpleNamespace(content=content))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class HeaderParserTests(unittest.TestCase):
    def test_parses_header_name_and_value(self):
        self.assertEqual(
            parse_header("X-Test-App=example"),
            ("X-Test-App", "example"),
        )

    def test_rejects_header_without_separator(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_header("missing-separator")

    def test_rejects_empty_header_name(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_header("  =value")


class PredictionParserTests(unittest.TestCase):
    def test_accepts_single_choice(self):
        self.assertEqual(run_eval_litellm.parse_prediction(" 3 \n", 4), 3)

    def test_accepts_exact_answer_json(self):
        self.assertEqual(
            run_eval_litellm.parse_prediction('{"answer": 4}', 4),
            4,
        )

    def test_rejects_digit_embedded_in_rationale(self):
        self.assertEqual(
            run_eval_litellm.parse_prediction(
                '3" or "4"? Let us reason about it',
                4,
            ),
            -1,
        )

    def test_rejects_markdown_wrapped_choice(self):
        self.assertEqual(run_eval_litellm.parse_prediction("**1**", 4), -1)

    def test_rejects_json_with_surrounding_text(self):
        self.assertEqual(
            run_eval_litellm.parse_prediction(
                'The result is {"answer": 2}',
                4,
            ),
            -1,
        )




class AskTransportTests(unittest.TestCase):
    def make_args(self, *, openai_compatible):
        return SimpleNamespace(
            model="exact/provider-model",
            max_tokens=17,
            timeout=23,
            api_base="https://example.invalid/v1",
            seed=1234,
            retries=1,
            openai_compatible=openai_compatible,
        )

    def test_openai_compatible_forwards_direct_request_kwargs(self):
        completion = RecordingCompletion()

        result = ask(
            completion,
            self.make_args(openai_compatible=True),
            "prompt",
            4,
        )

        self.assertEqual(result, "2")
        self.assertEqual(
            completion.calls,
            [{
                "model": "exact/provider-model",
                "messages": [{"role": "user", "content": "prompt"}],
                "max_completion_tokens": 17,
                "timeout": 23,
            }],
        )

    def test_litellm_retains_existing_request_kwargs(self):
        completion = RecordingCompletion()

        result = ask(
            completion,
            self.make_args(openai_compatible=False),
            "prompt",
            4,
        )

        self.assertEqual(result, "2")
        self.assertEqual(
            completion.calls,
            [{
                "model": "exact/provider-model",
                "messages": [{"role": "user", "content": "prompt"}],
                "temperature": 0,
                "max_tokens": 17,
                "timeout": 23,
                "api_base": "https://example.invalid/v1",
                "seed": 1234,
            }],
        )


class ParseRetryTests(unittest.TestCase):
    def make_args(self, *, retry_max_tokens, use_answer_tool=False):
        return SimpleNamespace(
            model="exact/provider-model",
            max_tokens=17,
            unparsed_retry_max_tokens=retry_max_tokens,
            unparsed_use_answer_tool=use_answer_tool,
            timeout=23,
            api_base="https://example.invalid/v1",
            seed=1234,
            retries=1,
            openai_compatible=True,
        )

    def test_retries_unparsed_response_with_larger_budget(self):
        completion = RecordingCompletion(["unfinished reasoning", "3"])

        with contextlib.redirect_stdout(io.StringIO()):
            raw, pred = run_eval_litellm.ask_and_parse(
                completion,
                self.make_args(retry_max_tokens=64),
                "prompt",
                4,
            )

        self.assertEqual((raw, pred), ("3", 3))
        self.assertEqual(
            [call["max_completion_tokens"] for call in completion.calls],
            [17, 64],
        )

    def test_stops_without_result_when_retry_is_still_unparsed(self):
        completion = RecordingCompletion(["unfinished", "still unfinished"])

        with (
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaisesRegex(SystemExit, "unparseable response"),
        ):
            run_eval_litellm.ask_and_parse(
                completion,
                self.make_args(retry_max_tokens=64),
                "prompt",
                4,
            )

        self.assertEqual(len(completion.calls), 2)

    def test_uses_forced_answer_tool_after_unparsed_retry(self):
        tool_message = SimpleNamespace(
            content=None,
            tool_calls=[SimpleNamespace(function=SimpleNamespace(
                name="submit_answer",
                arguments='{"answer": 4}',
            ))],
        )
        completion = RecordingCompletion([
            "unfinished",
            "still unfinished",
            tool_message,
        ])

        with contextlib.redirect_stdout(io.StringIO()):
            raw, pred = run_eval_litellm.ask_and_parse(
                completion,
                self.make_args(retry_max_tokens=64, use_answer_tool=True),
                "prompt",
                4,
            )

        self.assertEqual((raw, pred), ('{"answer": 4}', 4))
        self.assertEqual(len(completion.calls), 3)
        self.assertEqual(
            completion.calls[2]["tool_choice"]["function"]["name"],
            "submit_answer",
        )

    def test_preserves_pred_minus_one_without_retry_budget(self):
        completion = RecordingCompletion(["refusal"])

        raw, pred = run_eval_litellm.ask_and_parse(
            completion,
            self.make_args(retry_max_tokens=0),
            "prompt",
            4,
        )

        self.assertEqual((raw, pred), ("refusal", -1))
        self.assertEqual(len(completion.calls), 1)



class DirectCliValidationTests(unittest.TestCase):
    def assert_direct_validation_error(self, options, environ, expected):
        with tempfile.TemporaryDirectory() as directory:
            argv = [
                "run_eval_litellm.py",
                "--model",
                "test-model",
                "--tag",
                "validation",
                "--openai-compatible",
                *options,
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(run_eval_litellm, "BASE", directory),
                mock.patch.object(sys, "argv", argv),
                mock.patch.dict(os.environ, environ, clear=True),
                contextlib.redirect_stderr(stderr),
                self.assertRaises(SystemExit) as raised,
            ):
                run_eval_litellm.main()

            self.assertEqual(raised.exception.code, 2)
            self.assertIn(expected, stderr.getvalue())
            self.assertFalse(
                os.path.exists(os.path.join(directory, "results-validation.csv"))
            )

    def test_requires_api_base_before_opening_results(self):
        self.assert_direct_validation_error([], {}, "--api-base")

    def test_requires_api_key_environment_name_before_opening_results(self):
        self.assert_direct_validation_error(
            ["--api-base", "https://example.invalid/v1"],
            {},
            "--api-key-env",
        )

    def test_requires_nonempty_api_key_before_opening_results(self):
        self.assert_direct_validation_error(
            [
                "--api-base",
                "https://example.invalid/v1",
                "--api-key-env",
                "TEST_API_KEY",
            ],
            {"TEST_API_KEY": ""},
            "TEST_API_KEY",
        )


if __name__ == "__main__":
    unittest.main()
