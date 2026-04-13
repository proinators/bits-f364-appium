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

If at any point it asks for permissions, `<android.widget.Button text="Don't allow" resource-id="com.android.permissioncontroller:id/permission_deny_and_dont_ask_again_button">` tap on this.

If at any point it shows a banner `<android.widget.FrameLayout resource-id="com.makemytrip:id/fl_popup_container">`, then tap on `<android.widget.ImageView resource-id="com.makemytrip:id/iv_close">`

Never mind, I misread the assignment. We shouldn't be collecting flight data, we should go through all pages and reach the booking stage for the cheapest flight.

12. First of all if we are in any other activity after 5 seconds we need to press back `<android.widget.ImageView content-desc="Back" resource-id="com.makemytrip:id/back_button_new">`, `<android.widget.ImageView content-desc="Back" resource-id="back_icon">`, or Android back (Are there other variants)
13. In the flight search page, check that `<android.widget.TextView text="Cheapest" resource-id="cluster_tab_title">` the text is Cheapest. If not, click on `<android.view.View resource-id="cluster_tab_item">`, find `<android.widget.TextView text="Cheapest (Price Low to High)" resource-id="option_text">`, then tap on it
14. Tap on the first listing_card_v2, then `<android.widget.TextView text="BOOK NOW">` (scroll down until it appears), after 3 scrolls if it doesn't appear error out.
15. Wait till `<android.widget.TextView text="CONTINUE" resource-id="com.makemytrip:id/review_tv">` shows up, then scroll down until `<android.widget.TextView text="Add new adult">` appears, then tap on that (not the continue button)
16. (add the booking details to the initial data dict) Tap on `<android.widget.TextView text="MALE">` or `<android.widget.TextView text="FEMALE">` depending on which was chosen in the inital dict. Then enter the name in `<android.widget.EditText text="First & Middle Name" resource-id="com.makemytrip:id/et_passport_number">` and `<android.widget.EditText text="Last Name" resource-id="com.makemytrip:id/et_passport_number">`, then tap on `<android.widget.TextView text="CONFIRM" resource-id="com.makemytrip:id/confirm_button">`. Verify that `<android.widget.TextView text="Somebody Nobdoy" resource-id="com.makemytrip:id/gst_title">` exists in the page with a timeout, else repeat steps.
17. If these components show up on screen, tap on `<android.widget.TextView text="CONTINUE" resource-id="com.makemytrip:id/review_tv">`, then enter email and phone number in `<android.widget.EditText text="Email" resource-id="com.makemytrip:id/et_passport_number">` and `<android.widget.EditText text="Mobile No">` (send fake emails and numbers from https://temp-mail.org/en/ and https://receive-smss.com, but no need of an api I suppose, just define it in that initial dict?), then tap on `<android.widget.TextView text="CONFIRM">`. THen tap on the previous page continue again.
18. Tap on `<android.widget.TextView text="Book without Trip Secure">` (keep checking for other banners)
19. Tap on `<android.widget.TextView text="No, Let Me Choose" resource-id="com.makemytrip:id/snack_bar_footer_left">`. Then click on `<android.widget.TextView text="Skip To Payment" resource-id="com.makemytrip:id/tv_clear_skip">`, then `<android.widget.TextView text="Confirm & continue">` when it appears, then if "Total Due" doesn't appear on screen for sometime, find text like "I'll pass this time", "No thanks" and tap on that (like `<android.widget.TextView text="I'll pass this time">`)
20. Print the total due `<android.widget.TextView text="₹ 6,540" content-desc="₹ 6,540" resource-id="fare_summary_amount">`


I'll be making the script so that it must have taps run through a decorator that passes through the tap but also counts it in a variable (for analysis as required by the assignment)

## Stuff to implement
Hlways stay updated banner for notifications
Check if the date was already correct, also add scrolling up if we are ahead
handle the app being in other pages - click back

# Goibibo
For goibibo the home activity is `com.goibibo/com.goibibo.common.HomeActivity`
1. Close button for some of the popups: `<android.widget.ImageView content-desc="Close Button" resource-id="bs_cross">`. Also if it is in the login activity ` .feature.newAuth.presentation.auth.NewWelcomeLoginActivity`, then `<android.widget.TextView text="DO IT LATER" resource-id="com.goibibo:id/buttonSkip">` (check the resource id)
2. Flights button `<android.widget.Button content-desc="Flights" resource-id="com.goibibo:id/itemContainer">`
3. Similar to mmt, we have to press android back if it is in any other activity.
4. Funnily the flight details page is the exact same as mmt, except for the widget ids: For from city: `<android.view.ViewGroup resource-id="com.goibibo:id/from_selection_layout">` > RelativeLayout > LinearLayout (third child) > First child should be something like `<android.widget.TextView text="DEL">` - check the IATA code with that. For to city, `<android.view.ViewGroup resource-id="com.goibibo:id/to_city_layout">` > RelativeLayout > LinearLayout > first child should be something like `<android.widget.TextView text="BOM">` with the correct IATA code. For the date, check the text of `<android.widget.TextView text="14 Apr" resource-id="com.goibibo:id/tv_from_date">`. 
5. Departure city input in that page is `<android.widget.EditText text="From" resource-id="com.goibibo:id/departure_city_input">`, wait till `<android.widget.TextView text="HYD" resource-id="com.goibibo:id/city_code">` shows up, then tap that. Similarly for the to dialog, `<android.widget.EditText text="To" resource-id="com.goibibo:id/arrival_city_input">`, wait till `<android.widget.TextView text="DEL" resource-id="com.goibibo:id/city_code">` shows up, then tap it.
6. In the calendar view (tap on the tv_from_date text), keep scrolling up/down until you get to the right months, with the required month being the first of the two months rendered, then tap on the required date `<MonthViewV2 content-desc="26 APR 2026 Tap to select">` and then `<android.widget.TextView text="DONE" resource-id="com.goibibo:id/btnDone">` after waiting for a second.
7. Check traveller count and stuff `<android.widget.TextView text="1," resource-id="com.goibibo:id/tv_traveller_count">`, `<android.widget.TextView text="Economy/Premium Economy" resource-id="com.goibibo:id/tv_trip_type">`, if it is wrong, tap on it, adjust the counts under `<android.widget.LinearLayout resource-id="com.goibibo:id/adult_traveller_view">`, `<android.widget.LinearLayout resource-id="com.goibibo:id/child_traveller_view">`, `<android.widget.LinearLayout resource-id="com.goibibo:id/infant_traveller_view">`, under which you have `<android.widget.LinearLayout resource-id="com.goibibo:id/add_remove_view">`, and you have ids `com.goibibo:id/iv_subtract` and `com.goibibo:id/iv_add`, then finally tap on `<android.widget.TextView text="Economy/Premium Economy" resource-id="com.goibibo:id/tv_economy">` and then `<android.widget.Button text="DONE" resource-id="com.goibibo:id/done_button">`
8. Tap on `<android.widget.Button text="SEARCH FLIGHTS" resource-id="com.goibibo:id/search_button_flat">`. If `com.goibibo:id/snack_bar_footer_left` shows up, tap on that.
9. Tap on `<android.widget.TextView text="Cheapest" resource-id="com.goibibo:id/tv_title_tab">`, then tap on the first `<androidx.cardview.widget.CardView resource-id="com.goibibo:id/simple_listing_card">`, then when it appears `<android.widget.TextView text="BOOK NOW">`.
10. When it appears `<android.widget.TextView text="CONTINUE" resource-id="com.goibibo:id/review_tv">`, tap on it, which will auto scroll to the traveller details section, in which we tap on `<android.widget.TextView text="Add new adult">`. Choose `<android.widget.TextView text="MALE">` or `<android.widget.TextView text="FEMALE">`, enter name details in `<android.widget.EditText text="First & Middle Name" resource-id="com.goibibo:id/et_passport_number">` and `<android.widget.EditText text="Last Name" resource-id="com.goibibo:id/et_passport_number">`, then `<android.widget.TextView text="CONFIRM" resource-id="com.goibibo:id/confirm_button">`
11. Scroll down until `<android.widget.TextView text="Save these details to my profile" resource-id="com.goibibo:id/tvConfirmation">` appears, then tap on it.
12. Press on `<android.widget.TextView text="CONTINUE" resource-id="com.goibibo:id/review_tv">`. If `<android.widget.TextView text="Kindly enter contact details to proceed" resource-id="com.goibibo:id/error_message">` shows up, then enter details in `<android.widget.EditText text="Email" resource-id="com.goibibo:id/et_passport_number">` and `<android.widget.EditText text="Mobile No">`, then tap on `<android.widget.TextView text="CONFIRM">`, then press on the continue button again.
13. If `com.goibibo:id/snack_bar_footer_left` shows up, tap that (poll the screen). Else tap on `<android.widget.TextView text="CONFIRM" resource-id="com.goibibo:id/right_cta">` when that appears. 
14. Once again clear popups if any snack_bar_footer_left appears, then `<android.widget.TextView text="Skip To Payment" resource-id="com.goibibo:id/tv_clear_skip">` tap on that.
15. Wait till `<android.widget.TextView text="₹ 6,733" content-desc="₹ 6,733" resource-id="fare_summary_amount">` shows up, then report the final price in the console.
