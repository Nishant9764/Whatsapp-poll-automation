from playwright.sync_api import sync_playwright
import time


SESSION_DIR = "whatsapp_session"
WHATSAPP_URL = "https://web.whatsapp.com"


class WhatsAppBot:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    # =========================================================
    # START WHATSAPP
    # =========================================================

    def start(self):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            viewport={
                "width": 1400,
                "height": 900
            }
        )

        if self.browser.pages:
            self.page = self.browser.pages[0]
        else:
            self.page = self.browser.new_page()

        self.page.goto(WHATSAPP_URL)

    # =========================================================
    # LOGIN
    # =========================================================

    def is_logged_in(self):
        try:
            self.page.locator("#pane-side").wait_for(
                state="visible",
                timeout=5000
            )

            return True

        except Exception:
            return False

    def wait_for_login(self):
        print("\nWaiting for WhatsApp login...")

        while True:

            if self.is_logged_in():
                print("✅ WhatsApp login detected.")
                return

            time.sleep(2)

    # =========================================================
    # FIND GROUP
    # =========================================================

    def find_group(self, group_name):
        """
        Search for a WhatsApp group by name.
        Does NOT send anything.
        """

        print(f"\nSearching for group: {group_name}")

        search_box = self.page.locator(
            'div[contenteditable="true"][data-tab="3"]'
        ).first

        search_box.wait_for(
            state="visible",
            timeout=10000
        )

        search_box.click()

        search_box.press("ControlOrMeta+A")
        search_box.press("Backspace")

        search_box.fill(group_name)

        time.sleep(3)

        print("Search results loaded.")

    # =========================================================
    # OPEN GROUP
    # =========================================================

    def open_group(self, group_name):
        """
        Find and click the exact WhatsApp group.
        """

        print(f"\nLooking for exact group: {group_name}")

        result = self.page.locator(
            "#pane-side"
        ).get_by_text(
            group_name,
            exact=True
        ).first

        result.wait_for(
            state="visible",
            timeout=10000
        )

        result.click()

        time.sleep(2)

        print(f"✅ Opened group: {group_name}")

    # =========================================================
    # VERIFY GROUP
    # =========================================================

    def verify_group(self, group_name):
        """
        Verify that the requested group is currently open.
        """

        header = self.page.locator("header").first

        header.wait_for(
            state="visible",
            timeout=5000
        )

        header_text = header.inner_text()

        if group_name not in header_text:

            raise RuntimeError(
                f"Wrong chat opened.\n"
                f"Expected: {group_name}\n"
                f"Current header:\n{header_text}"
            )

        print(f"✅ Verified group: {group_name}")

    # =========================================================
    # CREATE POLL
    # =========================================================

        # =========================================================
    # CREATE POLL
    # =========================================================

    def create_poll(self, question, options):
        """
        Create and fill a native WhatsApp Poll.

        The poll is NOT sent here.
        """

        if not question.strip():
            raise ValueError(
                "Poll question cannot be empty."
            )

        if len(options) < 2:
            raise ValueError(
                "A WhatsApp poll requires at least 2 options."
            )

        if len(options) > 12:
            raise ValueError(
                "WhatsApp polls support a maximum of 12 options."
            )

        # Check for duplicate options
        cleaned_options = [
            option.strip()
            for option in options
            if option.strip()
        ]

        if len(cleaned_options) != len(options):
            raise ValueError(
                "Poll contains an empty option."
            )

        if len(set(option.lower() for option in cleaned_options)) != len(
            cleaned_options
        ):
            raise ValueError(
                "Poll contains duplicate options."
            )

        print("\n" + "=" * 60)
        print("CREATING POLL")
        print("=" * 60)

        print(f"Question: {question}")

        for index, option in enumerate(
            cleaned_options,
            start=1
        ):
            print(f"  {index}. {option}")

        # -----------------------------------------------------
        # STEP 1: Open attachment menu
        # -----------------------------------------------------

        attach_button = self.page.locator(
            'button[aria-label*="Attach"], '
            'button[aria-label*="attach"], '
            'button[title*="Attach"], '
            'button[title*="attach"]'
        ).first

        attach_button.wait_for(
            state="visible",
            timeout=10000
        )

        attach_button.click()

        time.sleep(1)

        # -----------------------------------------------------
        # STEP 2: Click Poll
        # -----------------------------------------------------

        poll_button = self.page.get_by_text(
            "Poll",
            exact=True
        ).last

        poll_button.wait_for(
            state="visible",
            timeout=5000
        )

        poll_button.click()

        time.sleep(1)

        print("Poll composer opened.")

        # -----------------------------------------------------
        # STEP 3: Question
        # -----------------------------------------------------

        question_input = self.page.get_by_placeholder(
            "Ask question",
            exact=True
        )

        question_input.wait_for(
            state="visible",
            timeout=5000
        )

        question_input.fill(question)

        print("✅ Question filled.")

        # -----------------------------------------------------
        # STEP 4: Get option fields
        # -----------------------------------------------------

        option_inputs = self.page.get_by_placeholder(
            "Add",
            exact=True
        )

        option_count = option_inputs.count()

        print(
            f"Initial option fields found: {option_count}"
        )

        if option_count < 2:
            raise RuntimeError(
                "Could not find the initial WhatsApp poll "
                "option fields."
            )

        # -----------------------------------------------------
        # STEP 5: Fill first two options
        # -----------------------------------------------------

        option_inputs.nth(0).fill(
            cleaned_options[0]
        )

        option_inputs.nth(1).fill(
            cleaned_options[1]
        )

        # -----------------------------------------------------
        # STEP 6: Add remaining options
        # -----------------------------------------------------

        for option in cleaned_options[2:]:

            current_inputs = self.page.get_by_placeholder(
                "Add",
                exact=True
            )

            before_count = current_inputs.count()

            # WhatsApp provides an "Add" action for another
            # option. We first try to locate a visible element
            # containing "Add".
            add_elements = self.page.get_by_text(
                "Add",
                exact=True
            )

            clicked = False

            for i in range(add_elements.count()):

                element = add_elements.nth(i)

                try:
                    if element.is_visible():
                        element.click()
                        clicked = True
                        break

                except Exception:
                    continue

            if not clicked:
                raise RuntimeError(
                    "Could not find the Add option control."
                )

            # Wait for the new option field
            self.page.wait_for_timeout(300)

            current_inputs = self.page.get_by_placeholder(
                "Add",
                exact=True
            )

            after_count = current_inputs.count()

            if after_count <= before_count:
                raise RuntimeError(
                    "WhatsApp did not create a new "
                    "poll option field."
                )

            # Fill the newly created field
            current_inputs.nth(
                after_count - 1
            ).fill(option)

        print(
            f"✅ Filled {len(cleaned_options)} options."
        )

        # -----------------------------------------------------
        # STEP 7: Disable multiple answers
        # -----------------------------------------------------

        self.disable_multiple_answers()

        print("✅ Multiple answers disabled.")

        print("\nPoll is completely prepared.")
        print("Poll has NOT been sent.")

    # =========================================================
    # DISABLE MULTIPLE ANSWERS
    # =========================================================

    def disable_multiple_answers(self):

        """
        WhatsApp polls default to allowing multiple answers.
        Our quiz requires exactly one answer.
        """

        label = self.page.get_by_text(
            "Allow multiple answers",
            exact=True
        )

        label.wait_for(
            state="visible",
            timeout=5000
        )

        # Find the nearest clickable parent.
        parent = label.locator(
            "xpath=.."
        )

        # Check for a checkbox inside the row.
        checkbox = parent.get_by_role(
            "checkbox"
        )

        if checkbox.count() > 0:

            checkbox = checkbox.first

            if checkbox.is_checked():
                checkbox.click()

            return

        # Fallback:
        # Clicking the setting row itself toggles it.
        parent.click()

    # =========================================================
    # SEND POLL
    # =========================================================

    def send_poll(self):

        """
        Send the currently prepared poll.
        """

        print("\nPreparing to send poll...")

        send_button = self.page.get_by_text(
            "Send",
            exact=True
        ).last

        send_button.wait_for(
            state="visible",
            timeout=5000
        )

        # Make sure it is enabled.
        if not send_button.is_enabled():
            raise RuntimeError(
                "Poll Send button is disabled. "
                "The poll may not be completely filled."
            )

        send_button.click()

        time.sleep(2)

        print("✅ Poll sent successfully.")

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()


# =============================================================
# MAIN / DEVELOPMENT TEST
# =============================================================

if __name__ == "__main__":

    bot = WhatsAppBot()

    try:

        bot.start()

        bot.wait_for_login()

        # -----------------------------------------------------
        # CHANGE THIS TO YOUR ACTUAL GROUP NAME
        # -----------------------------------------------------

        GROUP_NAME = "group_name"

        bot.find_group(GROUP_NAME)

        input(
            "\nCheck the Chromium window.\n"
            "Press ENTER when you're ready to open the group..."
        )

        bot.open_group(GROUP_NAME)

        bot.verify_group(GROUP_NAME)

        input(
            "\nGroup opened successfully.\n"
            "Press ENTER to close..."
        )

    except KeyboardInterrupt:

        print("\nClosing...")

    finally:

        bot.close()