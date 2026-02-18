# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


#####################################################################################3
#' This file contains:
#' 1. TweaksPanel : A large panel (effectively the 'right sidebar') 
#' 2.   CollapsibleBox : A panel containing sliders and/or checkboxes for one strategy
#' 3.       CollapsibleHeader : Header UI for each CollapsibleBox

#  PropertyManager calculates what strategies are to be included 
#  and  calls TweaksPanel's rebuild_for_layer() to poluate the whole tweakpanel 
# this is govened by 1. The current layer which proved values of each slider, and
#                    2. The strategies which tell the title and exact sliders to include 
# Strategies themselves are registered in ImageSession, so exact same panels 
#   are needed through a session 
#####################################################################################

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame, 
                               QToolButton, QSizePolicy, QLayout, QStackedWidget)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, Signal, QEvent
from PySide6.QtGui import QCursor

from .Factory import ParamWidgetFactory
from ..backend.Interfaces import APP_NAME, StrategyScope

import logging 
logger = logging.getLogger(APP_NAME)
#####################################################################################

class CollapsibleHeader(QFrame):
    """
    A custom clickable header that replaces the standard QToolButton.
    Layout: [Arrow] [Title] ........... [Icon]
    """
    # a signal must be declared outside init ! 
    toggled_signal = Signal(bool) 
    
    def __init__(self, title="", scope=StrategyScope.LAYER, parent=None):
        super().__init__(parent)

        

        
        
        
        # 1. Horizontal Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5) 
        self.layout.setSpacing(10)
        
        # 2. Arrow Indicator - DEFAULT CLOSED
        self.arrow_lbl = QLabel("▶") 
        #self.arrow_lbl.setStyleSheet("color: #888; font-size: 10px;")
        self.layout.addWidget(self.arrow_lbl)
        
        # 3. Title Text
        self.title_lbl = QLabel(title.upper())
        #self.title_lbl.setStyleSheet("font-weight: bold; color: #E0E0E0;") 
        self.layout.addWidget(self.title_lbl)
        
        # 4. Spacer
        self.layout.addStretch()
        
        # 5. Scope Icon
        icon_map = {
            StrategyScope.FACE: "👤",    
            StrategyScope.LAYER: "📄",   
            StrategyScope.GLOBAL: "🌐"   
        }
        
        lookup_key = scope
        if hasattr(scope, "value"): 
            lookup_key = scope
        elif isinstance(scope, str): 
            try:
                lookup_key = StrategyScope(scope)
            except ValueError:
                pass 

        icon_text = icon_map.get(lookup_key, "")
        
        if icon_text:
            self.scope_lbl = QLabel(icon_text)
            self.scope_lbl.setStyleSheet("color: #888; font-size: 14px; background: transparent;")
            tt_text = lookup_key.value if hasattr(lookup_key, "value") else str(lookup_key)
            self.scope_lbl.setToolTip(f"Scope: {tt_text.capitalize()}")
            self.layout.addWidget(self.scope_lbl)

        # 6. Interaction Styling & State
        self.is_expanded = False  # <--- FORCE DEFAULT FALSE
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


        self.setEnabled(True)


        # super().__init__(parent)
        self.setObjectName("CollapsibleHeader")
        
        

        
        

    def mousePressEvent(self, event):
        """Handle click to toggle"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            # Notify parent logic
            if self.parent() and hasattr(self.parent(), 'toggle_content'):
                self.parent().toggle_content()

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.arrow_lbl.setText("▼" if self.is_expanded else "▶")
        self.toggled_signal.emit(self.is_expanded) # used only to persist toggle across rebuilds

   
    


#####################################################################################


class CollapsibleBox(QWidget):
    """
    Container that holds the Header and the Content Area for one strategy 
    """
    def __init__(self, title="", scope=StrategyScope.LAYER, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. Add Custom Header
        self.header = CollapsibleHeader(title, scope, self)
        self.layout.addWidget(self.header)

        # 2. Add Content Area
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # --- FORCE DEFAULT CLOSED STATE ---
        self.content_area.setMaximumHeight(0) 
        self.content_area.setVisible(False)
        
        # We need a layout for the content area to hold the sliders
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 10, 5, 10) # Indent content slightly
        
        self.layout.addWidget(self.content_area)

        # 3. Animation Setup
        self.anim = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def toggle_content(self):
        """Called by header when clicked"""
        if self.header.is_expanded:
            # Expand
            self.content_area.setVisible(True)
            self.content_layout.activate()
            # Calculate required height
            h = self.content_layout.sizeHint().height()
            self.anim.setStartValue(0)
            self.anim.setEndValue(h)
            self.anim.start()
        else:
            # Collapse
            self.anim.setStartValue(self.content_area.height())
            self.anim.setEndValue(0)
            self.anim.start()

    def expand(self):
        """Force expand (initial state)"""
        if not self.header.is_expanded:
            self.header.toggle() # Update arrow
        
        self.content_area.setVisible(True)
        # Set max height to something large so it shows content
        self.content_area.setMaximumHeight(16777215)


#####################################################################################        


# ====================================================
# MAIN PANEL : The whole of right 'sidebar' 
#  Now uses a StackedWidget to swap between persistent
#  Background and Layer containers.
# ====================================================
class TweaksPanel(QWidget):
    """Contaians all the panels representing strategies.
    Now optimized to sync values instead of rebuilding from scratch."""
    def __init__(self, parent=None):
        super().__init__(parent)

        
        # These keys will be expanded by default. All others start collapsed.  
        # Important ! must be lowercase
        self.EXPANDED_DEFAULTS = {"mask edge","color", "blur", "whitebalance", "auto_wb"}  
        
        # ID for Theme Manager 
        self.setObjectName("PropertyPanel")
        self._expanded_prefs = self.EXPANDED_DEFAULTS.copy() 

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- NEW: PERSISTENT STORAGE ---
        self.stack = QStackedWidget()
        
        # Container 0: Background UI
        self.bg_container = QWidget()
        self.bg_layout = QVBoxLayout(self.bg_container)
        self.bg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._bg_widgets = {} # Maps param_name -> widget instance
        
        # Container 1: Layer UI
        self.layer_container = QWidget()
        self.layer_layout = QVBoxLayout(self.layer_container)
        self.layer_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layer_widgets = {} # Maps param_name -> widget instance

        self.stack.addWidget(self.bg_container)
        self.stack.addWidget(self.layer_container)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scroll.setWidget(self.stack)
        self.main_layout.addWidget(self.scroll)

    def rebuild_for_layer(self, layer_id, metadata_groups, current_state, callback):
        """
        Actual code that creates or updates the collapsible boxes. 
        """
        is_bg = (layer_id == "__bg__") # Match BACKGROUND_ID 
        active_layout = self.bg_layout if is_bg else self.layer_layout
        active_cache = self._bg_widgets if is_bg else self._layer_widgets
        
        # Switch the view immediately
        self.stack.setCurrentIndex(0 if is_bg else 1)

        # 1. INITIAL BUILD: If this container has never been populated, build it.
        if active_layout.count() == 0:
            self._build_container(active_layout, active_cache, metadata_groups, current_state, callback)
            active_layout.addStretch()
        
        # 2. SYNC: If already built, just update the widget values.
        else:
            self._sync_widgets(active_cache, metadata_groups, current_state)

    def _build_container(self, layout, cache, metadata_groups, current_state, callback):
        """One-time construction of the strategy panels. """
        for group_name, group_data in metadata_groups.items():
            if isinstance(group_data, tuple):
                scope, params = group_data
            else:
                scope = "layer" 
                params = group_data
            
            box = CollapsibleBox(group_name, scope)
            layout.addWidget(box)
            
            strat_key = group_name.lower() 
            if strat_key in self._expanded_prefs:
                box.expand() 

            box.header.toggled_signal.connect(
                lambda is_open, k=strat_key: self._update_pref(k, is_open)
            )

            for p_name, p_meta in params.items():
                val = self._get_value_from_state(p_name, strat_key, current_state, p_meta)
                w = ParamWidgetFactory.create_widget(p_name, p_meta, val, callback)
                if w:
                    box.add_widget(w)
                    cache[p_name] = w # Store reference for syncing

    

    def _sync_widgets(self, cache, metadata_groups, current_state):
        """Updates existing widgets without rebuilding them."""
        for group_name, group_data in metadata_groups.items():
            params = group_data[1] if isinstance(group_data, tuple) else group_data
            strat_key = group_name.lower()
            
            for ui_key, p_meta in params.items():
                if ui_key in cache:
                    # Resolve value using namespaced logic
                    val = self._get_value_from_state(ui_key, strat_key, current_state, p_meta)
                    cache[ui_key].set_value(val)

    

    def _get_value_from_state(self, ui_key, strat_key, current_state, p_meta):
        """Helper to resolve current value from layer state."""
        
        # 1. Handle Standard Layer Properties (No colon)
        if ":" not in ui_key:
            if hasattr(current_state, ui_key):
                return getattr(current_state, ui_key)
            return p_meta.get("default", 1.0)

        # 2. Handle Strategy Parameters
        actual_p_name = ui_key.split(":")[-1]
        
        # Get the adjustments dict (handle both Layer object and State object)
        adjustments = getattr(current_state, 'adjustments', {})
        
        # compare strat_key with the title of the panel
        # toLower() needed because keys are picked form UI titles  which are in TitleCase 
        adj_group = {}
        if strat_key in adjustments:
            adj_group = adjustments[strat_key]
        elif strat_key.lower() in adjustments:
            adj_group = adjustments[strat_key.lower()]
        else:
            # Last resort: find any key that matches case-insensitively
            for k in adjustments.keys():
                if k.lower() == strat_key.lower():
                    adj_group = adjustments[k]
                    break
        
        return adj_group.get(actual_p_name, p_meta.get("default", 0.0))



    def _update_pref(self, key, is_expanded):
        """Helper to update the persistent set safely"""
        if is_expanded:
            self._expanded_prefs.add(key)
        else:
            self._expanded_prefs.discard(key) 

    def clear_proxy_cache(self):
        """
        #' Safety function to be called when a brand new image is loaded.
        #' This completely wipes the persistent containers and maps.
        """
        # 1. Clear Background Container
        while self.bg_layout.count():
            item = self.bg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._bg_widgets.clear()

        # 2. Clear Layer Container
        while self.layer_layout.count():
            item = self.layer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._layer_widgets.clear()
        
        # 3. Reset simple-mode expansion preferences to defaults
        self._expanded_prefs = self.EXPANDED_DEFAULTS.copy() 

    
        