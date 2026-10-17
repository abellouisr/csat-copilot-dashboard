"""Open the Streamlit app in a headless browser and wake it if it has gone to sleep."""

import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "https://csat-copilot-dashboard.streamlit.app/")
WAKE_BUTTON = "Yes, get this app back up!"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(8_000)
    button = page.get_by_role("button", name=WAKE_BUTTON)
    if button.count():
        print("App was asleep: clicking the wake-up button")
        button.first.click()
        page.wait_for_timeout(90_000)  # give the app time to boot
    else:
        print("App is awake")
    print("Visited:", page.url)
    browser.close()
