import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

# ----------------------------
# Configuration
# ----------------------------
INTERESTS_URL = f"https://www.linkedin.com/in/{os.getenv("LINKEDIN_URL_TAG", "")}/details/interests/?detailScreenTabIndex=0"
COOKIES_PATH = Path("cookies.json")
PROFILE_DIR = Path("chrome_profile")  # persists full browser cache/cookies (best for Step 2)
LOGIN_URL = "https://www.linkedin.com/login"
HOME_URL = "https://www.linkedin.com/feed/"

WAIT_LONG = 20
WAIT_SHORT = 5


def make_driver():
    """Create a Chrome WebDriver with a persistent user profile (cache & cookies)."""
    options = webdriver.ChromeOptions()
    # Use a dedicated user-data-dir so you stay logged in across runs (Step 2)
    profile_abs = str(PROFILE_DIR.resolve())
    options.add_argument(f"--user-data-dir={profile_abs}")
    options.add_argument("--profile-directory=Default")
    # Optional: uncomment for visible window size
    options.add_argument("--window-size=1200,900")
    # NOTE: Running headless often triggers bot detection on login pages. Keep it visible.

    service = Service()  # Selenium Manager will fetch a compatible driver automatically
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(2)
    return driver


def is_logged_in(driver):
    """Heuristic: if global nav is present and we’re not on the login page, assume logged in."""
    try:
        WebDriverWait(driver, WAIT_SHORT).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        return True
    except TimeoutException:
        return False


def load_cookies_if_present(driver):
    """Optional cookie restore to avoid login (works best when used with PROFILE_DIR)."""
    if not COOKIES_PATH.exists():
        return
    driver.get("https://www.linkedin.com/")  # domain must match for setting cookies
    try:
        cookies = json.loads(COOKIES_PATH.read_text())
        for ck in cookies:
            # Selenium requires removing 'sameSite' or invalid fields in some versions
            ck.pop("sameSite", None)
            ck.pop("expiry", None)  # sometimes causes issues; cookie may still set
            try:
                driver.add_cookie(ck)
            except Exception:
                pass
        driver.refresh()
        time.sleep(2)
    except Exception:
        pass


def save_cookies(driver):
    """Persist cookies to file for later reuse."""
    try:
        cookies = driver.get_cookies()
        COOKIES_PATH.write_text(json.dumps(cookies, indent=2))
    except Exception:
        pass


def login_with_env(driver):
    """Step 1: Use .env USERNAME/PASSWORD to log into LinkedIn."""
    load_dotenv()
    username = os.getenv("USERNAME", "")
    password = os.getenv("PASSWORD", "")
    if not username or not password:
        raise RuntimeError("USERNAME or PASSWORD missing in .env")

    driver.get(LOGIN_URL)
    # If already logged in (sticky session), bail early.
    if is_logged_in(driver):
        return

    # Fill and submit the login form
    WebDriverWait(driver, WAIT_LONG).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    u = driver.find_element(By.ID, "username")
    p = driver.find_element(By.ID, "password")
    u.clear()
    u.send_keys(username)
    p.clear()
    p.send_keys(password)

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait for either successful login or potential 2FA page.
    # If 2FA appears, give you time to complete it manually.
    try:
        WebDriverWait(driver, WAIT_LONG).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
    except TimeoutException:
        # Give the user a chance to complete any challenge manually
        print("If 2FA/security check is visible, please complete it in the browser...")
        try:
            WebDriverWait(driver, 120).until(
                EC.presence_of_element_located((By.ID, "global-nav"))
            )
        except TimeoutException:
            raise RuntimeError("Login did not complete. Check credentials or challenges.")


def ensure_logged_in(driver):
    """Try cookie restore, then fall back to login if needed. Finally, save cookies."""
    # Attempt cookie restore (optional; profile dir usually suffices)
    load_cookies_if_present(driver)
    driver.get(HOME_URL)

    if not is_logged_in(driver):
        login_with_env(driver)

    # Save cookies for future runs
    save_cookies(driver)


def click_all_following_buttons_on_page(driver):
    """
    Click every visible 'Following' button on the current view.
    Returns the number of toggles performed.
    """
    toggled = 0

    # Find buttons whose visible text includes 'Following' (LinkedIn UI uses nested spans)
    # We match the span text then take its ancestor button.
    buttons = driver.find_elements(
        By.XPATH,
        "//button[.//span[normalize-space()='Following'] or normalize-space()='Following']",
    )

    for btn in buttons:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.2)
            try:
                btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", btn)

            # Wait for it to become 'Follow' (toggle complete)
            try:
                WebDriverWait(driver, WAIT_SHORT).until(
                    lambda d: "Following" not in btn.text
                )
            except Exception:
                # If the element went stale after toggle, that’s fine.
                pass

            toggled += 1
            time.sleep(0.2)
        except StaleElementReferenceException:
            # Item updated after click; treat as success and keep going
            toggled += 1
        except Exception:
            # Skip any problematic item and continue
            continue

    return toggled


def switch_to_companies_tab_if_present(driver):
    """
    Ensure we’re on the 'Companies' tab in the Interests page.
    The URL you provided should already be the Companies tab,
    but this adds a defensive click in case the UI changes.
    """
    try:
        # Look for a tab-like element containing 'Companies'
        tab = WebDriverWait(driver, WAIT_SHORT).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[.//span[contains(normalize-space(.), 'Companies')]]"
                    "|//a[contains(@href,'detailScreenTabIndex') and contains(., 'Companies')]",
                )
            )
        )
        tab.click()
        time.sleep(1)
    except TimeoutException:
        # If not found, we proceed assuming current tab is Companies.
        pass


def scroll_and_unfollow_all(driver):
    """
    Step 3: Scroll the page, repeatedly unfollowing every company until no more are left.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    total_unfollowed = 0
    unchanged_scrolls = 0

    while True:
        # Click 'Following' buttons currently in view
        toggled_now = click_all_following_buttons_on_page(driver)
        total_unfollowed += toggled_now

        # Scroll to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            unchanged_scrolls += 1
        else:
            unchanged_scrolls = 0
        last_height = new_height

        # If we didn't toggle anything this pass AND the scroll height isn't changing,
        # we’re likely done.
        if toggled_now == 0 and unchanged_scrolls >= 2:
            break

    return total_unfollowed


def main():
    driver = make_driver()
    try:
        ensure_logged_in(driver)

        # Go to interests page and ensure the Companies tab is active
        driver.get(INTERESTS_URL)
        WebDriverWait(driver, WAIT_LONG).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        switch_to_companies_tab_if_present(driver)

        print("Unfollowing all companies… this may take a bit as the page lazy-loads.")
        total = scroll_and_unfollow_all(driver)
        print(f"Done. Unfollowed {total} companies.")

        # Persist cookies again at the end (in case they rotated)
        save_cookies(driver)

        # Keep the window open for a moment so you can see the result
        time.sleep(2)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
