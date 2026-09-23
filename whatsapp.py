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
        """
        Check whether WhatsApp Web has finished loading
        the logged-in chat interface.
        """

        try:
            # WhatsApp's main chat area contains this navigation
            # element when the account is logged in.
            self.page.locator("#pane-side").wait_for(
                state="visible",
                timeout=5000
            )

            return True

        except Exception:
            return False

    def wait_for_login(self):
        print()
        print("=" * 60)
        print("WAITING FOR WHATSAPP LOGIN")
        print("=" * 60)
        print()
        print("If you see a QR code, scan it with your phone.")
        print("The program will continue automatically after login.")
        print()

        while True:

            if self.is_logged_in():
                print("✅ WhatsApp login detected.")
                return True

            time.sleep(2)

    def close(self):
        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()


if __name__ == "__main__":

    bot = WhatsAppBot()

    try:
        bot.start()

        print("WhatsApp Web opened.")

        bot.wait_for_login()

        print()
        print("WhatsApp is ready.")
        print("Nothing will be sent yet.")
        print()
        print("Press Ctrl+C to close.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nClosing...")

    finally:
        bot.close()