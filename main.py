import json
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from functools import wraps
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

    # ── Low-level helpers ─────────────────────────────────────────────────────

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

    # Popup/permission handlers (no-op by default, override as needed)

    def dismiss_popup_if_present(self):
        pass

    def dismiss_permission_if_present(self):
        pass

    # ── Orchestration ─────────────────────────────────────────────────────────

    def run(self, origin: str, destination: str,
            month: str, day: int, year: int) -> List[FlightResult]:
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
        print("Collecting results")
        self.results = self.collect_results()
        return self.results


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
        # If the from/to city layout is already visible we're on the flight
        # search screen — navigation already done (app reopened in last state).
        # Todo: we need to press back if we detect that we're on some other page (check the id)
        if self.element_exists(AppiumBy.ID,
                               "com.makemytrip:id/from_selection_layout", timeout=3):
            self.dismiss_popup_if_present()
            return

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

    _MONTH_ORDER = [
        "January ", "February ", "March ", "April ", "May ", "June ",
        "July ", "August ", "September ", "October ", "November ", "December ",
    ]

    def set_date(self, month: str, day: int, year: int):
        """
        We open the calendar widget, keep swiping till the month we want appears, then tap the right cell
        """
        self.tap(self.find(AppiumBy.ID, "com.makemytrip:id/from_date_layout"))
        self.dismiss_popup_if_present()

        rv_id = "com.makemytrip:id/rvCalendarMonth"
        self.find(AppiumBy.ID, rv_id)  # wait for calendar to render

        target_month_text = f"{month} "  # e.g. "June "
        target_idx = (
            self._MONTH_ORDER.index(target_month_text)
            if target_month_text in self._MONTH_ORDER else -1
        )

        month_xpath = (
            '//android.widget.TextView[@resource-id="com.makemytrip:id/tv_month"'
            ' and @text="{m}"]'
        )

        for _ in range(15):
            target_visible = self.element_exists(
                AppiumBy.XPATH, month_xpath.format(m=target_month_text), timeout=2
            )
            prev_visible = False
            if target_idx > 0:
                prev_visible = self.element_exists(
                    AppiumBy.XPATH,
                    month_xpath.format(m=self._MONTH_ORDER[target_idx - 1]),
                    timeout=2,
                )
            if target_visible and not prev_visible:
                break
            rv = self.driver.find_element(AppiumBy.ID, rv_id)
            rv_loc = rv.location
            rv_size = rv.size
            cx = rv_loc["x"] + rv_size["width"] // 2
            # Swipe up within the calendar RecyclerView to go ahead
            start_y = rv_loc["y"] + int(rv_size["height"] * 0.75)
            end_y = rv_loc["y"] + int(rv_size["height"] * 0.25)
            self.driver.swipe(cx, start_y, cx, end_y, duration=500)
            self.wait(0.5)

        month_abbr = month[:3].upper()
        # The content-desc is "D MON YYYY Tap to select" when unselected,
        # and "D MON YYYY Selected" when already selected.
        already_selected_desc = f"{day} {month_abbr} {year} Selected"
        to_select_candidates = [
            f"{day} {month_abbr} {year} Tap to select",
            f"{day} {month_abbr} {year}",
            f"{month_abbr} {day} {year} Tap to select",
            f"{month} {day}, {year} Tap to select",
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
                    el.get_attribute("content-desc")
                    for el in self.driver.find_elements(AppiumBy.XPATH, '//*[@content-desc]')
                    if str(day) in (el.get_attribute("content-desc") or "")
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

        self._adjust_count("com.makemytrip:id/adult_traveller_view", adults)
        self._adjust_count("com.makemytrip:id/child_traveller_view", children)
        self._adjust_count("com.makemytrip:id/infant_traveller_view", infants)

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
        """Step 10: Tap SEARCH FLIGHTS."""
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


# Will fill more
class GoibiboScraper(FlightScraper):
    APP_PACKAGE = "com.goibibo"
    APP_ACTIVITY = ""

    def dismiss_login_drawer_if_present(self):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def navigate_to_flights(self):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def select_one_way(self):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def set_origin(self, _city_code: str):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def set_destination(self, _city_code: str):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def set_date(self, _month: str, _day: int, _year: int):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def set_travellers(self, _adults: int = 1, _children: int = 0,
                       _infants: int = 0, _cabin: str = "Economy"):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def search_flights(self):
        raise NotImplementedError("Goibibo scraper not yet implemented")

    def collect_results(self) -> List[FlightResult]:
        raise NotImplementedError("Goibibo scraper not yet implemented")


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

        flights = scraper.run(
            origin="HYD",
            destination="DEL",
            month="June",
            day=15,
            year=2026,
        )

        output = {
            "app": app_name,
            "origin": "HYD",
            "destination": "DEL",
            "date": "15 June 2026",
            "total_taps": scraper.tap_count,
            "flights_found": len(flights),
            "flights": [asdict(f) for f in flights],
        }
        out_file = f"flights_{app_name.lower().replace(' ', '_')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to {out_file}")
        print(f"Total taps: {scraper.tap_count}")
        print(f"Flights found: {len(flights)}\n")

        col = "{:<22} {:>6} {:>6} {:>10} {:>14} {:>12}"
        print(col.format("Airline", "Dep", "Arr", "Duration", "Stops", "Price"))
        print("-" * 74)
        for fl in flights:
            print(col.format(
                fl.airline, fl.departure_time, fl.arrival_time,
                fl.duration, fl.stops, fl.price,
            ))

    except NotImplementedError as e:
        print(f"\nNot implemented: {e}")
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        scraper.end_session()
        stop_appium_server(appium_proc)


if __name__ == "__main__":
    main()
