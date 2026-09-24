"""
test_parser.py
---------------
Lightweight self-contained tests for parser.py -- no pytest required.
Run with:

    python3 test_parser.py

Covers:
  * the real questions.txt parses cleanly end-to-end
  * a well-formed sample block parses correctly
  * rejection of: too few options, too many options, empty options,
    duplicate options, missing ANSWER line, ANSWER pointing at a
    non-existent letter, and a question with no options at all.
"""

from __future__ import annotations

import os
import tempfile

from parser import parse_questions, QuestionParseError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_text(text: str):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        path = f.name
    try:
        return parse_questions(path)
    finally:
        os.remove(path)


def _expect_error(text: str, substring: str, label: str):
    try:
        _parse_text(text)
    except QuestionParseError as e:
        assert substring.lower() in str(e).lower(), (
            f"[{label}] wrong error message: {e}"
        )
        print(f"PASS: {label}")
        return
    raise AssertionError(f"[{label}] expected QuestionParseError, got none")


def test_real_questions_file():
    path = os.path.join(BASE_DIR, "questions.txt")
    questions = parse_questions(path)
    assert len(questions) > 0, "questions.txt produced zero questions"

    seen_texts = set()
    for q in questions:
        assert 2 <= len(q["options"]) <= 12, f"bad option count: {q}"
        assert q["answer"] in q["options"], f"answer not among options: {q}"
        lowered = [o.strip().lower() for o in q["options"]]
        assert len(set(lowered)) == len(lowered), f"duplicate options: {q}"
        assert all(o.strip() for o in q["options"]), f"empty option: {q}"
        seen_texts.add(q["question"])

    print(f"PASS: real questions.txt parsed cleanly ({len(questions)} questions)")


def test_well_formed_sample():
    sample = (
        "Q: What color is the sky?\n"
        "A) Green\n"
        "B) Blue\n"
        "C) Red\n"
        "ANSWER: B\n"
    )
    questions = _parse_text(sample)
    assert len(questions) == 1
    q = questions[0]
    assert q["question"] == "What color is the sky?"
    assert q["options"] == ["Green", "Blue", "Red"]
    assert q["answer"] == "Blue"
    assert q["index"] == 0
    print("PASS: well-formed sample parses correctly")


def test_multiple_questions_and_comments():
    sample = (
        "# a leading comment\n"
        "Q: First?\n"
        "A) X\n"
        "B) Y\n"
        "ANSWER: A\n"
        "\n"
        "# a comment between questions\n"
        "Q: Second?\n"
        "A) 1\n"
        "B) 2\n"
        "C) 3\n"
        "ANSWER: C\n"
    )
    questions = _parse_text(sample)
    assert len(questions) == 2
    assert questions[0]["index"] == 0
    assert questions[1]["index"] == 1
    assert questions[1]["answer"] == "3"
    print("PASS: multiple questions with comments parse correctly")


def test_rejects_too_few_options():
    _expect_error(
        "Q: Only one option?\nA) Solo\nANSWER: A\n",
        "at least",
        "too few options",
    )


def test_rejects_too_many_options():
    lines = ["Q: Too many?"]
    letters = "ABCDEFGHIJKLM"
    for i, letter in enumerate(letters):
        lines.append(f"{letter}) Option {i}")
    lines.append(f"ANSWER: A")
    _expect_error("\n".join(lines) + "\n", "at most", "too many options")


def test_rejects_empty_option():
    _expect_error(
        "Q: Has an empty option?\nA) Fine\nB) \nANSWER: A\n",
        "empty option",
        "empty option",
    )


def test_rejects_duplicate_options():
    _expect_error(
        "Q: Dup options?\nA) Same\nB) same\nANSWER: A\n",
        "duplicate option",
        "duplicate options",
    )


def test_rejects_missing_answer():
    _expect_error(
        "Q: No answer line?\nA) One\nB) Two\n",
        "no answer",
        "missing ANSWER line",
    )


def test_rejects_answer_pointing_nowhere():
    _expect_error(
        "Q: Bad answer letter?\nA) One\nB) Two\nANSWER: Z\n",
        "no option",
        "ANSWER letter not among options",
    )


def test_rejects_no_options_at_all():
    _expect_error(
        "Q: No options at all?\nANSWER: A\n",
        "at least",
        "no options at all",
    )


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"ERROR: {t.__name__}: {e!r}")

    print("\n" + "=" * 60)
    if failures:
        print(f"{failures} test(s) FAILED")
        raise SystemExit(1)
    else:
        print(f"All {len(tests)} tests passed.")
