"""
main.py
-------
Orchestrates one full daily quiz cycle:

    load config + questions + state
      -> if already completed: report and stop (no auto-restart)
      -> pick next unsent question, and the last SUCCESSFULLY sent
         question/answer for the recap line
      -> build the fixed intro message
      -> open WhatsApp, verify the target group
      -> send intro message, then build + send the native poll
      -> ONLY on full success: advance state.json

Any exception raised before the poll is confirmed sent aborts the run
without touching state.json, so the same question is retried on the
next scheduled run (see state.py and README "Failure safety").

Usage:
    python3 main.py            # normal mode: waits for the daily time, loops forever
    python3 main.py --once     # run exactly one quiz cycle now, then exit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

from parser import parse_questions, QuestionParseError
from state import load_state, mark_sent
from whatsapp import WhatsAppBot
import scheduler


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
QUESTIONS_PATH = os.path.join(BASE_DIR, "questions.txt")
STATE_PATH = os.path.join(BASE_DIR, "state.json")

MESSAGE_TEMPLATE_WITH_RECAP = (
    "Hare Krishna 🙏\n\n"
    "Today's quiz 👇\n\n"
    "{question}\n\n"
    "(Yesterday's question - Answer: {answer})"
)

MESSAGE_TEMPLATE_FIRST_RUN = (
    "Hare Krishna 🙏\n\n"
    "Today's quiz 👇\n\n"
    "{question}"
)


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"config.json not found at {path}.")
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    for key in ("group_name", "send_hour", "send_minute"):
        if key not in config:
            raise ValueError(f"config.json is missing required key: '{key}'")
    if not config["group_name"] or not config["group_name"].strip():
        raise ValueError("config.json 'group_name' is empty.")

    return config


def build_intro_message(question: str, last_question: str | None, last_answer: str | None) -> str:
    """
    Build today's fixed intro message. The "yesterday's answer" recap
    line is included only when we actually have a previously
    SUCCESSFULLY sent question (i.e. not on the very first run).
    """
    if last_question is None or last_answer is None:
        return MESSAGE_TEMPLATE_FIRST_RUN.format(question=question)
    return MESSAGE_TEMPLATE_WITH_RECAP.format(question=question, answer=last_answer)


def run_once() -> int:
    """
    Run exactly one quiz cycle. Returns a process exit code:
    0 on success (or on a clean "all questions completed" stop),
    1 on any failure (nothing was advanced; safe to retry).
    """
    try:
        config = load_config(CONFIG_PATH)
    except Exception as e:
        print(f"[CONFIG ERROR] {e}")
        return 1

    try:
        questions = parse_questions(QUESTIONS_PATH)
    except QuestionParseError as e:
        print(f"[QUESTIONS ERROR] {e}")
        return 1

    try:
        state = load_state(STATE_PATH)
    except Exception as e:
        print(f"[STATE ERROR] {e}")
        return 1

    total = len(questions)

    if state.completed or state.next_question_index >= total:
        print("All questions have been completed.")
        return 0

    today_q = questions[state.next_question_index]
    question_text = today_q["question"]
    correct_answer = today_q["answer"]
    options = today_q["options"]

    intro_message = build_intro_message(question_text, state.last_question, state.last_answer)

    print("\n" + "=" * 60)
    print(f"QUIZ CYCLE -- question {state.next_question_index + 1} of {total}")
    print("=" * 60)
    print(intro_message)
    print("-" * 60)

    bot = WhatsAppBot()
    try:
        bot.start()
        bot.wait_for_login()

        bot.find_group(config["group_name"])
        bot.open_group(config["group_name"])
        bot.verify_group(config["group_name"])

        # Order matters: intro message first, native poll second.
        bot.send_message(intro_message)
        bot.create_poll(question_text, options)
        bot.send_poll()

    except Exception:
        print("\n[SEND FAILED] Nothing was advanced in state.json; the "
              "next scheduled run will retry this same question.")
        traceback.print_exc()
        return 1
    finally:
        bot.close()

    # Only reached if every step above succeeded.
    new_index = state.next_question_index + 1
    mark_sent(
        STATE_PATH,
        state,
        question=question_text,
        answer=correct_answer,
        new_next_index=new_index,
        total_questions=total,
    )

    print(f"\nstate.json updated: next_question_index = {new_index} of {total}.")
    if new_index >= total:
        print("All questions have been completed.")

    return 0


def run_forever(config: dict) -> None:
    while True:
        exit_code = run_once()
        # Re-read config each cycle in case send_hour/send_minute changed.
        try:
            config = load_config(CONFIG_PATH)
        except Exception as e:
            print(f"[CONFIG ERROR] {e}")
            print("Retrying with previous schedule in 5 minutes...")
            import time
            time.sleep(300)
            continue

        # If everything is completed, stop looping entirely rather than
        # waking up forever to do nothing.
        try:
            state = load_state(STATE_PATH)
            questions = parse_questions(QUESTIONS_PATH)
            if state.completed or state.next_question_index >= len(questions):
                print("All questions have been completed. Exiting.")
                return
        except Exception:
            pass

        scheduler.wait_until_next_run(config["send_hour"], config["send_minute"])


def main() -> None:
    parser_ = argparse.ArgumentParser(description="Hare Krishna Daily Quiz Bot")
    parser_.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one quiz cycle immediately, then exit.",
    )
    args = parser_.parse_args()

    if args.once:
        sys.exit(run_once())

    config = load_config(CONFIG_PATH)
    run_forever(config)


if __name__ == "__main__":
    main()
