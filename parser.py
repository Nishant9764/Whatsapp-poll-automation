"""
parser.py
---------
Reads questions.txt and turns it into a validated, ordered list of
question dicts:

    {
        "index": 0,                     # 0-based position in the file
        "question": "...",
        "options": ["...", "...", ...], # 2-12 options, deduped/validated
        "answer": "...",                # exact text of the correct option
    }

File format (see the header comment inside questions.txt for the
human-facing version of these rules):

    Q: <question text>
    A) <option 1>
    B) <option 2>
    ...
    ANSWER: <letter of the correct option>

    Q: <next question>
    ...

Rules enforced here:
  * 2-12 options per question (WhatsApp Poll's own limit is 12).
  * No empty options.
  * No duplicate options (case-insensitive, whitespace-normalized).
  * Exactly one ANSWER line, and it must point at one of the options.
  * Lines starting with '#' and blank lines are ignored outside of a
    question block.

Any question that fails validation raises QuestionParseError with a
message that identifies the offending question, so problems in
questions.txt are caught long before the bot tries to use them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


class QuestionParseError(ValueError):
    """Raised when questions.txt contains an invalid/ambiguous question."""


@dataclass
class Question:
    index: int
    question: str
    options: List[str]
    answer: str

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "question": self.question,
            "options": list(self.options),
            "answer": self.answer,
        }


_Q_RE = re.compile(r"^Q:\s*(.+)$")
_OPT_RE = re.compile(r"^([A-Za-z])\)\s*(.*)$")
_ANSWER_RE = re.compile(r"^ANSWER:\s*([A-Za-z])\s*$", re.IGNORECASE)

MIN_OPTIONS = 2
MAX_OPTIONS = 12  # WhatsApp Poll hard limit


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _flush_block(lines: List[str], block_start_line: int) -> Optional[dict]:
    """Parse a single accumulated block of raw lines into a raw question."""
    if not lines:
        return None

    question_text = None
    options: List[str] = []
    option_letters: List[str] = []
    answer_letter = None

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = _Q_RE.match(line)
        if m:
            if question_text is not None:
                raise QuestionParseError(
                    f"Two 'Q:' lines found in one question block "
                    f"(around line {block_start_line}). Separate questions "
                    f"with a blank line."
                )
            question_text = m.group(1).strip()
            continue

        m = _OPT_RE.match(line)
        if m:
            option_letters.append(m.group(1).upper())
            options.append(m.group(2).strip())
            continue

        m = _ANSWER_RE.match(line)
        if m:
            if answer_letter is not None:
                raise QuestionParseError(
                    f"Two 'ANSWER:' lines found for the question starting "
                    f"near line {block_start_line}."
                )
            answer_letter = m.group(1).upper()
            continue

        raise QuestionParseError(
            f"Unrecognized line near line {block_start_line}: {raw!r}. "
            f"Expected 'Q:', 'A)'/'B)'/... , or 'ANSWER:'."
        )

    if question_text is None:
        raise QuestionParseError(
            f"Question block near line {block_start_line} has no 'Q:' line."
        )
    if not question_text:
        raise QuestionParseError(
            f"Question near line {block_start_line} has empty question text."
        )
    if answer_letter is None:
        raise QuestionParseError(
            f"Question '{question_text[:60]}...' has no ANSWER: line."
        )

    return {
        "question": question_text,
        "options": options,
        "option_letters": option_letters,
        "answer_letter": answer_letter,
        "line": block_start_line,
    }


def _validate(raw: dict) -> Question:
    question_text = raw["question"]
    options = raw["options"]
    letters = raw["option_letters"]
    answer_letter = raw["answer_letter"]
    line = raw["line"]

    if len(options) < MIN_OPTIONS:
        raise QuestionParseError(
            f"Question '{question_text[:60]}...' (near line {line}) has "
            f"only {len(options)} option(s); at least {MIN_OPTIONS} are required."
        )
    if len(options) > MAX_OPTIONS:
        raise QuestionParseError(
            f"Question '{question_text[:60]}...' (near line {line}) has "
            f"{len(options)} options; WhatsApp Poll allows at most {MAX_OPTIONS}."
        )

    for opt in options:
        if not opt.strip():
            raise QuestionParseError(
                f"Question '{question_text[:60]}...' (near line {line}) has "
                f"an empty option."
            )

    seen = set()
    for opt in options:
        key = _normalize(opt)
        if key in seen:
            raise QuestionParseError(
                f"Question '{question_text[:60]}...' (near line {line}) has "
                f"a duplicate option: '{opt}'."
            )
        seen.add(key)

    if answer_letter not in letters:
        raise QuestionParseError(
            f"Question '{question_text[:60]}...' (near line {line}) has "
            f"ANSWER: {answer_letter}, but there is no option '{answer_letter})'."
        )

    answer_text = options[letters.index(answer_letter)]

    return Question(index=-1, question=question_text, options=options, answer=answer_text)


def parse_questions(path: str) -> List[dict]:
    """
    Parse questions.txt at `path` and return a list of validated
    question dicts, in file order, each with a stable zero-based
    'index'.

    Raises QuestionParseError on any malformed or invalid question so
    that bad data is caught before the bot ever tries to send it.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    lines = raw_text.splitlines()

    blocks: List[List[str]] = []
    current: List[str] = []
    current_start = 1
    pending_start = 1

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append((current, current_start))
                current = []
            pending_start = lineno + 1
            continue
        if stripped.startswith("#"):
            if not current:
                pending_start = lineno + 1
            continue
        if not current:
            current_start = pending_start
        current.append(line)

    if current:
        blocks.append((current, current_start))

    questions: List[Question] = []
    for block_lines, start_line in blocks:
        raw = _flush_block(block_lines, start_line)
        if raw is None:
            continue
        q = _validate(raw)
        questions.append(q)

    if not questions:
        raise QuestionParseError(f"No valid questions found in {path}.")

    result = []
    for i, q in enumerate(questions):
        q.index = i
        result.append(q.to_dict())

    return result


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "questions.txt"
    qs = parse_questions(target)
    print(f"Parsed {len(qs)} valid questions from {target}.")
    counts = {}
    for q in qs:
        counts[len(q["options"])] = counts.get(len(q["options"]), 0) + 1
    print("Option-count distribution:", dict(sorted(counts.items())))
