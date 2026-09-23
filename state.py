import json
import os


STATE_FILE = "state.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "next_question_index": 0
        }

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)


def get_next_question(questions):
    state = load_state()

    index = state.get("next_question_index", 0)

    if index >= len(questions):
        return None

    return questions[index]


def mark_question_sent():
    state = load_state()

    state["next_question_index"] = (
        state.get("next_question_index", 0) + 1
    )

    save_state(state)