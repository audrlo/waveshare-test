#!/usr/bin/env python3
"""
Sam's Eye Loop for Waveshare 2.4" LCD (ILI9341 driver).
Large sky blue eyes with double-blink animation.
"""

import sys
import time
import random

# Add Waveshare library path
sys.path.insert(0, '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')

try:
    from roboeyes import RoboEyes
except ImportError:
    from eyes import RoboEyes

from PIL import Image


class Waveshare24Display:
    """
    Display driver for Waveshare 2.4" LCD Module (ILI9341).

    This display is 240x320 pixels with SPI interface.
    Uses LCD_2inch4 from the Waveshare library.
    """

    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        rotation: int = 0,
        backlight: int = 50,
        rst: int = 27,
        dc: int = 25,
        bl: int = 18,
        lib_path: str = None
    ):
        self.width = width
        self.height = height
        self.rotation = rotation

        # Import the correct library for 2.4" display
        LCD_2inch4 = self._import_waveshare_lib(lib_path)

        # Initialize display
        self.lcd = LCD_2inch4.LCD_2inch4(rst=rst, dc=dc, bl=bl)
        self.lcd.Init()
        self.lcd.clear()
        self.lcd.bl_DutyCycle(backlight)

    def _import_waveshare_lib(self, lib_path):
        """Import the Waveshare LCD library for 2.4" display."""
        # Try direct import first
        try:
            from lib import LCD_2inch4
            return LCD_2inch4
        except ImportError:
            pass

        # Common paths to try
        paths_to_try = [
            lib_path,
            '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python',
            '/home/pi/LCD_Module_RPI_code/RaspberryPi/python',
            '/opt/waveshare/LCD_Module_RPI_code/RaspberryPi/python',
        ]

        for path in paths_to_try:
            if path is None:
                continue
            try:
                if path not in sys.path:
                    sys.path.insert(0, path)
                from lib import LCD_2inch4
                return LCD_2inch4
            except ImportError:
                continue

        raise ImportError(
            "Waveshare LCD_2inch4 library not found. Make sure LCD_Module_RPI_code "
            "is installed. You can specify the path with lib_path parameter.\n"
            "Example: Waveshare24Display(lib_path='/path/to/LCD_Module_RPI_code/RaspberryPi/python')"
        )

    def show(self, image: Image.Image):
        """Display a PIL Image on the screen."""
        # The physical LCD is 240x320 (portrait)
        # For landscape mode (320x240), we rotate the image

        if self.rotation == 90:
            # Landscape: rotate 90° CCW (or 270° CW)
            image = image.transpose(Image.Transpose.ROTATE_270)
        elif self.rotation == 180:
            image = image.transpose(Image.Transpose.ROTATE_180)
        elif self.rotation == 270:
            # Landscape flipped: rotate 90° CW
            image = image.transpose(Image.Transpose.ROTATE_90)

        # Ensure correct size for physical display (240x320)
        if image.size != (240, 320):
            image = image.resize((240, 320), Image.Resampling.LANCZOS)

        # Send to display
        self.lcd.ShowImage(image)

    def clear(self):
        """Clear the display to black."""
        self.lcd.clear()

    def set_backlight(self, value: int):
        """Set backlight brightness (0-100)."""
        self.lcd.bl_DutyCycle(max(0, min(100, value)))

    def cleanup(self):
        """Clean up GPIO resources on exit."""
        try:
            self.lcd.module_exit()
        except Exception:
            pass

    def __del__(self):
        """Cleanup on object destruction."""
        self.cleanup()


def main():
    # Screen is 320x240 landscape
    screen_width = 320
    screen_height = 240

    # Eye sizing: maximize while keeping on screen
    margin = 10
    space_between = 16

    # Calculate max eye dimensions
    eye_width = (screen_width - 2 * margin - space_between) // 2  # = 142
    eye_height = screen_height - 2 * margin  # = 220

    # Make eyes slightly less tall than wide for better look
    eye_height = min(eye_height, 180)
    eye_width = min(eye_width, 140)

    # Border radius - nice rounded corners
    border_radius = 35

    # Colors
    bg_color = (0, 0, 0)  # Black background
    eye_color = (135, 206, 250)  # #87CEFA - Light Sky Blue

    print("Sam's Eye Loop (2.4\" LCD - ILI9341)")
    print(f"Eye size: {eye_width}x{eye_height}")
    print(f"Eye color: #87CEFA (Light Sky Blue)")
    print()

    # Create eyes
    eyes = RoboEyes(width=screen_width, height=screen_height)
    eyes.set_colors(bg_color, eye_color)
    eyes.set_width(eye_width)
    eyes.set_height(eye_height)
    eyes.set_border_radius(border_radius)
    eyes.set_space_between(space_between)

    # Create display for 2.4" LCD
    display = Waveshare24Display(
        width=screen_width,
        height=screen_height,
        rotation=90,
        backlight=100
    )

    print("Running! Press Ctrl+C to stop.")

    # Double-blink timing (2 to 3.5 seconds between double-blinks)
    def next_blink_time():
        return time.time() + random.uniform(2.0, 3.5)

    next_blink = next_blink_time()
    second_blink_pending = False
    second_blink_time = 0

    try:
        while True:
            now = time.time()

            # Check for double-blink
            if now >= next_blink and not second_blink_pending:
                eyes.blink()
                second_blink_pending = True
                second_blink_time = now + 0.25  # Second blink after 0.25s

            if second_blink_pending and now >= second_blink_time:
                eyes.blink()
                second_blink_pending = False
                next_blink = next_blink_time()

            frame = eyes.update()
            display.show(frame)

    except KeyboardInterrupt:
        print("\nStopping...")
        display.cleanup()
        print("Done!")


if __name__ == "__main__":
    main()
