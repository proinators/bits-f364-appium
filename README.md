# BITS F364 - Programming Assignment (Appium Code)
## Team members
|             Name | ID No.        |
|-----------------:|:--------------|
| Albert Sebastian | 2023A7PS0118H |
|    Pratyush Nair | 2023A7PS0160H |
| Siddharth Bhatia | 2023A7PS1106H |
|    Vishisht T.B. | 2023A7PS0042H |

The Appium Code section of Part A of the assignment was done by Pratyush Nair.

## Setup
1. Install JDK, the Android SDK and related platform tools, and setup your device for USB debugging (or setup an emulator)
2. Install Appium Code (skip this step if everything required has been installed)
```sh
npm install -g appium
appium driver install uiautomator2
appium plugin install inspector     # Optional, if you want to inspect elements in the UI
```
3. Install the required Python packages, using the manager of your choice - for this example we will be using uv
```sh
uv sync
```
Of course, you can also install it directly using pip:
```sh
pip install Appium-Python-Client
```
4. Run:
```sh
uv run main.py --app goibibo --device <device ID>
```
or replace goibibo with mmt