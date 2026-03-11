# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# ###############################################################################
# ImageSession is the only class in backend that the UI has to talk to 
# Works as the  bookkeeper of state as well as the controller of all the other backend compnents

# Terminology : Patch = buffer a.k.a ndarray 
# ###############################################################################





# ==========================================
# IMPORTS 
# ==========================================

# Python core 
import os
import gc
import shutil
import tempfile
import time
import uuid
import logging
import importlib
from typing import Dict, Any
try:
    import psutil #for RAM
except ImportError:
    psutil = None

# this application's python  requirements   
import numpy as np
import cv2  




# Profiling
# from  line_profiler import profile
#from memory_profiler import profile


# INTERNAL IMPORTS
#  Interfaces file is single source of truth for App's name 
from .Interfaces import APP_NAME


from .structures.Layer import Layer, LayerState
from .engines.MaskEngine import MaskEngine
from .engines.RenderEngine import RenderEngine
from .engines.ExportrenderEngine import ExportrenderEngine
from .engines.ExifEngine import ExifEngine
from .FaceMesh import FaceMeshService



# imports from concrete implementations 
from .Commands import (
    UpdateParamCommand, 
    UpdatePropertyCommand, 
    UpdateGeometryCommand, 
    AddLayerCommand, 
    DeleteLayerCommand
)


#  Import default strategies  # BlurStrategy, ColorEnhanceStrategy 
from .Strategies import  get_default_strategies  

# Import non-core strategies which we keep in strategies folder 

from .strategies.SmartSkin import SmartSkinStrategy
from .strategies.WhiteBalance import WhiteBalanceStrategy
from .strategies.AutoWhiteBalance import AutoWhiteBalanceStrategy
from .strategies.ParaBright import ParaBrightStrategy
from .strategies.BezierBright import BezierBrightStrategy
from .strategies.Gaffer3D import Gaffer3DStrategy
from .strategies.EyeEnhance import EyeEnhancerStrategy
from .strategies.ToneBalance import TonalBalanceStrategy

# segmentation engine 
from .Segmenters import MediaPipeSelfieSegmenter

# History Manger which aslo handles strategy calls 
from .CommandProcessor import CommandProcessor

# # Logging 
# from .LoggerSetup import setup_session_logging
# # Module level logger - name matches LoggerSetup
# logger = logging.getLogger(APP_NAME)

######################################################################
# Logging Setup
######################################################################
import logging  
#   automatically inherits the File+Console handlers we set up in __main__
logger = logging.getLogger(__name__)

######################################################################
# Importing STRATEGIES  IN FAULT TOLERANT MANNER 
# this will allow the application to launch even if some imported strategy file has errors
######################################################################
# 1. Define the plugins  
#    Format: (Module Path, Class Name, ID Key)
# PLUGIN_MANIFEST = [
#     
#     (".strategies.SmartSkin", "SmartSkinStrategy", "smart_skin"),
#     (".strategies.WhiteBalance", "WhiteBalanceStrategy", "white_balance"),
#     (".strategies.AutoWhiteBalance", "AutoWhiteBalanceStrategy", "auto-wb"),
#     (".strategies.ParaBright", "ParaBrightStrategy", "parabright"),
#     (".strategies.BezierBright", "BezierBrightStrategy", "selective"),
#     (".strategies.FaceRelightStrategy", "FaceRelightStrategy", "face_relight"),
# ]



# =====================================================================
# CORE IMAGE SESSION. ENTRY POINT AND CONTROLLER FOR BACKEND  OPERATION
# =====================================================================

class ImageSession:

    BACKGROUND_ID = "__bg__"

    # Supported Extensions (Centralized here for consistency)
    VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}



    # @profile
    def __init__(self, source_path: str, proxy_width: int = 1024): #2048
        
        self.temp_dir = None # tempfile.mkdtemp(prefix="img_session_")

        self.logger = logger #setup_session_logging() #TODO: Check  

        if source_path:
            self.source_path = source_path
        
        # self.source_path = source_path

        self.jpeg_quality=95

        # Use OpenCV to load the image (BGR format)
        self.source_img = cv2.imread(source_path)
        if self.source_img is None:
            raise FileNotFoundError(f"Could not load image: {source_path}")

        # Calculate proxy scale
        h, w = self.source_img.shape[:2]
        self.scale_factor = proxy_width / float(w)
        proxy_height = int(h * self.scale_factor)

        self.proxy_size = (proxy_width, proxy_height) 
        
        # Create the proxy image for the UI
        self.proxy_img = cv2.resize(self.source_img, (proxy_width, proxy_height), 
                                    interpolation=cv2.INTER_AREA)
        

        self.mask_engine = MaskEngine()
        
        self.layers = {}
        
        # registry of strategies
        # This registry dict also sets the order of apperance of strategies in UI
        #  (unless frontend reorders them)
        # the execution order will be set by each strategy's priority (low to high)
         
        self.strategies = get_default_strategies() 
        #{      "color": ColorEnhanceStrategy(), 
        #       "blur": BlurStrategy() }  
        #      

        # 2. Append Specialized AI Strategies
        # We add them to the dictionary with a unique key
        #self.strategies["selective"] = BezierBrightStrategy()
        #self.strategies["parabright"] = ParaBrightStrategy()
        self.strategies["tonalbalance"] = TonalBalanceStrategy()

        self.strategies["smart_skin"] = SmartSkinStrategy() 
        
        self.strategies["facelight3D"] = Gaffer3DStrategy()      
        self.strategies["eyesparks"] = EyeEnhancerStrategy()

        
        self.strategies["whitebalance"]= WhiteBalanceStrategy()
        self.strategies["auto_wb"]= AutoWhiteBalanceStrategy()


        # # Load Plugins and merge
        # plugins = self.load_plugins(PLUGIN_MANIFEST)
        # self.strategies.update(plugins)
        


        # Initialize Engines
        self.mask_engine = MaskEngine()
        self.render_engine = RenderEngine(self.strategies)
        self.export_engine = ExportrenderEngine()
        self.export_engine.set_logger(self.logger)
        
        
        
        
        self.cmd_processor = CommandProcessor()
        

        # --- REFACTOR: Background is now a true Layer ---
        
        # 1. Define bounds covering the entire canvas (x=0, y=0)
        bg_bounds = (0, 0, proxy_width, proxy_height)

        # 2. Instantiate the Layer
        # We pass is_background=True so UI/Render logic can identify it later
        bg_layer = Layer(
            layer_id=self.BACKGROUND_ID,
            proxy_patch=self.proxy_img,  # The patch is the full image
            bounds=bg_bounds,
            temp_dir=self.temp_dir,
            is_background=True
        )

        # 3. Create the Mask (Solid White = 100% Opacity everywhere)
        # We do this manually because we aren't running segmentation on the background
        #import numpy as np
        bg_layer.raw_mask = np.full((proxy_height, proxy_width), 255, dtype=np.uint8)

        # 4. Pre-fill Strategy Defaults
        # This ensures the sliders start at neutral positions
        for s_key, strategy in self.strategies.items():
            meta = strategy.get_metadata()
            for param, info in meta.items():
                bg_layer.state.adjustments[param] = info.get('default', 1.0)

        # 5. Store it in the main dictionary
        self.layers[self.BACKGROUND_ID] = bg_layer

        # registry of segmenters
        self.segmenters = {"mediapipe": MediaPipeSelfieSegmenter()}
        self.active_segmenter_key = "mediapipe"


        # Load and Sanitize Metadata once
        self.exif_data = self.exif_data = ExifEngine.load_safe_exif(source_path,strip_gps=False)
        #self._initialize_exif(self.source_path)



    # end of __init__     
    
    
   
    # =====================================================================
    # CORE LOGIC  : Layer Management - Create, delete, alter
    # =====================================================================

    # --- helper to Generate segmentation mask for a layer  ---
    def _generate_layer_mask(self, lid):
        """
        Generates the initial raw mask (Probability Map).
        Stays in ImageSession as it modifies Layer State directly.
        """
        layer = self.layers.get(lid)
        if not layer: return

        # 1. Identify the Segmenter
        engine = self.segmenters.get(self.active_segmenter_key)
        
        try:
            # 2. Run AI (Returns 0-255 Soft Mask)
            # This is the "SegmenterStrategy" interface we defined  
            mask = engine.segment(layer.proxy_patch, layer.state.adjustments)
            
            # 3. Store Result
            layer.raw_mask = mask
            
            # Clear the refinement cache since we have a brand new raw mask
            layer.strategy_cache.clear()
            
            self.logger.info(f"Generated raw mask for {lid}")

        except Exception as e:
            self.logger.error(f"Mask Gen Error {lid}: {e}")
            # Fallback: Empty Black Mask
            layer.raw_mask = np.zeros((layer.bounds[3], layer.bounds[2]), dtype=np.uint8)



    

    

    def create_layer(self, nx, ny, nw, nh):
        """
        Creates a new layer by slicing the proxy image array.
        nx, ny, nw, nh: Normalized coordinates (0.0 to 1.0)
        """
        # 1. Convert normalized coordinates to pixel coordinates
        proxy_h, proxy_w = self.proxy_img.shape[:2]
        px = int(nx * proxy_w)
        py = int(ny * proxy_h)
        pw = int(nw * proxy_w)
        ph = int(nh * proxy_h)

        # 2. Slice the NumPy array (Crop)
        # NumPy uses [row_start:row_end, col_start:col_end] -> [y:y+h, x:x+w]
        patch = self.proxy_img[py:py+ph, px:px+pw].copy()

        # 3. Generate a unique Layer ID
        # lid = f"layer_{len(self.layers)}_{int(time.time())}"
        lid = f"layer_{len(self.layers)}_{int(time.time())}" 
        # Friendly layer name for UI        
        count = len([l for l in self.layers.values() if not l.is_background]) + 1
        friendly_name = f"Frame {count}" # List will show  it as Frame for user's benefit
        
        # 4. Initialize the Layer object
        # Passing the NumPy patch directly
        layer = Layer(
            layer_id=lid,
            proxy_patch=patch,
            bounds=(px, py, pw, ph),
            temp_dir=self.temp_dir,  # TODO: check if needed here 
            name=friendly_name
        )

        self.layers[lid] = layer
        
        # 5. Kick off initial mask generation
        self._generate_layer_mask(lid)
        
        return lid
    

    
    # In backend/ImageSession.py
    # @profile
    def add_new_layer(self, nx=None, ny=None, nw=None, nh=None):
        """
        Creates a new layer.
        STRICTLY expects Normalized Coordinates (0.0 to 1.0).
        Rejects Pixel Coordinates to prevent memory crashes.
        """
        # 1. Logic for Defaults (Button Click)
        if nx is None:
            # Default Center Box
            nx, ny, nw, nh = 0.25, 0.25, 0.5, 0.5

        # --- SAFETY GUARD (STRICT NORMALIZATION CHECK) ---
        # If any value is > 1.0, the caller passed Pixels instead of Normalized Floats.
        # We must catch this before 'create_layer' multiplies it by image width.
        if nx > 1.01 or ny > 1.01 or nw > 1.01 or nh > 1.01:
            self.logger.error(
                f"CRITICAL: add_new_layer received Pixel values instead of Normalized!"
                f" Received: ({nx}, {ny}, {nw}, {nh})."
                f" Expected values between 0.0 and 1.0."
            )
            return None # Abort immediately

        # 2. Clamp to safe 0.0-1.0 range (in case of minor float errors)
        nx = max(0.0, min(nx, 1.0))
        ny = max(0.0, min(ny, 1.0))
        nw = max(0.001, min(nw, 1.0)) # Width must be > 0
        nh = max(0.001, min(nh, 1.0)) # Height must be > 0
        
        # 3. Create the Layer
        # Now we know create_layer will receive safe floats (e.g. 0.5), 
        # so 0.5 * 1000 = 500px (Safe).
        layer_id = self.create_layer(nx, ny, nw, nh)
        
        # 4. Push to History 
        #from .ImageSession import AddLayerCommand 
        cmd = AddLayerCommand(self, layer_id)
        self.cmd_processor.push(cmd)
        
        self.logger.info(f"Added new layer: {layer_id} at ({nx:.2f}, {ny:.2f})")
        return layer_id
    
    def delete_layer(self, layer_id):
        """
        Deletes a layer by ID.
        Supports Undo/Redo.
        Prevents deletion of the Background layer.
        """
        # 1. Validation
        if layer_id not in self.layers:
            self.logger.warning(f"delete_layer: Layer {layer_id} not found.")
            return

        if layer_id == self.BACKGROUND_ID:
            self.logger.warning("delete_layer: Cannot delete the Background layer.")
            return

        # 2. Execute via Command (enables Undo)
        # Ensure DeleteLayerCommand is visible here
        # If defined in the same file, this import might not be needed, 
        # but keeps it consistent with your other methods.
        # from .ImageSession import DeleteLayerCommand 
        
        cmd = DeleteLayerCommand(self, layer_id)
        self.cmd_processor.push(cmd) 
        # Note: history.push() calls cmd.execute() automatically, 
        # so the layer is deleted from the dict immediately.

            

    def update_layer_param(self, layer_id, strat_key, param_key, value, is_final=False, old_val=None):
        """
        Updates the dictionary values associated with a layer.
        
        Refactored: Unified logic for Background and Standard Layers.
        Both are now accessed via self.layers.
        """
        
        # 1. Validate Layer Existence
        # This now successfully finds the Background layer too!
        if layer_id not in self.layers:
            return

        layer = self.layers[layer_id]

        # 2. Handle Final Update (Slider Release) -> History
        if is_final:
            # We only create a command and push to history on release
            #from .backend.Commands import UpdateParamCommand # Adjusted import path if needed
            
            # Create command for Undo/Redo
            # This works for background too, assuming UpdateParamCommand stores/restores 'layer.state'
            cmd = UpdateParamCommand(layer_id, layer, strat_key, param_key, old_val, value)
            self.cmd_processor.push(cmd)
            #self.logger.info(f"UNDO PUSHED: {cmd}")

            # Ensure the value is permanently set in the state as well
            if strat_key not in layer.state.adjustments:
                layer.state.adjustments[strat_key] = {}
            layer.state.adjustments[strat_key][param_key] = value

        # 3. Handle Live Update (Slider Dragging) -> Rendering
        else:
            # Update the transient state for real-time rendering
            if strat_key not in layer.state.adjustments:
                layer.state.adjustments[strat_key] = {}
            
            # This updates the value for both Background and Standard layers
            layer.state.adjustments[strat_key][param_key] = value
            
            # We don't log 'live' ticks to avoid bloating the log file


    
    def update_layer_property(self, layer_id, prop_name, value, is_final=False, old_val=None):
        """
        Updates core layer properties (opacity, strength, feather).

        This is as good as calling a function directly 
        eg `session.update_layer_property(woman_id, "mask_expand", 10)`

        Therefore, also called by UI on each slider change and on release.
        By `onChange` and `onRelease` callbacks.
        Called for each slider tick, committed to history stack only on slider release.
        Logs and records history only when is_final=True.
        """
        if layer_id not in self.layers:
            return
            
        layer = self.layers[layer_id]

        if is_final:
            # Create a Command for the property change
            # from .ImageSession import UpdatePropertyCommand 
            
            cmd = UpdatePropertyCommand(layer_id, layer, prop_name, old_val, value)
            self.cmd_processor.push(cmd)
            #self.logger.info(f"UNDO PUSHED: {cmd}")
        else:
            # Just update the state for the live preview
            setattr(layer.state, prop_name, value)
            # No logging for live ticks

    

    def update_layer_bounds(self, layer_id, nx, ny, nw, nh, is_final=False):
        """
        Public API to move/resize a layer.
        nx, ny, nw, nh: Normalized coordinates (0.0 - 1.0)
        """
        if layer_id not in self.layers: return

        # --- SAFETY GUARD ---
        if nx > 1.01 or ny > 1.01 or nw > 1.01 or nh > 1.01:
            self.logger.error(f"update_layer_bounds received Pixel values! Aborting.")
            return
            
        # Clamp
        nx = max(0.0, min(nx, 1.0))
        ny = max(0.0, min(ny, 1.0))
        nw = max(0.001, min(nw, 1.0))
        nh = max(0.001, min(nh, 1.0))
        # --------------------

        # calculate pixels, history, apply ...
        # 1. Calculate new pixel bounds
        proxy_h, proxy_w = self.proxy_img.shape[:2]
        px = int(nx * proxy_w)
        py = int(ny * proxy_h)
        pw = int(nw * proxy_w)
        ph = int(nh * proxy_h)
        
        new_bounds = (px, py, pw, ph)
        layer = self.layers[layer_id]
        
        if is_final:
            old_bounds = layer.bounds
            old_mask = layer.raw_mask.copy() if layer.raw_mask is not None else None
            # from .ImageSession import UpdateGeometryCommand
            cmd = UpdateGeometryCommand(self, layer_id, old_bounds, new_bounds, old_mask)
            self.cmd_processor.push(cmd)

        self._apply_geometry_change(layer_id, new_bounds)
        
        if is_final:
            self.logger.info(f"Layer {layer_id} resized/moved.")

    
    # ###  Mask Manual  Editing API ###    

    # TODO : move some parts of this menthod  to ui module to remove Qt  
    def apply_mask_stroke(self, layer_id, qimage, mode):
        """
        !!! IMPORTANT: This function is TIGHTLY COUPLED to PySide6. !!!

        Called by UI when a brush stroke is finished.
        Merges the QImage stroke into the layer's persistent user masks.
        Ensures mutual exclusivity: Painting clears erasure, and erasing clears paint.

        
        The 'qimage' argument MUST be a QImage object. 
        Do not call this from non-GUI threads or CLI scripts without refactoring.

        """
        layer = self.layers.get(layer_id)
        if not layer: return

        # 1. Convert QImage to NumPy
        w, h = qimage.width(), qimage.height()
        ptr = qimage.constBits() 
        
        try:
            arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 4))
        except ValueError:
            bpl = qimage.bytesPerLine()
            flat_arr = np.frombuffer(ptr, np.uint8)
            arr = flat_arr.reshape((h, bpl))[:, :w*4].reshape((h, w, 4))
        
        # 2. Extract Mask (Alpha Channel)
        stroke_mask = arr[:, :, 3].copy() 
        _, stroke_mask = cv2.threshold(stroke_mask, 10, 255, cv2.THRESH_BINARY)
        
        # 3. Ensure Target Buffers Exist
        if layer.user_added_mask is None:
            layer.user_added_mask = np.zeros_like(layer.raw_mask)
        if layer.user_subtracted_mask is None:
            layer.user_subtracted_mask = np.zeros_like(layer.raw_mask)

        # 4. Resize Safety
        # (Ensure stroke matches layer dimensions exactly)
        target_h, target_w = layer.user_added_mask.shape[:2]
        if stroke_mask.shape[:2] != (target_h, target_w):
             stroke_mask = cv2.resize(stroke_mask, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

        # 5 Raise Flag which UI can check. Reshaping a layer will remove all amanual edits   
        layer.is_frozen = True    

        # 5. Apply Logic (The Fix)
        if mode == 'add':
            # A. Add pixels to the "Paint" layer
            layer.user_added_mask = cv2.bitwise_or(layer.user_added_mask, stroke_mask)
            
            # B. CRITICAL: Remove pixels from the "Erase" layer
            # "If I am painting here, stop erasing here."
            layer.user_subtracted_mask = cv2.bitwise_and(layer.user_subtracted_mask, cv2.bitwise_not(stroke_mask))
            
        elif mode == 'erase':
            # A. Add pixels to the "Erase" layer
            layer.user_subtracted_mask = cv2.bitwise_or(layer.user_subtracted_mask, stroke_mask)

            # B. CRITICAL: Remove pixels from the "Paint" layer
            # "If I am erasing here, remove any added paint."
            layer.user_added_mask = cv2.bitwise_and(layer.user_added_mask, cv2.bitwise_not(stroke_mask))

            
    def clear_user_mask(self, layer_id):
        """
        Nuke Logic: Clears manual edits when layer is moved/resized.
        """
        layer = self.layers.get(layer_id)
        if layer:
            layer.user_added_mask = None
            layer.user_subtracted_mask = None
            

    

    def _apply_geometry_change(self, layer_id, bounds):
        """
        Updates layer pixel data when moved/resized.
        """
        layer:Layer = self.layers[layer_id]
        layer.bounds = bounds
        px, py, pw, ph = bounds

        # 1. Update Proxy Patch (Slicing Logic)
        # We perform the slicing here because ImageSession owns 'self.proxy_img'
        h, w = self.proxy_img.shape[:2]
        
        # Safe Slicing
        px = max(0, min(px, w-1))
        py = max(0, min(py, h-1))
        pw = max(1, min(pw, w - px))
        ph = max(1, min(ph, h - py))
        
        layer.proxy_patch = self.proxy_img[py:py+ph, px:px+pw].copy()
        
        # 2. Re-run AI (Coordination)
        self._generate_layer_mask(layer_id)
        
        # 3. Clear State
        layer.user_added_mask = None
        layer.user_subtracted_mask = None

        #4. because the layer geometry is changed, there is sure to be no manually edited mask
        layer.is_frozen=False




            

    def reset_layer(self, layer_id):
        """
        Resets all parameters for the given layer to their default neutral states.
        """
        layer = self.layers.get(layer_id)
        if not layer: return

        # 1. Reset Fixed Layer Properties
        # These are the "Engine" properties
        layer.state.opacity = 1.0
        layer.state.effect_strength = 1.0 # 1.0 means "Full Effect", 0.0 means "Original"
        layer.state.adjustments_enabled = True
        
        # 2. Reset Masking Properties
        layer.state.mask_expand = 0
        layer.state.mask_feather = 0
        layer.state.mask_contrast = 1.0 # Default gamma/choke

        # 3. Reset Strategy Parameters (Color, Sharpen, etc.)
        # We look up the 'default' value from the strategy metadata dynamically
        layer.state.adjustments = {} # Clear old overrides
        
        for s_key, strategy in self.strategies.items():
            meta = strategy.get_metadata()
            for param, info in meta.items():
                # Store the default value in the state
                layer.state.adjustments[param] = info.get('default', 1.0)
        
        # ### NEW: Reset User Masks ###
        layer.user_added_mask = None
        layer.user_subtracted_mask = None

        # 4. Clear History for this layer (Optional)
        # Or you could push a "Mass Reset" command if you want Undo support
        self.logger.info(f"Layer {layer_id} reset to defaults.")




    
    
    
    
    #################################################################
    # --- Rendering Pipeline ---
    #################################################################

    # smaller layer should not be overwritten  by layers covering them
    # eg, face layer drawn  within body layer 
    def _get_layers_sorted_by_area(self):
        """
        Returns a list of visible layers sorted specifically for rendering:
        1. Background Layer (Always First/Bottom)
        2. Largest Layers (Body/Background Adjustments)
        3. Smallest Layers (Face/Eye Adjustments - Top)
        
        This implements the 'Painter's Algorithm' automatically.
        """
        # 1. Get the Background Layer
        # We explicitly handle it to ensure it is always index 0
        bg_layer = self.layers.get(self.BACKGROUND_ID)
        
        # 2. Get all other layers
        # (Filter out background to avoid duplicating it)
        standard_layers = [
            l for l in self.layers.values() 
            if not l.is_background and l.visible
        ]
        
        # 3. Sort Standard Layers by Area (Width * Height)
        # reverse=True means Descending Order (Largest -> Smallest)
        # Largest draws first (at the bottom), Smallest draws last (on top).
        standard_layers.sort(key=lambda l: l.bounds[2] * l.bounds[3], reverse=True)
        
        # 4. Combine
        final_list = []
        if bg_layer and bg_layer.visible:
            final_list.append(bg_layer)
            
        final_list.extend(standard_layers)
        
        return final_list

    
    
    #######################################################################
    ## Rendering Image on screen- live and final 
    #######################################################################
    

    def render_proxy(self, show_overlay=False):
        """
        Render the Proxy image. This it the image users see in the canvas as they edit 

        Delegates actual rendering to the RenderEngine.render_scene
        However, it sorts layers so smaller layers get procecessed after larger ones 
        (Face after Whole Person)
        """
        # 1. Get Sorted Layers (ImageSession manages the order)
        sorted_layers = self._get_layers_sorted_by_area()

        # 2. Delegate to Engine
        # We pass 'self.mask_engine' so the renderer can ask for masks on demand
        return self.render_engine.render_scene(
            sorted_layers, 
            self.proxy_size, 
            self.scale_factor, 
            self.mask_engine,
            show_overlay
        )
   
    
    # @profile
    def export_final(self, output_path, max_timeout=120):
        """Export the Final Image. This delegates to ExportEngine which , in 
            an asynchronous manner, First renders the large image then saves it.
            Will be auto-aborted if the process takes longer than max_timeout seconds
            Should be called by UI only after it has a vaid output path. 


        """
        # Delegate entire logic to the engine
        # We pass dependencies (render_engine, mask_engine) so ExportEngine can use them

        #print(f"jpeg qualit will be {self.jpeg_quality}")

        #this variable is necessary for a user-initiated abort
        self._abort_export= False
        
        self.export_engine.run(
            source_img=self.source_img,
            sorted_layers=self._get_layers_sorted_by_area(),
            proxy_size=self.proxy_size,
            output_path=output_path,
            render_engine=self.render_engine,
            mask_engine=self.mask_engine,
            abort_check_callback=self.abort_export_requested,
            max_timeout=max_timeout,
            image_quality=self.jpeg_quality,
            exif_dict=self.exif_data
        )

   
    # These two funcitons together help user-cancellation of export  
    def request_abort_export(self):
        """Sets the flag to stop the export loop midway. """
        self._abort_export = True
        

    def abort_export_requested(self):
        """A callback to be injected into the long run() of ExportRenderEngine

           ExportRenderEngine's heavy lifting rendering loop will periodically 
           call this to check if it has to abort            
         
        """
        if hasattr(self, "_abort_export"):                        
            return  self._abort_export
        else:
            self.logger.info("ImageSession: Cannot request export cancellation. Bad State!") 
            return False


    
    # ###########################################################
    # undo redo with logging 
    # ############################################################

    def undo(self):
        if self.cmd_processor.can_undo():
            
            cmd = self.cmd_processor.undo_stack[-1]
            self.logger.info(f"Action: UNDO -> {cmd}") #use __str__ method of cmd          
            # Perform the actual undo
            self.cmd_processor.undo()
            # RETURN THE ID OF THE AFFECTED LAYER
            # Most commands store 'layer_id' or 'layer.layer_id'                  
            self.logger.debug(f"Successfull Undo for layer {getattr(cmd, 'layer_id', 'unknown')}")
            return getattr(cmd, 'layer_id', None)  
        else:
            self.logger.warning("UNDO requested but undo_stack is empty.")
            return None


        

    def redo(self):
        if self.cmd_processor.can_redo():
            cmd = self.cmd_processor.redo_stack[-1]
            self.logger.info(f"Action: REDO -> {cmd}")            
            self.cmd_processor.redo() 
            self.logger.debug(f"Successfull Redo for layer {getattr(cmd, 'layer_id', 'unknown')}")
            return getattr(cmd, 'layer_id', None) 
        else:
            self.logger.warning("REDO requested but redo_stack is empty.")
            return None


    def is_background(self, layer_id):
        return layer_id == self.BACKGROUND_ID
    


    def get_refined_mask(self, layer):
        """get a feathered/expanded mask from raw mask. uses MaskEngine """
        return self.mask_engine.get_refined_mask(layer)

    def _process_high_res_mask(self, mask_arr, state, scale):
        """feathering etc for large mask, with some resource management  """
        return self.mask_engine.process_high_res_mask(mask_arr, state, scale)
    

    
    

    

    # ##################################################################
    #  Memory Release when closing 
    # #################################################################       
    
    def close(self):
        """
        Deep Cleanup: Breaks all circular references and explicitly clears high-res caches.

        Should be explicitely called by any UI that wants to end one session and 
            start next (say, for loading nest image), for better memory management
        """
        # 1. Abort any active engine work first
        if hasattr(self, 'export_engine'):
            self.export_engine.abort()

        # 2. Clear Layers via their own release_resources()
        if hasattr(self, 'layers'):
            for lid, layer in self.layers.items():
                layer.release_resources() 
            self.layers.clear()

        # 3. Clear Undo/History (Crucial for 50MP stability)
        if hasattr(self, 'undo_stack'):
            self.undo_stack.clear()
            self.undo_stack = None

        # 4. Sever RenderEngine links
        if self.render_engine:
            if hasattr(self.render_engine, 'cache'):
                self.render_engine.cache.clear()
            self.render_engine.session = None 
            self.render_engine = None

        # 5. Nullify huge image buffers
        self.source_img = None
        self.proxy_img = None
        self.rendered_image = None
        self.exif_data = None 
        
        # 6. FaceMeshService cache Flush               
        FaceMeshService().clear_cache()
        
        # 7. Flush OpenCV and Python GC
        # Running it twice to catch circular refs in the second pass
        gc.collect()
        gc.collect()  



    def __del__(self):
        """
        Sanity Check: This prints when Python ACTUALLY destroys the object.
        If you don't see this in your logs, you have a leak.
        """        
        
        print(f"DEBUG: ImageSession {id(self)} has been garbage collected.")




    @staticmethod
    def is_valid_image_path(path):
        """
        Static Utility: Checks if a path is a readable, supported image file.
        Returns the absolute path if valid, or None if invalid.        
        """
        if not path: 
            return None
            
        # 1. Basic Path Checks
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return None
        if not os.path.isfile(path):
            return None
            
        # 2. Check Extension
        _, ext = os.path.splitext(path)
        if ext.lower() not in ImageSession.VALID_EXTENSIONS:
            return None

        # 3. Check Read Permissions
        if not os.access(path, os.R_OK):
            return None
            
        return path
    

    # 2. Helper to load strategies 
    # Thsi takes care of bad imports 
    def load_plugins(self,manifest):
        """A safe way of importing so that one bad strategy does not kill the app before launch 
           In case some imported strategy file is bad 
           Optional  
        """
        loaded = {}
        for mod_path, cls_name, key in manifest:
            try:
                # Dynamically import the module
                module = importlib.import_module(mod_path, package=__package__)
                # Get the class from the module
                cls_ref = getattr(module, cls_name)
                # Instantiate it immediately (or store class ref)
                loaded[key] = cls_ref() 
                logger.info(f"Loaded plugin: {key}")
            except ImportError as e:
                logger.warning(f"Plugin missing: {key} ({e})")
            except Exception as e:
                logger.error(f"Plugin crashed: {key} ({e})")
        return loaded
    




                
            
        


        
        
    


