
# preferences_dialog.py
import sys
import os
from PySide2.QtWidgets import (QApplication, QDialog, QFileDialog, QMessageBox,
                               QWidget, QRadioButton, QVBoxLayout,
                               QDialogButtonBox)
from PySide2.QtCore import QFile, QSettings, QStandardPaths, Slot
from PySide2.QtUiTools import QUiLoader
# --- Import the configuration ---
#standard way of importing form same package  is to add . prefix
from .settings_config import SettingsConfig


class  PreferencesDialog(QDialog):


    def  __init__(self, parent=None):
        super().__init__(parent)
        # ... (UI Loading remains the same) ...
        ui_file_path = os.path.join(os.path.dirname(__file__), "preferences.ui")
        loader = QUiLoader()
        ui_file = QFile(ui_file_path)
        if not ui_file.open(QFile.ReadOnly):
            raise IOError(f"Could not open UI file: {ui_file.errorString()}")
        self.ui = loader.load(ui_file)
        ui_file.close()
        if not self.ui:
             raise RuntimeError(f"Failed to load UI from {ui_file_path}")
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)
        self.setWindowTitle(self.ui.windowTitle())
        self.resize(self.ui.size())
        self.settings = QSettings(SettingsConfig.ORGANIZATION_NAME,
                                  SettingsConfig.APPLICATION_NAME)
        self.load_settings()
        self.ui.browseButton.clicked.connect(self.browse_custom_folder)
        self.ui.picturesRadio.toggled.connect(self.update_custom_folder_state)
        self.ui.homeRadio.toggled.connect(self.update_custom_folder_state)
        self.ui.lastRadio.toggled.connect(self.update_custom_folder_state)
        self.ui.customRadio.toggled.connect(self.update_custom_folder_state)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.accepted.connect(self.save_settings)
        reset_button = self.ui.buttonBox.button(QDialogButtonBox.RestoreDefaults)
        if reset_button:
            reset_button.clicked.connect(self.reset_to_defaults)
        self.update_custom_folder_state()


    def  load_settings(self):
        print("Loading settings...")
        try:
            dialog_type = self.settings.value(
                SettingsConfig.Keys.FILE_DIALOG_TYPE,
                SettingsConfig.Defaults.FILE_DIALOG_TYPE, str
            )
            if dialog_type == SettingsConfig.FileDialogType.APPLICATION:
                self.ui.appRadio.setChecked(True)
            else:
                self.ui.systemRadio.setChecked(True)
            denoise = self.settings.value(
                SettingsConfig.Keys.DENOISE_ENABLED,
                SettingsConfig.Defaults.DENOISE_ENABLED, bool
            )
            self.ui.denoiseCheck.setChecked(denoise)
            custom_path = self.settings.value(
                SettingsConfig.Keys.START_FOLDER_CUSTOM_PATH,
                SettingsConfig.Defaults.START_FOLDER_CUSTOM_PATH, str
            )
            self.ui.customPathEdit.setText(custom_path)
            folder_choice = self.settings.value(
                SettingsConfig.Keys.START_FOLDER_CHOICE,
                SettingsConfig.Defaults.START_FOLDER_CHOICE, str
            )
            if folder_choice == SettingsConfig.StartFolderChoice.HOME:
                self.ui.homeRadio.setChecked(True)
            elif folder_choice == SettingsConfig.StartFolderChoice.LAST_OPENED:
                self.ui.lastRadio.setChecked(True)
            elif folder_choice == SettingsConfig.StartFolderChoice.CUSTOM:
                self.ui.customRadio.setChecked(True)
            else: 
                self.ui.picturesRadio.setChecked(True)
            brightness_mode = self.settings.value(
                SettingsConfig.Keys.BRIGHTNESS_MODE,
                SettingsConfig.Defaults.BRIGHTNESS_MODE, str
            )
            if brightness_mode == SettingsConfig.BrightnessMode.COLOR_CURVE:
                self.ui.curveRadio.setChecked(True)
            else: 
                self.ui.slidersRadio.setChecked(True)
            print("Settings loaded.")
            self.update_custom_folder_state()
        except Exception as e:
            print(f"Error loading settings: {e}")


    def  save_settings(self):
        print("Saving settings...")
        try:
            dialog_type = (SettingsConfig.FileDialogType.APPLICATION if self.ui.appRadio.isChecked()
                           else SettingsConfig.FileDialogType.SYSTEM)
            self.settings.setValue(SettingsConfig.Keys.FILE_DIALOG_TYPE, dialog_type)
            self.settings.setValue(SettingsConfig.Keys.DENOISE_ENABLED, self.ui.denoiseCheck.isChecked())
            folder_choice = SettingsConfig.StartFolderChoice.PICTURES 
            if self.ui.homeRadio.isChecked():
                folder_choice = SettingsConfig.StartFolderChoice.HOME
            elif self.ui.lastRadio.isChecked():
                folder_choice = SettingsConfig.StartFolderChoice.LAST_OPENED
            elif self.ui.customRadio.isChecked():
                folder_choice = SettingsConfig.StartFolderChoice.CUSTOM
            self.settings.setValue(SettingsConfig.Keys.START_FOLDER_CHOICE, folder_choice)
            self.settings.setValue(SettingsConfig.Keys.START_FOLDER_CUSTOM_PATH, self.ui.customPathEdit.text())
            brightness_mode = (SettingsConfig.BrightnessMode.COLOR_CURVE if self.ui.curveRadio.isChecked()
                               else SettingsConfig.BrightnessMode.SLIDERS)
            self.settings.setValue(SettingsConfig.Keys.BRIGHTNESS_MODE, brightness_mode)
            print("Settings saved.")
        except Exception as e:
             print(f"Error saving settings: {e}")
    @Slot()


    def  reset_to_defaults(self):
        print("Resetting settings to defaults in UI...")
        try:
            if SettingsConfig.Defaults.FILE_DIALOG_TYPE == SettingsConfig.FileDialogType.APPLICATION:
                 self.ui.appRadio.setChecked(True)
            else:
                 self.ui.systemRadio.setChecked(True)
            self.ui.denoiseCheck.setChecked(SettingsConfig.Defaults.DENOISE_ENABLED)
            self.ui.customPathEdit.setText(SettingsConfig.Defaults.START_FOLDER_CUSTOM_PATH)
            if SettingsConfig.Defaults.START_FOLDER_CHOICE == SettingsConfig.StartFolderChoice.HOME:
                self.ui.homeRadio.setChecked(True)
            elif SettingsConfig.Defaults.START_FOLDER_CHOICE == SettingsConfig.StartFolderChoice.LAST_OPENED:
                self.ui.lastRadio.setChecked(True)
            elif SettingsConfig.Defaults.START_FOLDER_CHOICE == SettingsConfig.StartFolderChoice.CUSTOM:
                self.ui.customRadio.setChecked(True)
            else: 
                self.ui.picturesRadio.setChecked(True)
            self.update_custom_folder_state()
            if SettingsConfig.Defaults.BRIGHTNESS_MODE == SettingsConfig.BrightnessMode.COLOR_CURVE:
                self.ui.curveRadio.setChecked(True)
            else: 
                self.ui.slidersRadio.setChecked(True)
            print("UI reset to defaults.")
        except Exception as e:
             print(f"Error resetting UI: {e}")
    @Slot()


    def  browse_custom_folder(self):
        current_path = self.ui.customPathEdit.text()
        if not current_path or not os.path.isdir(current_path):
            current_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Custom Start Folder", current_path
        )
        if folder_path:
            self.ui.customPathEdit.setText(folder_path)
    @Slot()


    def  update_custom_folder_state(self):
        try:
            is_custom = self.ui.customRadio.isChecked()
            self.ui.customPathEdit.setEnabled(is_custom)
            self.ui.browseButton.setEnabled(is_custom)
        except AttributeError:
            pass 