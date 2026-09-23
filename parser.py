import re


QUESTION_START = re.compile(r"^\s*(\d+)\.\s*(.*)$")

OPTION_MARKER = re.compile(
    r"^\s*(?:[A-Fa-f]|[ivxIVX]+)[.)]\s*(.+?)\s*$"
)

BULLET_OPTION = re.compile(
    r"^\s*[*•]\s*(.+?)\s*$"
)

STANDALONE_OPTION_LABEL = re.compile(
    r"^\s*(?:[A-Fa-f]|[ivxIVX]+)[.)]\s*$"
)

SEPARATOR = re.compile(r"^\s*-{5,}\s*$")

META_LINE = re.compile(
    r"^\s*(?:Today's|Tomorrow's|Yesterday's|"
    r"Today’s|Tomorrow’s|Yesterday’s)\s+"
    r"(?:quiz|question)\s*:?\s*$",
    re.IGNORECASE
)


def clean_line(line):
    """Basic whitespace cleanup."""
    return re.sub(r"\s+", " ", line).strip()


def split_into_numbered_sections(content):
    """
    Find every numbered question and collect content until
    the first separator line after it.
    """

    lines = content.splitlines()

    starts = []

    for i, line in enumerate(lines):
        match = QUESTION_START.match(line)

        if match:
            starts.append((i, int(match.group(1)), match.group(2).strip()))

    sections = []

    for index, (start, number, first_line) in enumerate(starts):

        end = len(lines)

        # A separator is the real boundary in this file.
        for i in range(start + 1, len(lines)):
            if SEPARATOR.match(lines[i]):
                end = i
                break

        sections.append({
            "start": start,
            "end": end,
            "number": number,
            "first_line": first_line,
            "lines": lines[start:end]
        })

    return sections


def extract_options_and_question(lines):
    """
    Extract question text and options from one question block.

    Handles:
    - A. option
    - a. option
    - 1. option
    - * option
    - standalone A. followed by option
    - completely unlabelled options
    """

    if not lines:
        return "", []

    # Remove metadata
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if META_LINE.match(line):
            continue

        cleaned.append(line)

    if not cleaned:
        return "", []

    # Remove question number from first line.
    first_match = QUESTION_START.match(cleaned[0])

    if first_match:
        question_number = first_match.group(1)
        first_question_text = first_match.group(2).strip()
    else:
        question_number = None
        first_question_text = cleaned[0]

    remaining = [first_question_text] + cleaned[1:]

    question_lines = []
    options = []

    i = 0

    while i < len(remaining):

        line = remaining[i].strip()

        # ---------------------------------------------------------
        # Bullet option
        # ---------------------------------------------------------
        bullet_match = BULLET_OPTION.match(line)

        if bullet_match:
            options.append(bullet_match.group(1).strip())
            i += 1
            continue

        # ---------------------------------------------------------
        # Letter / roman-numbered option
        # Example:
        # A. Krishna
        # b. Arjuna
        # ---------------------------------------------------------
        option_match = OPTION_MARKER.match(line)

        if option_match:
            options.append(option_match.group(1).strip())
            i += 1
            continue

        # ---------------------------------------------------------
        # Standalone option marker
        #
        # A.
        #    Some answer
        # ---------------------------------------------------------
        if STANDALONE_OPTION_LABEL.match(line):

            i += 1

            while i < len(remaining) and not remaining[i].strip():
                i += 1

            if i < len(remaining):
                options.append(remaining[i].strip())
                i += 1

            continue

        # ---------------------------------------------------------
        # Otherwise this is still question text.
        # ---------------------------------------------------------
        question_lines.append(line)

        i += 1

    # -------------------------------------------------------------
    # If explicit option markers were found, we're done.
    # -------------------------------------------------------------
    if options:
        question = " ".join(question_lines)
        return question.strip(), options

    # -------------------------------------------------------------
    # No explicit markers.
    #
    # This file contains questions where the options are simply
    # listed one per line.
    # -------------------------------------------------------------
    if len(question_lines) >= 5:

        # The first line is normally the question.
        #
        # Example:
        #
        # How long did the battle go on?
        # 14 days
        # 18 days
        # 21 days
        #
        # For 5+ lines we need a heuristic.
        question = question_lines[0]

        potential_options = question_lines[1:]

        # If the question appears incomplete and there are
        # exactly 5 candidate lines, the first candidate may
        # actually be a continuation of the question.
        if (
            len(potential_options) == 5
            and not re.search(r"[?.!:;]$", question)
        ):
            question += " " + potential_options[0]
            potential_options = potential_options[1:]

        return question.strip(), potential_options

    # -------------------------------------------------------------
    # Very small / malformed block.
    # Preserve everything rather than silently deleting data.
    # -------------------------------------------------------------
    if len(question_lines) >= 2:

        question = question_lines[0]
        options = question_lines[1:]

        return question.strip(), options

    return " ".join(question_lines).strip(), []


def parse_questions(file_path):
    """
    Main parser.

    Returns a list of dictionaries:

    {
        "number": 100,
        "question": "...",
        "options": [...]
    }
    """

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    content = content.replace("\r\n", "\n")
    content = content.replace("\r", "\n")

    sections = split_into_numbered_sections(content)

    questions = []

    for section in sections:

        question, options = extract_options_and_question(
            section["lines"]
        )

        if not question:
            continue

        questions.append({
            "number": section["number"],
            "question": question,
            "options": options
        })

    return questions