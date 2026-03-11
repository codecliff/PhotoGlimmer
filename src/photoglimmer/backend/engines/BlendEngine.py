# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# #######################################################################
# Contains fast and low-memory blending methods 
# Should be used to about numpy based blending that often require 
# float32 arrays which are memory hogs compared to uint8  
# Note that we are generally ok with float32 for small proxy image and use these only for final render
# #######################################################################

import cv2
import numpy as np

class BlendEngine:
    """
    A collection of high-performance, SIMD-optimized blending utilities 
    designed for Large  image processing.
    """

    

    
    @staticmethod
    def fast_mask_blend(base_img: np.ndarray, effect_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Fault-Tolerant LERP blending, aims to minimize memory requirement 
        Automatically handles channel broadcasting only when required.
        Can exapnd mask if needed
        """
        # 1. Determine if mask needs expansion
        # base_img is (H, W, 3), mask might be (H, W) or (H, W, 1)
        if base_img.ndim == 3 and (mask.ndim == 2 or (mask.ndim == 3 and mask.shape[2] == 1)):
            # We only merge if base is 3rd-dim and mask is effectively 1st-dim
            mask_3c = cv2.merge([mask, mask, mask])
        else:
            # Fallback for callers already passing (H, W, 3) or grayscale-to-grayscale
            mask_3c = mask

        # 2. Signed differences (Remains uint8)
        diff_pos = cv2.subtract(effect_img, base_img) 
        diff_neg = cv2.subtract(base_img, effect_img) 

        # 3. Scale and Reconstruct
        # Using scale=1.0/255.0 is the 'Secret Sauce' for SIMD speed
        weighted_pos = cv2.multiply(diff_pos, mask_3c, scale=1.0/255.0)
        weighted_neg = cv2.multiply(diff_neg, mask_3c, scale=1.0/255.0)

        res = cv2.add(base_img, weighted_pos)
        res = cv2.subtract(res, weighted_neg)
        
        return res
    
    
    @staticmethod
    def fast_screen_blend(base_img: np.ndarray, light_img: np.ndarray, mask: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Optimized Screen Blend for Gaffer Strategy.
        Formula: 255 - ((255 - image) * (255 - light)) / 255
        """
        # Invert both layers
        inv_img = cv2.bitwise_not(base_img)
        inv_light = cv2.bitwise_not(light_img)
        
        # Multiply inverted (Scale handles division)
        screen_delta = cv2.multiply(inv_img, inv_light, scale=1.0/255.0)
        screen_result = cv2.bitwise_not(screen_delta)
        
        # If strength is 1.0, we just return the screen_result masked
        # Otherwise, apply strength to the mask first
        if strength < 1.0:
            mask = cv2.convertScaleAbs(mask, alpha=strength)
            
        return BlendEngine.fast_mask_blend(base_img, screen_result, mask)
    

    
    
    