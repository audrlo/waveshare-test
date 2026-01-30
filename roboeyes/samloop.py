#!/usr/bin/env python3
"""
Sam's Eye Loop - Large sky blue eyes cycling through moods.
"""

import sys
import time

# Add Waveshare library path
sys.path.insert(0, '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')

try:
    from roboeyes import RoboEyes, WaveshareDisplay
except ImportError:
    from eyes import RoboEyes
    from display import WaveshareDisplay


def main():
    # Screen is 320x240 landscape
    # Size eyes to fill screen with minimal margins
    screen_width = 320
    screen_height = 240

    # Eye sizing: maximize while keeping on screen
    # Leave 10px margin on each side for safety during animations
    margin = 10
    space_between = 16

    # Calculate max eye dimensions
    # Width: (screen_width - 2*margin - space_between) / 2
    eye_width = (screen_width - 2 * margin - space_between) // 2  # = 142
    # Height: screen_height - 2*margin
    eye_height = screen_height - 2 * margin  # = 220

    # Make eyes slightly less tall than wide for better look
    eye_height = min(eye_height, 180)
    eye_width = min(eye_width, 140)

    # Border radius - nice rounded corners
    border_radius = 35

    # Colors
    bg_color = (0, 0, 0)  # Black background
    eye_color = (135, 206, 250)  # #87CEFA - Light Sky Blue

    print("Sam's Eye Loop")
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

    # Enable regular blinking
    eyes.set_autoblinker(True, interval=3.5, variation=1.0)

    # Create display
    display = WaveshareDisplay(
        width=screen_width,
        height=screen_height,
        rotation=90,
        backlight=50
    )

    print("Running! Press Ctrl+C to stop.")

    try:
        while True:
            frame = eyes.update()
            display.show(frame)

    except KeyboardInterrupt:
        print("\nStopping...")
        display.cleanup()
        print("Done!")


if __name__ == "__main__":
    main()
