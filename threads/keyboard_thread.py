import os
import subprocess
import sys
from PyQt5.QtCore import QThread, Qt

def open_system_keyboard():
    """Open the system soft keyboard depending on the platform"""
    if sys.platform == "win32":
        print("Opening virtual keyboard on Windows")
        os.system("osk")  # Open on-screen keyboard on Windows
    elif sys.platform == "darwin":
        print("Opening virtual keyboard on macOS")
        os.system("open -a Keyboard")  # Open system keyboard on macOS
    elif sys.platform == "linux":
        print("Opening virtual keyboard on Linux")
        os.system("onboard &")  # Open onboard keyboard (Ubuntu or similar)

def set_keyboard_position():
    """Set the position of the virtual keyboard (Linux specific example)"""
    if sys.platform == "linux":
        # Use xdotool to move the onboard keyboard to the bottom of the screen
        try:
            subprocess.run(["xdotool", "search", "--name", "Onboard", "windowmove", "0", "1440"], check=True)
        except FileNotFoundError:
            print("xdotool is not installed. Please install it for position control.")
        except subprocess.CalledProcessError:
            print("Failed to move the Onboard keyboard. Ensure it is running.")

class KeyboardThread(QThread):
    """Thread to open the virtual keyboard"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        open_system_keyboard()
        self.msleep(500)  # Delay to ensure keyboard is open
        set_keyboard_position()