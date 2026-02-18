# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# A global strategy that tries to apply AWB to whole image 
# Approach - 'Gray World' algorithm and LUT. For speed and control on buffer sizes, mostly
# Note : we are using opencv bundled with mediapipe . so no contrib, no xphoto 
# #######################################################################

import cv2
import numpy as np

from photoglimmer.backend.Interfaces import StrategyScope

class AutoWhiteBalanceStrategy:
    def __init__(self):
        # PRIORITY: 0 (Highest/First)
        # Runs alongside manual White Balance as a fundamental correction.
        self.priority = 0
        
        # CONTRACT: Global strategies are applied to the "Source" of every layer.
        self.isGlobal = True 
        self.scope = StrategyScope.GLOBAL
        
        self.meta = {
            "enabled": {
                "type": "checkbox", 
                "label": "Auto White Balance", 
                "default": False
            }
        }

    def get_metadata(self):
        return self.meta

    

   
    # from memory_profiler import profile 
    
    # @profile
    def apply(self, img, mask, params, scale_factor=1.0, 
              cache=None, *args, **kwargs):
        """
        Optimized 'Gray World' algorithm using LUTs.
        Reduces memory usage by avoiding float32 image conversion.
        """
        # 1. Check if enabled
        if not params.get("enabled", False):
            return img

        # 2. Calculate Channel Averages
        # cv2.mean is highly optimized and works directly on uint8
        b_mean, g_mean, r_mean, _ = cv2.mean(img)

        # Safety: Avoid divide by zero for pitch-black images
        # We use a small epsilon or check for 0 to be safe
        if b_mean < 1 or g_mean < 1 or r_mean < 1:
            return img

        # 3. Compute "Gray" Target (Average of all channels)
        k = (b_mean + g_mean + r_mean) / 3.0

        # 4. Calculate Scale Factors
        b_scale = k / b_mean
        g_scale = k / g_mean
        r_scale = k / r_mean

        # --- OPTIMIZATION START ---

        # 5. Generate Look-Up Tables (LUT)
        # Instead of multiplying the whole image by floats, we multiply a range of 0-255.
        base_range = np.arange(256, dtype=np.uint8).reshape(1, 256)

        # cv2.convertScaleAbs(src, alpha=scale) performs: sat(src * scale + 0)
        # This handles the clipping (0-255) and rounding automatically.
        lut_b = cv2.convertScaleAbs(base_range, alpha=b_scale)
        lut_g = cv2.convertScaleAbs(base_range, alpha=g_scale)
        lut_r = cv2.convertScaleAbs(base_range, alpha=r_scale)

        # Merge into a single 3-channel LUT: Shape (1, 256, 3)
        lut = cv2.merge([lut_b, lut_g, lut_r])

        # 6. Apply LUT
        # This replaces the entire "to_float -> multiply -> clip -> to_uint8" pipeline
        wb_img = cv2.LUT(img, lut)

        # --- OPTIMIZATION END ---

        # 7. Optimized Integer Blending
        # Only if a mask is present (rare for AutoWB, but we respect the contract)
        if mask is None:
            return wb_img        
        
        else:  # never run for us, actually 
            from ..engines.BlendEngine import BlendEngine
            return BlendEngine.fast_mask_blend(img, wb_img, mask)
        
        ###########################################

        # # Expand mask for broadcasting (HxWx1)
        # if len(mask.shape) == 2:
        #     mask_expanded = mask[:, :, None]
        # else:
        #     mask_expanded = mask

        # # Cast to int16 to prevent overflow during mix, then normalize
        # p_int = img.astype(np.int16)
        # e_int = wb_img.astype(np.int16)
        # m_int = mask_expanded.astype(np.int16)

        # # Formula: (Target * Mask + Source * (255 - Mask)) // 255
        # # Adding 127 helps round to nearest integer rather than floor
        # final = (e_int * m_int + p_int * (255 - m_int) + 127) // 255
        
        # return final.astype(np.uint8)


        #############################################
       
    