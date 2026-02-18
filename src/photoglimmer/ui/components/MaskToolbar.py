# ######################################################################################
# Manual mask edit sub-toolbar . Used by ToolbarSetup 
# ######################################################################################

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QToolButton, 
                               QButtonGroup, QSlider, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal

class MaskToolbar(QWidget):
    """
    The 'Capsule' widget in the toolbar containing:
    1. Master Toggle (Edit Mask)
    2. Brush Tools (Paint/Erase)
    3. Size Slider
    """
    
    # Signals to Controller (MainWindow)
    mode_toggled = Signal(bool)     # True=Editing, False=Normal
    tool_changed = Signal(str)      # 'add' or 'erase'
    size_changed = Signal(int)      # Brush radius

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ID is crucial for QSS targeting (see main.qss #MaskGroup)
        self.setObjectName("MaskGroup")
        # without  WA_StyledBackground, no custom style for a toolbar 
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        
        
        # Force the widget to hug its contents tightly (Do not expand)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._setup_ui()
        
        # Initialize internal state (Sub-controls disabled by default)
        self._set_sub_controls_enabled(False)

    def _setup_ui(self):
        # A. The Master Switch
        self.btn_mask_mode = QToolButton()
        self.btn_mask_mode.setText("🎭 Manual Mask")
        self.btn_mask_mode.setCheckable(True)
        self.btn_mask_mode.setToolTip("Enter Mask Editing Mode (Locks Layer Movement)")
        self.btn_mask_mode.toggled.connect(self._on_master_toggled)
        self.layout.addWidget(self.btn_mask_mode)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(line)

        # B. Tools
        self.paint_tools_group = QButtonGroup(self)
        self.paint_tools_group.setExclusive(True)

        

        self.btn_paint = QToolButton()

        self.btn_paint.setObjectName("btnPaint")


        self.btn_paint.setText("🖌 Paint")
        self.btn_paint.setCheckable(True)
        self.btn_paint.setChecked(True)
        self.btn_paint.clicked.connect(lambda: self.tool_changed.emit('add'))
        self.paint_tools_group.addButton(self.btn_paint)
        self.layout.addWidget(self.btn_paint)

        self.btn_erase = QToolButton()

        self.btn_erase.setObjectName("btnErase")

        self.btn_erase.setText("⌫ Erase")
        self.btn_erase.setCheckable(True)
        self.btn_erase.clicked.connect(lambda: self.tool_changed.emit('erase'))
        self.paint_tools_group.addButton(self.btn_erase)
        self.layout.addWidget(self.btn_erase)

        # C. Size Slider
        self.layout.addWidget(QLabel("Size:"))
        self.brush_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.brush_size_slider.setRange(5, 100)
        self.brush_size_slider.setValue(20)
        self.brush_size_slider.setFixedWidth(80)
        self.brush_size_slider.valueChanged.connect(self.size_changed.emit)
        self.layout.addWidget(self.brush_size_slider)

    # ==========================================
    # INTERNAL LOGIC
    # ==========================================

    def _on_master_toggled(self, checked):
        """Handle internal state changes when Master Switch is clicked."""
        self._set_sub_controls_enabled(checked)
        self.mode_toggled.emit(checked)

    def _set_sub_controls_enabled(self, enabled):
        """Helper to dim/undim the tools inside the capsule."""
        self.btn_paint.setEnabled(enabled)
        self.btn_erase.setEnabled(enabled)
        self.brush_size_slider.setEnabled(enabled)
        

    # ==========================================
    # PUBLIC API
    # ==========================================

    def set_available(self, available):
        """
        Enables/Disables the entire widget based on whether a valid layer is selected.
        If disabling, it automatically turns off the Edit Mode.
        """
        self.btn_mask_mode.setEnabled(available)
        if not available and self.btn_mask_mode.isChecked():
            self.btn_mask_mode.setChecked(False) # Triggers _on_master_toggled(False)

    def is_active(self):
        return self.btn_mask_mode.isChecked()

    def get_current_mode(self):
        return 'add' if self.btn_paint.isChecked() else 'erase'

    def get_brush_size(self):
        return self.brush_size_slider.value()
    