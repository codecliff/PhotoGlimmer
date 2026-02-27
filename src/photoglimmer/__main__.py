# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# The entry point of our application  responsible for safely launching MainWindow
# Also handles showing of splash screen 

import sys, time 
import logging

# Only import what is strictly needed to show the Splash Screen
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QElapsedTimer, QTimer
from pathlib import Path

from .backend.LoggerSetup import setup_session_logging
from .ui.components.SplashScreen import SplashScreen

# [CHANGE] Import version info (Lightweight, so safe to import here)
from .backend.Interfaces import APP_NAME, APP_VERSION



import os
from pathlib import Path

import os
from importlib import resources
from PySide6.QtGui import QFontDatabase

def load_embedded_fonts():
    """Load fonts from  this source code location. We carry our own fonts, on all platforms"""
    # 1. Access the 'assets.fonts' sub-package within your 'photoglimmer' package
    try:
        # This returns a traversable path to the fonts directory
        font_dir = resources.files("photoglimmer") / "assets" / "fonts"
        
        if not font_dir.is_dir():
            return

        for font_file in font_dir.glob("*.ttf"):
            # Register the font with Qt's internal database
            # We use str() because Qt expects a file path string
            QFontDatabase.addApplicationFont(str(font_file))
            
    except Exception as e:
        print(f"Warning: Could not load embedded fonts: {e}")

# Call this immediately after creating   QApplication
# app = QApplication(sys.argv)
# load_embedded_fonts()


def sanitize_image_path(raw_path: str):
    """
    Validates and normalizes a command-line file path.
    Returns: Absolute string path if valid, else None.
    """
    if not raw_path: 
        return None
        
    try:
        # 1. Resolve to Absolute Path
        path_obj = Path(raw_path).resolve()
        path_str = str(path_obj)

        # 2. Path Length Check (Critical for Windows/OpenCV)
        # Standard max safe length is 260. We use 255 to be safe.        
        # older C standard libraries that still have this limit.
        if len(path_str) > 255 and os.name == 'nt':
            print(f"Warning: Path too long (>255 chars). OpenCV may fail: {path_str[:50]}...")
            return None
            
        # 3. Existence Check
        if not path_obj.exists():
            print(f"Warning: File not found: {raw_path}")
            return None
            
        # 4. File Type Check
        if not path_obj.is_file():
            print(f"Warning: Path is not a file: {raw_path}")
            return None
            
        # 5. Extension Check
        valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        if path_obj.suffix.lower() not in valid_exts:
            print(f"Warning: Unsupported file extension: {path_obj.name}")
            return None
            
        return path_str
        
    except Exception as e:
        print(f"Error validating path: {e}")
        return None
    
    

def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.resolve()
    return base_path / relative_path

def main():
    # 0. Display version 
    # Check for version flag manually (we aren't using argparse for now)
    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"{APP_NAME} {APP_VERSION}")
        sys.exit(0)

    # 1. LIGHTWEIGHT STARTUP
    logger = setup_session_logging("Photoglimmer")
    sys.excepthook = lambda cls, exc, tb: logger.critical("Uncaught exception", exc_info=(cls, exc, tb))

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    load_embedded_fonts()
    
    icon_path = get_resource_path("icons/appicon-64.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 2. SHOW SPLASH IMMEDIATELY
    splash_path = get_resource_path("assets/splash.png")
    # print(f"splash_path: {splash_path}") # Optional debug print

    splash = SplashScreen(splash_path)
    splash.center_on_screen()
    splash.show()
    
    # CRITICAL: We Yield a bit to  paint the splash BEFORE we load heavy libs
    # 10 processEvents and 10 wakeups give a good chance of being awake when OS offers you a handle to paint area
    for _ in range(10):
        app.processEvents()
        time.sleep(0.01)

    timer = QElapsedTimer()
    timer.start()

    try:
        # 3. HEAVY LOADING (Lazy Imports)
        logger.info("Loading heavy modules...")
        
        from .ui.managers.SettingsManager import SettingsManager
        from .ui.managers.ThemeManager import ThemeManager
        from .ui.MainWindow import MainWindow
        
        # Load Theme
        try:
            temp_settings = SettingsManager()
            initial_theme = temp_settings.theme
        except:
            initial_theme = "Dark"
        ThemeManager.apply_theme(app, initial_theme)

        # Parse Args for Image Path
        # We take the first argument that DOESN'T start with '-'
        initial_image_path = None
        
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                # Ignore flags like -v or --debug
                if arg.startswith("-"):
                    continue
                    
                # Sanitize the potential path
                clean_path = sanitize_image_path(arg)
                
                if clean_path:
                    initial_image_path = clean_path
                    break # Stop after finding the first valid image
                else:
                    print("Ignoring invalid path")

        # Initialize Window
        window = MainWindow(image_path=initial_image_path)

        # Initialize Window (Triggers backend/Mediapipe initialization)
        window = MainWindow(image_path=initial_image_path)
        
        # 4. TRANSITION
        elapsed = timer.elapsed()
        min_display_time = 3000 
        remaining_wait = max(0, min_display_time - elapsed)

        def start_app():
            window.show()
            # Fade out splash after window is shown
            QTimer.singleShot(200, splash.finish)

        QTimer.singleShot(remaining_wait, start_app)

        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Fatal startup error: {e}", exc_info=True)
        sys.exit(1)



if __name__ == "__main__":
    main()

