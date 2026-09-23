from playwright.sync_api import sync_playwright
import time


SESSION_DIR = "whatsapp_session"
WHATSAPP_URL = "https://web.whatsapp.com"


class WhatsAppBot:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

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

    def find_group(self, group_name):
        """
        Search for a WhatsApp group by name.
        Does NOT send anything.
        """

        print(f"\nSearching for group: {group_name}")

        # WhatsApp Web search box
        search_box = self.page.locator(
            'div[contenteditable="true"][data-tab="3"]'
        ).first

        search_box.wait_for(
            state="visible",
            timeout=10000
        )

        search_box.click()

        # Clear existing text
        search_box.press("ControlOrMeta+A")
        search_box.press("Backspace")

        search_box.fill(group_name)

        # Give WhatsApp time to display results
        time.sleep(3)

        print("Search results loaded.")

        # Show visible text for debugging
        print("\nVisible search area:")
        print(self.page.locator("#pane-side").inner_text())

    def open_group(self, group_name):
        """
        Find and click the requested group.
        """

        print(f"\nLooking for exact group: {group_name}")

        # Search result containing the group name.
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

    def close(self):
        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()


if __name__ == "__main__":

    bot = WhatsAppBot()

    try:
        bot.start()

        bot.wait_for_login()

        # --------------------------------------------------
        # CHANGE THIS TO YOUR ACTUAL WHATSAPP GROUP NAME
        # --------------------------------------------------

        GROUP_NAME = "group_name"

        bot.find_group(GROUP_NAME)

        input(
            "\nCheck the Chromium window. "
            "Press ENTER when you're ready to continue..."
        )

        bot.open_group(GROUP_NAME)

        input(
            "\nGroup opened successfully. "
            "Press ENTER to close..."
        )

    except KeyboardInterrupt:
        print("\nClosing...")

    finally:
        bot.close()

def create_poll(self, question, options):
    """
    Open the native WhatsApp Poll UI and fill in the question/options.
    Does NOT click Send.
    """

    print("\nCreating poll...")
    print(f"Question: {question}")
    print(f"Options: {len(options)}")

    # Click the + / attachment button
    attach_button = self.page.locator(
        'button[aria-label*="Attach"], '
        'button[aria-label*="attachment"]'
    ).first

    attach_button.wait_for(
        state="visible",
        timeout=10000
    )

    attach_button.click()

    time.sleep(1)

    # Click Poll from the attachment menu
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

    print("Poll dialog opened.")

    # Find the poll question input
    question_input = self.page.locator(
        'div[contenteditable="true"]'
    ).filter(
        has=self.page.locator(
            '[data-lexical-text="true"]'
        )
    ).first

    # If the above selector doesn't work on the current UI,
    # we'll inspect the actual dialog and adjust it.
    question_input.wait_for(
        state="visible",
        timeout=5000
    )

    question_input.fill(question)

    # Find poll option inputs.
    # WhatsApp initially provides two options.
    option_inputs = self.page.locator(
        'div[contenteditable="true"]'
    )

    visible_inputs = []

    for i in range(option_inputs.count()):
        element = option_inputs.nth(i)

        if element.is_visible():
            visible_inputs.append(element)

    print(f"Visible editable fields: {len(visible_inputs)}")

    # The exact UI selectors can vary between WhatsApp versions.
    # We'll inspect before attempting to fill options.
    print("Poll UI detected.")