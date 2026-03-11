# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# ##############################################################################
# A global strategy to change color temperature of whole image 
# 
# ##############################################################################


import cv2
import numpy as np
from ..Interfaces import StrategyScope



 
class WhiteBalanceStrategy:
    def __init__(self):
        self.priority = 0
        self.isGlobal = True 
        self.scope = StrategyScope.GLOBAL
        
        
        self.meta = {
            "temp": {"type": "slider", "range": (-100, 100), "label": "Temperature", "default": 0}
        }

    def get_metadata(self):
        return self.meta

    
    def apply(self, img, mask, params, scale_factor=1.0, cache=None, *args, **kwargs):
        """
        Optimized White Balance using Look-Up Tables (LUT).
        Avoids float32 conversion of the image.
        """
        temp = params.get("temp", 0)
        
        # --- 1. Quick Exit ---
        if abs(temp) < 1:
            return img

        # --- 2. Calculate Scaling Factors ---
        # Same von Kries logic, but we only calculate it for the formula
        t_val = temp / 200.0 
        b_scale = 1.0 - t_val 
        r_scale = 1.0 + t_val

        # --- 3. Generate Look-Up Table (LUT) ---
        # instead of multiplying 2 million pixels, we multiply 256 integers.
        # We create a range [0, 1, 2, ... 255]
        base_range = np.arange(256, dtype=np.uint8).reshape(1, 256)

        # Create the LUT for each channel using convertScaleAbs
        # This handles the float multiplication and the clipping (0-255) automatically
        lut_b = cv2.convertScaleAbs(base_range, alpha=b_scale)
        lut_g = base_range # Green doesn't change
        lut_r = cv2.convertScaleAbs(base_range, alpha=r_scale)

        # Merge into a single 3-channel LUT: Shape (1, 256, 3)
        # OpenCV allows applying different tables to different channels simultaneously
        lut = cv2.merge([lut_b, lut_g, lut_r])

        # --- 4. Apply LUT ---
        # This is extremely fast and allocates only the destination uint8 array
        wb_img = cv2.LUT(img, lut)

        # --- 5. Blending (If Mask Exists) ---
        if mask is None:
            return wb_img
        
        # If there is a mask, we use the optimized integer blending 
        # (Same technique as ColorEnhanceStrategy)
        
        # Expand mask for broadcasting
        if len(mask.shape) == 2:
            mask_expanded = mask[:, :, None]
        else:
            mask_expanded = mask

        # Integer Blend: (Target * Mask + Source * (255 - Mask)) // 255
        p_int = img.astype(np.int16)
        e_int = wb_img.astype(np.int16)
        m_int = mask_expanded.astype(np.int16)

        final = (e_int * m_int + p_int * (255 - m_int) + 127) // 255
        
        return final.astype(np.uint8)
    