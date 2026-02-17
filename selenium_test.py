from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

# Initialize the Chrome driver using WebDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # 1. Open your local Django server address
    driver.get("http://127.0.0.1:8000/login/")
    
    # 2. Perform actions: enter credentials and click login
    driver.find_element(By.NAME, "username").send_keys("pranavwaghmare")
    driver.find_element(By.NAME, "password").send_keys("ilovemai")
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    
    # 3. Verify success
    time.sleep(2)
    if "Dashboard" in driver.title or "Welcome" in driver.page_source:
        print("TEST PASSED: Functional login successful.")
    else:
        print("TEST FAILED: Could not verify login success.")
        exit(1) # Signal failure to Jenkins

finally:
    driver.quit()
