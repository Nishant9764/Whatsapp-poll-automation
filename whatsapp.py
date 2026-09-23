from playwright.sync_api import sync_playwright


SESSION_DIR = "whatsapp_session"


def open_whatsapp():
    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            viewport={"width": 1400, "height": 900}
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        page.goto("https://web.whatsapp.com")

        print("\nWhatsApp Web opened.")
        print("If you see a QR code, scan it with your phone.")
        print("After WhatsApp loads, press ENTER here.")

        input()

        print("Session saved.")

        browser.close()


if __name__ == "__main__":
    open_whatsapp()