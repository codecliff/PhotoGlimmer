# ######################################################################################
# The LEFT sidebar of our application 
# Displays -- A list of layers, A layer reset button , and A mask preview 
# ######################################################################################

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                               QPushButton, QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap

class Sidebar(QWidget):
    """
    The main Left Dock of the application.
    Contains  A list of layers, A layer reset button , and A mask preview     
    """
    
    # Signals to MainWindow
    layer_selected = Signal(object)      # layer_id
    layer_visibility_toggled = Signal(object, bool) # layer_id, is_visible
    add_layer_clicked = Signal()
    reset_layer_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(300)
        
        # ID for Theme Manager (QSS targeting)
        self.setObjectName("Sidebar")
        
        # Removed hardcoded styles to allow ThemeManager to control appearance
        # self.setStyleSheet("#sidebar_container { color: #AAA; border: 2px solid; } ")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        self._setup_ui()

    def _setup_ui(self):
        # 1. Layer List Section
        self.list_title_label= QLabel("Frames ☰")
        self.list_title_label.setObjectName("SidebTitle")
        #self.list_title_label.setObjectName("CollapsibleHeader")
        self.layout.addWidget(self.list_title_label)
        
        self.layer_list_widget = QListWidget()
        # Handle user clicking a row
        self.layer_list_widget.currentItemChanged.connect(self._on_list_selection)
        # Handle checkbox toggles
        self.layer_list_widget.itemChanged.connect(self._on_item_changed)
        
        self.layout.addWidget(self.layer_list_widget)

        # "Add Layer" button
        # self.btn_add = QPushButton("Add New Layer")
        # self.btn_add.clicked.connect(self.add_layer_clicked.emit)
        # self.layout.addWidget(self.btn_add)

        # --- RESET BUTTON ---
        self.btn_reset = QPushButton("Reset Layer Defaults")
        self.btn_reset.clicked.connect(self.reset_layer_clicked.emit)
        self.layout.addWidget(self.btn_reset)

        
        # 2. Mask Preview Section
        self.mask_title_label= QLabel("Mask 🎭")
        self.mask_title_label.setObjectName("SidebTitle") # commmon name for qss

        self.layout.addWidget(self.mask_title_label)
        self.mask_preview_label = QLabel()
        self.mask_preview_label.setFixedSize(240, 180) 
        
        # ID for Theme Manager
        self.mask_preview_label.setObjectName("MaskPreview")
        
        # Removed hardcoded styles
        # self.mask_preview_label.setStyleSheet(
        #     "border-radius: 5px; border-color: #888A85; background-color: #1A1A1A; margin:2px; padding:5px"
        # )
        
        self.mask_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.mask_preview_label)

        
        
        self.layout.addStretch() 

    # ==========================================
    # PUBLIC API
    # ==========================================

    def set_interface_enabled(self, enabled):
        """Enables/Disables the interactive elements."""
        self.layer_list_widget.setEnabled(enabled)
        # self.btn_add.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)

    def clear_all(self):
        """Clears the list and the preview image."""
        self.layer_list_widget.clear()
        self.mask_preview_label.clear()

    def clear_selection(self):
        """Deselects the current item."""
        self.layer_list_widget.clearSelection()
        self.layer_list_widget.setCurrentItem(None)

    def add_layer_entry(self, layer_id, name, is_visible=True, is_selected=False):
        """Creates a new row in the layer list."""
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, layer_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if is_visible else Qt.CheckState.Unchecked)
        
        self.layer_list_widget.addItem(item)
        
        if is_selected:
            self.layer_list_widget.setCurrentItem(item)

    def select_layer(self, layer_id):
        """Programmatically highlights a row based on Layer ID."""
        self.layer_list_widget.blockSignals(True) # Prevent feedback loop
        
        found = False
        for i in range(self.layer_list_widget.count()):
            item = self.layer_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == layer_id:
                self.layer_list_widget.setCurrentItem(item)
                found = True
                break
        
        if not found:
            self.clear_selection()

        self.layer_list_widget.blockSignals(False)

    def remove_layer_entry(self, layer_id):
        """Removes the row corresponding to the layer ID."""
        for i in range(self.layer_list_widget.count()):
            item = self.layer_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == layer_id:
                self.layer_list_widget.takeItem(i)
                break
        
        # Auto-fallback: If only Background remains, select it
        if self.layer_list_widget.count() == 1:
            self.layer_list_widget.setCurrentRow(0)

    def set_mask_image(self, mask_arr):
        """Updates the visual thumbnail from a numpy array."""
        if mask_arr is None:
            self.mask_preview_label.clear()
            return

        # Convert Grayscale NumPy -> QImage -> QPixmap
        h, w = mask_arr.shape
        qimg = QImage(mask_arr.data, w, h, w, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimg)
        
        # Scale for UI
        scaled_pixmap = pixmap.scaled(
            self.mask_preview_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.mask_preview_label.setPixmap(scaled_pixmap)

    # ==========================================
    # INTERNAL HANDLERS
    # ==========================================

    def _on_list_selection(self, current, previous):
        if not current: 
            # If selection is cleared, emit None to disable property panel
            self.layer_selected.emit(None)
            return
            
        lid = current.data(Qt.ItemDataRole.UserRole)
        self.layer_selected.emit(lid)

    def _on_item_changed(self, item):
        """Handles Checkbox Toggles."""
        lid = item.data(Qt.ItemDataRole.UserRole)
        is_checked = (item.checkState() == Qt.CheckState.Checked)
        
        self.layer_visibility_toggled.emit(lid, is_checked)
        