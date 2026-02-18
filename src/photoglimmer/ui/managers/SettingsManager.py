# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# Reposnible for actual reading  and writing  of Preferences/Settings 
# Is used by multiple ui components to read settings , and also by preference Dialog
# MRU file list is also stored in settings ,  so this is used every time a file is opened
# Note : Settings are a Qt thing. Backend does not access any settings variable at any point
#        UI reads settings and may use them as parameter for calling some function in backend 
# ######################################################################################    
import os
from PySide6.QtCore import QSettings, QStandardPaths

class SettingsManager:
    """
    Centralized Configuration Handler.
    Implements 'Cached State': Loads from disk at startup, serves from RAM thereafter.
    """
    # --- KEYS ---
    KEY_THEME = "app/theme"
    KEY_OPEN_MODE = "paths/open_mode"       
    KEY_OPEN_CUSTOM = "paths/open_custom"   
    KEY_SAVE_MODE = "paths/save_mode"       
    KEY_SAVE_CUSTOM = "paths/save_custom"
    KEY_JPEG_QUALITY = "export/jpeg_quality"
    KEY_UNDO_LIMIT = "performance/undo_limit"
    KEY_RECENT_FILES = "history/recent_files"

    # --- MODES ---
    MODE_LAST_USED = "Last Used"
    MODE_PICTURES = "Pictures Folder"
    MODE_HOME = "Home Folder"
    MODE_CUSTOM = "Custom Folder"
    MODE_SOURCE = "Same as Original Image"

    # --- DEFAULTS ---
    DEFAULTS = {
        KEY_THEME: "Dark",
        KEY_OPEN_MODE: MODE_LAST_USED,
        KEY_OPEN_CUSTOM: "",
        KEY_SAVE_MODE: MODE_SOURCE,
        KEY_SAVE_CUSTOM: "",
        KEY_JPEG_QUALITY: 95,
        KEY_UNDO_LIMIT: 20,
        KEY_RECENT_FILES: []
    }

    def __init__(self):
        self.settings = QSettings("Photoglimmer", "PhotoEditor")
        
        # === THE CACHE (Your "Global Variables") ===
        # We load everything into public attributes for direct, fast access.
        self.theme = "Dark"
        self.jpeg_quality = 95
        self.undo_limit = 20
        self.open_path_hint = ""  # The resolved path string
        self.save_path_mode = ""  # We store the mode, resolving path dynamically
        self.save_custom_path = ""
        self.recent_files = []

        # Load immediately on instantiation
        self.load_from_disk()

    
    # hardened 
    def load_from_disk(self):
        """Called at Startup or Cancel."""
        
        # 1. Load Strings (Safe, QSettings handles defaults)
        self.theme = str(self._get_raw(self.KEY_THEME))
        self.save_path_mode = str(self._get_raw(self.KEY_SAVE_MODE))
        self.save_custom_path = str(self._get_raw(self.KEY_SAVE_CUSTOM))

        # 2. Load Integers (VULNERABLE - NEEDS TRY/EXCEPT)
        try:
            self.jpeg_quality = int(self._get_raw(self.KEY_JPEG_QUALITY))
        except (ValueError, TypeError):
            self.jpeg_quality = self.DEFAULTS[self.KEY_JPEG_QUALITY] # Fallback
            
        try:
            self.undo_limit = int(self._get_raw(self.KEY_UNDO_LIMIT))
        except (ValueError, TypeError):
            self.undo_limit = self.DEFAULTS[self.KEY_UNDO_LIMIT]

        # 3. Load Lists
        self.recent_files = self._get_raw(self.KEY_RECENT_FILES, type_cast=list)

        # 4. Logic (Safe, relies on internal methods)
        self.open_path_hint = self._resolve_open_dir()
        

    def save_to_disk(self):
        """Called when user clicks 'Save' in Preferences."""
        self.settings.setValue(self.KEY_THEME, self.theme)
        self.settings.setValue(self.KEY_JPEG_QUALITY, self.jpeg_quality)
        self.settings.setValue(self.KEY_UNDO_LIMIT, self.undo_limit)
        
        # Note: Directory Modes are updated via specialized setters below, 
        # or you can manually sync them here if you bind them to attributes.
        
        # Update the RAM cache for paths immediately
        self.open_path_hint = self._resolve_open_dir()

    # --- INTERNAL HELPERS ---
    def _get_raw(self, key, type_cast=None):
        val = self.settings.value(key, self.DEFAULTS.get(key))
        if type_cast is list and not isinstance(val, list):
            return []
        return val

    def _resolve_open_dir(self):
        mode = self._get_raw(self.KEY_OPEN_MODE)
        if mode == self.MODE_PICTURES:
            return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        elif mode == self.MODE_HOME:
            return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation)
        elif mode == self.MODE_CUSTOM:
            custom = self._get_raw(self.KEY_OPEN_CUSTOM)
            return custom if custom and os.path.isdir(custom) else ""
        return "" # Last Used

    # --- DYNAMIC RESOLVER (Cannot be cached purely) ---
    def get_save_directory(self, source_image_path=None):
        """
        Calculates save path using the Cached Settings.
        """
        #print(f"saving with source path {source_image_path} ")
        if self.save_path_mode == self.MODE_SOURCE and source_image_path:
            return os.path.dirname(source_image_path)
        
        elif self.save_path_mode == self.MODE_PICTURES:
            return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        
        elif self.save_path_mode == self.MODE_CUSTOM:
            if self.save_custom_path and os.path.isdir(self.save_custom_path):
                return self.save_custom_path
                
        return "" 

    # --- MRU SETTERS (Must write to disk immediately) ---
    def add_recent_file(self, path):
        # Update RAM
        path = os.path.abspath(path)
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
        
        # Sync to Disk
        self.settings.setValue(self.KEY_RECENT_FILES, self.recent_files)

    def clear_recent_files(self):
        self.recent_files = []
        self.settings.setValue(self.KEY_RECENT_FILES, self.recent_files)

