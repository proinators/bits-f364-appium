import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time


def goibibo():
    total_clicks = 0
    start_time = time.perf_counter()
    print("Running for https://www.goibibo.com")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.get("https://www.goibibo.com")
    time.sleep(5)

    # 1. Close Login Popup
    try:
        driver.find_element(By.XPATH, "//span[contains(@class, 'icClose')]").click()
        total_clicks += 1
        time.sleep(1)
    except:
        pass

    # 2. Select Source and Destination
    driver.find_element(By.ID, "fromCity").click()
    total_clicks += 1
    time.sleep(2)
    from_input = driver.switch_to.active_element
    from_input.send_keys("Hyderabad")
    time.sleep(2)
    from_input.send_keys(Keys.ARROW_DOWN)
    time.sleep(2)
    from_input.send_keys(Keys.ENTER)
    total_clicks += 1
    time.sleep(3)

    # Destination
    driver.find_element(By.ID, "toCity").click()
    total_clicks += 1
    time.sleep(2)
    to_input = driver.switch_to.active_element
    to_input.send_keys("Delhi")
    time.sleep(2)
    to_input.send_keys(Keys.ARROW_DOWN)
    time.sleep(2)
    to_input.send_keys(Keys.ENTER)
    total_clicks += 1
    time.sleep(3)

    # 3. Calendar Navigation (June 2026)

    # driver.find_element(By.CLASS_NAME, "dates").click()

    isJune = False
    while not isJune:
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'June 2026')]")
            isJune = True
        except:
            driver.find_element(By.XPATH, "//span[@aria-label='Next Month']").click()
            total_clicks += 1
            time.sleep(1)

    driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Jun 15 2026')]").click()
    total_clicks += 1
    time.sleep(2)
    driver.find_element(By.XPATH, "//a[contains(@class, 'primaryBtn')]").click()
    total_clicks += 1
    print("Clicked on search, waiting on results...")
    time.sleep(10)

    try:
        driver.find_element(By.XPATH, "//span[text()='Done']").click()
        total_clicks += 1
    except:
        pass

    search_btn = driver.find_element(By.XPATH, "//*[text()='SEARCH']")
    driver.execute_script("arguments[0].click();", search_btn)
    total_clicks += 1
    print("Searching...")
    time.sleep(10)

    time.sleep(5)
    try:
        overlay = driver.find_element(By.CLASS_NAME, "coachmarkOverlay")
        driver.execute_script("arguments[0].click();", overlay)
        total_clicks += 1
        print("Dismissed the coachmark overlay.")
    except:
        driver.execute_script("document.body.click();")
        total_clicks += 1
        print("No overlay found, clicked body to clear UI.")

    time.sleep(2)

    try:
        driver.find_element(By.CLASS_NAME, "ViewFareBtn").click()
        total_clicks += 1
        time.sleep(5)
        driver.find_element(By.XPATH, "(//button[text()='BOOK NOW'])[1]").click()
        total_clicks += 1
        time.sleep(5)
    except:
        driver.find_element(By.XPATH, "(//button[text()='BOOK NOW'])[1]").click()
        total_clicks += 1

    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])
    print("Changed tabs...")

    driver.find_elements(By.XPATH, "//label[contains(@class, 'radioboxContainer')]")[
        1
    ].click()
    total_clicks += 1
    time.sleep(2)

    addAdult = driver.find_element(By.CLASS_NAME, "addTravellerBtn")
    driver.execute_script("arguments[0].click();", addAdult)
    total_clicks += 1
    time.sleep(2)

    driver.find_element(
        By.XPATH, "//input[contains(@placeholder, 'First & Middle Name')]"
    ).send_keys("John")
    driver.find_element(By.XPATH, "//input[@placeholder='Last Name']").send_keys("Doe")
    driver.find_element(By.XPATH, "//input[@value='MALE']").click()
    total_clicks += 1
    print("Selected Male...")
    time.sleep(1)

    try:
        day_select = Select(
            driver.find_element(
                By.XPATH, "//select[contains(@class, 'day')] | (//select)[1]"
            )
        )
        total_clicks += 1
        day_select.select_by_visible_text("1")
        month_select = Select(
            driver.find_element(
                By.XPATH, "//select[contains(@class, 'month')] | (//select)[2]"
            )
        )
        total_clicks += 1
        month_select.select_by_visible_text("January")
        year_select = Select(
            driver.find_element(
                By.XPATH, "//select[contains(@class, 'year')] | (//select)[3]"
            )
        )
        total_clicks += 1
        year_select.select_by_visible_text("2000")
        print("DOB set to 1 Jan 2000")
    except Exception as e:
        print(f"DOB fail (might be direct text input): {e}")

    driver.find_element(By.XPATH, "//input[@placeholder='Mobile No']").send_keys(
        "8888888888"
    )
    time.sleep(1)

    driver.find_element(By.XPATH, "//input[@placeholder='Email']").send_keys(
        "email@gmail.com"
    )
    time.sleep(1)

    try:
        confirm = driver.find_element(By.XPATH, "//label[@for='confirm_check']")
        driver.execute_script("arguments[0].click();", confirm)
        total_clicks += 1
        print("Checked billing details checkbox...")
    except:
        pass
    time.sleep(1)

    continue_btn = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    print("Clicked Continue...")
    time.sleep(10)

    try:
        popup_confirm = driver.find_element(
            By.XPATH, "//button[text()='OK' or text()='CONFIRM']"
        )
        driver.execute_script("arguments[0].click();", popup_confirm)
        total_clicks += 1
        print("Confirmed details...")
        time.sleep(3)
    except:
        pass

    continue_btn = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    print("Clicked Continue to Payment...")
    time.sleep(3)

    print("Reached Payment! Done.")
    end_time = time.perf_counter()
    time.sleep(1)
    print(f"Total clicks: {total_clicks}")
    print(f"Total time taken: {end_time - start_time:0.6f} seconds")
    time.sleep(20)
    driver.quit()


goibibo()
