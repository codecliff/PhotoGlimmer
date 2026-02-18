# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# A FACTORY pattern for creating sliders and checkboxes 
# automatically as per the 'meta' parameters defined in a strategy 
# Is used by the PropertyPanel to generate control ui for right sidebar

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSlider, 
                               QLabel, QCheckBox, QToolButton)
from PySide6.QtCore import Qt

class ParamWidgetFactory:
    @staticmethod
    def create_widget(name, meta, current_val, callback):
        """
        Factory remains the entry point but now creates enhanced widgets. 
        """
        control_type = meta.get("type", "slider")
        
        if control_type == "slider":
            return LabeledSlider(name, meta, current_val, callback)
        elif control_type == "checkbox":
            return LabeledCheckbox(name, meta, current_val, callback)
        
        return QLabel(f"Unknown: {name}")

class LabeledSlider(QWidget):
    
    def __init__(self, name, meta, current_val, callback):
        """meta is a dict. See PropertyManager class for details """
        super().__init__()
        self.name = name
        self.meta = meta
        self.callback = callback
        self.label_text = meta.get("label", name)
        self.default_val = meta.get("default", 1.0) 
        self.min_val, self.max_val = meta.get("range", (0.0, 1.0)) 
        self.old_val = current_val 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Label + Reset + Value)
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.label_text)
        
        # ---  RESET BUTTON ---
        self.btn_reset = QToolButton()
        #self.btn_reset.setObjectName("BSlideReset")

        self.btn_reset.setText("↺")
        self.btn_reset.setToolTip(f"Reset to default ({self.default_val})")
        self.btn_reset.setStyleSheet("border: none; background: transparent; margin:0px;padding:0px ;color: #888;")
        self.btn_reset.clicked.connect(self.reset_to_default)
        
        self.value_label = QLabel(f"{current_val:.2f}") 

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_reset)
        header_layout.addWidget(self.value_label)
        
        layout.addLayout(header_layout)
        
        # Slider Setup
        self.steps = 1000 
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.steps)
        self.set_value(current_val) # Use the new sync method
        
        self.slider.valueChanged.connect(self._on_slider_moved) 
        self.slider.sliderReleased.connect(self._on_slider_released) 
        
        layout.addWidget(self.slider)



    def set_value(self, val):
        """Updates the UI without triggering callbacks to the backend."""
        self.slider.blockSignals(True)
        denom = (self.max_val - self.min_val) if (self.max_val != self.min_val) else 1.0
        pos = int((val - self.min_val) / denom * self.steps)
        self.slider.setValue(pos)
        self.value_label.setText(f"{val:.2f}")
        self.old_val = val
        self.slider.blockSignals(False)

    def reset_to_default(self):
        """Triggers a reset to the default value defined in metadata."""
        self.set_value(self.default_val)
        # Notify backend that this is a final, committed change 
        self.callback(self.name, self.default_val, True, self.old_val)

    def _on_slider_moved(self, pos):
        new_val = self.min_val + (pos / self.steps) * (self.max_val - self.min_val) 
        self.value_label.setText(f"{new_val:.2f}")
        self.callback(self.name, new_val, False, self.old_val) 

    def _on_slider_released(self):
        pos = self.slider.value() 
        final_val = self.min_val + (pos / self.steps) * (self.max_val - self.min_val) 
        self.callback(self.name, final_val, True, self.old_val) 
        self.old_val = final_val 

class LabeledCheckbox(QWidget):
    def __init__(self, name, meta, current_val, callback):
        super().__init__()
        self.name = name
        self.callback = callback
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox(meta.get("label", name)) 
        self.set_value(current_val)
        
        self.checkbox.toggled.connect(
            lambda checked: self.callback(self.name, checked, True, not checked) 
        )
        layout.addWidget(self.checkbox)

    def set_value(self, val):
        """Updates checkbox state without triggering callback."""
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(bool(val))
        self.checkbox.blockSignals(False)