"""
Display drivers for RoboEyes.
Supports Waveshare LCD modules and mock display for testing.
"""

from typing import Optional
from PIL import Image


class WaveshareDisplay:
    """
    Display driver for Waveshare 2" LCD Module (ST7789VW).

    Requires the Waveshare LCD_Module_RPI_code library to be installed.

    Usage:
        display = WaveshareDisplay()
        display.show(pil_image)
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
        lib_path: Optional[str] = None
    ):
        """
        Initialize Waveshare display.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            rotation: Display rotation (0, 90, 180, 270)
            backlight: Backlight brightness (0-100)
            rst: GPIO pin for reset
            dc: GPIO pin for data/command
            bl: GPIO pin for backlight
            lib_path: Path to Waveshare library (auto-detected if None)
        """
        self.width = width
        self.height = height
        self.rotation = rotation

        # Try to import Waveshare library
        LCD_2inch = self._import_waveshare_lib(lib_path)

        # Initialize display
        self.lcd = LCD_2inch.LCD_2inch(rst=rst, dc=dc, bl=bl)
        self.lcd.Init()
        self.lcd.clear()
        self.lcd.bl_DutyCycle(backlight)

    def _import_waveshare_lib(self, lib_path: Optional[str]):
        """Import the Waveshare LCD library."""
        import sys

        # Try direct import first
        try:
            from lib import LCD_2inch
            return LCD_2inch
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
                from lib import LCD_2inch
                return LCD_2inch
            except ImportError:
                continue

        raise ImportError(
            "Waveshare LCD library not found. Make sure LCD_Module_RPI_code "
            "is installed. You can specify the path with lib_path parameter.\n"
            "Example: WaveshareDisplay(lib_path='/path/to/LCD_Module_RPI_code/RaspberryPi/python')"
        )

    def show(self, image: Image.Image):
        """Display a PIL Image on the screen."""
        # Handle size mismatch
        if image.size != (self.width, self.height):
            if image.size == (self.height, self.width):
                # Dimensions swapped - rotate
                image = image.transpose(Image.Transpose.ROTATE_90)
            else:
                # Resize to fit
                image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # Apply rotation if needed
        if self.rotation == 90:
            image = image.transpose(Image.Transpose.ROTATE_90)
        elif self.rotation == 180:
            image = image.transpose(Image.Transpose.ROTATE_180)
        elif self.rotation == 270:
            image = image.transpose(Image.Transpose.ROTATE_270)

        # Send to display
        self.lcd.ShowImage(image)

    def clear(self):
        """Clear the display to black."""
        self.lcd.clear()

    def set_backlight(self, value: int):
        """
        Set backlight brightness.

        Args:
            value: Brightness level 0-100
        """
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


class MockDisplay:
    """
    Mock display for testing without hardware.

    Stores the last frame for inspection but doesn't display anything.
    Useful for development and testing on non-Pi systems.
    """

    def __init__(self, width: int = 240, height: int = 320):
        """
        Initialize mock display.

        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height
        self.last_frame: Optional[Image.Image] = None
        self.frame_count = 0

    def show(self, image: Image.Image):
        """Store the frame (doesn't actually display)."""
        self.last_frame = image.copy()
        self.frame_count += 1

    def clear(self):
        """Clear stored frame."""
        self.last_frame = None

    def set_backlight(self, value: int):
        """No-op for mock display."""
        pass

    def cleanup(self):
        """No-op for mock display."""
        pass

    def save_frame(self, path: str):
        """
        Save the last frame to a file (useful for debugging).

        Args:
            path: File path to save to (e.g., 'frame.png')
        """
        if self.last_frame:
            self.last_frame.save(path)


class PreviewDisplay:
    """
    Display that shows frames in a desktop window.

    Useful for development on desktop systems.
    Requires a display environment (won't work over SSH without X forwarding).
    """

    def __init__(self, width: int = 240, height: int = 320, scale: int = 2):
        """
        Initialize preview display.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            scale: Scale factor for the preview window
        """
        self.width = width
        self.height = height
        self.scale = scale
        self._window_open = False

    def show(self, image: Image.Image):
        """Show the frame in a preview window."""
        if self.scale != 1:
            image = image.resize(
                (self.width * self.scale, self.height * self.scale),
                Image.Resampling.NEAREST
            )
        image.show()

    def clear(self):
        """No-op for preview display."""
        pass

    def set_backlight(self, value: int):
        """No-op for preview display."""
        pass

    def cleanup(self):
        """No-op for preview display."""
        pass
