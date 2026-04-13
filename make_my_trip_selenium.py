import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def mmt():
    print("Running for https://makemytrip.com")
    
    total_clicks = 0
    start_time = time.time()

    def log(msg):
        print(f"{msg} | Clicks: {total_clicks} | Time: {time.time() - start_time:.2f}s")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.get("https://makemytrip.com")
    time.sleep(5)

    # close annoying popup
    try:
        driver.find_element(By.CLASS_NAME, "commonModal__close").click()
        total_clicks += 1
        log("Closed annoying popup")
        time.sleep(1)
    except:
        pass

    # ignore AI search and use default search
    try:
        driver.find_element(
            By.XPATH, "//span[contains(text(), 'Back to Classic Search')]"
        ).click()
        total_clicks += 1
        log("Back to Classic Search clicked")
        time.sleep(1)
    except:
        pass

    # select source city
    driver.find_element(By.ID, "fromCity").click()
    total_clicks += 1
    time.sleep(2)
    from_input = driver.switch_to.active_element
    from_input.send_keys("Hyderabad")
    time.sleep(2)
    from_input.send_keys(Keys.ARROW_DOWN)
    from_input.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Selected source city: Hyderabad")
    time.sleep(3)

    # select destination city
    driver.find_element(By.ID, "toCity").click()
    total_clicks += 1
    time.sleep(2)
    to_input = driver.switch_to.active_element
    to_input.send_keys("Delhi")
    time.sleep(2)
    to_input.send_keys(Keys.ARROW_DOWN)
    to_input.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Selected destination city: Delhi")
    time.sleep(3)

    # navigate to June 2026
    isJune = False
    while not isJune:
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'June 2026')]")
            isJune = True
        except:
            driver.find_element(By.XPATH, "//span[@aria-label='Next Month']").click()
            total_clicks += 1
            log("Navigated calendar forward")
            time.sleep(1)

    driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Jun 15 2026')]").click()
    total_clicks += 1
    log("Selected date: Jun 15 2026")
    time.sleep(2)

    driver.find_element(By.XPATH, "//a[contains(@class, 'primaryBtn')]").click()
    total_clicks += 1
    log("Clicked on search, waiting on results...")
    time.sleep(15)

    driver.find_element(By.CLASS_NAME, "ViewFareBtn").click()
    total_clicks += 1
    log("Opened fare popup")
    time.sleep(3)

    driver.find_element(By.XPATH, "(//button[contains(text(), 'BOOK NOW')])[1]").click()
    total_clicks += 1
    log("Clicked Book Now, waiting for new tab...")
    time.sleep(5)

    # switch to the new tab
    driver.switch_to.window(driver.window_handles[-1])
    log("Switched to new tab")
    time.sleep(5)

    # click "No, I will book without trip secure"
    driver.find_elements(By.XPATH, "//label[contains(@class, 'radioboxContainer')]")[1].click()
    total_clicks += 1
    log("Declined trip secure")
    time.sleep(2)

    driver.find_element(By.CLASS_NAME, "addTravellerBtn").click()
    total_clicks += 1
    log("Clicked Add New Adult")
    time.sleep(2)

    # fill first name
    driver.find_element(
        By.XPATH,
        "//input[contains(@placeholder, 'First & Middle Name') or contains(@placeholder, 'first name')]",
    ).send_keys("John")
    log("Filled first name")
    time.sleep(1)

    # fill last name
    driver.find_element(
        By.XPATH,
        "//input[contains(@placeholder, 'Last Name') or contains(@placeholder, 'last name')]",
    ).send_keys("Doe")
    log("Filled last name")
    time.sleep(1)

    # select male
    driver.find_element(By.XPATH, "//input[@type='radio' and @value='MALE']").click()
    total_clicks += 1
    log("Selected Male")
    time.sleep(1)

    # fill mobile number
    driver.find_element(
        By.XPATH, "//div[@id='contactDetails']//input[@placeholder='Mobile No']"
    ).send_keys("8888888888")
    log("Filled mobile number")
    time.sleep(1)

    # fill email
    driver.find_element(
        By.XPATH, "//div[@id='contactDetails']//input[@placeholder='Email']"
    ).send_keys("email@gmail.com")
    log("Filled email")
    time.sleep(1)

    # check "confirm and save billing details to your profile"
    confirm = driver.find_element(By.ID, "cb_gst_info")
    driver.execute_script("arguments[0].click();", confirm)
    total_clicks += 1
    log("Checked billing details checkbox")
    time.sleep(1)

    # click continue
    first_continue = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", first_continue)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Clicked Continue")
    time.sleep(10)

    # confirm details popup
    try:
        popup_confirm = driver.find_element(
            By.XPATH, "//div[contains(@class, 'detailsPopupFooter')]//button"
        )
        driver.execute_script("arguments[0].click();", popup_confirm)
        total_clicks += 1
        log("Confirmed details popup")
        time.sleep(3)
    except:
        pass

    # seat selection popup - click "Yes Please"
    driver.find_element(
        By.XPATH,
        "//button[contains(text(), 'Yes Please') or contains(text(), 'Yes, Please') or contains(text(), 'YES PLEASE')]",
    ).click()
    total_clicks += 1
    log("Accepted seat suggestion")
    time.sleep(3)

    continue_btn = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Clicked continue on the seat menu")
    time.sleep(3)

    continue_btn = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Clicked continue on the food menu")
    time.sleep(3)

    # I understand popup for window seat
    try:
        popup_confirm = driver.find_element(
            By.XPATH, "//div[contains(@class, 'footerBtnWrap')]//button"
        )
        driver.execute_script("arguments[0].click();", popup_confirm)
        total_clicks += 1
        log("Pressed I understand for window seat confirmation popup")
        time.sleep(3)
    except:
        pass

    continue_btn = driver.find_element(By.CSS_SELECTOR, "#cta_section button")
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Clicked continue on the cabs menu")
    time.sleep(3)

    # close flexibility popup
    try:
        wait_short = WebDriverWait(driver, 5)
        flexi_close = wait_short.until(
            EC.element_to_be_clickable((By.XPATH,
                "//*[contains(@class,'flexi') or contains(@class,'Flexi')]"
                "//*[contains(@class,'close') or contains(@class,'Close') or contains(@class,'dismiss')]"
                " | //div[contains(@class,'modal')]//button[contains(@class,'close') or contains(@class,'Close')]"
            ))
        )
        driver.execute_script("arguments[0].click();", flexi_close)
        total_clicks += 1
        log("Closed flexibility popup")
        time.sleep(2)
    except:
        log("No flexibility popup found, continuing...")

    wait = WebDriverWait(driver, 15)
    continue_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#cta_section button"))
    )
    driver.execute_script("arguments[0].focus();", continue_btn)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    total_clicks += 1
    log("Clicked continue on the add-ons menu")
    time.sleep(3)

    total_time = time.time() - start_time
    print(f"\nAll steps completed till payment!")
    print(f"Total clicks (including Enter presses): {total_clicks}")
    print(f"Total time taken: {total_time:.2f} seconds")
    
    time.sleep(30)
    quit(0)


mmt()