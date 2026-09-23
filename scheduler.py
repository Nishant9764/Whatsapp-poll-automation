import time
from datetime import datetime

from state import get_next_question, mark_question_sent
from parser import parse_questions


QUESTIONS_FILE = "questions.txt"


def wait_until(hour, minute):

    print(
        f"Waiting until {hour:02d}:{minute:02d}..."
    )

    while True:

        now = datetime.now()

        if now.hour == hour and now.minute == minute:
            return

        time.sleep(20)


def get_question_for_today():

    questions = parse_questions(QUESTIONS_FILE)

    if not questions:
        raise RuntimeError(
            "No questions found."
        )

    question = get_next_question(questions)

    if question is None:
        print("All questions have been completed.")
        return None

    return question