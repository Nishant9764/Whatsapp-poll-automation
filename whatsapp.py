"""
whatsapp.py
-----------
All WhatsApp Web browser automation lives here. Nothing in this module
knows about quiz content, state.json, or scheduling -- it only knows
how to drive the WhatsApp Web UI:

    start()                    launch Chromium with a persistent profile
    wait_for_login()           block until QR login is complete
    find_group(name)           search for a group by name
    open_group(name)           open the exact matching group
    verify_group(name)         confirm the right chat is open
    send_message(text)         send a plain text message
    create_poll(question, opt) build (but do not send) a native poll
    send_poll()                send the poll built by create_poll()
    close()                    tear down the browser

Every method raises on failure instead of swallowing errors, so that
main.py can treat "an exception was raised" as "nothing was sent" and
safely leave state.json untouched (see state.py's module docstring).
"""

from __future__ import annotations

import time
from typing import List

from playwright.sync_api import sync_playwright


SESSION_DIR = "whatsapp_session"
WHATSAPP_URL = "https://web.whatsapp.com"

MAX_POLL_OPTIONS = 12
MIN_POLL_OPTIONS = 2


class WhatsAppBot:

    def __init__(self, session_dir: str = SESSION_DIR, headless: bool = False):
        self.session_dir = session_dir
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    # =========================================================
    # START / LOGIN
    # =========================================================

    def start(self) -> None:
        """
        Launch Chromium with a PERSISTENT context stored in
        `self.session_dir`. Re-using this directory on every run is
        what lets an already-linked WhatsApp Web session survive
        across restarts without re-scanning the QR code.
        """
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=self.headless,
            viewport={"width": 1400, "height": 900},
        )

        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        self.page.goto(WHATSAPP_URL)

    def is_logged_in(self) -> bool:
        try:
            self.page.locator("#pane-side").wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def wait_for_login(self, poll_seconds: float = 2.0, timeout_seconds: float = 300.0) -> None:
        """
        Block until WhatsApp Web reports a logged-in session (the chat
        list pane becomes visible), or raise TimeoutError after
        `timeout_seconds`. A valid persistent session usually logs in
        within a few seconds with no QR scan required.
        """
        print("\nWaiting for WhatsApp login...")
        waited = 0.0
        while waited < timeout_seconds:
            if self.is_logged_in():
                print("WhatsApp login detected.")
                return
            time.sleep(poll_seconds)
            waited += poll_seconds
        raise TimeoutError(
            f"WhatsApp did not log in within {timeout_seconds:.0f}s. "
            f"If this is the first run, scan the QR code in the opened "
            f"browser window and re-run."
        )

    # =========================================================
    # FIND / OPEN / VERIFY GROUP
    # =========================================================

    def find_group(self, group_name: str) -> None:
        """Type `group_name` into the search box. Does NOT open or send anything."""
        print(f"\nSearching for group: {group_name}")

        search_box = self.page.locator('div[contenteditable="true"][data-tab="3"]').first
        search_box.wait_for(state="visible", timeout=10000)
        search_box.click()
        search_box.press("ControlOrMeta+A")
        search_box.press("Backspace")
        search_box.fill(group_name)

        time.sleep(3)
        print("Search results loaded.")

    def open_group(self, group_name: str) -> None:
        """Click the exact matching chat/group from the search results."""
        print(f"Looking for exact group: {group_name}")

        result = self.page.locator("#pane-side").get_by_text(group_name, exact=True).first
        result.wait_for(state="visible", timeout=10000)
        result.click()

        time.sleep(2)
        print(f"Opened group: {group_name}")

    def verify_group(self, group_name: str) -> None:
        """
        Confirm the chat header actually contains `group_name` before
        anything is sent. Raises RuntimeError on mismatch -- callers
        must treat that as "stop, send nothing" (see main.py).
        """
        header = self.page.locator("header").first
        header.wait_for(state="visible", timeout=5000)

        header_text = header.inner_text()
        if group_name not in header_text:
            raise RuntimeError(
                f"Wrong chat is open. Expected group '{group_name}', but the "
                f"open chat header reads:\n{header_text}"
            )

        print(f"Verified group: {group_name}")

    # =========================================================
    # SEND PLAIN TEXT MESSAGE (the intro message)
    # =========================================================

    def send_message(self, text: str) -> None:
        """
        Type and send a plain text message in the currently open chat.
        Used for the daily intro message that precedes the poll.
        """
        if not text.strip():
            raise ValueError("Cannot send an empty message.")

        message_box = self.page.locator(
            'div[contenteditable="true"][data-tab="10"], '
            'footer div[contenteditable="true"]'
        ).first
        message_box.wait_for(state="visible", timeout=10000)
        message_box.click()

        # WhatsApp's rich-text box turns "\n" into a newline only when
        # the newline is inserted with Shift+Enter; a plain Enter
        # sends the message. We type line by line to preserve the
        # multi-line template exactly.
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line:
                self.page.keyboard.insert_text(line)
            if i != len(lines) - 1:
                self.page.keyboard.press("Shift+Enter")

        self.page.keyboard.press("Enter")
        time.sleep(1.5)
        print("Intro message sent.")

    # =========================================================
    # CREATE POLL (build, but do not send)
    # =========================================================

    def create_poll(self, question: str, options: List[str]) -> None:
        """
        Build a native WhatsApp Poll with "Allow multiple answers"
        disabled. Does NOT click the final Send button -- call
        send_poll() afterwards.
        """
        if not question.strip():
            raise ValueError("Poll question cannot be empty.")

        cleaned_options = [opt.strip() for opt in options]
        if any(not opt for opt in cleaned_options):
            raise ValueError("Poll contains an empty option.")
        if len(cleaned_options) < MIN_POLL_OPTIONS:
            raise ValueError(f"A WhatsApp poll requires at least {MIN_POLL_OPTIONS} options.")
        if len(cleaned_options) > MAX_POLL_OPTIONS:
            raise ValueError(f"WhatsApp polls support at most {MAX_POLL_OPTIONS} options.")
        if len({opt.lower() for opt in cleaned_options}) != len(cleaned_options):
            raise ValueError("Poll contains duplicate options.")

        print("\n" + "=" * 60)
        print("CREATING POLL")
        print("=" * 60)
        print(f"Question: {question}")
        for i, opt in enumerate(cleaned_options, start=1):
            print(f"  {i}. {opt}")

        # --- Step 1: open the attachment menu ---
        attach_button = self.page.locator(
            'button[aria-label*="Attach"], button[aria-label*="attach"], '
            'button[title*="Attach"], button[title*="attach"]'
        ).first
        attach_button.wait_for(state="visible", timeout=10000)
        attach_button.click()
        time.sleep(1)

        # --- Step 2: click "Poll" ---
        poll_button = self.page.get_by_text("Poll", exact=True).last
        poll_button.wait_for(state="visible", timeout=5000)
        poll_button.click()
        time.sleep(1)
        print("Poll composer opened.")

        # --- Step 3: fill the question ---
        question_input = self.page.get_by_placeholder("Ask question", exact=True)
        question_input.wait_for(state="visible", timeout=5000)
        question_input.fill(question)
        print("Question filled.")

        # --- Step 4: fill the first two (always-present) option fields ---
        option_inputs = self.page.get_by_placeholder("Add", exact=True)
        if option_inputs.count() < 2:
            raise RuntimeError("Could not find the initial WhatsApp poll option fields.")

        option_inputs.nth(0).fill(cleaned_options[0])
        option_inputs.nth(1).fill(cleaned_options[1])

        # --- Step 5: add + fill any remaining options one at a time ---
        for option in cleaned_options[2:]:
            current_inputs = self.page.get_by_placeholder("Add", exact=True)
            before_count = current_inputs.count()

            add_elements = self.page.get_by_text("Add", exact=True)
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
                raise RuntimeError("Could not find the 'Add option' control.")

            self.page.wait_for_timeout(300)

            current_inputs = self.page.get_by_placeholder("Add", exact=True)
            after_count = current_inputs.count()
            if after_count <= before_count:
                raise RuntimeError("WhatsApp did not create a new poll option field.")

            current_inputs.nth(after_count - 1).fill(option)

        print(f"Filled {len(cleaned_options)} options.")

        # --- Step 6: disable "Allow multiple answers" ---
        self.disable_multiple_answers()
        print("Multiple answers disabled.")
        print("Poll is fully prepared (NOT sent yet).")

    def disable_multiple_answers(self) -> None:
        """WhatsApp polls default to allowing multiple answers; our quiz
        requires exactly one, so this must run before send_poll()."""
        label = self.page.get_by_text("Allow multiple answers", exact=True)
        label.wait_for(state="visible", timeout=5000)

        parent = label.locator("xpath=..")
        checkbox = parent.get_by_role("checkbox")

        if checkbox.count() > 0:
            checkbox = checkbox.first
            if checkbox.is_checked():
                checkbox.click()
            return

        # Fallback for markup where clicking the row itself toggles it.
        parent.click()

    def send_poll(self) -> None:
        """Send the poll previously built by create_poll()."""
        print("Sending poll...")

        send_button = self.page.get_by_text("Send", exact=True).last
        send_button.wait_for(state="visible", timeout=5000)

        if not send_button.is_enabled():
            raise RuntimeError(
                "Poll Send button is disabled -- the poll may not be fully filled in."
            )

        send_button.click()
        time.sleep(2)
        print("Poll sent successfully.")

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self) -> None:
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
