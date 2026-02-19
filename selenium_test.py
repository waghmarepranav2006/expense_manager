from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Headless mode allows the test to run in the background
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("http://127.0.0.1:8000/login/")
    driver.find_element(By.NAME, "username").send_keys("pranavwaghmare")
    driver.find_element(By.NAME, "password").send_keys("ilovemai")
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    
    time.sleep(2)
    # Verify the specific header from your view_expenses.html template
    if "My Expenses" in driver.page_source:
        print("TEST PASSED: Functional login successful.")
    else:
        print("TEST FAILED: Could not find dashboard header.")
        exit(1)
finally:
    driver.quit()
