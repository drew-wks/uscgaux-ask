import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit as st


def check_app_status(url, success_strings=None, failure_strings=None):
    """
    This function checks the status of a web application by navigating to the provided URL 
    and searching for specific text strings on the page using Selenium to automate a 
    Chrome browser in headless mode

    Args:
        url (str): The URL of the web page to check.
        success_strings (list[str], optional): List of strings that indicate app is working.
            Defaults to ["Hosted with Streamlit"].
        failure_strings (list[str], optional): List of strings that indicate app is down.
            Defaults to ["Zzzz"].

    Behavior:
        - If any success string is found, prints success message.
        - If any failure string is found, prints failure message.
        - If neither are found, prints the entire text content of the page.
        - Includes error handling for network errors or web driver issues.

    Note:
        This script is designed to run in headless mode, making it suitable for use in 
        environments without a GUI, such as in automated CI/CD pipelines on GitHub Actions.

    Example:
        >>> check_app_status("https://ask-test.streamlit.app/", ["USCG Auxiliary"], ["Zzzz"])
        🎉 Yay! App is working: 'USCG Auxiliary'
    """
    if success_strings is None:
        success_strings = ["Hosted with Streamlit"]
    if failure_strings is None:
        failure_strings = ["Zzzz"]
    try:
        # Set up Chrome options for headless mode
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model, required for running in containers
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

        # Set up the Selenium WebDriver with Chrome in headless mode
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) # remove options= paraamter for non-headless model
        

        driver.get(url)
        time.sleep(5) # give time for javascript to load
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Check for success strings first
        for success_string in success_strings:
            if success_string in page_text:
                print(f"🎉 Yay! App is working: '{success_string}'")
                return

        # Check for failure strings
        for failure_string in failure_strings:
            if failure_string in page_text:
                print(f"⚠️ App is down: '{failure_string}'")
                return

        # If neither success nor failure strings found
        print("Text found on the page:")
        print(page_text)

    except Exception as e:
        print(f"An error occurred while trying to access {url}: {e}")
    finally:
        driver.quit()


check_app_status(
    st.secrets["APP_URL"], 
    st.secrets.get("SUCCESS_STRINGS", ["Hosted with Streamlit"]), 
    st.secrets.get("FAILURE_STRINGS", ["Zzzz"])
)
