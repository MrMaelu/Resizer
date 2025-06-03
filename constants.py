import os
import sys

if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = os.path.join(BASE_PATH, "configs")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0