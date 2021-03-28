from m5 import display
from fonts import vga2_bold_16x32 as font_big
from fonts import vga1_8x8 as font_little
import time

VERSION = "0.0.1"

BACKGROUND = 0x0000ff
FOREGROUND = 0x00ff00

display.fill(BACKGROUND)
display.off()
display.on()
display.rotation(1)
display.text(font_big, "embit", 5, 5, FOREGROUND, BACKGROUND)
display.text(font_little, "on esp32", 5, 40, FOREGROUND, BACKGROUND)
display.text(font_little, "version "+VERSION, 5, 120, FOREGROUND, BACKGROUND)
time.sleep(1)
execfile('hww.py')
