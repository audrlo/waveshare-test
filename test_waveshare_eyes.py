#!/usr/bin/env python3
"""
Test RoboEyes with Waveshare 2" LCD Display

Usage:
    1. Copy roboeyes.py and waveshare_display.py to your Pi
    2. cd to the directory with these files
    3. Run: python3 test_waveshare_eyes.py
"""

import sys
import time

# Add Waveshare library path
sys.path.insert(0, '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')

# Import roboeyes (assumes roboeyes.py is in current directory)
from roboeyes import RoboEyes, Mood

# Import Waveshare display wrapper
from waveshare_display import WaveshareDisplay


def main():
    print("Initializing RoboEyes with Waveshare 2\" LCD...")
    
    # Create eyes renderer
    # Note: Waveshare 2" is 240x320, but displayed in portrait mode
    eyes = RoboEyes(width=240, height=320)
    
    # Create display
    display = WaveshareDisplay(
        width=240,
        height=320,
        rotation=180,    # Adjust if display is upside down (try 0 or 180)
        backlight=50     # Brightness 0-100
    )
    
    print("Display initialized!")
    print("Running eye animations... Press Ctrl+C to stop.")
    
    # Enable automatic behaviors
    eyes.set_autoblink(True, interval=3, variation=2)
    eyes.set_idle_mode(True, interval=2, variation=1)
    
    try:
        frame_count = 0
        start_time = time.time()
        
        while True:
            # Update and render
            frame = eyes.update()
            display.show(frame)
            
            frame_count += 1
            
            # Print FPS every 60 frames
            if frame_count % 60 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Running... FPS: {fps:.1f}")
            
            # Demo different moods every 10 seconds
            elapsed = time.time() - start_time
            mood_index = int(elapsed / 10) % 4
            moods = [Mood.DEFAULT, Mood.HAPPY, Mood.ANGRY, Mood.TIRED]
            eyes.set_mood(moods[mood_index])
    
    except KeyboardInterrupt:
        print("\nStopping...")
        display.cleanup()
        print("Done!")


if __name__ == "__main__":
    main()
