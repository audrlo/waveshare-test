"""
RoboEyes - Animated Robot Eyes for Raspberry Pi
A Python port of the FluxGarage RoboEyes Arduino library.

https://github.com/FluxGarage/RoboEyes

Designed for ST7789 displays (like Waveshare 2" LCD) on Raspberry Pi.
"""

from .eyes import RoboEyes, Mood, Position
from .display import WaveshareDisplay, MockDisplay

__version__ = "1.0.0"
__all__ = ["RoboEyes", "Mood", "Position", "WaveshareDisplay", "MockDisplay"]
