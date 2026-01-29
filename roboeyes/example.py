#!/usr/bin/env python3
"""
Simple RoboEyes Example - Basic usage on Waveshare 2" LCD.

This is the minimal code needed to get animated eyes running.
"""

import sys
import time

# Add Waveshare library path (adjust if needed)
sys.path.insert(0, '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')

# Import RoboEyes
try:
    from roboeyes import RoboEyes, Mood, WaveshareDisplay
except ImportError:
    # Running directly from the roboeyes folder
    from eyes import RoboEyes, Mood
    from display import WaveshareDisplay


def main():
    # Create the eye renderer (landscape orientation)
    eyes = RoboEyes(width=320, height=240)

    # Configure eye size (optional - defaults work fine)
    eyes.set_width(70)
    eyes.set_height(70)
    eyes.set_border_radius(20)
    eyes.set_space_between(15)

    # Enable automatic blinking and idle wandering
    eyes.set_autoblinker(True, interval=3.0, variation=1.5)
    eyes.set_idle_mode(True, interval=2.0, variation=1.0)

    # Create the display (landscape orientation)
    display = WaveshareDisplay(
        width=320,
        height=240,
        rotation=90,     # 90 for landscape, try 270 if upside down
        backlight=50     # Brightness 0-100
    )

    print("RoboEyes running! Press Ctrl+C to stop.")

    try:
        while True:
            # Get the next frame and display it
            frame = eyes.update()
            display.show(frame)

            # Optional: cycle through moods every 10 seconds
            mood_index = int(time.time() / 10) % 4
            moods = [Mood.DEFAULT, Mood.HAPPY, Mood.ANGRY, Mood.TIRED]
            eyes.set_mood(moods[mood_index])

    except KeyboardInterrupt:
        print("\nStopping...")
        display.cleanup()


if __name__ == "__main__":
    main()
