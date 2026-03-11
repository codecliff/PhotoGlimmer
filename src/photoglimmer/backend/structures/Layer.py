# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# Layers are the main pixel data repository for our application 
# each layer represents one rectanfgular area selected by the user
# we are caching a lto of image slice and mask data with each layer
# background too is a layer 
# UI usually addresses layer as frame , for the sake of user 

# #######################################################################


import numpy as np
from typing import Dict, Any

# ==========================================
# DATA STRUCTURES
# Layer: Represents a specific subject/area in the image
# ==========================================

class LayerState:
    def __init__(self, is_background=False):
        # We initiate the values that do not belong to strategy, but are hardcoaded 
        # Ensure that these values match PropertyManager or Strategy 
        # Else you risk triggering mask generation even if only brightness slider changes
        self.adjustments: Dict[str, Any] = {"threshold": 0.5}
        self.opacity, self.visible = 1.0, True
        self.mask_feather: float = 30.0  
        
        self.mask_expand: int = 0
        self.mask_contrast: float = 1.0
        self.effect_strength: float = 1.0

        self.adjustments_enabled = True # in our UI, is the layer checked in layer list? 

        # we need to lock some things form the bckground layer 
        if is_background:
            self.opacity = 1.0           # Background must be opaque
            self.mask_feather = 0.0      # Background cannot have soft edges
            self.mask_expand = 0
            self.mask_contrast = 1.0     # Keep mask sharp
                               

class Layer:
    def __init__(self, layer_id, proxy_patch, bounds, temp_dir, is_background=False, name="Layer"):
        self.layer_id = layer_id
        self.name = name
        self.proxy_patch = proxy_patch  # The original image pixels
        self.bounds = bounds            # (x, y, w, h)
        self.temp_dir = temp_dir        # to be used if we ever opt for disk caching
        self.state = LayerState(is_background)
        
        self.raw_mask = None            # To be filled by _generate_layer_mask
        
        # --- User Manual addition/subtraction to Masks ---
        self.user_added_mask = None       
        self.user_subtracted_mask = None

        # --- Strategy Cache ---
        # Used for strategy-specific persistent data (e.g. Gaffer3D geometry)
        self.strategy_cache = {}

        self.visible = True
        
        # background layer is to be treaded differently , set a flag 
        self.is_background = is_background
        self.is_frozen = False  

    def release_resources(self):
        """Explicitly clears all heavy RAM-resident data for this layer."""
        if hasattr(self, 'strategy_cache'):
            self.strategy_cache.clear()
        
        self.proxy_patch = None
        self.raw_mask = None
        self.user_added_mask = None
        self.user_subtracted_mask = None

        