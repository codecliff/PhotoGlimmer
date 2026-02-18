# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# Skin Smoothening 
# Works on Face + Neck, tries to avoid eyeglasses 
# uses singleton FaceMeshService to get special masks  
# ######################################################################################

import cv2
import numpy as np
from ..Interfaces import AdjustmentStrategy, StrategyScope
from ..FaceMesh import FaceMeshService
from ..engines.BlendEngine import BlendEngine

# from memory_profiler import profile

class SmartSkinStrategy(AdjustmentStrategy):
    def __init__(self):
        self.scope = StrategyScope.FACE
        self.priority = 3 # Executed after general cleanup
        
    def get_metadata(self):
        return {
            "skin_smooth": {"type": "slider", "range": (0.0, 1.0), "default": 0.0, "label": "Smoothing"},
            "skin_radius": {"type": "slider", "range": (0.0, 1.0), "default": 0.3, "label": "Radius"},
            "skin_warmth": {"type": "slider", "range": (-1.0, 1.0), "default": 0.0, "label": "Warmth"},
            "detail_preserve": {"type": "slider", "range": (0.0, 1.0), "default": 0.5, "label": "Preserve Detail"}
        }

    
    
    def apply(self, image, mask, params, scale_factor=1.0, cache=None, *args, **kwargs):
        smooth_strength = params.get("skin_smooth", 0.0)
        warmth_strength = params.get("skin_warmth", 0.0)
        detail_strength = params.get("detail_preserve", 0.5)
        
        if smooth_strength < 0.01 and abs(warmth_strength) < 0.01:
            return image

        h, w = image.shape[:2]
        service = FaceMeshService() #singleton
        face_skin_mask = service.get_skin_mask(image)
        if face_skin_mask is None: return image

        # --- 1. OPTIMIZED DETAIL PRESERVATION ---
        # Only run this if we are actually smoothing
        detail_mask = None
        if smooth_strength >= 0.01:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Use CV_16S (16-bit) instead of CV_64F (64-bit). 
            # This drops RAM usage from 384MB per array to ~96MB.
            dx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
            dy = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
            
            # Fast Absolute Magnitude in uint8
            edge_map = cv2.addWeighted(cv2.convertScaleAbs(dx), 0.5, 
                                     cv2.convertScaleAbs(dy), 0.5, 0)
            
            # Clear dx/dy immediately to free ~200MB
            del dx, dy
            
            detail_mask = cv2.threshold(edge_map, int(40 * (1.0 - detail_strength)), 255, cv2.THRESH_BINARY_INV)[1]
            detail_mask = cv2.GaussianBlur(detail_mask, (3, 3), 0)

        # --- 2. EFFECTIVE MASK CONSTRUCTION ---
        if mask is not None:
            _, binary_user_mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
            effective_mask = cv2.multiply(face_skin_mask, binary_user_mask, scale=1.0/255.0)
        else:
            effective_mask = face_skin_mask

        # Apply Detail Protection to the skin mask
        if detail_mask is not None:
            effective_mask = cv2.multiply(effective_mask, detail_mask, scale=1.0/255.0)

        processed = image.copy()
        
        # A. Apply Smoothing
        if smooth_strength >= 0.01:
            norm_radius = params.get("skin_radius", 0.3)
            radius = int((norm_radius * 0.05) * max(h, w)) | 1 
            
            # High-Pass Frequency Separation
            blur = cv2.GaussianBlur(image, (radius, radius), 0)
            high_pass = cv2.addWeighted(image, 1.0, blur, -1.0, 128)
            
            # Reuse the 'blur' variable name or delete to keep memory flat
            smoothed_tex = cv2.GaussianBlur(high_pass, (radius, radius), 0)
            diff = cv2.addWeighted(high_pass, 1.0, smoothed_tex, -1.0, 128)
            smoothed_full = cv2.addWeighted(image, 1.0, diff, -1.0, 128)
            
            alpha_s = cv2.convertScaleAbs(effective_mask, alpha=smooth_strength)
            processed = BlendEngine.fast_mask_blend(processed, smoothed_full, alpha_s)
            
            # Cleanup temporary large buffers
            del high_pass, smoothed_tex, diff, smoothed_full

        # B. Apply Warmth
        if abs(warmth_strength) >= 0.01:
            # Note: warmth is applied to 'processed', which already has smoothing
            warm_img = processed.copy().astype(np.int16)
            if warmth_strength > 0:
                warm_img[:, :, 2] += int(warmth_strength * 30) 
                warm_img[:, :, 1] += int(warmth_strength * 15) 
                warm_img[:, :, 0] -= int(warmth_strength * 20) 
            else:
                warm_img[:, :, 0] += int(abs(warmth_strength) * 30)
                warm_img[:, :, 2] -= int(abs(warmth_strength) * 25)

            warm_img = np.clip(warm_img, 0, 255).astype(np.uint8)
            alpha_w = cv2.convertScaleAbs(effective_mask, alpha=abs(warmth_strength))
            processed = BlendEngine.fast_mask_blend(processed, warm_img, alpha_w)

        return processed