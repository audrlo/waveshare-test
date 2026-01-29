"""
WaveshareDisplay - Display driver for Waveshare 2" LCD Module
Add this to your roboeyes.py or import it separately.

This wraps the Waveshare LCD_Module_RPI_code library to work with RoboEyes.
"""

from PIL import Image


class WaveshareDisplay:
    """
    Display driver for Waveshare 2" LCD Module (ST7789VW).
    
    Requires the Waveshare LCD_Module_RPI_code to be installed.
    
    Usage:
        # Make sure you're in the right directory or have the lib folder in path
        import sys
        sys.path.append('/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')
        
        from waveshare_display import WaveshareDisplay
        display = WaveshareDisplay()
        display.show(pil_image)
    """
    
    def __init__(
        self,
        width: int = 240,
        height: int = 320,
        rotation: int = 180,  # Waveshare typically needs 180 rotation
        backlight: int = 50,   # Backlight duty cycle (0-100)
        rst: int = 27,
        dc: int = 25,
        bl: int = 18
    ):
        self.width = width
        self.height = height
        self.rotation = rotation
        
        try:
            # Try to import Waveshare library
            from lib import LCD_2inch
        except ImportError:
            # If not in path, try adding the common location
            import sys
            sys.path.insert(0, '/home/sam-pi/LCD_Module_RPI_code/RaspberryPi/python')
            try:
                from lib import LCD_2inch
            except ImportError:
                raise ImportError(
                    "Waveshare LCD library not found. Make sure LCD_Module_RPI_code "
                    "is installed and the lib folder is in your Python path.\n"
                    "Try: sys.path.append('/path/to/LCD_Module_RPI_code/RaspberryPi/python')"
                )
        
        # Initialize display
        self.lcd = LCD_2inch.LCD_2inch(rst=rst, dc=dc, bl=bl)
        self.lcd.Init()
        self.lcd.clear()
        self.lcd.bl_DutyCycle(backlight)
    
    def show(self, image: Image.Image):
        """Display a PIL Image on the screen."""
        # Resize if needed
        if image.size != (self.width, self.height):
            # Check if dimensions are swapped (landscape vs portrait)
            if image.size == (self.height, self.width):
                image = image.transpose(Image.ROTATE_90)
            else:
                image = image.resize((self.width, self.height))
        
        # Apply rotation
        if self.rotation != 0:
            image = image.rotate(self.rotation)
        
        # Send to display
        self.lcd.ShowImage(image)
    
    def clear(self):
        """Clear the display."""
        self.lcd.clear()
    
    def set_backlight(self, value: int):
        """Set backlight brightness (0-100)."""
        self.lcd.bl_DutyCycle(value)
    
    def cleanup(self):
        """Clean up GPIO on exit."""
        self.lcd.module_exit()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except:
            pass
