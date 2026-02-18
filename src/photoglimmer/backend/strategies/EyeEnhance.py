# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ##############################################################################
# A strategy to enhance eyes 
# asks the singleton FaceMeshService for eye mask 
# ##############################################################################
import cv2
import numpy as np
from ..Interfaces import AdjustmentStrategy, StrategyScope
from ..FaceMesh import FaceMeshService
from ..engines.BlendEngine import BlendEngine

class EyeEnhancerStrategy(AdjustmentStrategy):
    def __init__(self):
        self.scope = StrategyScope.FACE
        # Priority 5: Runs after Lighting (Gaffer) to provide the final "pop"
        self.priority = 5 

    def get_metadata(self):
        return {
            "eye_whitening": {"type": "slider", "range": (0.0, 1.0), "default": 0.0, "label": "Whitening"},
            "eye_clarity":   {"type": "slider", "range": (0.0, 1.0), "default": 0.0, "label": "Iris Pop"},
            "eye_brightness":{"type": "slider", "range": (0.0, 1.0), "default": 0.0, "label": "Brightness"}
        }
    
    # from memory_profiler import profile
    # @profile # memory spike ~7x the layer size
    def apply(self, image, mask, params, scale_factor=1.0, cache=None, *args, **kwargs):
        whitening = params.get("eye_whitening", 0.0)
        clarity   = params.get("eye_clarity", 0.0)
        brightness = params.get("eye_brightness", 0.0)

        # Quick exit if no adjustments are set
        if whitening < 0.01 and clarity < 0.01 and brightness < 0.01:
            return image

        # 1. Access Shared Service for Masks
        service = FaceMeshService()
        eye_data = service.get_eye_masks(image)
        if eye_data is None: return image
        
        sclera_mask, iris_mask = eye_data
        processed = image.copy()

        # 2. SCLERA WHITENING (Lab Color Space)
        # We target a/b channels to neutralize redness/yellowing without a "gray" look.
        if whitening > 0.01:
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2Lab)
            l, a, b_chan = cv2.split(lab)
            
            # Subtle Lightness boost
            l = cv2.add(l, int(whitening * 12))
            
            # Neutralize chroma (128 is neutral in Lab)
            a = cv2.addWeighted(a, 1.0 - (whitening * 0.5), 128, whitening * 0.5, 0)
            b_chan = cv2.addWeighted(b_chan, 1.0 - (whitening * 0.5), 128, whitening * 0.5, 0)
            
            white_res = cv2.merge([l, a, b_chan])
            white_res = cv2.cvtColor(white_res, cv2.COLOR_Lab2BGR)
            processed = BlendEngine.fast_mask_blend(processed, white_res, sclera_mask)

        # 3. IRIS CLARITY (Micro-contrast for iris fibers)
        if clarity > 0.01:
            # Small radius Gaussian for high-frequency detail sharpening
            blur = cv2.GaussianBlur(processed, (0, 0), 2.0)
            sharp = cv2.addWeighted(processed, 1.6, blur, -0.6, 0)
            
            alpha_i = cv2.convertScaleAbs(iris_mask, alpha=clarity)
            processed = BlendEngine.fast_mask_blend(processed, sharp, alpha_i)

        # 4. BRIGHTNESS
        if brightness > 0.01:
            bright_res = cv2.convertScaleAbs(processed, alpha=1.0, beta=int(brightness * 25))
            # Apply to the combined eye area
            processed = BlendEngine.fast_mask_blend(processed, bright_res, sclera_mask)

        return processed
    