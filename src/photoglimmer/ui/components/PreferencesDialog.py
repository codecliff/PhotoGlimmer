# ######################################################################################
# Preference / Settings Dialog Box 
# Dumb UI 
# Actual Read/write of settings is managed by SettingsManager  
# ######################################################################################

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QSpinBox, QLineEdit, QPushButton, 
                               QFileDialog, QGroupBox, QFormLayout, QSlider, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from ..managers.SettingsManager import SettingsManager

class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self.setWindowOpacity(0.95)


        self.setModal(True)
        self.resize(550, 450)
        self.settings = SettingsManager()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # --- 1. GENERAL (Theme & Import) ---
        grp_general = QGroupBox("General & Import")
        form_general = QFormLayout()
        
        # Theme
        self.combo_theme = QComboBox()
        #self.combo_theme.addItems(["Dark", "Light"])
        from ..managers.ThemeManager import ThemeManager
        self.combo_theme.addItems(list(ThemeManager.PALETTES.keys()))
        
        
        self.combo_theme.setCurrentText(self.settings.theme)
        form_general.addRow("Theme:", self.combo_theme)

        # Import Directory Mode
        self.combo_open_mode = QComboBox()
        self.combo_open_mode.addItems([
            SettingsManager.MODE_LAST_USED,
            SettingsManager.MODE_PICTURES,
            SettingsManager.MODE_HOME,
            SettingsManager.MODE_CUSTOM
        ])
        # read raw mode string
        current_open_mode = self._get_current_value(SettingsManager.KEY_OPEN_MODE)
        self.combo_open_mode.setCurrentText(current_open_mode)
        self.combo_open_mode.currentTextChanged.connect(self._toggle_open_custom)
        form_general.addRow("Default Open Location:", self.combo_open_mode)

        # Import Custom Widget (Hidden by default)
        current_open_custom = self._get_current_value(SettingsManager.KEY_OPEN_CUSTOM)
        self.wid_open_custom = self._create_path_picker(current_open_custom)
        form_general.addRow("   ↳ Custom Path:", self.wid_open_custom)
        
        grp_general.setLayout(form_general)
        layout.addWidget(grp_general)

        # --- 2. EXPORT SETTINGS ---
        grp_export = QGroupBox("Export Settings")
        form_export = QFormLayout()

        # Save Directory Mode
        self.combo_save_mode = QComboBox()
        self.combo_save_mode.addItems([
            SettingsManager.MODE_SOURCE,
            SettingsManager.MODE_LAST_USED,
            SettingsManager.MODE_PICTURES,
            SettingsManager.MODE_CUSTOM
        ])
        
        current_save_mode = self._get_current_value(SettingsManager.KEY_SAVE_MODE)
        self.combo_save_mode.setCurrentText(current_save_mode)
        self.combo_save_mode.currentTextChanged.connect(self._toggle_save_custom)
        form_export.addRow("Default Save Location:", self.combo_save_mode)

        # Save Custom Widget
        current_save_custom = self._get_current_value(SettingsManager.KEY_SAVE_CUSTOM)
        self.wid_save_custom = self._create_path_picker(current_save_custom)
        form_export.addRow("   ↳ Custom Path:", self.wid_save_custom)

        # JPEG Quality (Slider + Spinner)
        qual_layout = QHBoxLayout()
        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(85, 100)
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(85, 100)
        
        # Sync Slider <-> Spinner
        self.slider_quality.valueChanged.connect(self.spin_quality.setValue)
        self.spin_quality.valueChanged.connect(self.slider_quality.setValue)
        
        # Set Value (Use attribute)
        self.slider_quality.setValue(self.settings.jpeg_quality)
        
        qual_layout.addWidget(self.slider_quality)
        qual_layout.addWidget(self.spin_quality)
        form_export.addRow("JPEG Quality:", qual_layout)
        
        # Undo Limit
        self.spin_undo = QSpinBox()
        self.spin_undo.setRange(1, 100)
        self.spin_undo.setValue(self.settings.undo_limit)
        form_export.addRow("Max Undo Levels:", self.spin_undo)

        grp_export.setLayout(form_export)
        layout.addWidget(grp_export)

        # --- 3. ACTIONS ---
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("BtnDialogOK")
        self.btn_save.clicked.connect(self.validate_and_save)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Initial Toggle State
        self._toggle_open_custom(self.combo_open_mode.currentText())
        self._toggle_save_custom(self.combo_save_mode.currentText())

    def _get_current_value(self, key):
        """
        Helper to read raw values from QSettings, respecting Defaults.
        Needed because SettingsManager attributes only store resolved paths, 
        not the 'Mode' strings.
        """
        default = SettingsManager.DEFAULTS.get(key)
        val = self.settings.settings.value(key, default)
        return str(val)

    def _create_path_picker(self, default_text):
        """Helper to create the LineEdit+Browse combo"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        
        line_edit = QLineEdit(default_text)
        btn = QPushButton("Browse")
        btn.clicked.connect(lambda: self._browse_folder(line_edit))
        
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        
        # Store refs dynamically so we can access them later
        widget.line_edit = line_edit 
        return widget

    def _browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)

    def _toggle_open_custom(self, text):
        self.wid_open_custom.setVisible(text == SettingsManager.MODE_CUSTOM)

    def _toggle_save_custom(self, text):
        self.wid_save_custom.setVisible(text == SettingsManager.MODE_CUSTOM)

    def validate_and_save(self):
        # 1. Validate Custom Paths (only if mode is Custom)
        if self.combo_open_mode.currentText() == SettingsManager.MODE_CUSTOM:
            path = self.wid_open_custom.line_edit.text()
            if not os.path.isdir(path) or not os.access(path, os.R_OK):
                QMessageBox.warning(self, "Invalid Path", "The Custom Open directory does not exist or is not readable.")
                return

        if self.combo_save_mode.currentText() == SettingsManager.MODE_CUSTOM:
            path = self.wid_save_custom.line_edit.text()
            if not os.path.isdir(path) or not os.access(path, os.W_OK):
                QMessageBox.warning(self, "Invalid Path", "The Custom Save directory does not exist or is not writable.")
                return

        # 2. Update RAM Attributes (Fast Access)
        self.settings.theme = self.combo_theme.currentText()
        self.settings.jpeg_quality = self.spin_quality.value()
        self.settings.undo_limit = self.spin_undo.value()

        # 3. Update Raw Settings (Modes & Paths)
        self.settings.settings.setValue(SettingsManager.KEY_OPEN_MODE, self.combo_open_mode.currentText())
        self.settings.settings.setValue(SettingsManager.KEY_OPEN_CUSTOM, self.wid_open_custom.line_edit.text())
        
        self.settings.settings.setValue(SettingsManager.KEY_SAVE_MODE, self.combo_save_mode.currentText())
        self.settings.settings.setValue(SettingsManager.KEY_SAVE_CUSTOM, self.wid_save_custom.line_edit.text())
        
        # 4. Commit to Disk
        self.settings.save_to_disk()
        
        self.accept()
