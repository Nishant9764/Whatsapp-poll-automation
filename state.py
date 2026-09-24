"""
state.py
--------
Manages state.json: the single source of truth for which question comes
next, and what the previous *successfully sent* question/answer were.

CRITICAL INVARIANT (see README): state is only ever advanced by calling
mark_sent() AFTER a poll has actually been sent on WhatsApp. Nothing in
this module advances progress as a side effect of merely reading it, so
a crash anywhere before mark_sent() is called leaves state.json
untouched and the next run retries the same question.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


DEFAULT_STATE = {
    "next_question_index": 0,
    "last_question": None,
    "last_answer": None,
    "last_sent_at": None,
    "completed": False,
}


@dataclass
class QuizState:
    next_question_index: int
    last_question: Optional[str]
    last_answer: Optional[str]
    last_sent_at: Optional[str]
    completed: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "QuizState":
        merged = {**DEFAULT_STATE, **d}
        return cls(
            next_question_index=merged["next_question_index"],
            last_question=merged["last_question"],
            last_answer=merged["last_answer"],
            last_sent_at=merged["last_sent_at"],
            completed=merged.get("completed", False),
        )

    def to_dict(self) -> dict:
        return asdict(self)


def load_state(path: str) -> QuizState:
    """
    Load state.json. If the file is missing, a fresh state is created
    (first run). If the file exists but is corrupt/unreadable, we raise
    rather than silently resetting progress -- a corrupt state file
    must never be treated as "start from question 1", since that could
    re-send already-completed questions.
    """
    if not os.path.exists(path):
        return QuizState.from_dict(dict(DEFAULT_STATE))

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return QuizState.from_dict(dict(DEFAULT_STATE))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"state.json at {path} is corrupt and could not be parsed: {e}. "
            f"Refusing to guess a fresh state, since that risks re-sending "
            f"already-completed questions. Please inspect/restore it manually "
            f"(a state.json.bak-* backup may exist alongside it)."
        ) from e

    if not isinstance(data, dict):
        raise RuntimeError(f"state.json at {path} does not contain a JSON object.")

    return QuizState.from_dict(data)


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON atomically: write to a temp file, then rename over the
    target. This avoids ever leaving state.json half-written if the
    process is killed mid-write."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".state_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def save_state(path: str, state: QuizState) -> None:
    # Keep one rolling backup of the previous state before overwriting,
    # purely as an extra safety net for manual recovery.
    if os.path.exists(path):
        try:
            shutil.copyfile(path, path + ".bak")
        except OSError:
            pass
    _atomic_write_json(path, state.to_dict())


def mark_sent(path: str, state: QuizState, question: str, answer: str,
              new_next_index: int, total_questions: int) -> QuizState:
    """
    Record a SUCCESSFUL send. Must only be called after the WhatsApp
    poll has actually been sent. Advances next_question_index and
    stores this question/answer as "last successful" for tomorrow's
    recap line.
    """
    completed = new_next_index >= total_questions
    updated = QuizState(
        next_question_index=new_next_index,
        last_question=question,
        last_answer=answer,
        last_sent_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        completed=completed,
    )
    save_state(path, updated)
    return updated
