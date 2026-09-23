import json
import sys
import time

from parser import parse_questions
from state import get_next_question, mark_question_sent
from whatsapp import WhatsAppBot
from scheduler import wait_until_next_run


CONFIG_FILE = "config.json"
QUESTIONS_FILE = "questions.txt"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def run_once():
    print("\n" + "=" * 60)
    print("WHATSAPP DAILY POLL BOT")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Load configuration
    # ---------------------------------------------------------
    config = load_config()

    group_name = config["group_name"]

    if not group_name or group_name == "YOUR GROUP NAME":
        raise RuntimeError(
            "Please set your actual WhatsApp group name in config.json."
        )

    print(f"\nTarget group: {group_name}")

    # ---------------------------------------------------------
    # 2. Parse questions
    # ---------------------------------------------------------
    print("\nLoading questions...")

    questions = parse_questions(QUESTIONS_FILE)

    if not questions:
        raise RuntimeError("No questions found in questions.txt.")

    print(f"Loaded {len(questions)} questions.")

    # ---------------------------------------------------------
    # 3. Get next unsent question
    # ---------------------------------------------------------
    question = get_next_question(questions)

    if question is None:
        print("\n🎉 All questions have already been sent.")
        return

    print("\n" + "-" * 60)
    print("NEXT QUESTION")
    print("-" * 60)

    print(f"Question: {question['question']}")

    for index, option in enumerate(question["options"], start=1):
        print(f"{index}. {option}")

    # ---------------------------------------------------------
    # 4. Start WhatsApp
    # ---------------------------------------------------------
    bot = WhatsAppBot()

    try:
        print("\nStarting WhatsApp...")

        bot.start()

        # -----------------------------------------------------
        # 5. Wait for WhatsApp login
        # -----------------------------------------------------
        bot.wait_for_login()

        # -----------------------------------------------------
        # 6. Find target group
        # -----------------------------------------------------
        bot.find_group(group_name)

        # -----------------------------------------------------
        # 7. Open exact group
        # -----------------------------------------------------
        bot.open_group(group_name)

        # -----------------------------------------------------
        # 8. Verify correct group
        # -----------------------------------------------------
        bot.verify_group(group_name)

        # -----------------------------------------------------
        # 9. Create poll
        # -----------------------------------------------------
        bot.create_poll(
            question=question["question"],
            options=question["options"]
        )

        # -----------------------------------------------------
        # 10. Send poll
        # -----------------------------------------------------
        bot.send_poll()

        # -----------------------------------------------------
        # 11. Mark question as sent ONLY after successful send
        # -----------------------------------------------------
        mark_question_sent()

        print("\n" + "=" * 60)
        print("✅ DAILY POLL COMPLETED")
        print("=" * 60)

    except Exception as error:
        print("\n" + "=" * 60)
        print("❌ POLL FAILED")
        print("=" * 60)

        print(f"\nError: {error}")

        print(
            "\nThe question was NOT marked as sent."
            "\nIt will remain available for the next run."
        )

        raise

    finally:
        bot.close()


def main():
    config = load_config()

    send_hour = config["send_hour"]
    send_minute = config["send_minute"]

    # ---------------------------------------------------------
    # --once
    #
    # Runs exactly one poll immediately and exits.
    # ---------------------------------------------------------
    if "--once" in sys.argv:
        run_once()
        return

    # ---------------------------------------------------------
    # Daily scheduler mode
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("WHATSAPP DAILY POLL BOT")
    print("=" * 60)

    print(
        f"\nDaily schedule: "
        f"{send_hour:02d}:{send_minute:02d}"
    )

    print("Scheduler is running...")
    print("Press Ctrl+C to stop the bot.")

    while True:
        try:
            # -------------------------------------------------
            # Wait until the next scheduled time
            # -------------------------------------------------
            wait_until_next_run(
                send_hour,
                send_minute
            )

            # -------------------------------------------------
            # Execute one complete poll cycle
            # -------------------------------------------------
            run_once()

        except KeyboardInterrupt:
            print("\n\nBot stopped by user.")
            break

        except Exception as error:
            print("\n" + "=" * 60)
            print("❌ DAILY RUN FAILED")
            print("=" * 60)

            print(f"\nError: {error}")

            print(
                "\nThe question was not marked as sent."
                "\nThe bot will continue waiting for the next scheduled run."
            )

            # Give the process a short recovery period
            time.sleep(30)


if __name__ == "__main__":
    main()