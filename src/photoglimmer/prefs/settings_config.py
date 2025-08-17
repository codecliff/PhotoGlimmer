
# settings_config.py
from PySide6.QtCore import QStandardPaths


class  SettingsConfig:
    # --- QSettings Identification ---
    ORGANIZATION_NAME = "Codecliff"
    APPLICATION_NAME = "PhotoGlimmer"


    class  Keys:
        FILE_DIALOG_TYPE = "fileOpenDialog/type"
        DENOISE_ENABLED = "denoise/enabled"
        START_FOLDER_CHOICE = "startFolder/choice"
        START_FOLDER_CUSTOM_PATH = "startFolder/customPath"
        BRIGHTNESS_MODE = "brightness/mode"
        LAST_OPENED_PATH = "paths/lastOpened"


    class  FileDialogType:
        SYSTEM = "System"
        APPLICATION = "Application"


    class  StartFolderChoice:
        PICTURES = "Pictures"
        HOME = "Home"
        LAST_OPENED = "Last"
        CUSTOM = "Custom"


    class  BrightnessMode:
        SLIDERS = "Sliders"
        COLOR_CURVE = "Color Curve"


    class  Defaults:
        FILE_DIALOG_TYPE = "System"
        DENOISE_ENABLED = False
        START_FOLDER_CHOICE = "Pictures"
        START_FOLDER_CUSTOM_PATH = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        BRIGHTNESS_MODE = "Sliders"
        LAST_OPENED_PATH = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)