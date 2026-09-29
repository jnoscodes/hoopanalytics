"""Visit the live demo in a real (headless) browser so it doesn't go to sleep.

Streamlit Community Cloud puts apps to sleep after 12 hours without traffic,
and a sleeping app shows a "Yes, get this app back up!" button instead of
the app. A plain HTTP request (curl, an uptime pinger) isn't enough: the
app only runs once a browser opens a live session with it. So this script
drives an actual browser, clicks the wake-up button if the app is asleep,
then waits until the app itself has rendered.

Run on a schedule by .github/workflows/keep-awake.yml. Exits non-zero if the
app never loads, which makes the workflow run fail -- GitHub then emails the
repo owner, so this doubles as a basic "live demo is down" alert.
"""

import sys
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

APP_URL = "https://hoopanalytics.streamlit.app/"
WAKE_BUTTON_TEXT = "Yes, get this app back up!"
APP_TITLE_TEXT = "HoopAnalytics"

# Waking a sleeping app restarts its container and reinstalls dependencies,
# which can take a few minutes on Streamlit's side.
LOAD_TIMEOUT_SECONDS = 300
POLL_SECONDS = 2
# Stay connected briefly once loaded, so the visit registers as a session.
STAY_SECONDS = 15


def _find_in_frames(page, make_locator):
    """Return the first visible match across all frames, or None.

    The app runs inside an iframe on the outer streamlit.app page, so the
    top-level document alone isn't enough to search.
    """
    for frame in page.frames:
        try:
            locator = make_locator(frame).first
            if locator.is_visible():
                return locator
        except PlaywrightError:
            continue  # frame navigated/detached mid-check; recheck next poll
    return None


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded")

        clicked_wake = False
        start = time.monotonic()

        while time.monotonic() - start < LOAD_TIMEOUT_SECONDS:
            if _find_in_frames(page, lambda f: f.get_by_role("heading", name=APP_TITLE_TEXT)):
                elapsed = time.monotonic() - start
                state = "was asleep, woken up" if clicked_wake else "was already awake"
                print(f"OK: app loaded in {elapsed:.0f}s ({state}).")
                page.wait_for_timeout(STAY_SECONDS * 1000)
                browser.close()
                return 0

            wake_button = None if clicked_wake else _find_in_frames(
                page, lambda f: f.get_by_text(WAKE_BUTTON_TEXT)
            )
            if wake_button:
                print("App is asleep: clicking the wake-up button.")
                wake_button.click()
                clicked_wake = True

            page.wait_for_timeout(POLL_SECONDS * 1000)

        print(f"FAILED: app did not load within {LOAD_TIMEOUT_SECONDS}s.")
        page.screenshot(path="keep_awake_failure.png", full_page=True)
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
