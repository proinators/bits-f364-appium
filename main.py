import json
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import List, Optional

from appium import webdriver
from appium.options.android.uiautomator2.base import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class FlightResult:
    airline: str
    departure_time: str
    departure_city: str
    arrival_time: str
    arrival_city: str
    duration: str
    stops: str
    price: str


@dataclass
class BookingDetails:
    gender: str       # "MALE" or "FEMALE"
    first_name: str
    last_name: str
    email: str
    phone: str


class FlightScraper(ABC):
    """
    Common abstract class to build the tester for both the apps
    """
    APP_PACKAGE: str = ""
    APP_ACTIVITY: str = ""

    def __init__(self, device_id: str, appium_url: str = "http://127.0.0.1:4723"):
        self.device_id = device_id
        self.appium_url = appium_url
        self.driver: Optional[webdriver.Remote] = None
        self.tap_count: int = 0
        self.results: List[FlightResult] = []

    def start_session(self):
        opts = UiAutomator2Options()
        opts.device_name = self.device_id
        opts.app_package = self.APP_PACKAGE
        opts.app_activity = self.APP_ACTIVITY
        opts.no_reset = True
        self.driver = webdriver.Remote(self.appium_url, options=opts)
        self.driver.implicitly_wait(0)

    def end_session(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def tap(self, element):
        """Just something that 'intercepts' each tap and counts it."""
        self.tap_count += 1
        element.click()

    def wait(self, seconds: float = 1.0):
        time.sleep(seconds)

    def find(self, by, value, timeout: int = 10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def find_clickable(self, by, value, timeout: int = 10):
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def find_all(self, by, value):
        return self.driver.find_elements(by, value)

    def element_exists(self, by, value, timeout: int = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def _press_back(self):
        """Press the Android system back button."""
        assert self.driver is not None
        self.driver.back()

    # Shared calendar helpers

    _MONTH_ABBRS = [
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    ]

    def _visible_months_in_rv(self, rv_id: str) -> list:
        """
        Inspect every element with a content-desc inside the calendar RecyclerView
        and return an ordered list of (month_abbr_3, year_int) tuples, earliest first.
        Works for both MMT and Goibibo since both use the same
        "D MON YYYY ..." content-desc format (e.g. "15 JUN 2026 Tap to select").
        """
        assert self.driver is not None
        try:
            rv = self.driver.find_element(AppiumBy.ID, rv_id)
        except NoSuchElementException:
            return []
        seen: list = []
        seen_keys: set = set()
        for el in rv.find_elements(AppiumBy.XPATH, './/*[@content-desc]'):
            desc = str(el.get_attribute("content-desc") or "")
            parts = desc.split()
            # Expected: "D MON YYYY ..." where D is a day number, MON is 3-letter month
            if (len(parts) >= 3 and parts[0].isdigit()
                    and len(parts[1]) == 3 and parts[1].isalpha()):
                try:
                    mon = parts[1].upper()
                    yr = int(parts[2])
                    if mon in self._MONTH_ABBRS:
                        key = (mon, yr)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            seen.append(key)
                except (ValueError, IndexError):
                    pass
        return seen

    def _scroll_calendar_to_month(self, rv_id: str, target_abbr: str, target_year: int):
        """
        Scroll a calendar RecyclerView until the target month is the *first* visible month.
        Scrolls forward (up) or backward (down) as needed. When the target is already
        the second of two visible months, a smaller swipe nudges it to the top.
        """
        assert self.driver is not None
        target_abbr = target_abbr.upper()
        target_key = target_year * 12 + self._MONTH_ABBRS.index(target_abbr)

        for _ in range(24):
            visible = self._visible_months_in_rv(rv_id)
            if not visible:
                self.wait(0.5)
                continue

            first_abbr, first_year = visible[0]
            first_key = first_year * 12 + self._MONTH_ABBRS.index(first_abbr)

            if first_abbr == target_abbr and first_year == target_year:
                break  # target is already first — done

            rv = self.driver.find_element(AppiumBy.ID, rv_id)
            rv_loc = rv.location
            rv_size = rv.size
            cx = rv_loc["x"] + rv_size["width"] // 2

            if len(visible) >= 2:
                second_abbr, second_year = visible[1]
                if second_abbr == target_abbr and second_year == target_year:
                    # Target is the second month — small nudge upward to make it first
                    start_y = rv_loc["y"] + int(rv_size["height"] * 0.55)
                    end_y   = rv_loc["y"] + int(rv_size["height"] * 0.25)
                    self.driver.swipe(cx, start_y, cx, end_y, duration=400)
                    self.wait(0.5)
                    continue

            # Full swipe in the appropriate direction
            if target_key > first_key:
                # Target is ahead in time — swipe up (forward)
                start_y = rv_loc["y"] + int(rv_size["height"] * 0.75)
                end_y   = rv_loc["y"] + int(rv_size["height"] * 0.25)
            else:
                # Target is behind in time — swipe down (backward)
                start_y = rv_loc["y"] + int(rv_size["height"] * 0.25)
                end_y   = rv_loc["y"] + int(rv_size["height"] * 0.75)
            self.driver.swipe(cx, start_y, cx, end_y, duration=500)
            self.wait(0.5)

    # The following will be implemented by the corresponding classes

    @abstractmethod
    def dismiss_login_drawer_if_present(self):
        pass

    @abstractmethod
    def navigate_to_flights(self):
        pass

    @abstractmethod
    def select_one_way(self):
        pass

    @abstractmethod
    def set_origin(self, city_code: str):
        pass

    @abstractmethod
    def set_destination(self, city_code: str):
        pass

    @abstractmethod
    def set_date(self, month: str, day: int, year: int):
        pass

    @abstractmethod
    def set_travellers(self, adults: int = 1, children: int = 0,
                       infants: int = 0, cabin: str = "Economy"):
        pass

    @abstractmethod
    def search_flights(self):
        pass

    @abstractmethod
    def collect_results(self) -> List[FlightResult]:
        pass

    @abstractmethod
    def sort_by_cheapest(self):
        pass

    @abstractmethod
    def select_first_flight(self):
        """Tap the first (cheapest) result and reach the BOOK NOW screen."""
        pass

    @abstractmethod
    def fill_traveller_details(self, details: BookingDetails):
        pass

    @abstractmethod
    def fill_contact_details(self, details: BookingDetails):
        pass

    @abstractmethod
    def proceed_to_payment(self) -> str:
        """Complete all pre-payment steps and return the total-due string."""
        pass

    # Popup/permission handlers (no-op by default, override as needed)

    def dismiss_popup_if_present(self):
        pass

    def dismiss_permission_if_present(self):
        pass

    def run(self, origin: str, destination: str,
            month: str, day: int, year: int,
            booking: BookingDetails) -> str:
        print("Waiting for the app to start...")
        self.wait(3)
        print("Checking for login drawers")
        self.dismiss_login_drawer_if_present()
        print("Navigating to flights")
        self.navigate_to_flights()
        print("Selecting one way")
        self.select_one_way()
        print("Setting origin/departure")
        self.set_origin(origin)
        self.dismiss_popup_if_present()
        print("Setting destination/arrival")
        self.set_destination(destination)
        self.dismiss_popup_if_present()
        print("Setting date")
        self.set_date(month, day, year)
        print("Checking and setting travellers' details")
        self.set_travellers()
        print("Proceeding to search")
        self.search_flights()
        print("Sorting by cheapest")
        self.sort_by_cheapest()
        print("Selecting first (cheapest) flight")
        self.select_first_flight()
        print("Filling traveller details")
        self.fill_traveller_details(booking)
        print("Filling contact details")
        self.fill_contact_details(booking)
        print("Proceeding to payment")
        total_due = self.proceed_to_payment()
        return total_due


class MakeMyTripScraper(FlightScraper):
    APP_PACKAGE = "com.makemytrip"
    APP_ACTIVITY = "com.mmt.travel.app.home.ui.SplashActivityPrimary"

    def _dismiss_permission(self):
        """Tap 'Don't allow' on Android permission dialogs. Todo: Handle in built notification banners"""
        deny_id = ("com.android.permissioncontroller:"
                   "id/permission_deny_and_dont_ask_again_button")
        if self.element_exists(AppiumBy.ID, deny_id, timeout=2):
            self.tap(self.driver.find_element(AppiumBy.ID, deny_id))

    def _dismiss_banner(self):
        """Close promotional banners if present."""
        container_id = "com.makemytrip:id/fl_popup_container"
        close_id = "com.makemytrip:id/iv_close"
        if self.element_exists(AppiumBy.ID, container_id, timeout=2):
            if self.element_exists(AppiumBy.ID, close_id, timeout=2):
                self.tap(self.driver.find_element(AppiumBy.ID, close_id))
        rating_bar_id = "com.makemytrip:id/rating_bar"
        dark_bg_id = "com.makemytrip:id/view_bg_dark"
        if self.element_exists(AppiumBy.ID, rating_bar_id, timeout=2):
            if self.element_exists(AppiumBy.ID, dark_bg_id, timeout=2):
                self.tap(self.driver.find_element(AppiumBy.ID, dark_bg_id))

    def dismiss_popup_if_present(self):
        """Combines all the dismissing steps into one method"""
        self._dismiss_permission()
        self._dismiss_banner()

    # Dismiss the login drawer if it appears
    def dismiss_login_drawer_if_present(self):
        login_xpath = (
            '//*[contains(@text, "Login") and '
            '@resource-id="com.makemytrip:id/tv_header"]'
        )
        if self.element_exists(AppiumBy.XPATH, login_xpath, timeout=5):
            close_btn = self.find(AppiumBy.ID, "com.makemytrip:id/iv_cross")
            self.tap(close_btn)
        self.dismiss_popup_if_present()


    def navigate_to_flights(self):
        # Press back until we land on the home screen or the flight-search form.
        # Handles the case where the app was left deep in some other activity.
        for _ in range(5):
            if self.element_exists(AppiumBy.ID,
                                   "com.makemytrip:id/from_selection_layout", timeout=2):
                self.dismiss_popup_if_present()
                return
            # Visible Flights button means we're on the home screen — stop pressing back
            if self.element_exists(
                AppiumBy.XPATH,
                '//android.widget.Button[@text="Flights"]', timeout=2
            ):
                break
            self._press_back()
            self.dismiss_popup_if_present()
            self.wait(1.0)

        # We have multiple selectors here so that we increase chances of finding the button
        selectors = [
            (AppiumBy.XPATH,
             '//android.widget.Button[@text="Flights" '
             'and @resource-id="com.makemytrip:id/container"]'),
            (AppiumBy.XPATH,
             '//*[@resource-id="com.makemytrip:id/container" and @text="Flights"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"Flights")]'),
        ]
        btn = None
        for by, value in selectors:
            if self.element_exists(by, value, timeout=5):
                btn = self.driver.find_element(by, value)
                break
        if btn is None:
            print("[DEBUG] Current activity:",
                  self.driver.execute_script("mobile: getCurrentActivity"))
            raise RuntimeError("Could not find Flights button on home screen")
        self.tap(btn)
        self.dismiss_popup_if_present()

    def select_one_way(self):
        selector = self.find(AppiumBy.ID, "com.makemytrip:id/switchTabsSelector")
        one_way = selector.find_element(
            AppiumBy.XPATH, './/android.widget.TextView[@text="ONE WAY"]'
        )
        if one_way.get_attribute("selected") != "true":
            self.tap(one_way)
        self.dismiss_popup_if_present()

    def _current_city_in_layout(self, layout_id: str) -> Optional[str]:
        """
        Get the IATA city code in that layout, so that we can reduce the number of taps
        """
        try:
            layout = self.driver.find_element(AppiumBy.ID, layout_id)
            texts = [
                el.get_attribute("text")
                for el in layout.find_elements(AppiumBy.XPATH, './/android.widget.TextView')
            ]
            for t in texts:
                if t and len(t) == 3 and t.isupper() and t.isalpha():
                    return t
        except NoSuchElementException:
            pass
        return None

    def set_origin(self, city_code: str):
        """Set departure city; skip if already correct."""
        layout_id = "com.makemytrip:id/from_selection_layout"
        if self._current_city_in_layout(layout_id) == city_code:
            return
        self.tap(self.find(AppiumBy.ID, layout_id))
        self.dismiss_popup_if_present()
        search_box = self.find(AppiumBy.ID, "com.makemytrip:id/departure_city_input")
        search_box.clear()
        search_box.send_keys(city_code)
        result = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                AppiumBy.XPATH,
                f'//android.widget.TextView'
                f'[@text="{city_code}" and @resource-id="com.makemytrip:id/city_code"]',
            ))
        )
        self.tap(result)

    def set_destination(self, city_code: str):
        """Set arrival city; skip if already correct."""
        layout_id = "com.makemytrip:id/to_city_layout"
        if self._current_city_in_layout(layout_id) == city_code:
            return
        self.tap(self.find(AppiumBy.ID, layout_id))
        self.dismiss_popup_if_present()
        search_box = self.find(AppiumBy.ID, "com.makemytrip:id/arrival_city_input")
        search_box.clear()
        search_box.send_keys(city_code)
        result = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                AppiumBy.XPATH,
                f'//android.widget.TextView'
                f'[@text="{city_code}" and @resource-id="com.makemytrip:id/city_code"]',
            ))
        )
        self.tap(result)

    def set_date(self, month: str, day: int, year: int):
        """
        Open the calendar, scroll bidirectionally until the target month is first,
        then tap the date cell and confirm.
        """
        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/from_date_layout"))
        self.dismiss_popup_if_present()

        rv_id = "com.makemytrip:id/rvCalendarMonth"
        self.find(AppiumBy.ID, rv_id)  # wait for calendar to render

        month_abbr = month[:3].upper()
        self._scroll_calendar_to_month(rv_id, month_abbr, year)

        # The content-desc is "D MON YYYY Tap to select" when unselected,
        # and "D MON YYYY Selected" when already selected.
        already_selected_desc = f"{day} {month_abbr} {year} Selected"
        to_select_candidates = [
            f"{day} {month_abbr} {year} Tap to select",
            f"{day} {month_abbr} {year}",
        ]

        already_selected = self.element_exists(
            AppiumBy.XPATH, f'//*[@content-desc="{already_selected_desc}"]', timeout=3
        )

        if not already_selected:
            day_el = None
            for desc in to_select_candidates:
                if self.element_exists(AppiumBy.XPATH, f'//*[@content-desc="{desc}"]', timeout=3):
                    day_el = self.driver.find_element(AppiumBy.XPATH,
                                                      f'//*[@content-desc="{desc}"]')
                    break
            if day_el is None:
                all_descs = [
                    str(el.get_attribute("content-desc"))
                    for el in self.driver.find_elements(AppiumBy.XPATH, '//*[@content-desc]')
                    if str(day) in str(el.get_attribute("content-desc") or "")
                ]
                print(f"[DEBUG] Elements with day {day} in content-desc: {all_descs[:20]}")
                raise RuntimeError(f"Could not find date cell for {day} {month_abbr} {year}")
            self.tap(day_el)
        self.wait(0.5)
        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/btnDone"))

    def _read_count(self, section_id: str) -> int:
        xpath = (
            f'//android.widget.LinearLayout[@resource-id="{section_id}"]'
            f'//android.widget.LinearLayout[@resource-id="com.makemytrip:id/add_remove_view"]'
            f'//android.widget.TextView[@resource-id="com.makemytrip:id/tv_count"]'
        )
        return int(self.driver.find_element(AppiumBy.XPATH, xpath).get_attribute("text"))

    def _adjust_count(self, section_id: str, target: int):
        """Tap +/- until the count in this traveller section matches target."""
        # We use the tuple because we first find the right section, then get the count and buttons within it
        add_remove_xpath = (
            f'//android.widget.LinearLayout[@resource-id="{section_id}"]'
            f'//android.widget.LinearLayout[@resource-id="com.makemytrip:id/add_remove_view"]'
        )
        add_remove = self.driver.find_element(AppiumBy.XPATH, add_remove_xpath)
        count_xpath = f'.//android.widget.TextView[@resource-id="com.makemytrip:id/tv_count"]'

        current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))
        while current < target:
            self.tap(add_remove.find_element(AppiumBy.ID, "com.makemytrip:id/iv_add"))
            current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))
        while current > target:
            self.tap(add_remove.find_element(AppiumBy.ID, "com.makemytrip:id/iv_subtract"))
            current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))


    def set_travellers(self, adults: int = 1, children: int = 0,
                       infants: int = 0, cabin: str = "Economy"):
        """Verify/set traveller count and cabin class."""
        count_el = self.find(AppiumBy.ID, "com.makemytrip:id/tv_traveller_count")
        cabin_el = self.find(AppiumBy.ID, "com.makemytrip:id/tv_trip_type")
        count_text = count_el.get_attribute("text").strip()
        cabin_text = cabin_el.get_attribute("text")

        # count_text is like "1, " — extract the leading number
        count_num = count_text.rstrip(", ")
        already_correct = (count_num == str(adults) and cabin in cabin_text)
        if already_correct:
            return

        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/traveller_and_cabin_layout"))
        self.dismiss_popup_if_present()

        self._adjust_count("com.makemytrip:id/child_traveller_view", children)
        self._adjust_count("com.makemytrip:id/infant_traveller_view", infants)
        self._adjust_count("com.makemytrip:id/adult_traveller_view", adults)

        # Select Economy/Premium Economy cabin
        economy_tv = self.find(
            AppiumBy.XPATH,
            '//android.widget.TextView'
            '[@text="Economy/Premium Economy" and @resource-id="com.makemytrip:id/tv_economy"]',
        )
        self.tap(economy_tv)

        # Tap DONE (identified by its sibling header text to be unambiguous)
        done_btn = self.find(
            AppiumBy.XPATH,
            '//android.widget.Button'
            '[@text="DONE" and @resource-id="com.makemytrip:id/done_button"]',
        )
        self.tap(done_btn)
        self.dismiss_popup_if_present()

    def search_flights(self):
        """Tap SEARCH FLIGHTS."""
        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/search_button_flat"))
        self.dismiss_popup_if_present()

    def collect_results(self) -> List[FlightResult]:
        """
        Scroll the results page and collect every flight card.
        Stops when three consecutive scrolls produce no new cards.
        """
        results: List[FlightResult] = []
        seen: set = set()

        print("Waiting for flight results to load...")
        card_xpath = '//*[@resource-id="listing_card_v2"]'
        self.find(AppiumBy.XPATH, card_xpath, timeout=30)

        size = self.driver.get_window_size()
        scroll_start_y = int(size["height"] * 0.70)
        scroll_end_y = int(size["height"] * 0.25)
        scroll_x = size["width"] // 2

        no_new_streak = 0
        max_scrolls = 40

        for scroll_num in range(max_scrolls):
            self.dismiss_popup_if_present()
            cards = self.find_all(AppiumBy.XPATH, card_xpath)
            new_this_round = 0

            for card in cards:
                try:
                    airline = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="airline_name"]'
                    ).get_attribute("text")

                    dep_time = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="departure_time"]'
                    ).get_attribute("text")

                    arr_time = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="arrival_time"]'
                    ).get_attribute("text")

                    duration = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="duration_text"]'
                    ).get_attribute("text")

                    stops = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="stops_text"]'
                    ).get_attribute("text")

                    price = card.find_element(
                        AppiumBy.XPATH, './/*[@resource-id="final_price"]'
                    ).get_attribute("text")

                    # Verify source/destination city codes
                    city_els = card.find_elements(
                        AppiumBy.XPATH, './/*[@resource-id="city_code"]'
                    )
                    dep_city = city_els[0].get_attribute("text") if len(city_els) > 0 else ""
                    arr_city = city_els[1].get_attribute("text") if len(city_els) > 1 else ""

                    flight_key = (airline, dep_time, arr_time)
                    if flight_key not in seen and dep_city and arr_city:
                        seen.add(flight_key)
                        results.append(FlightResult(
                            airline=airline,
                            departure_time=dep_time,
                            departure_city=dep_city,
                            arrival_time=arr_time,
                            arrival_city=arr_city,
                            duration=duration,
                            stops=stops,
                            price=price,
                        ))
                        new_this_round += 1

                except NoSuchElementException:
                    continue

            print(f"  Scroll {scroll_num + 1}: +{new_this_round} new "
                  f"(total {len(results)})")

            if new_this_round == 0:
                no_new_streak += 1
                if no_new_streak >= 3:
                    break
            else:
                no_new_streak = 0

            # Swipe from scroll_start_y up to scroll_end_y to reveal content below
            self.driver.swipe(
                scroll_x, scroll_start_y,
                scroll_x, scroll_end_y,
                duration=600,
            )
            self.wait(1.5)

        print(f"Collection complete — {len(results)} flights found.")
        return results

    # ── Booking flow ────────────────────────────────────────────────────────

    def sort_by_cheapest(self):
        """
        Ensure the results are sorted cheapest-first.
        If the active tab is already "Cheapest" we skip; otherwise open the sort
        dropdown and pick "Cheapest (Price Low to High)".
        """
        # Wait for results to load before checking the sort tab
        self.find(AppiumBy.XPATH, '//*[@resource-id="listing_card_v2"]', timeout=30)
        self.dismiss_popup_if_present()

        cheapest_xpath = (
            '//android.widget.TextView'
            '[@text="Cheapest" and @resource-id="cluster_tab_title"]'
        )
        if self.element_exists(AppiumBy.XPATH, cheapest_xpath, timeout=3):
            # Already on cheapest tab — nothing to do
            return

        # Open the sort/filter dropdown
        sort_tab = self.find(AppiumBy.XPATH, '//*[@resource-id="cluster_tab_item"]')
        self.tap(sort_tab)

        # Pick the cheapest option from the list
        option_xpath = (
            '//android.widget.TextView'
            '[@text="Cheapest (Price Low to High)" and @resource-id="option_text"]'
        )
        self.tap(self.find(AppiumBy.XPATH, option_xpath))
        self.dismiss_popup_if_present()

    def select_first_flight(self):
        card_xpath = '//*[@resource-id="listing_card_v2"]'
        self.find(AppiumBy.XPATH, card_xpath, timeout=30)
        self.dismiss_popup_if_present()

        first_card = self.find_all(AppiumBy.XPATH, card_xpath)[0]
        self.tap(first_card)
        self.wait(1.5)
        self.dismiss_popup_if_present()

        book_now_xpath = '//android.widget.TextView[@text="BOOK NOW"]'
        self.find(AppiumBy.XPATH, book_now_xpath, timeout=15)
        self.tap(self.find_all(AppiumBy.XPATH, book_now_xpath)[0])
        self.dismiss_popup_if_present()

    def fill_traveller_details(self, details: BookingDetails):
        """
        Wait for review screen, tap CONTINUE (auto-scrolls to traveller section),
        add traveller details, and confirm.
        """
        continue_id = "com.makemytrip:id/review_tv"
        self.tap(self.find(AppiumBy.ID, continue_id, timeout=20))
        self.dismiss_popup_if_present()

        add_adult_xpath = '//android.widget.TextView[@text="Add new adult"]'
        self.tap(self.find(AppiumBy.XPATH, add_adult_xpath, timeout=10))
        self.dismiss_popup_if_present()

        gender_xpath = f'//android.widget.TextView[@text="{details.gender}"]'
        self.tap(self.find(AppiumBy.XPATH, gender_xpath))

        first_name_el = self.find(
            AppiumBy.XPATH,
            '//android.widget.EditText[@text="First & Middle Name"]',
        )
        first_name_el.send_keys(details.first_name)

        last_name_el = self.find(
            AppiumBy.XPATH,
            '//android.widget.EditText[@text="Last Name"]',
        )
        last_name_el.send_keys(details.last_name)

        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/confirm_button"))

        if not self.element_exists(
            AppiumBy.XPATH,
            f'//android.widget.TextView[contains(@text, "{details.last_name}")]',
            timeout=10,
        ):
            raise RuntimeError(
                f"Traveller '{details.first_name} {details.last_name}' did not appear after confirmation"
            )

    def fill_contact_details(self, details: BookingDetails):
        """
        Tap CONTINUE, enter email + phone, confirm, then tap CONTINUE again.
        """
        continue_id = "com.makemytrip:id/review_tv"
        self.tap(self.find(AppiumBy.ID, continue_id))
        self.dismiss_popup_if_present()

        # Enter email (hint text "Email" when empty)
        email_el = self.find(AppiumBy.XPATH, '//android.widget.EditText[@text="Email"]')
        email_el.clear()
        email_el.send_keys(details.email)

        # Enter phone number (hint text "Mobile No" when empty)
        phone_el = self.find(AppiumBy.XPATH, '//android.widget.EditText[@text="Mobile No"]')
        phone_el.clear()
        phone_el.send_keys(details.phone)

        self.tap(self.find(AppiumBy.XPATH, '//android.widget.TextView[@text="CONFIRM"]'))
        self.dismiss_popup_if_present()

        # Tap the review CONTINUE once more to advance past the review page
        self.tap(self.find(AppiumBy.ID, continue_id))
        self.dismiss_popup_if_present()

    def proceed_to_payment(self) -> str:
        """
        Skip insurance / add-ons, reach the payment summary,
        and return the total-due string.
        """
        # Skip "Trip Secure" insurance upsell
        trip_secure_xpath = '//android.widget.TextView[@text="Book without Trip Secure"]'
        if self.element_exists(AppiumBy.XPATH, trip_secure_xpath, timeout=10):
            self.tap(self.driver.find_element(AppiumBy.XPATH, trip_secure_xpath))
        self.dismiss_popup_if_present()

        # Step 19a: Dismiss "No, Let Me Choose" snackbar if it appears
        no_choose_id = "com.makemytrip:id/snack_bar_footer_left"
        if self.element_exists(AppiumBy.ID, no_choose_id, timeout=5):
            self.tap(self.driver.find_element(AppiumBy.ID, no_choose_id))
        self.dismiss_popup_if_present()

        # Step 19b: Skip To Payment
        skip_id = "com.makemytrip:id/tv_clear_skip"
        self.tap(self.find(AppiumBy.ID, skip_id, timeout=15))
        self.dismiss_popup_if_present()

        # Step 19c: Tap "Confirm & continue" when it appears
        confirm_continue_xpath = '//android.widget.TextView[@text="Confirm & continue"]'
        if self.element_exists(AppiumBy.XPATH, confirm_continue_xpath, timeout=10):
            self.tap(self.driver.find_element(AppiumBy.XPATH, confirm_continue_xpath))
        self.dismiss_popup_if_present()

        # Step 19d: If total due doesn't show up quickly, dismiss any remaining upsell
        fare_id = "fare_summary_amount"
        if not self.element_exists(AppiumBy.XPATH,
                                   f'//*[@resource-id="{fare_id}"]', timeout=5):
            for dismiss_text in ["I'll pass this time", "No thanks", "SKIP"]:
                dismiss_xpath = f'//android.widget.TextView[@text="{dismiss_text}"]'
                if self.element_exists(AppiumBy.XPATH, dismiss_xpath, timeout=3):
                    self.tap(self.driver.find_element(AppiumBy.XPATH, dismiss_xpath))
                    break

        # Read total due
        total_el = self.find(
            AppiumBy.XPATH, f'//*[@resource-id="{fare_id}"]', timeout=15
        )
        total_due = total_el.get_attribute("text") or ""
        print(f"Total due: {total_due}")
        return total_due


class GoibiboScraper(FlightScraper):
    APP_PACKAGE = "com.goibibo"
    APP_ACTIVITY = "com.goibibo.common.HomeActivity"

    def _dismiss_permission(self):
        """Tap 'Don't allow' on Android permission dialogs (e.g. notifications)."""
        assert self.driver is not None
        deny_id = ("com.android.permissioncontroller:"
                   "id/permission_deny_and_dont_ask_again_button")
        if self.element_exists(AppiumBy.ID, deny_id, timeout=2):
            self.tap(self.driver.find_element(AppiumBy.ID, deny_id))

    def _dismiss_popup(self):
        """Close bottom-sheet popups: the bs_cross and npCrossButton variants."""
        assert self.driver is not None
        for close_xpath in (
            '//*[@resource-id="bs_cross"]',
            '//*[@resource-id="com.goibibo:id/npCrossButton"]',
        ):
            if self.element_exists(AppiumBy.XPATH, close_xpath, timeout=2):
                self.tap(self.driver.find_element(AppiumBy.XPATH, close_xpath))

    def _dismiss_touch_outside(self):
        """Dismiss the touch_outside overlay that sometimes appears after search."""
        assert self.driver is not None
        touch_id = "com.goibibo:id/touch_outside"
        if self.element_exists(AppiumBy.ID, touch_id, timeout=2):
            self.tap(self.driver.find_element(AppiumBy.ID, touch_id))

    def _dismiss_snackbar(self):
        """Tap whichever snackbar footer button is visible (left or middle)."""
        assert self.driver is not None
        for snack_id in (
            "com.goibibo:id/snack_bar_footer_left",
            "com.goibibo:id/snack_bar_footer_middle",
        ):
            if self.element_exists(AppiumBy.ID, snack_id, timeout=2):
                self.tap(self.driver.find_element(AppiumBy.ID, snack_id))
                break  # only one snackbar is shown at a time

    def dismiss_popup_if_present(self):
        """Combines all Goibibo popup-dismissal steps."""
        self._dismiss_permission()
        self._dismiss_popup()
        self._dismiss_touch_outside()
        self._dismiss_snackbar()

    def dismiss_login_drawer_if_present(self):
        """
        If on the login screen, tap DO IT LATER; also close any
        bottom-sheet popups with the cross button.
        """
        # Login activity shows a "DO IT LATER" button
        skip_id = "com.goibibo:id/buttonSkip"
        if self.element_exists(AppiumBy.ID, skip_id, timeout=5):
            self.tap(self.driver.find_element(AppiumBy.ID, skip_id))
        self.dismiss_popup_if_present()

    def navigate_to_flights(self):
        """
        Press back until we reach the home screen or the flight-search form,
        handling login screens along the way, then tap the Flights button.
        """
        assert self.driver is not None
        for _ in range(5):
            if self.element_exists(AppiumBy.ID,
                                   "com.goibibo:id/from_selection_layout", timeout=2):
                self.dismiss_popup_if_present()
                return
            # Home screen has the Flights button — stop pressing back
            if self.element_exists(
                AppiumBy.XPATH,
                '//android.widget.Button[@content-desc="Flights"]', timeout=2
            ):
                break
            # If we landed on the login screen, skip it before going back
            skip_id = "com.goibibo:id/buttonSkip"
            if self.element_exists(AppiumBy.ID, skip_id, timeout=2):
                self.tap(self.driver.find_element(AppiumBy.ID, skip_id))
                self.dismiss_popup_if_present()
                continue
            self._press_back()
            self.dismiss_popup_if_present()
            self.wait(1.0)

        flights_xpath = (
            '//android.widget.Button'
            '[@content-desc="Flights" and @resource-id="com.goibibo:id/itemContainer"]'
        )
        self.tap(self.find(AppiumBy.XPATH, flights_xpath))
        self.dismiss_popup_if_present()

    def select_one_way(self):
        """Select ONE WAY tab; skip if already selected."""
        selector_id = "com.goibibo:id/switchTabsSelector"
        if not self.element_exists(AppiumBy.ID, selector_id, timeout=3):
            return
        selector = self.find(AppiumBy.ID, selector_id)
        one_way = selector.find_element(
            AppiumBy.XPATH, './/android.widget.TextView[@text="ONE WAY"]'
        )
        if one_way.get_attribute("selected") != "true":
            self.tap(one_way)
        self.dismiss_popup_if_present()

    def _current_city_in_layout(self, layout_id: str) -> Optional[str]:
        """
        Get the IATA code from the city layout to skip redundant taps.
        The code is the first 3-letter all-caps TextView inside the layout.
        """
        try:
            layout = self.driver.find_element(AppiumBy.ID, layout_id)
            texts = [
                el.get_attribute("text")
                for el in layout.find_elements(AppiumBy.XPATH, './/android.widget.TextView')
            ]
            for t in texts:
                if t and len(t) == 3 and t.isupper() and t.isalpha():
                    return t
        except NoSuchElementException:
            pass
        return None

    def set_origin(self, city_code: str):
        """Set departure city; skip if already correct."""
        layout_id = "com.goibibo:id/from_selection_layout"
        if self._current_city_in_layout(layout_id) == city_code:
            return
        self.tap(self.find(AppiumBy.ID, layout_id))
        self.dismiss_popup_if_present()
        search_box = self.find(AppiumBy.ID, "com.goibibo:id/departure_city_input")
        search_box.clear()
        search_box.send_keys(city_code)
        result = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                AppiumBy.XPATH,
                f'//android.widget.TextView'
                f'[@text="{city_code}" and @resource-id="com.goibibo:id/city_code"]',
            ))
        )
        self.tap(result)

    def set_destination(self, city_code: str):
        """Set arrival city; skip if already correct."""
        layout_id = "com.goibibo:id/to_city_layout"
        if self._current_city_in_layout(layout_id) == city_code:
            return
        self.tap(self.find(AppiumBy.ID, layout_id))
        self.dismiss_popup_if_present()
        search_box = self.find(AppiumBy.ID, "com.goibibo:id/arrival_city_input")
        search_box.clear()
        search_box.send_keys(city_code)
        result = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                AppiumBy.XPATH,
                f'//android.widget.TextView'
                f'[@text="{city_code}" and @resource-id="com.goibibo:id/city_code"]',
            ))
        )
        self.tap(result)

    def set_date(self, month: str, day: int, year: int):
        """
        Open the date picker by tapping tv_from_date. Scroll the calendar
        RecyclerView bidirectionally (using MonthViewV2 content-descs) until the target
        month is the first visible month, then tap the date cell and confirm.
        """
        self.tap(self.find(AppiumBy.ID, "com.goibibo:id/tv_from_date"))
        self.dismiss_popup_if_present()

        rv_id = "com.goibibo:id/rvCalendarMonth"
        self.find(AppiumBy.ID, rv_id)  # wait for calendar to render
        self.wait(0.5)

        month_abbr = month[:3].upper()
        self._scroll_calendar_to_month(rv_id, month_abbr, year)

        # content-desc format: "26 APR 2026 Tap to select" or "26 APR 2026 Selected"
        already_selected_desc = f"{day} {month_abbr} {year} Selected"
        to_select_candidates = [
            f"{day} {month_abbr} {year} Tap to select",
            f"{day} {month_abbr} {year}",
        ]

        already_selected = self.element_exists(
            AppiumBy.XPATH, f'//*[@content-desc="{already_selected_desc}"]', timeout=3
        )

        if not already_selected:
            day_el = None
            for desc in to_select_candidates:
                if self.element_exists(AppiumBy.XPATH, f'//*[@content-desc="{desc}"]', timeout=3):
                    day_el = self.driver.find_element(AppiumBy.XPATH,
                                                      f'//*[@content-desc="{desc}"]')
                    break
            if day_el is None:
                all_descs = [
                    str(el.get_attribute("content-desc"))
                    for el in self.driver.find_elements(AppiumBy.XPATH, '//*[@content-desc]')
                    if str(day) in str(el.get_attribute("content-desc") or "")
                ]
                print(f"[DEBUG] Elements with day {day} in content-desc: {all_descs[:20]}")
                raise RuntimeError(f"Could not find date cell for {day} {month_abbr} {year}")
            self.tap(day_el)

        self.wait(1.0)
        self.tap(self.find(AppiumBy.ID, "com.goibibo:id/btnDone"))

    def _adjust_count(self, section_id: str, target: int):
        """Tap +/- until the traveller count for a section matches target."""
        add_remove_xpath = (
            f'//android.widget.LinearLayout[@resource-id="{section_id}"]'
            f'//android.widget.LinearLayout[@resource-id="com.goibibo:id/add_remove_view"]'
        )
        add_remove = self.driver.find_element(AppiumBy.XPATH, add_remove_xpath)
        count_xpath = './/android.widget.TextView[@resource-id="com.goibibo:id/tv_count"]'

        current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))
        while current < target:
            self.tap(add_remove.find_element(AppiumBy.ID, "com.goibibo:id/iv_add"))
            current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))
        while current > target:
            self.tap(add_remove.find_element(AppiumBy.ID, "com.goibibo:id/iv_subtract"))
            current = int(add_remove.find_element(AppiumBy.XPATH, count_xpath).get_attribute("text"))

    def set_travellers(self, adults: int = 1, children: int = 0,
                       infants: int = 0, cabin: str = "Economy"):
        """Verify/set traveller count and cabin class."""
        count_el = self.find(AppiumBy.ID, "com.goibibo:id/tv_traveller_count")
        cabin_el = self.find(AppiumBy.ID, "com.goibibo:id/tv_trip_type")
        count_num = (count_el.get_attribute("text") or "").strip().rstrip(", ")
        cabin_text = cabin_el.get_attribute("text") or ""

        if count_num == str(adults) and cabin in cabin_text:
            return

        self.tap(self.find(AppiumBy.ID, "com.goibibo:id/traveller_and_cabin_layout"))
        self.dismiss_popup_if_present()

        self._adjust_count("com.goibibo:id/child_traveller_view", children)
        self._adjust_count("com.goibibo:id/infant_traveller_view", infants)
        self._adjust_count("com.goibibo:id/adult_traveller_view", adults)

        economy_tv = self.find(
            AppiumBy.XPATH,
            '//android.widget.TextView'
            '[@text="Economy/Premium Economy" and @resource-id="com.goibibo:id/tv_economy"]',
        )
        self.tap(economy_tv)

        done_btn = self.find(
            AppiumBy.XPATH,
            '//android.widget.Button'
            '[@text="DONE" and @resource-id="com.goibibo:id/done_button"]',
        )
        self.tap(done_btn)
        self.dismiss_popup_if_present()

    def search_flights(self):
        """Tap SEARCH FLIGHTS."""
        self.tap(self.find(AppiumBy.ID, "com.goibibo:id/search_button_flat"))
        self.dismiss_popup_if_present()

    def collect_results(self) -> List[FlightResult]:
        """Not used in the booking flow; retained to satisfy the abstract interface."""
        raise NotImplementedError("collect_results is not used in the booking flow")

    # ── Booking flow ────────────────────────────────────────────────────────

    def sort_by_cheapest(self):
        """Step 9a: Tap the Cheapest tab on the results screen."""
        cheapest_xpath = (
            '//android.widget.TextView'
            '[@text="Cheapest" and @resource-id="com.goibibo:id/tv_title_tab"]'
        )
        # Wait for results to appear first
        self.find(
            AppiumBy.XPATH,
            '//androidx.cardview.widget.CardView[@resource-id="com.goibibo:id/simple_listing_card"]',
            timeout=30,
        )
        self.dismiss_popup_if_present()

        assert self.driver is not None
        if self.element_exists(AppiumBy.XPATH, cheapest_xpath, timeout=3):
            cheapest_el = self.driver.find_element(AppiumBy.XPATH, cheapest_xpath)
            # Tap only if it is not already the active/selected tab
            if cheapest_el.get_attribute("selected") != "true":
                self.tap(cheapest_el)
        self.dismiss_popup_if_present()

    def select_first_flight(self):
        card_id = "com.goibibo:id/simple_listing_card"
        cards = self.find_all(
            AppiumBy.XPATH,
            f'//androidx.cardview.widget.CardView[@resource-id="{card_id}"]',
        )
        self.tap(cards[0])
        self.wait(1.5)
        self.dismiss_popup_if_present()

        book_now_xpath = '//android.widget.TextView[@text="BOOK NOW"]'
        self.find(AppiumBy.XPATH, book_now_xpath, timeout=15)
        self.tap(self.find_all(AppiumBy.XPATH, book_now_xpath)[0])
        self.dismiss_popup_if_present()

    def fill_traveller_details(self, details: BookingDetails):
        """
        Tap CONTINUE on the review screen (auto-scrolls to traveller
        section), add a new adult traveller, tap CONTINUE again after the dialog
        closes, tick the save-to-profile checkbox, then tap CONTINUE once more to
        advance to the contact-details section.
        """
        # CONTINUE auto-scrolls to the traveller section
        continue_id = "com.goibibo:id/review_tv"
        self.tap(self.find(AppiumBy.ID, continue_id, timeout=20))
        self.dismiss_popup_if_present()

        add_adult_xpath = '//android.widget.TextView[@text="Add new adult"]'
        self.tap(self.find(AppiumBy.XPATH, add_adult_xpath, timeout=10))
        self.dismiss_popup_if_present()

        # Choose gender
        gender_xpath = f'//android.widget.TextView[@text="{details.gender}"]'
        self.tap(self.find(AppiumBy.XPATH, gender_xpath))

        first_name_el = self.find(
            AppiumBy.XPATH,
            '//android.widget.EditText[@text="First & Middle Name"]',
        )
        first_name_el.send_keys(details.first_name)

        last_name_el = self.find(
            AppiumBy.XPATH,
            '//android.widget.EditText[@text="Last Name"]',
        )
        last_name_el.send_keys(details.last_name)

        self.tap(self.find(AppiumBy.ID, "com.goibibo:id/confirm_button"))
        self.dismiss_popup_if_present()

        # After the traveller dialog closes, tap CONTINUE to reach the next section
        self.tap(self.find(AppiumBy.ID, continue_id, timeout=10))
        self.dismiss_popup_if_present()

        # Scroll down to the "Save these details" checkbox and tick it
        assert self.driver is not None
        size = self.driver.get_window_size()
        scroll_x = size["width"] // 2
        scroll_start_y = int(size["height"] * 0.70)
        scroll_end_y = int(size["height"] * 0.25)

        checkbox_id = "com.goibibo:id/confirmationCheckBox"
        for _ in range(5):
            if self.element_exists(AppiumBy.ID, checkbox_id, timeout=3):
                break
            self.driver.swipe(scroll_x, scroll_start_y, scroll_x, scroll_end_y, duration=500)
            self.wait(0.8)

        if self.element_exists(AppiumBy.ID, checkbox_id, timeout=3):
            checkbox = self.driver.find_element(AppiumBy.ID, checkbox_id)
            # Only tap if not already checked
            if checkbox.get_attribute("checked") != "true":
                self.tap(checkbox)

        # Tap CONTINUE once more to advance to the contact-details section and wait
        self.tap(self.find(AppiumBy.ID, continue_id, timeout=10))
        self.wait(1.0)
        self.dismiss_popup_if_present()

    def fill_contact_details(self, details: BookingDetails):
        """
        Fill email + phone (CONTINUE was already tapped at the end of
        fill_traveller_details), confirm, then tap CONTINUE again to proceed to
        seat selection / skip-to-payment.
        """
        continue_id = "com.goibibo:id/review_tv"

        # Fill email and phone — scroll down to find them if needed
        assert self.driver is not None
        size = self.driver.get_window_size()
        scroll_x = size["width"] // 2
        scroll_start_y = int(size["height"] * 0.70)
        scroll_end_y = int(size["height"] * 0.25)

        email_xpath = '//android.widget.EditText[@text="Email"]'
        for _ in range(3):
            if self.element_exists(AppiumBy.XPATH, email_xpath, timeout=3):
                break
            self.driver.swipe(scroll_x, scroll_start_y, scroll_x, scroll_end_y, duration=500)
            self.wait(0.8)

        email_el = self.find(AppiumBy.XPATH, email_xpath)
        email_el.clear()
        email_el.send_keys(details.email)

        phone_el = self.find(AppiumBy.XPATH, '//android.widget.EditText[@text="Mobile No"]')
        phone_el.clear()
        phone_el.send_keys(details.phone)

        self.tap(self.find(AppiumBy.XPATH, '//android.widget.TextView[@text="CONFIRM"]'))
        self.dismiss_popup_if_present()

        # Tap CONTINUE to advance to seat selection / skip-to-payment
        self.tap(self.find(AppiumBy.ID, continue_id))
        self.dismiss_popup_if_present()

    def proceed_to_payment(self) -> str:
        """
        Dismiss add-ons, skip to payment, and return the total-due string.
        """
        assert self.driver is not None

        # Step 13a: Tap "Travel Unsecured" snackbar if it appears (skip insurance)
        travel_unsecured_xpath = (
            '//android.widget.TextView'
            '[@text="Travel Unsecured" and @resource-id="com.goibibo:id/snack_bar_footer_left"]'
        )
        if self.element_exists(AppiumBy.XPATH, travel_unsecured_xpath, timeout=5):
            self.tap(self.driver.find_element(AppiumBy.XPATH, travel_unsecured_xpath))

        # Step 13b: Tap the right-side CONFIRM CTA if it appears
        confirm_cta_xpath = (
            '//android.widget.TextView'
            '[@text="CONFIRM" and @resource-id="com.goibibo:id/right_cta"]'
        )
        if self.element_exists(AppiumBy.XPATH, confirm_cta_xpath, timeout=10):
            self.tap(self.driver.find_element(AppiumBy.XPATH, confirm_cta_xpath))
        self._dismiss_snackbar()

        # Skip To Payment
        skip_id = "com.goibibo:id/tv_clear_skip"
        self.tap(self.find(AppiumBy.ID, skip_id, timeout=15))
        self._dismiss_snackbar()

        # Wait for the fare summary amount and return it
        fare_el = self.find(
            AppiumBy.XPATH,
            '//*[@resource-id="fare_summary_amount"]',
            timeout=20,
        )
        total_due = fare_el.get_attribute("text") or ""
        print(f"Total due: {total_due}")
        return total_due


def _appium_is_live(port: int) -> bool:
    """Return True if an Appium server is already accepting connections."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start_appium_server(port: int = 4723) -> Optional[subprocess.Popen]:
    """
    Start Appium on *port* and return the Popen handle.
    If a server is already running there, return None (caller must not stop it).
    """
    if _appium_is_live(port):
        print(f"Appium already running on port {port} — reusing.")
        return None

    print(f"Starting Appium server on port {port}...")
    # Attempting to fix an issue with there being two paths for Android Sdk on my system
    import os, shutil
    from pathlib import Path
    env = os.environ.copy()
    adb_path = shutil.which("adb")
    if adb_path:
        # adb lives at <sdk>/platform-tools/adb  →  sdk root is two levels up
        sdk_root = str(Path(adb_path).resolve().parent.parent)
        env["ANDROID_HOME"] = sdk_root
        env["ANDROID_SDK_ROOT"] = sdk_root
    proc = subprocess.Popen(
        ["appium", "--port", str(port), "--log-level", "warn"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(3)
    if proc.poll() is not None:
        _, err = proc.communicate()
        raise RuntimeError(f"Appium failed to start:\n{err.decode()}")
    print("Appium server is up.")
    return proc


def stop_appium_server(proc: Optional[subprocess.Popen]):
    """Stop a server we started; no-op if proc is None (server was pre-existing)."""
    if proc is None:
        return
    print("Stopping Appium server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Appium server stopped.")


# Fake details used for the booking flow (no real payment is made)
_BOOKING_DETAILS = BookingDetails(
    gender="MALE",
    first_name="Test",
    last_name="User",
    email="testuser123@mailnull.com",
    phone="9000000001",
)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Appium flight scraper")
    parser.add_argument("--app", choices=["mmt", "goibibo"],
                        help="App to scrape: mmt or goibibo")
    parser.add_argument("--device", metavar="DEVICE_ID",
                        help="ADB device ID (from `adb devices`)")
    args = parser.parse_args()

    print("=== Flight Scraper (Appium Code) ===\n")

    # ── App choice ────────────────────────────────────────────────────────────
    if args.app:
        choice = "1" if args.app == "mmt" else "2"
    else:
        print("Which app would you like to use?")
        print("  1. MakeMyTrip")
        print("  2. Goibibo")
        choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        scraper_cls = MakeMyTripScraper
        app_name = "MakeMyTrip"
    elif choice == "2":
        scraper_cls = GoibiboScraper
        app_name = "Goibibo"
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    # ── Device ID ─────────────────────────────────────────────────────────────
    device_id = args.device or input("Enter device ID (from `adb devices`): ").strip()
    if not device_id:
        print("Device ID cannot be empty. Exiting.")
        sys.exit(1)

    appium_proc = start_appium_server()
    scraper = scraper_cls(device_id)

    try:
        print(f"\nConnecting to {app_name}...")
        scraper.start_session()

        total_due = scraper.run(
            origin="HYD",
            destination="DEL",
            month="June",
            day=15,
            year=2026,
            booking=_BOOKING_DETAILS,
        )

        output = {
            "app": app_name,
            "origin": "HYD",
            "destination": "DEL",
            "date": "15 June 2026",
            "total_taps": scraper.tap_count,
            "total_due": total_due,
            "booking": asdict(_BOOKING_DETAILS),
        }
        out_file = f"booking_{app_name.lower().replace(' ', '_')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to {out_file}")
        print(f"Total taps: {scraper.tap_count}")
        print(f"Total due:  {total_due}")

    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        scraper.end_session()
        stop_appium_server(appium_proc)


if __name__ == "__main__":
    main()
