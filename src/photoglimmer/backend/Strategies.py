# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# This file contains the two Default strategies 
# Other optional strategies can be found in backend.strategies
# Each Strategy represents one operation/filter/tweak that this app can perform  
# These operations are called Strategies only because they follow the strategy design pattern

# These default strategies do not use the specialized nested mask so their masking and blending 
# is handled directly by RenderEngine / ExporRenderEngine
# If you want to develop any new strategy , you should create a separate file in backend/strategies/
# see  AdjustmentStrategy in Interfaces.py to understand the structure/contract  

# #######################################################################




from  .Interfaces import AdjustmentStrategy
from .engines.BlendEngine import BlendEngine
import cv2
import numpy as np
# from memory_profiler import profile
# from line_profiler import profile




########################################################################
# 1. Blurring
########################################################################


class BlurStrategy(AdjustmentStrategy):
    def get_metadata(self):
        # what the auto-generated ui panels will show 
        return {
            "amount": {
                "type": "slider",
                "range": (0.0, 100.0), # Expanded range for more flexibility
                "label": "Blur Intensity",
                "default": 0.0
            }
        }

    
    def apply(self, image, mask, params, scale_factor, cache=None):
        # algorithm for this tweak 
        intensity = params.get("amount", 0.0)
        if intensity <= 0:
            return image

        # 1. Normalized Scaling
        # We want 'intensity 10' to look the same on a 1000px proxy and 8000px export.
        # REFERENCE_WIDTH is the 'logical' width where the slider feels 1:1.
        REFERENCE_WIDTH = 2000.0 
        current_width = image.shape[1]
        
        # Calculate the multiplier based on actual resolution
        res_scale = current_width / REFERENCE_WIDTH
        
        # 2. Determine Sigma (The 'True' Blur intensity)
        # Sigma controls the bell curve; k_size is just the window.
        sigma = intensity * res_scale
        
        # 3. Calculate Kernel Size (Standard rule: 6 * sigma + 1)
        k_size = int(6 * sigma) | 1  # Ensures it's odd via bitwise OR
        
        # Constrain k_size to something reasonable (e.g., 5% of width) to prevent crashes
        max_k = int(current_width * 0.05) | 1
        k_size = min(k_size, max_k)

        # 4. Apply Gaussian Blur
        # Passing sigma instead of 0 for precision
        return cv2.GaussianBlur(image, (k_size, k_size), sigmaX=sigma)
    
    

##############################################################################
# 2. Classic Color Tweaking Brightness + Saturation + Contrast
##############################################################################

class ColorEnhanceStrategy(AdjustmentStrategy):
    def get_metadata(self):
        return {
            'brightness': {'type': 'slider', 'range': (0.0, 2.0), 'default': 1.0, 'label': 'Brightness'},
            'saturation': {'type': 'slider', 'range': (0.0, 2.0), 'default': 1.0, 'label': 'Saturation'},
            'contrast': {'type': 'slider', 'range': (0.5, 2.0), 'default': 1.0, 'label': 'Contrast'}
        }
    

    #@profile
    def apply(self, patch, mask, params, scale_factor, cache=None):
        # 1. Make sure we are needed to run this , or return 
        sat = params.get('saturation', 1.0)
        con = params.get('contrast', 1.0)
        bri = params.get('brightness', 1.0)
        if abs(sat - 1.0) < 0.01 and abs(con - 1.0) < 0.01 and abs(bri - 1.0) < 0.01:
            return patch

        # 2.Perform the thig.  Do  TILED blending  for EVERYTHING to reduce memory        
        h, w = patch.shape[:2]
        tile_size = 2048
        final = np.zeros_like(patch) # Or patch.copy() if you prefer safety
        
        alpha_v = con * bri
        beta_v = 127.5 * (1.0 - con) * bri

        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                y2, x2 = min(h, y + tile_size), min(w, x + tile_size)
                
                # Slice views (0 MB cost)
                p_tile = patch[y:y2, x:x2]
                m_tile = mask[y:y2, x:x2]

                # --- Apply Adjustments to Tile ---
                # This only creates a ~12MB buffer for the tile
                e_tile = cv2.convertScaleAbs(p_tile, alpha=alpha_v, beta=beta_v)
                
                if abs(sat - 1.0) > 0.01:
                    g = cv2.cvtColor(e_tile, cv2.COLOR_BGR2GRAY)
                    g3 = cv2.merge([g, g, g])
                    e_tile = cv2.addWeighted(e_tile, sat, g3, 1.0 - sat, 0)

                # --- Blend Tile ---
                # Using the fast_mask_blend on a SMALL tile
                final[y:y2, x:x2] = BlendEngine.fast_mask_blend(p_tile, e_tile, m_tile)

        return final



    ############################################################################
    #  A helper  method that can directly be used by imagesession to register these default strategies 
    #  Any other strategies can  imported form their own files and added to registry by ui
    # The ImageSession generally uses this format - `self.strategies["tonalbalance"] = TonalBalanceStrategy()`
     ############################################################################
def get_default_strategies():
    """Returns the registry of available effects."""
    return {
        "color": ColorEnhanceStrategy(),
        "blur": BlurStrategy()
    }
