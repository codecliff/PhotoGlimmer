# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################

import os
import sys
import subprocess
from pathlib import Path
import gc

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QToolBar, QListWidget, 
                               QListWidgetItem, QFileDialog, QApplication, QMessageBox,
                               QSlider, QToolButton, QButtonGroup, QFrame, QSizePolicy,
                               QGraphicsColorizeEffect)
from PySide6.QtGui import (QImage, QPixmap, QAction, QColor, QKeySequence, 
                           QDragEnterEvent, QDropEvent, QCloseEvent, QIcon, QDesktopServices)
from PySide6.QtCore import Qt, QThread,QUrl,QSize,QTimer

#from PySide6.QtWidgets import QWidgetAction # Ensure this is imported



# --- CUSTOM MODULES ---

from .ActionSetup import ActionSetup
from .MenuSetup import MenuSetup
from .ToolbarSetup import ToolbarSetup



from ..backend.Interfaces import APP_NAME
from ..backend.ImageSession import ImageSession
from .Canvas import InteractiveCanvas
from .PropertyPanel import TweaksPanel
from .components.Sidebar import Sidebar
from .components.MaskToolbar import MaskToolbar
from .components.LoadingOverlay import LoadingOverlay
from .components.CustomDialog import CustomDialog
from .components.HelpDialog import HelpDialog
from .utils.GuiUtils import GuiUtils
from .io.ExportManager import ExportManager

from .managers.SettingsManager import SettingsManager
from .managers.PropertyManager import PropertyManager
from .managers.ThemeManager import ThemeManager  # Ensure ThemeManager is imported if used

import cv2
import numpy as np 

ASSETS_PATH = Path(__file__).parent.parent / "assets"

######################################################################
# Logging Setup
######################################################################
import logging  
# inherits the File+Console handlers set in  __main__
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    The Main Application Window.
    Acts as the Controller between the UI (Canvas/Sidebar) and the Backend (ImageSession).
    """
    
    # --- UI STATES ---
    STATE_BLANK = 0           # App Launch (No Image)
    STATE_UNSELECTED = 1      # Image Loaded, No Layer Selected ( not the same as 3)
    STATE_LAYER = 2           # Standard Layer Selected
    STATE_BACKGROUND = 3      # Background Layer Selected

       


    # initialize without image_path : blank state
    # initialize with  image_path : done by main  for "open with photoglimmer"
    def __init__(self, image_path=None): 
        super().__init__()

        self.setAcceptDrops(True) # drag and drop 

        self.settings_manager = SettingsManager() # Loads values into RAM

        # CHANGE 2: Initialize session as None initially
        self.session = None
        self.active_layer_id = None 
            
        # UI Flags
        self.show_mask_overlay = False 
        self._was_mask_editing_before_hide = False
        
        self.setWindowTitle(f"{APP_NAME}: Illuminate Me!")

        current_dir = Path(__file__).parent.resolve()
        icon_path = current_dir.parent / "icons" / "appicon-64.png"  
        app_icon = QIcon(QPixmap(str(icon_path)))      
        self.setWindowIcon(app_icon)
        
        # --- Status Bar ---
        self.status_bar = self.statusBar()

        # 3. Build UI Layout
        # (Must be done BEFORE loading an image so _perform_load can access widgets)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Create Actions (Attaches self.act_open, etc.)
        ActionSetup(self) 

        # 2. Build UI (Uses those actions)
        MenuSetup.setup(self)
        ToolbarSetup.setup(self)

        
        
        # --- A. LEFT: Sidebar (Layers/Masks) ---
        self.sidebar = Sidebar()
        self.sidebar.layer_selected.connect(self.on_layer_selection_changed)
        self.sidebar.layer_visibility_toggled.connect(self.on_layer_item_changed)
        self.sidebar.add_layer_clicked.connect(self.on_add_layer_clicked)
        self.sidebar.reset_layer_clicked.connect(self.on_reset_layer)

        #self.main_layout.addWidget(self.sidebar, 1)
        self.sidebar.setFixedWidth(260) 
        self.main_layout.addWidget(self.sidebar, 0)

        # --- B. CENTER: Canvas ---
        self.setup_canvas() #is given stretch 1 , fill all available space

        # --- C. RIGHT: Tweaks Panel Property Panel ---
        # TODO: rename this valieable
        self.prop_panel = TweaksPanel()
        self.prop_panel.setFixedWidth(300) 
        # self.main_layout.addWidget(self.prop_panel, 2)
        self.main_layout.addWidget(self.prop_panel, 0)

        # Attach Managers
        self.prop_manager = PropertyManager(self.session, self.prop_panel, self.on_property_updated)
        self.export_manager = ExportManager(self)  

        # 4. Overlay for Busy Spinner
        self.overlay = LoadingOverlay(self)
        self.overlay.canceled.connect(self.cancel_export) 
        self.overlay.hide()

        
        self.set_window_size()
        self.show_status("Ready")


        # Flag to track if we need to auto-fit the image 
        self._pending_initial_zoom = False

        
        # Now that UI is built, we can safely load the image if provided
        if image_path:
            # _perform_load handles creating the session, setting up managers, and resetting workspace
            self._perform_load(image_path)
            self._pending_initial_zoom = True # to ensure canvas is zoomed to fit on first display 
        else:
            # Default empty state
            self.canvas.set_pixmap(None)
            self._set_ui_state(self.STATE_BLANK)

        


    # ============================================================
    # STATE MANAGEMENT for deciding the display nuances for the whole window 
    # ============================================================
    def _set_ui_state(self, state):
        """
        The Single Source of Truth for enabling/disabling UI components.
        """
        # 1. STATE_BLANK (App Launch)
        if state == self.STATE_BLANK:
            # Top Bar
            self.act_export.setEnabled(False)
            self.act_undo.setEnabled(False)
            self.act_redo.setEnabled(False)
            self.act_zoom_in.setEnabled(False)
            self.act_zoom_out.setEnabled(False)
            self.act_zoom_fit.setEnabled(False)
            self.act_toggle_overlays.setEnabled(False)
            
            # Components
            self.sidebar.set_interface_enabled(False)
            self.mask_toolbar.set_available(False)
            self.prop_panel.setEnabled(False)
            
            # Canvas (Visible but inactive)
            # self.canvas.setVisible(True) # Always visible to hold layout

        # 2. STATE_UNSELECTED (Image Loaded, Nothing Clicked)
        #    This is the state where use has clicked on the background outside all layers
        elif state == self.STATE_UNSELECTED:
            # Top Bar
            self.act_export.setEnabled(True)
            self.act_undo.setEnabled(True) # Simple approach: Always enable if image loaded
            self.act_redo.setEnabled(True)
            self.act_zoom_in.setEnabled(True)
            self.act_zoom_out.setEnabled(True)
            self.act_zoom_fit.setEnabled(True)
            self.act_toggle_overlays.setEnabled(True)
            
            # Components
            self.sidebar.set_interface_enabled(True) # Can Add Layer
            self.mask_toolbar.set_available(False)   # Cannot Mask Void
            self.prop_panel.setEnabled(False)        # Cannot Edit Void

        # 3. STATE_LAYER (Standard Adjustment Layer)
        #    User has selectedd a layer
        elif state == self.STATE_LAYER:
            # Top Bar
            self.act_export.setEnabled(True)
            self.act_undo.setEnabled(True)
            self.act_redo.setEnabled(True)
            self.act_zoom_in.setEnabled(True)
            self.act_zoom_out.setEnabled(True)
            self.act_zoom_fit.setEnabled(True)
            self.act_toggle_overlays.setEnabled(True)
            
            # Components
            self.sidebar.set_interface_enabled(True)
            self.mask_toolbar.set_available(True)  # Can Mask
            self.prop_panel.setEnabled(True)       # Can Edit

        # 4. STATE_BACKGROUND (Base Image)
        #    User has selected Background from the sidebar list
        #    This is the only way of selecting background   
        elif state == self.STATE_BACKGROUND:
            # Top Bar
            self.act_export.setEnabled(True)
            self.act_undo.setEnabled(True)
            self.act_redo.setEnabled(True)
            self.act_zoom_in.setEnabled(True)
            self.act_zoom_out.setEnabled(True)
            self.act_zoom_fit.setEnabled(True)
            self.act_toggle_overlays.setEnabled(True)
            
            # Components
            self.sidebar.set_interface_enabled(True)
            self.mask_toolbar.set_available(False) # Cannot Mask Background
            self.prop_panel.setEnabled(True)       # Can Edit Globals  



   

    def setup_canvas(self):
        """Initializes the Canvas and connects Signals."""
        self.canvas = InteractiveCanvas()

        self.canvas.setObjectName("CentralCanvas")
        
        self.canvas.setMinimumWidth(500)

        self.canvas.geometry_created.connect(self.on_geometry_created)
        self.canvas.geometry_changed.connect(self.on_geometry_changed)
        self.canvas.layer_selected.connect(self.on_layer_selected_from_canvas)
        self.canvas.layer_deleted.connect(self.on_layer_deleted)
        self.canvas.selection_cleared.connect(self.on_selection_cleared_from_canvas)
        self.canvas.mask_stroke_finished.connect(self.on_mask_stroke_finished)
        self.canvas.ui_visibility_changed.connect(self.update_overlay_button_state)
        self.canvas.file_dropped.connect(self._attempt_load_image)
        self.canvas.zoom_changed.connect(self.update_zoom_status)
        self.canvas.layers_limit_reached.connect(self.on_layer_limit_hit)
        
        self.main_layout.addWidget(self.canvas, 1)

    
        

     

    # ============================================================
    # MASK EDITING LOGIC
    # ============================================================
    def toggle_mask_edit_mode(self, checked):
        """Master Switch for Mask Editing."""
        self._set_mask_ui_state(checked)
        self.show_mask_overlay = checked
        self.update_display()
        
        if checked:
            mode = 'add' if self.mask_toolbar.get_current_mode() == 'add' else 'erase'
            size = self.mask_toolbar.get_brush_size()
            self.canvas.set_brush_params(active=True, mode=mode, size=size)
        else:
            self.canvas.set_brush_params(active=False)

    def _set_mask_ui_state(self, enabled):
        """Helper to dim/undim the tools inside the capsule."""
        # This logic is mostly handled internally by MaskToolbar now
        pass 

    def on_mask_mode_toggled(self, active):
        """Called when user clicks 'Edit Mask'."""
        self.show_mask_overlay = active
        self.update_display()

        if active:
            mode = self.mask_toolbar.get_current_mode()
            size = self.mask_toolbar.get_brush_size()
            self.canvas.set_brush_params(active=True, mode=mode, size=size)
        else:
            self.canvas.set_brush_params(active=False)
            

    def on_brush_tool_changed(self, mode):
        if self.mask_toolbar.is_active():
            size = self.mask_toolbar.get_brush_size()
            self.canvas.set_brush_params(active=True, mode=mode, size=size)

    def on_brush_size_changed(self, size):
        if self.mask_toolbar.is_active():
            mode = self.mask_toolbar.get_current_mode()
            self.canvas.set_brush_params(active=True, mode=mode, size=size)

    # ============================================================
    # MASK PREVIEW  : Red Overlay and  sidebar preview
    # ============================================================
    def _create_red_overlay(self, mask_arr):
        """Converts a single-channel mask (uint8) into a Red RGBA QPixmap."""
        h, w = mask_arr.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, 0] = 255 # Red
        rgba[:, :, 3] = mask_arr # Alpha
        qimg = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(qimg)

    def update_mask_preview(self, layer_id):
        """Updates the small mask thumbnail AND the main canvas overlay."""
        layer = self.session.layers.get(layer_id)
        if not layer: return

        mask_arr = self.session.get_refined_mask(layer)
        if mask_arr is None:
            self.sidebar.set_mask_image(None)
            self.canvas.update_layer_mask_preview(layer_id, QPixmap())
            return

        self.sidebar.set_mask_image(mask_arr) 

        if self.show_mask_overlay:
            pixmap_red = self._create_red_overlay(mask_arr)
            self.canvas.update_layer_mask_preview(layer_id, pixmap_red)
        else:
            self.canvas.update_layer_mask_preview(layer_id, QPixmap())


    def on_mask_stroke_finished(self, layer_id, qimage, mode):
        """for handling mask_stroke_finished signal from canvas during manual mask edit"""
        if not self.session: return
        if hasattr(self.session, 'apply_mask_stroke'):
            self.session.apply_mask_stroke(layer_id, qimage, mode)
        self.update_mask_preview(layer_id)
        self.update_display()

    # ============================================================
    # FILE I/O
    # ============================================================
        
    #with preference support 
    def on_open_image(self):
        # 1. Get Directory from Settings Manager (Pre-calculated in RAM)
        # Uses the logic defined in Preferences (Last Used vs Custom vs Home)
        start_dir = self.settings_manager.open_path_hint
        
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", start_dir, "Images (*.jpg *.png *.jpeg)")
        if path:
            self._attempt_load_image(path)

            

    def _attempt_load_image(self, path):
        if self.session:
            should_load = CustomDialog.question(
                self, 
                "Replace Image?", 
                "Loading a new image will discard the current workspace. Continue?",
                ok_text="Load New", 
                cancel_text="Cancel"
            )
            if should_load:
                 self._perform_load(path)
        else:
            self._perform_load(path)



    # ###############################################################
    #  _perform_load loads a new image . 1 Image = 1 ImageSession
    #   - If a ImageSession is already present, user has an image already open
    #   - Makes sure previosu ImageSession ends , and leaves behind no memroy leak
    #   - Also makes sure the ever=present TweaksPanel clears any state memory 
    #   - Then iniatializes a bradn new ImageSession 
    # ###############################################################
    def _perform_load(self, path):
        """ Loading a New Image."""
        try:
            self.show_status(f"Loading: {os.path.basename(path)}...", 0)     


            # IF user already has an image open , deal with that state first 
            
            # --- CLEAN UP ANY OLD SESSION ---       
            if self.session:
                # Tell managers to handle their own internal state/threads
                self.prop_manager.set_session(None) 
                if hasattr(self, 'export_manager'):
                    self.export_manager.cleanup() # Thread safety happens here

                # Destroy the session's internal high-res buffers
                self.session.close()
                self.session = None
                
                # Now that all owners have let go, the memory is truly free
                gc.collect()
                gc.collect()

            # End if  
            
            #-------------------------
            # if we want to perform a memory leak inspection, we do it here 
            # inspect_leaked_objects()   
            #--------------------------

            # --- INITIALIZE NEW SESSION ---

            # OLD Session cleaned up , create a new ImageSession 
            
            self.session = ImageSession(path)

            # 4. Sidebar and workspace resets
            self.prop_panel.clear_proxy_cache()
            self.prop_manager.set_session(self.session)
            
            if hasattr(self.session, 'proxy_img'):
                # Convert proxy for display
                original_pixmap = GuiUtils.convert_cv_to_qpixmap(self.session.proxy_img)
                self.canvas.set_original_pixmap(original_pixmap)
            
            if hasattr(self, 'export_manager'):
                self.export_manager.set_session(self.session)

            # Sync workspace to the new session
            self.reset_workspace(target_layer_id=self.session.BACKGROUND_ID)

            # 5. UI Flourish and State
            self.canvas.zoom_reset()
            self.settings_manager.add_recent_file(path)
            MenuSetup.update_recent_menu(self)
            
            self.show_status(f"{os.path.basename(path)} Loaded", 3000)  
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.show_status(f"Error loading image: {str(e)}", 5000)
        


    # ============================================================
    # WORKSPACE & DISPLAY
    # ============================================================
    def reset_workspace(self, target_layer_id=None):
        """ Recreates the whole of layer list in the right sidebar ,
            Asks for the canvas to be repained with update_display()
            and sets UI state for the whole window by calling  set_UI_state()

            Called when Window is creating a new session 
            OR after each Undo/Redo         
        
        """
        
        # 1. Clear Data
        if hasattr(self.canvas, 'items_hidden'):
            self.canvas.items_hidden = False
        self.sidebar.clear_all()
        
        # 2. Add Background
        desired_selection = target_layer_id if target_layer_id else self.active_layer_id
        is_bg_selected = (self.session.BACKGROUND_ID == desired_selection)
        
        #background layer has to be manually added to list 
        # TODO : maybe move this to somewhere more permanent 
        self.sidebar.add_layer_entry(
            layer_id=self.session.BACKGROUND_ID,
            name="Background",
            is_visible=True,
            is_selected=is_bg_selected
        )
        
        # 3. Add Layers
        if hasattr(self.session, 'layers'):
            for lid, layer in self.session.layers.items():
                if layer.is_background: continue
                display_label = getattr(layer, 'name', f"Layer {lid}")
                is_selected = (lid == desired_selection)
                is_visible = layer.visible
                
                self.sidebar.add_layer_entry(
                    layer_id=lid,
                    name=display_label,
                    is_visible=is_visible,
                    is_selected=is_selected
                )
        
        # 4. Refresh View
        self.update_display()
        
        # 5. Determine correct UI State based on Selection
        if desired_selection is None:
            self._set_ui_state(self.STATE_UNSELECTED)
        elif desired_selection == self.session.BACKGROUND_ID:
            self._set_ui_state(self.STATE_BACKGROUND)
        else:
            self._set_ui_state(self.STATE_LAYER)

        if target_layer_id is None: 
             self.canvas.zoom_reset()


    

    def update_display(self):
        """ Updates the  canvas showing the  current state of the image and layers frames
            Render_proxy called here !  
            Also Update  mask preview  
        """
        if not self.session: return

        # 1. Render Composite & Update Background
        res_bgr = self.session.render_proxy(show_overlay=False) 
        self.canvas.set_pixmap(GuiUtils.convert_cv_to_qpixmap(res_bgr))        
        
        # 2. Update Overlay Items (Rects)
        # Note: Ensure your canvas.set_layers() now initializes items 
        # using the Layer OBJECT, not just the ID.
        self.canvas.set_layers(self.session.layers, self.active_layer_id)
        
        # 3. Force Overlay Repaint (The Fix)
        # Since we removed the manual sync loop, we must tell the scene 
        # to repaint. The items will check 'self.layer.is_frozen' 
        # inside their paint() method and draw the lock if needed.
        if self.canvas.scene:
            self.canvas.scene.update()

        # 4. Update Mask Preview Panel
        if self.active_layer_id:
            self.update_mask_preview(self.active_layer_id)

            

    # ============================================================
    # CANVAS INTERACTION
    # ============================================================
    # A VERY IMPORTANT HELPER FUNCITON
    # PASS ANY DIMENSIONS AND COORDINATES TO BACKEND ONLY AS NORMALIZED
    # INTERACTIVECANVAS IS EMITING EVERYTHING AS PIXELS	
    def _pixels_to_normalized(self, px, py, pw, ph):
        if not self.session or self.session.proxy_img is None: return 0.0, 0.0, 0.0, 0.0
        img_h, img_w = self.session.proxy_img.shape[:2]
        if img_w == 0 or img_h == 0: return 0.0, 0.0, 0.0, 0.0
        return px / float(img_w), py / float(img_h), pw / float(img_w), ph / float(img_h)
        
    def on_add_layer_clicked(self):
        self.sidebar.clear_selection()
        self.active_layer_id = None
        
        # Switch to Unselected State
        self._set_ui_state(self.STATE_UNSELECTED)
        
        print("Ready to draw: Click and drag anywhere on the image.")

    def on_geometry_created(self, px, py, pw, ph):
        """handles signal from canvas telling user has drawn a new rect"""
        if not self.session: return
        nx, ny, nw, nh = self._pixels_to_normalized(px, py, pw, ph)
        new_layer_id = self.session.add_new_layer(nx, ny, nw, nh)
        new_layer = self.session.layers[new_layer_id]
        
        # Add and Select
        self.sidebar.add_layer_entry(new_layer_id, new_layer.name, is_selected=True)
        self.update_display()



    def _snap_back_layer_rect(self, layer_id):
        """
        Reverts the visual layer rectangle to backend truth.
        """
        if not self.session or not self.canvas: return
        
        layer = self.session.layers.get(layer_id)
        if not layer: return

        
        # layer.bounds is in pixels (x, y, w, h)        
        r_px, r_py, r_pw, r_ph = layer.bounds

        # Ensure we have valid integers
        r_px, r_py = int(r_px), int(r_py)
        r_pw, r_ph = int(r_pw), int(r_ph)

        # C. Find and Reset Item
        if self.canvas.scene:
            for item in self.canvas.scene.items():
                if hasattr(item, 'layer_id') and item.layer_id == layer_id:
                    
                    # 1. Reset Position (Top-Left in Scene Coords)
                    item.setPos(r_px, r_py)
                    
                    # 2. Reset Size (Rect relative to item's local 0,0)
                    item.setRect(0, 0, r_pw, r_ph)
                    
                    # 3. Force Visibility/Selection (In case it got lost)
                    item.setVisible(True)
                    item.setSelected(True)
                    
                    # 4. Sync Handles & Repaint
                    if hasattr(item, 'update_handles'):
                        item.update_handles()
                    
                    item.update()
                    self.canvas.scene.update()
                    self.canvas.viewport().update()
                    break
                


    def on_geometry_changed(self, layer_id, px, py, pw, ph):
        """canvas tells user has reshaped or moved a rect
           Must get permission befor emoving a locked (manual mask edited) layer   
        """
        if not self.session: return
        
        # 1. RETRIEVE LAYER
        layer = self.session.layers.get(layer_id)
        if not layer: return

        # 2. CHECK FREEZE GUARD
        if layer.is_frozen:
            should_move = CustomDialog.question(
                self, 
                "Modify Painted Layer?", 
                f"The layer '{layer.name}' has manual mask edits.\n\n"
                "Moving it will misalign your painted mask. Continue?",
                ok_text="Move Anyway", 
                cancel_text="Cancel"
            )

            if not should_move:
                self._snap_back_layer_rect(layer_id)
                print("returned from _snap_back_layer_rect")
                return # STOP. Do not update backend.

        # 3. PROCEED (Normal Update)
        nx, ny, nw, nh = self._pixels_to_normalized(px, py, pw, ph)
        
        if hasattr(self.session, 'update_layer_bounds'):
            self.session.update_layer_bounds(layer_id, nx, ny, nw, nh, is_final=True)
            
        # If user forced a move, clear the mask and unfreeze
        if layer.is_frozen: 
             if hasattr(self.session, 'clear_user_mask'):
                 self.session.clear_user_mask(layer_id)
                 layer.is_frozen = False 
        
        self.update_display() 
        if layer_id == self.active_layer_id:
            self.update_mask_preview(layer_id)
    


    def on_layer_selected_from_canvas(self, layer_id):
        self.sidebar.select_layer(layer_id)        
        self.on_layer_selection_changed(layer_id)

    def on_layer_deleted(self, layer_id):
        if not self.session: return
        self.session.delete_layer(layer_id)
        self.sidebar.remove_layer_entry(layer_id)
        self.update_display()

    def on_selection_cleared_from_canvas(self):
        """user has clicked on background on canvas"""
        self.active_layer_id = None
        self.sidebar.clear_selection()
        self.sidebar.set_mask_image(None)
        
        # Apply Unselected State
        self._set_ui_state(self.STATE_UNSELECTED)

    # ============================================================
    # OTHER HANDLERS
    # ============================================================
    def on_undo(self):
        affected_id = self.session.undo()
        self.reset_workspace(target_layer_id=affected_id)

    def on_redo(self):
        affected_id = self.session.redo()
        self.reset_workspace(target_layer_id=affected_id)

    def on_toggle_overlays(self, checked):
        """called when H key is pressed """
        self.canvas.toggle_overlay_visibility(force_hide=checked)

    

    #TODO: move it to somwhere with other toolbar-related  functions 
    def update_overlay_button_state(self, visible):
        """
        Called when Canvas emits 'ui_visibility_changed' (e.g. user pressed 'H').
        Handles the 'Safety Interlock' to prevent blind editing.
        """
        # 1. Sync the Main Toolbar Button visual state
        # (If UI is Visible, Button is Unchecked. If UI is Hidden, Button is Checked)
        was_blocked = self.act_toggle_overlays.blockSignals(True)
        self.act_toggle_overlays.setChecked(not visible)
        self.act_toggle_overlays.setText("👁 Show Boxes" if not visible else "👁 Hide Boxes")
        self.act_toggle_overlays.blockSignals(was_blocked)

        # 2. SAFETY INTERLOCK LOGIC
        if not visible:
            # --- ENTERING CLEAN PREVIEW MODE ---
            
            # Did the user have the mask tool open?
            self._was_mask_editing_before_hide = self.mask_toolbar.is_active()

            # A. If we are currently editing a mask, FORCE IT OFF.
            # We cannot allow painting when boundaries are invisible.
            if self.mask_toolbar.is_active():
                # Setting Checked(False) triggers the 'toggled' signal, 
                # which calls toggle_mask_edit_mode(False), disabling the brush.
                self.mask_toolbar.btn_mask_mode.setChecked(False)

            # B. Disable the Toolbar entirely so user can't re-enable it blindly
            self.mask_toolbar.set_available(False)

        else:
            
            
            # C. Restore Toolbar Availability based on current selection logic
            # Use the single source of truth: our defined states
            is_valid_layer = (
                self.active_layer_id is not None 
                and self.active_layer_id != self.session.BACKGROUND_ID
            )
            self.mask_toolbar.set_available(is_valid_layer)
            # E. RESUME EDITING (The New Feature)
            # If we were editing before, and it's still valid to do so, turn it back on.
            if is_valid_layer and self._was_mask_editing_before_hide:
                self.mask_toolbar.btn_mask_mode.setChecked(True)
                
            # Reset the memory flag
            self._was_mask_editing_before_hide = False


    # End of update_overlay_button_state        

    def on_property_updated(self, layer_id, p_name):
        """A callback passed to Tweaks Panel  """
        self.update_display()
        if p_name and p_name.startswith("mask_"):
            # if mask edge is altered in tweak panel 
            self.update_mask_preview(layer_id)            

    def on_reset_layer(self):
        """Resets all the sliders in teak panel.
           Calls update_display() which sets off a rendering chain 

          called by a button on the left sidebar
        """
        if not self.active_layer_id: return
        self.session.reset_layer(self.active_layer_id)
        self.prop_manager.refresh_for_layer(self.active_layer_id)
        self.update_mask_preview(self.active_layer_id)
        self.update_display()

   

    def on_layer_selection_changed(self, layer_id):
        """Called when user selects a different layer from canvas or Sidebar.

            Changes tweakpanel and mask but does nto need to render image anew        
        """
        # 1. Handle Deselection
        if not layer_id:
            self.active_layer_id = None
            self.canvas.set_active_layer(None) # Clear canvas highlight
            self._set_ui_state(self.STATE_UNSELECTED)
            return
            
        # 2. Update Active ID
        self.active_layer_id = layer_id
        
        # 3. SYNC CANVAS HIGHLIGHT
        # move the yellow border in canvas
        # note-- canvas.set_active_layer blocks signal  so there will be 
        # no infinite loop even if this function is called by on_layer_selected_from_canvas
        self.canvas.set_active_layer(layer_id)
        
        # 4. Refresh Managers
        self.prop_manager.refresh_for_layer(layer_id)
        
        # Optional: If you want to see the red mask for the newly selected layer immediately
        self.update_mask_preview(layer_id)
        
        # 5. Set Correct UI State
        if layer_id == self.session.BACKGROUND_ID:
            self._set_ui_state(self.STATE_BACKGROUND)
        else:
            self._set_ui_state(self.STATE_LAYER)
            

    def on_layer_item_changed(self, layer_id, is_checked):
        """ when the checkbox state in layer list changes"""
        layer = self.session.layers.get(layer_id)
        if not layer: return

        if layer.is_background:            
            layer.state.adjustments_enabled = is_checked
        else:            
            layer.visible = is_checked
            
        self.update_display()
        if layer_id == self.active_layer_id:
            self.prop_panel.setEnabled(is_checked)


    def get_quality_preference(self, qual:int):
        """for final jpeg image"""
        q= qual if  qual>=85 and qual<=100 else 95
        return q

    
    # with preferences support 
    def on_export(self):
        """
        Called when user tells to export the final result 

        1. Shows a file dialog and Gets the Export path from user 
        2. Calls ExportManager.startExport to save the image asynchronously and atomically         
        
        """

        if not self.session: return

        

        # 1. Determine Source Path (if available) for logic calculations
        current_src = self.session.source_path if hasattr(self.session, 'source_path') else None

        # 2. Get the Directory based on User Preference
        # (Same as Source, Last Used, Pictures, or Custom)
        save_dir = self.settings_manager.get_save_directory(current_src)
        
        # 3. Construct Default Filename
        # We try to preserve the original extension and append the App Name
        default_name = "output.jpg"
    
        
        if current_src:
            base_name = os.path.splitext(os.path.basename(current_src))[0]
            ext = os.path.splitext(current_src)[1]
            
            # If extension is weird or missing, default to .jpg
            if not ext: ext = ".jpg"
            
            default_name = f"{base_name}_{APP_NAME}{ext}"
            
        # Combine directory and filename for the Dialog
        # If save_dir is empty (Last Used), QFileDialog handles it automatically.
        full_suggested_path = os.path.join(save_dir, default_name) if save_dir else default_name   
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Final Image", full_suggested_path, "Images (*.jpg *.jpeg *.png)")
        if not file_path: return
        
        # backend cannot access preferences which are tied to ui/platform  
        #self.export_manager.set_quality_preference(self.settings_manager.jpeg_quality)
        self.session.jpeg_quality= self.get_quality_preference(self.settings_manager.jpeg_quality)

        self.export_manager.set_session(self.session) #rahul
        
        self.export_manager.start_export(file_path)


    # ============================================================
    # DRAG & DROP + UTILS
    # To allow dropping of image files on to anywhere in the window  
    # Including canvas 
    # ============================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                path = urls[0].toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.toggle_canvas_dimming(True)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.toggle_canvas_dimming(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.toggle_canvas_dimming(False)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._attempt_load_image(path)

    def closeEvent(self, event: QCloseEvent):
        """called when window is closed (Exit)"""
        should_exit = CustomDialog.question(
            self, "Exit Photoglimmer?", "Are you sure you want to quit?",
            ok_text="Exit", cancel_text="Stay"
        )
        if should_exit: event.accept()
        else: event.ignore()

    def resizeEvent(self, event):
        self.overlay.resize(self.size())
        super().resizeEvent(event)

   
    # Refactored to prevent hide ui button glowing up during exit:
    def toggle_canvas_dimming(self, active):
        """
        Toggles the 'Grayed Out' visual state of the canvas.
        Needed when shwing modal dialog or overlay when exporting image 
        Includes logic to preserve the original visibility state.
        """
        # 1. Block Signals
        # We don't want temporary dimming to trigger the "H" key logic (Toolbar updates)
        was_blocked = self.canvas.blockSignals(True)
        
        if active:
            # A. Cache the current state before we mess with it
            # (Did the user already have items hidden?)
            self._pre_dim_hidden_state = getattr(self.canvas, 'items_hidden', False)

            # B. Force Hide for clean look behind dialog
            self.canvas.toggle_overlay_visibility(force_hide=True)
            self.canvas.setEnabled(False)
            
            # C. Apply Grayscale visual effect
            if not getattr(self, 'gray_effect', None):
                self.gray_effect = QGraphicsColorizeEffect()
                self.gray_effect.setColor(QColor(100, 100, 100)) 
                self.gray_effect.setStrength(0.8)
                self.canvas.setGraphicsEffect(self.gray_effect)
        else:
            # A. Restore to the ORIGINAL state (not just force show)
            # If user had items hidden before dialog, keep them hidden.
            restore_hidden = getattr(self, '_pre_dim_hidden_state', False)
            self.canvas.toggle_overlay_visibility(force_hide=restore_hidden)
            
            self.canvas.setEnabled(True)
            
            # B. Cleanup Effect
            self.canvas.setGraphicsEffect(None)
            if hasattr(self, 'gray_effect'):
                del self.gray_effect
        
        # 2. Restore Signals
        self.canvas.blockSignals(was_blocked)


    def show_status(self, message, timeout=3000):
        """show a message in window with timeout. use 0 for display_till_overwritten"""
        if self.status_bar :
            self.status_bar.showMessage(message, timeout)

    def update_zoom_status(self, scale):
        percentage = int(scale * 100)
        self.show_status(f"Zoom: {percentage}%")    

    def on_open_file_location(self):
        if self.session and self.session.source_path:
            GuiUtils.open_browser(self.session.source_path)

    def on_open_preferences(self):
        """
        Opens the Preferences Dialog.
        Reloads local settings cache if changes were saved.
        """
        # Local import to prevent circular dependency issues
        from .components.PreferencesDialog import PreferencesDialog
        from .managers.ThemeManager import ThemeManager
        
        dlg = PreferencesDialog(self)
        if dlg.exec():
            # === CRITICAL STEP ===
            # The Dialog wrote new values to Disk (QSettings).
            # But our MainWindow.settings object still holds the OLD values in RAM.
            # We must force a reload so we see the changes immediately.
            self.settings_manager.load_from_disk()
            
            # 1. Apply Theme immediately
            # (No restart needed for color changes)
            ThemeManager.apply_theme(self, self.settings_manager.theme)
            
            # 2. Notify User
            self.show_status("Preferences Saved", 2000)


    def open_original_in_system_viewer(self):
        """Launches the current source image in the OS default viewer."""
        if not self.session or not self.session.source_path:
            return
            
        # QUrl.fromLocalFile handles path formatting (forward/back slashes) automatically
        file_url = QUrl.fromLocalFile(self.session.source_path)
        QDesktopServices.openUrl(file_url)       

    

    


    def showEvent(self, event):
        """
        Triggered automatically by Qt when the window appears.
        This guarantees the Layout has the correct screen dimensions.
        """
        super().showEvent(event)
        
        if self._pending_initial_zoom:
            # We use a tiny delay (50ms) to let the layout engine 
            # finish snapping widgets to the grid before we calculate zoom.
            QTimer.singleShot(50, self.canvas.zoom_reset)
            self._pending_initial_zoom = False


    def center_on_screen(self):
        """
        Centers the window on the available screen geometry (accounting for taskbars).
        """
        
        screen_geo = self.screen().availableGeometry() #desktop excludes taskbar       
        window_geo = self.frameGeometry() #window geometry        
        window_geo.moveCenter(screen_geo.center()) #calculate
        self.move(window_geo.topLeft()) #move


    

    def open_help(self):
        # 1. Check if window exists and is "alive"
        if hasattr(self, 'help_window') and self.help_window is not None:
            # If it's already open, just bring it to the front
            self.help_window.raise_()
            self.help_window.activateWindow()
            return

        # 2. Create Fresh Instance
        self.help_window = HelpDialog(self)
        
        # 3. listen for close of help window , so you can remove ref to it
        # help window is a bit big, I want to remove it from memory
        self.help_window.finished.connect(self._on_help_closed)
        
        self.help_window.show_guide()

    def _on_help_closed(self):
        """Callback to release memory reference to help window"""
        self.help_window = None



    def show_about(self):
        # Local import to avoid circular dependencies
        from .components.AboutDialog import AboutDialog
        
        dlg = AboutDialog(self)
        dlg.exec() # Modal execution    


    def  set_window_size(self):
        """Either show a 1600 x 900 size mani window fir to the small screen size """
        # Calculate available geometry (Screen size minus Taskbars/Docks)
        screen_geo = self.screen().availableGeometry()
        
        # Desired Size
        target_w, target_h = 1600, 900
        
        # Use the smaller of the two dimensions to ensure no overflow
        # We subtract a small buffer (e.g., 20px) to be safe regarding window borders
        final_w = min(target_w, screen_geo.width() - 20)
        final_h = min(target_h, screen_geo.height() - 50) # More buffer for title bar

        self.resize(final_w, final_h)
        self.center_on_screen()    

    def on_layer_limit_hit(self, limit):
        # Shows a message in the bottom bar for 3 seconds
        self.show_status(f"Layer limit reached: Max {limit} layers allowed ! ", 3000) 


    def cancel_export(self):
        print("mainwindow- cancel export")
        self.show_status("Cancelling Export..." , 5000)
        self.session.request_abort_export()  








########################################################################################
# A Helper message to find any memory leaks 
# is not part of mainwindow
# call it in  _perform_load after one session is closed and before new one is loaded
# Note :Also check this x aborting the export thread !

# DO NOT DELETE !
#######################################################################################

def inspect_leaked_objects(label="Snapshot"):
    """
    Comprehensive leak detective:
    1. Summarizes key instance counts and large NumPy arrays.
    2. Deep-traces referrers for any surviving ImageSession.
    """
    print(f"\n{'='*20} {label.upper()} LEAK INSPECTION {'='*20}")
    
    gc.collect()
    objects = gc.get_objects()
    
    # 1. Summary Tracking
    targets = {
        'ImageSession': 0,
        'RenderEngine': 0,
        'ExportrenderEngine': 0,
        'ExportWorker': 0
    }
    large_arrays = []
    leaked_sessions = []

    # Single pass through the heap
    for obj in objects:
        obj_type = type(obj)
        name = obj_type.__name__
        
        # Track our core classes
        if name in targets:
            targets[name] += 1
            if name == 'ImageSession':
                leaked_sessions.append(obj)
            
        # Track heavy NumPy arrays (> 10MB)
        if isinstance(obj, np.ndarray):
            size_mb = obj.nbytes / (1024 * 1024)
            if size_mb > 10:
                large_arrays.append((obj.shape, obj.dtype, size_mb))

    # --- PART A: SUMMARY REPORT ---
    for cls_name, count in targets.items():
        print(f"  {cls_name:20} instances in RAM: {count}")

    print(f"  Large NumPy arrays (>10MB) in RAM: {len(large_arrays)}")
    for shape, dtype, mb in sorted(large_arrays, key=lambda x: x[2], reverse=True):
        print(f"    - {mb:.2f} MB | {shape} | {dtype}")
    
    # --- PART B: REFERRER TRACING (Only if Sessions exist) ---
    if leaked_sessions:
        print(f"\n--- DEEP TRACE: {len(leaked_sessions)} LEAKED SESSION(S) ---")
        for session in leaked_sessions:
            print(f"FOUND LEAKED SESSION ID: {id(session)}")
            
            # Find what is holding this session
            referrers = gc.get_referrers(session)
            for ref in referrers:
                # Ignore internal trackers
                if ref is objects or ref is leaked_sessions: 
                    continue
                
                print(f"  Held by: {type(ref)} | ID: {id(ref)}")
                
                # If held by a dict, find the object that owns that dict
                if isinstance(ref, dict):
                    for parent in gc.get_referrers(ref):
                        # Avoid cyclical reporting of the same session
                        if parent is session: continue
                        print(f"    Owner of dict: {type(parent)}")
    
    print(f"{'='*55}\n")

    