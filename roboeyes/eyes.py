"""
RoboEyes - Main animation engine.
A Python port of the FluxGarage RoboEyes Arduino library.
"""

import time
import random
import math
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image, ImageDraw


class Mood(IntEnum):
    """Eye mood/expression states."""
    DEFAULT = 0
    TIRED = 1
    ANGRY = 2
    HAPPY = 3


class Position(IntEnum):
    """Eye position constants (compass directions)."""
    DEFAULT = 0  # Center
    N = 1
    NE = 2
    E = 3
    SE = 4
    S = 5
    SW = 6
    W = 7
    NW = 8


@dataclass
class EyeGeometry:
    """Geometry for a single eye with animation state."""
    # Current values
    width: float = 36.0
    height: float = 36.0
    border_radius: float = 8.0

    # Target values (for tweening)
    width_next: float = 36.0
    height_next: float = 36.0
    border_radius_next: float = 8.0

    # Default values (for reset)
    width_default: float = 36.0
    height_default: float = 36.0
    border_radius_default: float = 8.0


class RoboEyes:
    """
    Animated robot eyes renderer.

    A Python port of the FluxGarage RoboEyes Arduino library.
    Renders animated robot eyes to PIL Images for display on LCD screens.

    Usage:
        from roboeyes import RoboEyes, Mood, WaveshareDisplay

        eyes = RoboEyes(width=240, height=320)
        eyes.set_autoblinker(True)
        eyes.set_idle_mode(True)

        display = WaveshareDisplay()

        while True:
            frame = eyes.update()
            display.show(frame)
    """

    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        bg_color: Tuple[int, int, int] = (0, 0, 0),
        eye_color: Tuple[int, int, int] = (255, 255, 255),
        frame_rate: int = 50
    ):
        """
        Initialize RoboEyes.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            bg_color: Background color RGB tuple
            eye_color: Eye color RGB tuple
            frame_rate: Target frame rate (default 50 fps)
        """
        self.screen_width = width
        self.screen_height = height
        self.bg_color = bg_color
        self.eye_color = eye_color

        # Frame rate control
        self.frame_rate = frame_rate
        self.frame_interval = 1.0 / frame_rate
        self._last_frame_time = 0.0

        # Eye geometry
        self.left_eye = EyeGeometry()
        self.right_eye = EyeGeometry()
        self.space_between = 10  # Space between eyes

        # Position state
        self._x = 0.0  # Current X offset from center
        self._y = 0.0  # Current Y offset from center
        self._x_next = 0.0  # Target X
        self._y_next = 0.0  # Target Y

        # Eye open state (1.0 = open, 0.0 = closed)
        self._left_open = 1.0
        self._right_open = 1.0
        self._left_open_next = 1.0
        self._right_open_next = 1.0

        # Mood state
        self._mood = Mood.DEFAULT
        self._tired = False
        self._angry = False
        self._happy = False

        # Feature flags
        self._cyclops = False
        self._curious = False
        self._h_flicker = False
        self._v_flicker = False
        self._h_flicker_amplitude = 2
        self._v_flicker_amplitude = 2

        # Animation flags
        self._autoblinker = False
        self._idle = False
        self._confused = False
        self._laugh = False

        # Sweat animation
        self._sweat = False
        self._sweat_pos = [0.0, 0.0, 0.0]  # Y positions for 3 drops
        self._sweat_sizes = [1.0, 1.0, 1.0]  # Size multipliers

        # Blink timing
        self._blink_timer = 0.0
        self._blink_interval = 4.0
        self._blink_interval_variation = 2.0
        self._next_blink_time = 0.0
        self._is_blinking = False
        self._blink_start_time = 0.0
        self._blink_duration = 0.15

        # Idle timing
        self._idle_timer = 0.0
        self._idle_interval = 3.0
        self._idle_interval_variation = 2.0
        self._next_idle_time = 0.0

        # Confused animation
        self._confused_timer = 0.0
        self._confused_duration = 0.5
        self._confused_start_time = 0.0

        # Laugh animation
        self._laugh_timer = 0.0
        self._laugh_duration = 0.5
        self._laugh_start_time = 0.0

        # Pre-calculated constraints
        self._update_constraints()

        # Schedule first events
        self._schedule_next_blink()
        self._schedule_next_idle()

    def _update_constraints(self):
        """Update screen constraint calculations."""
        eye_w = self.left_eye.width + self.right_eye.width + self.space_between
        eye_h = max(self.left_eye.height, self.right_eye.height)

        self._max_x = (self.screen_width - eye_w) / 2 - 5
        self._max_y = (self.screen_height - eye_h) / 2 - 5

    # ========== Configuration Methods ==========

    def set_frame_rate(self, fps: int):
        """Set the target frame rate."""
        self.frame_rate = fps
        self.frame_interval = 1.0 / fps

    def set_width(self, left: int, right: Optional[int] = None):
        """Set eye width(s) in pixels."""
        if right is None:
            right = left
        self.left_eye.width_next = float(left)
        self.left_eye.width_default = float(left)
        self.right_eye.width_next = float(right)
        self.right_eye.width_default = float(right)
        self._update_constraints()

    def set_height(self, left: int, right: Optional[int] = None):
        """Set eye height(s) in pixels."""
        if right is None:
            right = left
        self.left_eye.height_next = float(left)
        self.left_eye.height_default = float(left)
        self.right_eye.height_next = float(right)
        self.right_eye.height_default = float(right)
        self._update_constraints()

    def set_border_radius(self, left: int, right: Optional[int] = None):
        """Set eye corner radius in pixels."""
        if right is None:
            right = left
        self.left_eye.border_radius_next = float(left)
        self.left_eye.border_radius_default = float(left)
        self.right_eye.border_radius_next = float(right)
        self.right_eye.border_radius_default = float(right)

    def set_space_between(self, space: int):
        """Set space between eyes (can be negative for overlap)."""
        self.space_between = space
        self._update_constraints()

    def set_colors(self, bg: Tuple[int, int, int], eye: Tuple[int, int, int]):
        """Set background and eye colors."""
        self.bg_color = bg
        self.eye_color = eye

    # ========== Mood & Position ==========

    def set_mood(self, mood: Mood):
        """Set the eye mood/expression."""
        self._mood = mood
        self._tired = (mood == Mood.TIRED)
        self._angry = (mood == Mood.ANGRY)
        self._happy = (mood == Mood.HAPPY)

    def set_position(self, position: Position):
        """Set where the eyes are looking."""
        # Calculate target offsets based on position
        x_offset = 0.0
        y_offset = 0.0

        if position == Position.N:
            y_offset = -self._max_y * 0.8
        elif position == Position.NE:
            x_offset = self._max_x * 0.8
            y_offset = -self._max_y * 0.8
        elif position == Position.E:
            x_offset = self._max_x * 0.8
        elif position == Position.SE:
            x_offset = self._max_x * 0.8
            y_offset = self._max_y * 0.8
        elif position == Position.S:
            y_offset = self._max_y * 0.8
        elif position == Position.SW:
            x_offset = -self._max_x * 0.8
            y_offset = self._max_y * 0.8
        elif position == Position.W:
            x_offset = -self._max_x * 0.8
        elif position == Position.NW:
            x_offset = -self._max_x * 0.8
            y_offset = -self._max_y * 0.8
        # DEFAULT = center (0, 0)

        self._x_next = x_offset
        self._y_next = y_offset

    def look(self, direction: str):
        """Convenience method to look in a direction by string name."""
        direction = direction.lower().strip()
        mapping = {
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
        self.set_position(mapping.get(direction, Position.DEFAULT))

    # ========== Eye Open/Close ==========

    def open(self, left: bool = True, right: bool = True):
        """Open eye(s)."""
        if left:
            self._left_open_next = 1.0
        if right:
            self._right_open_next = 1.0

    def close(self, left: bool = True, right: bool = True):
        """Close eye(s)."""
        if left:
            self._left_open_next = 0.0
        if right:
            self._right_open_next = 0.0

    def blink(self, left: bool = True, right: bool = True):
        """Trigger a blink animation."""
        self._is_blinking = True
        self._blink_start_time = time.time()
        self._blink_left = left
        self._blink_right = right

    def wink_left(self):
        """Wink the left eye."""
        self.blink(left=True, right=False)

    def wink_right(self):
        """Wink the right eye."""
        self.blink(left=False, right=True)

    # ========== Feature Toggles ==========

    def set_cyclops(self, enabled: bool):
        """Enable/disable single eye (cyclops) mode."""
        self._cyclops = enabled

    def set_curiosity(self, enabled: bool):
        """Enable/disable curiosity mode (outer eye grows when looking sideways)."""
        self._curious = enabled

    def set_h_flicker(self, enabled: bool, amplitude: int = 2):
        """Enable horizontal position flicker."""
        self._h_flicker = enabled
        self._h_flicker_amplitude = amplitude

    def set_v_flicker(self, enabled: bool, amplitude: int = 2):
        """Enable vertical position flicker."""
        self._v_flicker = enabled
        self._v_flicker_amplitude = amplitude

    def set_sweat(self, enabled: bool):
        """Enable/disable animated sweat drops."""
        self._sweat = enabled
        if enabled:
            self._sweat_pos = [0.0, 5.0, 10.0]
            self._sweat_sizes = [1.0, 0.8, 0.6]

    # ========== Auto Behaviors ==========

    def set_autoblinker(self, enabled: bool, interval: float = 4.0, variation: float = 2.0):
        """
        Enable/disable automatic random blinking.

        Args:
            enabled: Turn autoblinker on/off
            interval: Base interval between blinks in seconds
            variation: Random variation (+/-) in seconds
        """
        self._autoblinker = enabled
        self._blink_interval = interval
        self._blink_interval_variation = variation
        if enabled:
            self._schedule_next_blink()

    def set_idle_mode(self, enabled: bool, interval: float = 3.0, variation: float = 2.0):
        """
        Enable/disable idle eye wandering.

        Args:
            enabled: Turn idle mode on/off
            interval: Base interval between movements in seconds
            variation: Random variation (+/-) in seconds
        """
        self._idle = enabled
        self._idle_interval = interval
        self._idle_interval_variation = variation
        if enabled:
            self._schedule_next_idle()

    def _schedule_next_blink(self):
        """Schedule the next automatic blink."""
        variation = random.uniform(-self._blink_interval_variation, self._blink_interval_variation)
        self._next_blink_time = time.time() + max(0.5, self._blink_interval + variation)

    def _schedule_next_idle(self):
        """Schedule the next idle position change."""
        variation = random.uniform(-self._idle_interval_variation, self._idle_interval_variation)
        self._next_idle_time = time.time() + max(0.5, self._idle_interval + variation)

    # ========== Special Animations ==========

    def anim_confused(self, duration: float = 0.5):
        """Trigger confused animation (horizontal shake)."""
        self._confused = True
        self._confused_start_time = time.time()
        self._confused_duration = duration

    def anim_laugh(self, duration: float = 0.5):
        """Trigger laugh animation (vertical shake)."""
        self._laugh = True
        self._laugh_start_time = time.time()
        self._laugh_duration = duration

    # ========== Tweening ==========

    def _tween(self, current: float, target: float) -> float:
        """Simple tweening: move current halfway to target."""
        return (current + target) / 2.0

    def _tween_fast(self, current: float, target: float) -> float:
        """Faster tweening for quick animations."""
        return current + (target - current) * 0.4

    # ========== Update & Render ==========

    def _process_auto_behaviors(self):
        """Process autoblinker and idle mode."""
        now = time.time()

        # Autoblinker
        if self._autoblinker and not self._is_blinking:
            if now >= self._next_blink_time:
                self.blink()
                self._schedule_next_blink()

        # Idle mode
        if self._idle and not self._confused and not self._laugh:
            if now >= self._next_idle_time:
                # Pick random position
                positions = list(Position)
                self.set_position(random.choice(positions))
                self._schedule_next_idle()

    def _process_animations(self):
        """Process running animations."""
        now = time.time()

        # Blink animation
        if self._is_blinking:
            elapsed = now - self._blink_start_time
            t = elapsed / self._blink_duration

            if t >= 1.0:
                # Blink complete
                self._is_blinking = False
                if self._blink_left:
                    self._left_open_next = 1.0
                if self._blink_right:
                    self._right_open_next = 1.0
            else:
                # Blink curve: close then open
                blink_curve = 1.0 - math.sin(t * math.pi)
                if self._blink_left:
                    self._left_open = blink_curve
                if self._blink_right:
                    self._right_open = blink_curve

        # Confused animation (horizontal shake)
        if self._confused:
            elapsed = now - self._confused_start_time
            if elapsed >= self._confused_duration:
                self._confused = False
            else:
                t = elapsed / self._confused_duration
                shake = math.sin(t * math.pi * 8) * 15 * (1 - t)
                self._x = self._x_next + shake

        # Laugh animation (vertical shake)
        if self._laugh:
            elapsed = now - self._laugh_start_time
            if elapsed >= self._laugh_duration:
                self._laugh = False
            else:
                t = elapsed / self._laugh_duration
                shake = math.sin(t * math.pi * 10) * 8 * (1 - t)
                self._y = self._y_next + shake

    def _update_geometry(self):
        """Update eye geometry with tweening."""
        # Position tweening (unless animation is controlling it)
        if not self._confused:
            self._x = self._tween(self._x, self._x_next)
        if not self._laugh:
            self._y = self._tween(self._y, self._y_next)

        # Eye open state tweening
        if not self._is_blinking:
            self._left_open = self._tween_fast(self._left_open, self._left_open_next)
            self._right_open = self._tween_fast(self._right_open, self._right_open_next)

        # Curious mode: outer eye height increases when looking sideways
        if self._curious:
            look_amount = abs(self._x) / max(self._max_x, 1) * 0.3
            if self._x > 5:  # Looking right, left eye grows
                self.left_eye.height_next = self.left_eye.height_default * (1 + look_amount)
            elif self._x < -5:  # Looking left, right eye grows
                self.right_eye.height_next = self.right_eye.height_default * (1 + look_amount)
            else:
                self.left_eye.height_next = self.left_eye.height_default
                self.right_eye.height_next = self.right_eye.height_default

        # Geometry tweening
        self.left_eye.width = self._tween(self.left_eye.width, self.left_eye.width_next)
        self.left_eye.height = self._tween(self.left_eye.height, self.left_eye.height_next)
        self.left_eye.border_radius = self._tween(self.left_eye.border_radius, self.left_eye.border_radius_next)

        self.right_eye.width = self._tween(self.right_eye.width, self.right_eye.width_next)
        self.right_eye.height = self._tween(self.right_eye.height, self.right_eye.height_next)
        self.right_eye.border_radius = self._tween(self.right_eye.border_radius, self.right_eye.border_radius_next)

    def _update_sweat(self):
        """Update sweat drop animation."""
        if not self._sweat:
            return

        for i in range(3):
            self._sweat_pos[i] += 1.5
            self._sweat_sizes[i] = 1.0 - (self._sweat_pos[i] / 50) * 0.5

            if self._sweat_pos[i] > 50:
                self._sweat_pos[i] = random.uniform(0, 10)
                self._sweat_sizes[i] = 1.0

    def _draw_eye(self, draw: ImageDraw.ImageDraw, x: float, y: float,
                  width: float, height: float, radius: float,
                  is_left: bool = True):
        """Draw a single eye with mood modifications."""
        # Ensure dimensions are valid integers
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)
        radius = int(radius)

        # Skip if too small
        if width < 4 or height < 4:
            return

        radius = min(radius, width // 2, height // 2)

        # Draw main eye shape
        x2 = x + width
        y2 = y + height
        if x2 > x and y2 > y:
            draw.rounded_rectangle([x, y, x2, y2], radius=radius, fill=self.eye_color)

        # Draw mood overlays (only if eye is large enough)
        if height < 20:
            return

        if self._tired:
            # Tired: eyelid drooping from top
            lid_height = int(height * 0.4)
            if is_left:
                points = [
                    (x - 2, y - 2),
                    (x + width + 2, y - 2),
                    (x + width + 2, y + lid_height),
                ]
            else:
                points = [
                    (x - 2, y - 2),
                    (x + width + 2, y - 2),
                    (x - 2, y + lid_height),
                ]
            draw.polygon(points, fill=self.bg_color)

        elif self._angry:
            # Angry: eyelid angled inward (opposite of tired)
            lid_height = int(height * 0.35)
            if is_left:
                points = [
                    (x - 2, y - 2),
                    (x + width + 2, y - 2),
                    (x - 2, y + lid_height),
                ]
            else:
                points = [
                    (x - 2, y - 2),
                    (x + width + 2, y - 2),
                    (x + width + 2, y + lid_height),
                ]
            draw.polygon(points, fill=self.bg_color)

        elif self._happy:
            # Happy: squinted from bottom (smile)
            lid_height = int(height * 0.4)
            lid_y = y + height - lid_height
            y2_overlay = y + height + 2
            if y2_overlay > lid_y:
                draw.rounded_rectangle(
                    [x - 2, lid_y, x + width + 2, y2_overlay],
                    radius=radius,
                    fill=self.bg_color
                )

    def _draw_sweat_drops(self, draw: ImageDraw.ImageDraw, eye_x: float, eye_y: float, eye_height: float):
        """Draw animated sweat drops near the eye."""
        if not self._sweat:
            return

        # Position drops to the right of the right eye
        base_x = eye_x + 10
        base_y = eye_y - 5

        drop_color = (100, 150, 255)  # Light blue

        for i, (pos_y, size) in enumerate(zip(self._sweat_pos, self._sweat_sizes)):
            drop_x = base_x + i * 8
            drop_y = base_y + pos_y

            # Scale drop size
            drop_w = int(4 * size)
            drop_h = int(6 * size)

            if drop_w > 1 and drop_h > 1:
                # Draw teardrop (ellipse + triangle)
                draw.ellipse(
                    [drop_x - drop_w, drop_y, drop_x + drop_w, drop_y + drop_h],
                    fill=drop_color
                )
                # Triangle point
                draw.polygon([
                    (drop_x, drop_y - drop_h // 2),
                    (drop_x - drop_w, drop_y + 2),
                    (drop_x + drop_w, drop_y + 2),
                ], fill=drop_color)

    def update(self) -> Image.Image:
        """
        Update animation state and render a frame.

        Returns:
            PIL Image ready for display
        """
        # Frame rate limiting
        now = time.time()
        elapsed = now - self._last_frame_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)
        self._last_frame_time = time.time()

        # Process behaviors and animations
        self._process_auto_behaviors()
        self._process_animations()
        self._update_geometry()
        self._update_sweat()

        # Create frame
        img = Image.new('RGB', (self.screen_width, self.screen_height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Calculate base positions
        center_x = self.screen_width / 2
        center_y = self.screen_height / 2

        # Apply flicker
        flicker_x = random.randint(-self._h_flicker_amplitude, self._h_flicker_amplitude) if self._h_flicker else 0
        flicker_y = random.randint(-self._v_flicker_amplitude, self._v_flicker_amplitude) if self._v_flicker else 0

        offset_x = self._x + flicker_x
        offset_y = self._y + flicker_y

        if self._cyclops:
            # Single centered eye
            eye_w = self.left_eye.width
            eye_h = self.left_eye.height * self._left_open
            eye_r = self.left_eye.border_radius

            if eye_h > 1:
                ex = center_x - eye_w / 2 + offset_x
                ey = center_y - eye_h / 2 + offset_y
                self._draw_eye(draw, ex, ey, eye_w, eye_h, eye_r, is_left=True)
        else:
            # Two eyes
            total_width = self.left_eye.width + self.space_between + self.right_eye.width
            start_x = center_x - total_width / 2 + offset_x

            # Left eye
            left_h = self.left_eye.height * self._left_open
            if left_h > 1:
                left_y = center_y - left_h / 2 + offset_y
                self._draw_eye(
                    draw, start_x, left_y,
                    self.left_eye.width, left_h, self.left_eye.border_radius,
                    is_left=True
                )

            # Right eye
            right_x = start_x + self.left_eye.width + self.space_between
            right_h = self.right_eye.height * self._right_open
            if right_h > 1:
                right_y = center_y - right_h / 2 + offset_y
                self._draw_eye(
                    draw, right_x, right_y,
                    self.right_eye.width, right_h, self.right_eye.border_radius,
                    is_left=False
                )

                # Sweat drops (near right eye)
                if self._sweat:
                    self._draw_sweat_drops(draw, right_x + self.right_eye.width, right_y, right_h)

        return img

    def get_frame(self) -> Image.Image:
        """Alias for update()."""
        return self.update()

    # ========== Getters ==========

    def get_screen_constraint_x(self) -> float:
        """Get maximum X offset for eye movement."""
        return self._max_x

    def get_screen_constraint_y(self) -> float:
        """Get maximum Y offset for eye movement."""
        return self._max_y
