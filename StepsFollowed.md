This document will explain how I went about building the whole repo. Assume the working directory to be the repo location.
1. Basic setup:
```sh
git init
npm install -g appium
appium driver install uiautomator2
appium plugin install inspector
uv init
uv add Appium-Python-Client
```
2. Installed the apps on my phone, setup developer options and USB debugging. Then I run the following to find out the package name of the two apps:
```sh
adb shell dumpsys window displays | grep -E 'mCurrentFocus'
```
I get the package names to be `com.makemytrip` and `com.goibibo`

# MakeMyTrip
1. I use Appium Inspector, connect to my phone using the session config:
```json
{
  "platformName": "Android",
  "appium:automationName": "uiautomator2",
  "appium:deviceName": "<deviceid>",
  "appium:appPackage": "com.makemytrip",
  "appium:appActivity": "com.mmt.travel.app.home.ui.SplashActivityPrimary",
  "appium:noReset": true
}
```
This launches the app
2. (Check first time launch later) Since I had already opened the app before, I was able to go to the home screen activity directly, but sometimes a drawer shows up for login: If I detect `<android.widget.TextView text="Login for the Best Travel Offers" resource-id="com.makemytrip:id/tv_header">` (check for the term login only) then I have to click on `<android.widget.ImageView content-desc="Go Back" resource-id="com.makemytrip:id/iv_cross">`
3. Find the button with `<android.widget.Button text="Flights" resource-id="com.makemytrip:id/container">` and tap on it.
4. Click on `<android.widget.TextView text="ONE WAY">` in `<android.widget.LinearLayout resource-id="com.makemytrip:id/switchTabsSelector">` (confirmed that double taps in case it was already active doesn't deselect it, but also you can check the `selected` bool property to reduce taps)
5. For the from and to, you have the widgets `<android.view.ViewGroup resource-id="com.makemytrip:id/from_selection_layout">` and `<android.view.ViewGroup resource-id="com.makemytrip:id/to_city_layout">`. Tap on them, then send text into `<android.widget.EditText text="From" resource-id="com.makemytrip:id/departure_city_input">` (or `<android.widget.EditText text="To" resource-id="com.makemytrip:id/arrival_city_input">`), wait till `<android.widget.TextView text="HYD" resource-id="com.makemytrip:id/city_code">` (or `<android.widget.TextView text="DEL" resource-id="com.makemytrip:id/city_code">`) shows up, then tap on its parent ViewGroup element. Skip the respective set of steps if under `<android.view.ViewGroup resource-id="com.makemytrip:id/from_selection_layout">` > `<android.widget.RelativeLayout>` > `<android.widget.LinearLayout>` > `<android.widget.TextView text="HYD">` the text is right (similarly under `<android.view.ViewGroup resource-id="com.makemytrip:id/to_city_layout">` > .. > .. > `<android.widget.TextView text="DEL">`)
6. Tap on `<android.view.ViewGroup resource-id="com.makemytrip:id/from_date_layout">`
7. Scroll until `<android.widget.TextView text="June " resource-id="com.makemytrip:id/tv_month">` is there in the tree but `<android.widget.TextView text="May " resource-id="com.makemytrip:id/tv_month">` is not there in the tree under `<androidx.recyclerview.widget.RecyclerView resource-id="com.makemytrip:id/rvCalendarMonth">`
8. Tap on `<c content-desc="15 JUN 2026 Tap to select">`, then tap on `<android.widget.TextView text="DONE" resource-id="com.makemytrip:id/btnDone">` after a slight delay.
9. Verify that `<android.widget.TextView text="1," resource-id="com.makemytrip:id/tv_traveller_count">` has text = "1, ", and `<android.widget.TextView text="Economy/Premium Economy" resource-id="com.makemytrip:id/tv_trip_type">` has "Economy/Premium Economy" else tap on `<android.view.ViewGroup resource-id="com.makemytrip:id/traveller_and_cabin_layout">`. Then tap on `<android.widget.ImageView content-desc="Decrease number of passenger" resource-id="com.makemytrip:id/iv_subtract">` or `<android.widget.ImageView content-desc="Increase number of passenger" resource-id="com.makemytrip:id/iv_add">` so that `<android.widget.TextView text="1" resource-id="com.makemytrip:id/tv_count">` has 1, under `<android.widget.LinearLayout resource-id="com.makemytrip:id/adult_traveller_view">`, and similarly adjust the other counts under `<android.widget.LinearLayout resource-id="com.makemytrip:id/child_traveller_view">` and `<android.widget.LinearLayout resource-id="com.makemytrip:id/infant_traveller_view">` (they are not directly under those views, there's a `<android.widget.LinearLayout resource-id="com.makemytrip:id/add_remove_view">` in between). Then tap on `<android.widget.TextView text="Economy/Premium Economy" resource-id="com.makemytrip:id/tv_economy">` - if not available, error out. Finally click on `<android.widget.Button text="DONE" resource-id="com.makemytrip:id/done_button">` (the one with the sibling `<android.widget.TextView text="ADD NUMBER OF TRAVELLERS" resource-id="com.makemytrip:id/add_traveller_header">`). Skip all this if the details were already right.
10. Click on `<android.widget.Button text="SEARCH FLIGHTS" resource-id="com.makemytrip:id/search_button_flat">`
11. Wait until at least one `<android.view.View resource-id="listing_card_v2">` shows up, then keep scrolling and tracking all those listing cards. Under listing_card_v2 > listing_card_container > airline_header you will have `<android.widget.TextView text="IndiGo" resource-id="airline_name">` and under ...card_container somewhere again you will have the following data: `<android.widget.TextView text="21:00" resource-id="departure_time">`, `<android.widget.TextView text="HYD" resource-id="city_code">` (verify this and arrival city, don't add it to our list if this is not correct) `<android.widget.TextView text="2h 25m" content-desc="2 hours 25 minutes" resource-id="duration_text">`, `<android.widget.TextView text="Non stop" resource-id="stops_text">`, `<android.widget.TextView text="23:25" resource-id="arrival_time">`, `<android.widget.TextView text="DEL" resource-id="city_code">`, `<android.widget.TextView text="₹ 6,130" resource-id="final_price">`
12. I should collect all this data, save it in a JSON and display it


I'll be making the script so that it must have taps run through a decorator that passes through the tap but also counts it in a variable (for analysis as required by the assignment)