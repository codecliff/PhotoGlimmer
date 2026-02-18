# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# Setting up logging for out application
# Log level is best setup in __main.py__
# #######################################################################

import logging
import os
import sys
import platform
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_session_logging(app_name="Photoglimmer"):
    """
    Sets up logging to OS-standard user directories.
    """
    home = Path.home()
    system = platform.system()

    # 1. Determine the Correct OS Path
    if system == "Windows":
        # C:\Users\<User>\AppData\Local\Photoglimmer\Logs
        base_path = Path(os.getenv("LOCALAPPDATA")) / app_name / "Logs"
    
    elif system == "Darwin": #(macOS)
        # ~/Library/Logs/Photoglimmer
        base_path = home / "Library" / "Logs" / app_name
    
    else: # Linux / Unix
        # ~/.local/share/photoglimmer/logs
        # Uses XDG standard if available, defaults to .local/share
        xdg_data = os.getenv("XDG_DATA_HOME", home / ".local" / "share")
        base_path = Path(xdg_data) / app_name.lower() / "logs"

    # 2. Ensure Directory Exists
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        log_file = base_path / f"{app_name}.log"
    except PermissionError:
        # Fallback to temp if permissions are broken
        import tempfile
        base_path = Path(tempfile.gettempdir())
        log_file = base_path / f"{app_name}.log"

    # 3. Configure Logger
    # Use getLogger() without arguments to grab the Root Logger.
    # This ensures logs from ANY module in your app are captured.
    logger = logging.getLogger() 
    logger.setLevel(logging.DEBUG)
    # logger.setLevel(logging.WARN)
    
    # Clean existing handlers to prevent duplicate lines if function is called twice
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 4. File Handler (Rotation Strategy)
    # maxBytes=1_000_000 (1MB) -> Prevents huge files
    # backupCount=1 -> Keeps 'app.log' and 'app.log.1'. Older logs are deleted.
    # mode='a' -> Append. (Use mode='w' if you strictly want to wipe on every launch, but 'a' is safer for crash forensics)
    try:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=1*1024*1024, 
            backupCount=1, 
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"CRITICAL: Failed to write logs to {log_file}: {e}", file=sys.stderr)

    # 5. Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO) 
    logger.addHandler(console_handler)

    logger.info(f"--- Session Started ---")
    logger.info(f"Log path: {log_file}")
    
    return logger


