#!/usr/bin/env python3
"""
RoboEyes Demo - Demonstrates all features on Waveshare 2" LCD.

Usage:
    python3 -m roboeyes.demo

Or run directly:
    python3 demo.py
"""

import sys
import time
import argparse

# Handle running as module or directly
try:
    from roboeyes import RoboEyes, Mood, Position, WaveshareDisplay, MockDisplay
except ImportError:
    from eyes import RoboEyes, Mood, Position
    from display import WaveshareDisplay, MockDisplay


def run_demo(display_type: str = "waveshare", lib_path: str = None):
    """Run the RoboEyes demo."""
    print("=" * 50)
    print("RoboEyes Demo")
    print("A Python port of FluxGarage RoboEyes")
    print("=" * 50)
    print()

    # Create eyes (landscape orientation)
    print("Initializing RoboEyes...")
    eyes = RoboEyes(width=320, height=240)

    # Configure eye appearance
    eyes.set_width(70, 70)
    eyes.set_height(70, 70)
    eyes.set_border_radius(20, 20)
    eyes.set_space_between(15)

    # Create display
    print(f"Initializing display ({display_type})...")
    if display_type == "waveshare":
        try:
            display = WaveshareDisplay(
                width=320,
                height=240,
                rotation=90,
                backlight=50,
                lib_path=lib_path
            )
        except ImportError as e:
            print(f"Warning: {e}")
            print("Falling back to mock display...")
            display = MockDisplay(width=320, height=240)
    else:
        display = MockDisplay(width=320, height=240)

    print("Display initialized!")
    print()
    print("Running demo sequence... Press Ctrl+C to stop.")
    print()

    # Enable auto behaviors
    eyes.set_autoblinker(True, interval=3.0, variation=1.5)

    try:
        start_time = time.time()
        frame_count = 0
        last_fps_time = start_time
        demo_phase = 0
        phase_start = start_time

        while True:
            # Update and display
            frame = eyes.update()
            display.show(frame)
            frame_count += 1

            # Calculate FPS every second
            now = time.time()
            if now - last_fps_time >= 1.0:
                fps = frame_count / (now - last_fps_time)
                elapsed = now - start_time
                print(f"[{elapsed:6.1f}s] FPS: {fps:5.1f} | Phase: {demo_phase}")
                frame_count = 0
                last_fps_time = now

            # Demo sequence - change phase every 5 seconds
            phase_elapsed = now - phase_start
            if phase_elapsed >= 5.0:
                demo_phase = (demo_phase + 1) % 12
                phase_start = now

                if demo_phase == 0:
                    print("  -> Default mood, looking around (idle mode)")
                    eyes.set_mood(Mood.DEFAULT)
                    eyes.set_idle_mode(True, interval=1.5, variation=0.5)
                    eyes.set_sweat(False)

                elif demo_phase == 1:
                    print("  -> Happy mood!")
                    eyes.set_mood(Mood.HAPPY)
                    eyes.set_idle_mode(False)
                    eyes.set_position(Position.DEFAULT)

                elif demo_phase == 2:
                    print("  -> Angry mood!")
                    eyes.set_mood(Mood.ANGRY)
                    eyes.set_position(Position.DEFAULT)

                elif demo_phase == 3:
                    print("  -> Tired mood...")
                    eyes.set_mood(Mood.TIRED)
                    eyes.set_position(Position.S)

                elif demo_phase == 4:
                    print("  -> Looking around (compass directions)")
                    eyes.set_mood(Mood.DEFAULT)

                elif demo_phase == 5:
                    print("  -> Confused animation!")
                    eyes.anim_confused(duration=0.8)

                elif demo_phase == 6:
                    print("  -> Laugh animation!")
                    eyes.anim_laugh(duration=0.8)

                elif demo_phase == 7:
                    print("  -> Winking left...")
                    eyes.wink_left()

                elif demo_phase == 8:
                    print("  -> Winking right...")
                    eyes.wink_right()

                elif demo_phase == 9:
                    print("  -> Curiosity mode ON")
                    eyes.set_curiosity(True)
                    eyes.set_idle_mode(True, interval=1.0, variation=0.5)

                elif demo_phase == 10:
                    print("  -> Sweating nervously...")
                    eyes.set_curiosity(False)
                    eyes.set_idle_mode(False)
                    eyes.set_sweat(True)
                    eyes.set_mood(Mood.DEFAULT)
                    eyes.set_position(Position.DEFAULT)

                elif demo_phase == 11:
                    print("  -> Cyclops mode!")
                    eyes.set_sweat(False)
                    eyes.set_cyclops(True)
                    eyes.set_mood(Mood.DEFAULT)

                # Reset cyclops at end
                if demo_phase == 0:
                    eyes.set_cyclops(False)

            # Cycle through positions during phase 4
            if demo_phase == 4:
                sub_phase = int((phase_elapsed * 2) % 9)
                positions = [
                    Position.N, Position.NE, Position.E, Position.SE,
                    Position.S, Position.SW, Position.W, Position.NW,
                    Position.DEFAULT
                ]
                eyes.set_position(positions[sub_phase])

    except KeyboardInterrupt:
        print()
        print("Stopping demo...")
        display.cleanup()
        print("Done!")


def main():
    parser = argparse.ArgumentParser(description="RoboEyes Demo")
    parser.add_argument(
        "--display", "-d",
        choices=["waveshare", "mock"],
        default="waveshare",
        help="Display type (default: waveshare)"
    )
    parser.add_argument(
        "--lib-path", "-l",
        help="Path to Waveshare LCD library"
    )
    args = parser.parse_args()

    run_demo(display_type=args.display, lib_path=args.lib_path)


if __name__ == "__main__":
    main()
