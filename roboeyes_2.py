"""
RoboEyes - Animated Robot Eyes for Raspberry Pi
A Python port of the FluxGarage RoboEyes Arduino library.

Designed for ST7789 displays (240x320) on Raspberry Pi 5.
"""

import time
import random
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple, Callable
from PIL import Image, ImageDraw


class Mood(Enum):
    DEFAULT = "default"
    HAPPY = "happy"
    ANGRY = "angry"
    TIRED = "tired"


class Position(Enum):
    DEFAULT = "default"  # center
    N = "n"
    NE = "ne"
    E = "e"
    SE = "se"
    S = "s"
    SW = "sw"
    W = "w"
    NW = "nw"


@dataclass
class EyeConfig:
    """Configuration for a single eye."""
    width: float = 80.0
    height: float = 80.0
    border_radius: float = 15.0

    # For mood transformations
    width_default: float = 80.0
    height_default: float = 80.0
    border_radius_default: float = 15.0


@dataclass
class EyeState:
    """Current animated state of eyes."""
    # Position offsets from center
    x_offset: float = 0.0
    y_offset: float = 0.0

    # Current dimensions (animated)
    left_width: float = 80.0
    left_height: float = 80.0
    left_radius: float = 15.0
    right_width: float = 80.0
    right_height: float = 80.0
    right_radius: float = 15.0

    # Open state (1.0 = fully open, 0.0 = closed)
    left_open: float = 1.0
    right_open: float = 1.0

    # Mood modifiers for eye shape
    left_top_mod: float = 0.0  # Modify top of eye (for angry/tired)
    left_bottom_mod: float = 0.0
    right_top_mod: float = 0.0
    right_bottom_mod: float = 0.0


class RoboEyes:
    """
    Animated robot eyes renderer.

    Usage:
        eyes = RoboEyes(width=240, height=320)
        eyes.set_mood(Mood.HAPPY)
        eyes.set_position(Position.NE)

        while True:
            frame = eyes.update()
            # display frame on your screen
    """

    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        bg_color: Tuple[int, int, int] = (0, 0, 0),
        eye_color: Tuple[int, int, int] = (255, 255, 255),
        frame_rate: int = 60
    ):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.eye_color = eye_color
        self.frame_rate = frame_rate
        self.frame_time = 1.0 / frame_rate
        self.last_frame_time = 0.0

        # Eye configuration
        self.left_eye = EyeConfig()
        self.right_eye = EyeConfig()
        self.space_between = 20

        # Current state
        self.state = EyeState()

        # Target state (for smooth transitions)
        self._target_x_offset = 0.0
        self._target_y_offset = 0.0
        self._target_left_open = 1.0
        self._target_right_open = 1.0

        # Mood targets
        self._target_left_top_mod = 0.0
        self._target_left_bottom_mod = 0.0
        self._target_right_top_mod = 0.0
        self._target_right_bottom_mod = 0.0

        # Animation speed (0-1, higher = faster)
        self.transition_speed = 0.15
        self.blink_speed = 0.4

        # Current mood and position
        self.mood = Mood.DEFAULT
        self.position = Position.DEFAULT

        # Features
        self.cyclops_mode = False
        self.curiosity_mode = False
        self.autoblink_enabled = False
        self.autoblink_interval = 4.0  # seconds
        self.autoblink_variation = 2.0
        self._next_blink_time = 0.0

        self.idle_mode = False
        self.idle_interval = 3.0
        self.idle_variation = 2.0
        self._next_idle_time = 0.0

        # Flicker
        self.h_flicker = False
        self.v_flicker = False
        self.h_flicker_amplitude = 2
        self.v_flicker_amplitude = 2

        # Animation state
        self._animating = False
        self._animation_func: Optional[Callable] = None
        self._animation_start_time = 0.0

        # Sweat drop
        self.sweat_enabled = False
        self._sweat_y = 0.0
        self._sweat_visible = False

        # Initialize state
        self._update_eye_dimensions()
        self._schedule_next_blink()
        self._schedule_next_idle()

    def _update_eye_dimensions(self):
        """Update state dimensions from config."""
        self.state.left_width = self.left_eye.width
        self.state.left_height = self.left_eye.height
        self.state.left_radius = self.left_eye.border_radius
        self.state.right_width = self.right_eye.width
        self.state.right_height = self.right_eye.height
        self.state.right_radius = self.right_eye.border_radius

    # === Configuration Methods ===

    def set_width(self, left: float, right: Optional[float] = None):
        """Set eye widths in pixels."""
        if right is None:
            right = left
        self.left_eye.width = left
        self.left_eye.width_default = left
        self.right_eye.width = right
        self.right_eye.width_default = right
        self._update_eye_dimensions()

    def set_height(self, left: float, right: Optional[float] = None):
        """Set eye heights in pixels."""
        if right is None:
            right = left
        self.left_eye.height = left
        self.left_eye.height_default = left
        self.right_eye.height = right
        self.right_eye.height_default = right
        self._update_eye_dimensions()

    def set_border_radius(self, left: float, right: Optional[float] = None):
        """Set eye corner radius in pixels."""
        if right is None:
            right = left
        self.left_eye.border_radius = left
        self.left_eye.border_radius_default = left
        self.right_eye.border_radius = right
        self.right_eye.border_radius_default = right
        self._update_eye_dimensions()

    def set_space_between(self, space: int):
        """Set space between eyes (can be negative for overlap)."""
        self.space_between = space

    def set_cyclops(self, enabled: bool):
        """Enable/disable single eye (cyclops) mode."""
        self.cyclops_mode = enabled

    def set_curiosity(self, enabled: bool):
        """Enable/disable curiosity mode (outer eye grows when looking sideways)."""
        self.curiosity_mode = enabled

    def set_colors(self, bg: Tuple[int, int, int], eye: Tuple[int, int, int]):
        """Set background and eye colors."""
        self.bg_color = bg
        self.eye_color = eye

    # === Mood & Position ===

    def set_mood(self, mood: Mood):
        """Set the eye mood/expression."""
        self.mood = mood

        if mood == Mood.DEFAULT:
            self._target_left_top_mod = 0.0
            self._target_left_bottom_mod = 0.0
            self._target_right_top_mod = 0.0
            self._target_right_bottom_mod = 0.0

        elif mood == Mood.HAPPY:
            # Squint from bottom (happy/smiling)
            self._target_left_top_mod = 0.0
            self._target_left_bottom_mod = 0.4
            self._target_right_top_mod = 0.0
            self._target_right_bottom_mod = 0.4

        elif mood == Mood.ANGRY:
            # Slant inward from top (angry eyebrows)
            self._target_left_top_mod = 0.35  # inner side down
            self._target_left_bottom_mod = 0.0
            self._target_right_top_mod = 0.35
            self._target_right_bottom_mod = 0.0

        elif mood == Mood.TIRED:
            # Droop from top (tired/sleepy)
            self._target_left_top_mod = 0.5
            self._target_left_bottom_mod = 0.0
            self._target_right_top_mod = 0.5
            self._target_right_bottom_mod = 0.0

    def set_position(self, position: Position):
        """Set where the eyes are looking."""
        self.position = position

        # Calculate offsets based on position
        max_x = (self.width - self.left_eye.width - self.right_eye.width - self.space_between) / 2 - 10
        max_y = (self.height - max(self.left_eye.height, self.right_eye.height)) / 2 - 10

        offsets = {
            Position.DEFAULT: (0, 0),
            Position.N: (0, -max_y * 0.7),
            Position.NE: (max_x * 0.7, -max_y * 0.7),
            Position.E: (max_x * 0.7, 0),
            Position.SE: (max_x * 0.7, max_y * 0.7),
            Position.S: (0, max_y * 0.7),
            Position.SW: (-max_x * 0.7, max_y * 0.7),
            Position.W: (-max_x * 0.7, 0),
            Position.NW: (-max_x * 0.7, -max_y * 0.7),
        }

        self._target_x_offset, self._target_y_offset = offsets.get(position, (0, 0))

    def look(self, direction: str):
        """Convenience method to set position by string."""
        position_map = {
            "center": Position.DEFAULT,
            "default": Position.DEFAULT,
            "n": Position.N, "north": Position.N, "up": Position.N,
            "ne": Position.NE, "northeast": Position.NE,
            "e": Position.E, "east": Position.E, "right": Position.E,
            "se": Position.SE, "southeast": Position.SE,
            "s": Position.S, "south": Position.S, "down": Position.S,
            "sw": Position.SW, "southwest": Position.SW,
            "w": Position.W, "west": Position.W, "left": Position.W,
            "nw": Position.NW, "northwest": Position.NW,
        }
        pos = position_map.get(direction.lower(), Position.DEFAULT)
        self.set_position(pos)

    # === Eye Open/Close ===

    def open(self, left: bool = True, right: bool = True):
        """Open eyes."""
        if left:
            self._target_left_open = 1.0
        if right:
            self._target_right_open = 1.0

    def close(self, left: bool = True, right: bool = True):
        """Close eyes."""
        if left:
            self._target_left_open = 0.0
        if right:
            self._target_right_open = 0.0

    # === Blink Animation ===

    def blink(self, left: bool = True, right: bool = True):
        """Trigger a blink animation."""
        self._start_animation(lambda t: self._blink_animation(t, left, right), duration=0.25)

    def wink_left(self):
        """Wink the left eye."""
        self.blink(left=True, right=False)

    def wink_right(self):
        """Wink the right eye."""
        self.blink(left=False, right=True)

    def _blink_animation(self, t: float, left: bool, right: bool):
        """Blink animation function."""
        # Blink is a quick close and open
        blink_curve = 1.0 - math.sin(t * math.pi)  # 1 -> 0 -> 1

        if left:
            self.state.left_open = blink_curve
        if right:
            self.state.right_open = blink_curve

        return t >= 1.0

    # === Special Animations ===

    def anim_confused(self, duration: float = 0.6):
        """Trigger confused animation (horizontal shake)."""
        self._start_animation(lambda t: self._confused_animation(t), duration=duration)

    def _confused_animation(self, t: float):
        """Confused shake animation."""
        shake = math.sin(t * math.pi * 8) * 15 * (1 - t)  # Decaying shake
        self.state.x_offset = self._target_x_offset + shake
        return t >= 1.0

    def anim_laugh(self, duration: float = 0.6):
        """Trigger laugh animation (vertical shake)."""
        self._start_animation(lambda t: self._laugh_animation(t), duration=duration)

    def _laugh_animation(self, t: float):
        """Laugh shake animation."""
        shake = math.sin(t * math.pi * 10) * 8 * (1 - t)
        self.state.y_offset = self._target_y_offset + shake
        return t >= 1.0

    def _start_animation(self, func: Callable, duration: float):
        """Start a timed animation."""
        self._animating = True
        self._animation_func = func
        self._animation_start_time = time.time()
        self._animation_duration = duration

    # === Auto Behaviors ===

    def set_autoblink(self, enabled: bool, interval: float = 4.0, variation: float = 2.0):
        """Enable/disable automatic random blinking."""
        self.autoblink_enabled = enabled
        self.autoblink_interval = interval
        self.autoblink_variation = variation
        if enabled:
            self._schedule_next_blink()

    def _schedule_next_blink(self):
        """Schedule the next automatic blink."""
        delay = self.autoblink_interval + random.uniform(-self.autoblink_variation, self.autoblink_variation)
        self._next_blink_time = time.time() + max(0.5, delay)

    def set_idle_mode(self, enabled: bool, interval: float = 3.0, variation: float = 2.0):
        """Enable/disable idle eye wandering."""
        self.idle_mode = enabled
        self.idle_interval = interval
        self.idle_variation = variation
        if enabled:
            self._schedule_next_idle()

    def _schedule_next_idle(self):
        """Schedule the next idle movement."""
        delay = self.idle_interval + random.uniform(-self.idle_variation, self.idle_variation)
        self._next_idle_time = time.time() + max(0.5, delay)

    # === Flicker Effects ===

    def set_h_flicker(self, enabled: bool, amplitude: int = 2):
        """Enable horizontal flicker effect."""
        self.h_flicker = enabled
        self.h_flicker_amplitude = amplitude

    def set_v_flicker(self, enabled: bool, amplitude: int = 2):
        """Enable vertical flicker effect."""
        self.v_flicker = enabled
        self.v_flicker_amplitude = amplitude

    # === Sweat Drop ===

    def set_sweat(self, enabled: bool):
        """Enable/disable sweat drop animation."""
        self.sweat_enabled = enabled
        if enabled:
            self._sweat_y = 0.0
            self._sweat_visible = True

    # === Update & Render ===

    def _lerp(self, current: float, target: float, speed: float) -> float:
        """Linear interpolation for smooth transitions."""
        diff = target - current
        if abs(diff) < 0.01:
            return target
        return current + diff * speed

    def _update_state(self):
        """Update animated state towards targets."""
        # Smooth position transitions
        self.state.x_offset = self._lerp(self.state.x_offset, self._target_x_offset, self.transition_speed)
        self.state.y_offset = self._lerp(self.state.y_offset, self._target_y_offset, self.transition_speed)

        # Smooth open/close (faster for blinks)
        self.state.left_open = self._lerp(self.state.left_open, self._target_left_open, self.blink_speed)
        self.state.right_open = self._lerp(self.state.right_open, self._target_right_open, self.blink_speed)

        # Smooth mood transitions
        self.state.left_top_mod = self._lerp(self.state.left_top_mod, self._target_left_top_mod, self.transition_speed)
        self.state.left_bottom_mod = self._lerp(self.state.left_bottom_mod, self._target_left_bottom_mod, self.transition_speed)
        self.state.right_top_mod = self._lerp(self.state.right_top_mod, self._target_right_top_mod, self.transition_speed)
        self.state.right_bottom_mod = self._lerp(self.state.right_bottom_mod, self._target_right_bottom_mod, self.transition_speed)

        # Curiosity mode: outer eye grows when looking sideways
        if self.curiosity_mode:
            look_amount = abs(self.state.x_offset) / 50
            if self.state.x_offset > 5:  # Looking right
                self.state.left_height = self.left_eye.height_default * (1 + look_amount * 0.2)
            elif self.state.x_offset < -5:  # Looking left
                self.state.right_height = self.right_eye.height_default * (1 + look_amount * 0.2)
            else:
                self.state.left_height = self.left_eye.height_default
                self.state.right_height = self.right_eye.height_default

    def _process_auto_behaviors(self):
        """Process automatic blink and idle behaviors."""
        now = time.time()

        # Auto blink
        if self.autoblink_enabled and now >= self._next_blink_time and not self._animating:
            self.blink()
            self._schedule_next_blink()

        # Idle mode
        if self.idle_mode and now >= self._next_idle_time and not self._animating:
            positions = list(Position)
            new_pos = random.choice(positions)
            self.set_position(new_pos)
            self._schedule_next_idle()

    def _process_animation(self):
        """Process current animation if any."""
        if not self._animating or self._animation_func is None:
            return

        elapsed = time.time() - self._animation_start_time
        t = min(1.0, elapsed / self._animation_duration)

        done = self._animation_func(t)

        if done:
            self._animating = False
            self._animation_func = None

    def _draw_rounded_rect(self, draw: ImageDraw, x: float, y: float,
                           width: float, height: float, radius: float,
                           top_mod: float = 0.0, bottom_mod: float = 0.0,
                           color: Tuple[int, int, int] = (255, 255, 255)):
        """Draw a rounded rectangle with optional top/bottom modifications."""
        # Clamp radius
        radius = min(radius, width / 2, height / 2)

        # Apply modifications for moods
        top_offset = height * top_mod
        bottom_offset = height * bottom_mod

        # Effective height after modifications
        eff_height = height - top_offset - bottom_offset
        if eff_height < 2:
            return

        y_top = y + top_offset
        
        # Clamp radius to avoid invalid coordinates when height is small
        radius = min(radius, eff_height / 2, width / 2)

        # Draw using polygon for modified shapes, or simple rounded rect for normal
        if top_mod > 0.01 or bottom_mod > 0.01:
            # Draw as filled polygon (approximate rounded corners)
            points = []

            # Top left corner
            points.append((x + radius, y_top))

            # Top right corner
            points.append((x + width - radius, y_top))

            # Right side
            points.append((x + width, y_top + radius))
            points.append((x + width, y_top + eff_height - radius))

            # Bottom right
            points.append((x + width - radius, y_top + eff_height))

            # Bottom left
            points.append((x + radius, y_top + eff_height))

            # Left side
            points.append((x, y_top + eff_height - radius))
            points.append((x, y_top + radius))

            draw.polygon(points, fill=color)

            # Draw corner circles
            r = radius
            # Top-left
            draw.ellipse([x, y_top, x + r * 2, y_top + r * 2], fill=color)
            # Top-right
            draw.ellipse([x + width - r * 2, y_top, x + width, y_top + r * 2], fill=color)
            # Bottom-right
            draw.ellipse([x + width - r * 2, y_top + eff_height - r * 2, x + width, y_top + eff_height], fill=color)
            # Bottom-left
            draw.ellipse([x, y_top + eff_height - r * 2, x + r * 2, y_top + eff_height], fill=color)

            # Fill center rectangles
            draw.rectangle([x + radius, y_top, x + width - radius, y_top + eff_height], fill=color)
            draw.rectangle([x, y_top + radius, x + width, y_top + eff_height - radius], fill=color)
        else:
            # Simple rounded rectangle
            draw.rounded_rectangle(
                [x, y_top, x + width, y_top + eff_height],
                radius=radius,
                fill=color
            )

    def _draw_sweat_drop(self, draw: ImageDraw, x: float, y: float):
        """Draw animated sweat drop."""
        if not self.sweat_enabled or not self._sweat_visible:
            return

        # Animate sweat drop falling
        self._sweat_y += 2
        if self._sweat_y > 40:
            self._sweat_y = 0

        drop_y = y + self._sweat_y

        # Draw teardrop shape
        draw.ellipse([x - 4, drop_y, x + 4, drop_y + 8], fill=(100, 150, 255))
        draw.polygon([(x, drop_y - 6), (x - 4, drop_y + 2), (x + 4, drop_y + 2)], fill=(100, 150, 255))

    def update(self) -> Image.Image:
        """
        Update animation state and render a frame.
        Returns a PIL Image that can be displayed.
        """
        # Frame rate limiting
        now = time.time()
        elapsed = now - self.last_frame_time
        if elapsed < self.frame_time:
            time.sleep(self.frame_time - elapsed)
        self.last_frame_time = time.time()

        # Process behaviors and animations
        self._process_auto_behaviors()
        self._process_animation()
        self._update_state()

        # Create frame
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Calculate eye positions
        center_x = self.width / 2
        center_y = self.height / 2

        # Apply flicker
        flicker_x = random.randint(-self.h_flicker_amplitude, self.h_flicker_amplitude) if self.h_flicker else 0
        flicker_y = random.randint(-self.v_flicker_amplitude, self.v_flicker_amplitude) if self.v_flicker else 0

        offset_x = self.state.x_offset + flicker_x
        offset_y = self.state.y_offset + flicker_y

        if self.cyclops_mode:
            # Single centered eye
            eye_w = self.state.left_width
            eye_h = self.state.left_height * self.state.left_open
            eye_r = self.state.left_radius

            ex = center_x - eye_w / 2 + offset_x
            ey = center_y - eye_h / 2 + offset_y

            self._draw_rounded_rect(
                draw, ex, ey, eye_w, eye_h, eye_r,
                self.state.left_top_mod, self.state.left_bottom_mod,
                self.eye_color
            )
        else:
            # Two eyes
            total_width = self.state.left_width + self.space_between + self.state.right_width
            start_x = center_x - total_width / 2 + offset_x

            # Left eye
            left_h = self.state.left_height * self.state.left_open
            if left_h > 1:
                left_y = center_y - left_h / 2 + offset_y
                self._draw_rounded_rect(
                    draw, start_x, left_y,
                    self.state.left_width, left_h, self.state.left_radius,
                    self.state.left_top_mod, self.state.left_bottom_mod,
                    self.eye_color
                )

            # Right eye
            right_x = start_x + self.state.left_width + self.space_between
            right_h = self.state.right_height * self.state.right_open
            if right_h > 1:
                right_y = center_y - right_h / 2 + offset_y
                self._draw_rounded_rect(
                    draw, right_x, right_y,
                    self.state.right_width, right_h, self.state.right_radius,
                    self.state.right_top_mod, self.state.right_bottom_mod,
                    self.eye_color
                )

            # Sweat drop (top right of right eye)
            if self.sweat_enabled:
                sweat_x = right_x + self.state.right_width + 10
                sweat_y = center_y - self.state.right_height / 2 - 20 + offset_y
                self._draw_sweat_drop(draw, sweat_x, sweat_y)

        return img

    def get_frame(self) -> Image.Image:
        """Alias for update() - returns current frame."""
        return self.update()


# === Display Drivers ===

class ST7789Display:
    """
    Display driver for ST7789 LCD on Raspberry Pi.
    Requires: pip install st7789 RPi.GPIO spidev Pillow
    """

    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        rotation: int = 0,
        port: int = 0,
        cs: int = 0,
        dc: int = 25,
        rst: int = 24,
        backlight: int = 18
    ):
        try:
            import st7789
            import RPi.GPIO as GPIO
        except ImportError:
            raise ImportError(
                "ST7789 display requires: pip install st7789 RPi.GPIO spidev"
            )

        self.width = width
        self.height = height

        # Initialize display
        self.display = st7789.ST7789(
            port=port,
            cs=cs,
            dc=dc,
            rst=rst,
            backlight=backlight,
            width=width,
            height=height,
            rotation=rotation,
            spi_speed_hz=60000000
        )

    def show(self, image: Image.Image):
        """Display a PIL Image on the screen."""
        self.display.display(image)


class LumaDisplay:
    """
    Display driver using luma.lcd library.
    Requires: pip install luma.lcd
    """

    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        rotation: int = 0,
        gpio_DC: int = 25,
        gpio_RST: int = 24,
        gpio_backlight: int = 18
    ):
        try:
            from luma.core.interface.serial import spi
            from luma.lcd.device import st7789
        except ImportError:
            raise ImportError(
                "Luma display requires: pip install luma.lcd"
            )

        serial = spi(
            port=0,
            device=0,
            gpio_DC=gpio_DC,
            gpio_RST=gpio_RST,
            bus_speed_hz=60000000
        )

        self.device = st7789(
            serial,
            width=width,
            height=height,
            rotate=rotation,
            gpio_backlight=gpio_backlight,
            active_low=False
        )
        self.width = width
        self.height = height

    def show(self, image: Image.Image):
        """Display a PIL Image on the screen."""
        self.device.display(image)


class MockDisplay:
    """Mock display for testing without hardware."""

    def __init__(self, width: int = 240, height: int = 320):
        self.width = width
        self.height = height
        self.last_frame: Optional[Image.Image] = None

    def show(self, image: Image.Image):
        """Store frame (for testing)."""
        self.last_frame = image


# === Convenience Function ===

def create_eyes(
    display_type: str = "auto",
    width: int = 240,
    height: int = 320,
    **kwargs
) -> Tuple[RoboEyes, any]:
    """
    Create RoboEyes instance with display.

    Args:
        display_type: "st7789", "luma", "mock", or "auto"
        width: Display width
        height: Display height
        **kwargs: Additional display arguments

    Returns:
        Tuple of (RoboEyes instance, display instance)
    """
    eyes = RoboEyes(width=width, height=height)

    if display_type == "auto":
        # Try to detect available display
        try:
            display = ST7789Display(width=width, height=height, **kwargs)
            return eyes, display
        except (ImportError, Exception):
            pass

        try:
            display = LumaDisplay(width=width, height=height, **kwargs)
            return eyes, display
        except (ImportError, Exception):
            pass

        # Fall back to mock
        display = MockDisplay(width=width, height=height)
        return eyes, display

    elif display_type == "st7789":
        display = ST7789Display(width=width, height=height, **kwargs)
    elif display_type == "luma":
        display = LumaDisplay(width=width, height=height, **kwargs)
    else:
        display = MockDisplay(width=width, height=height)

    return eyes, display
