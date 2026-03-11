# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################

import cv2
import numpy as np
from typing import Dict, Optional
from ..Interfaces import AdjustmentStrategy, StrategyScope

class BezierBrightStrategy(AdjustmentStrategy):
    """
    Adjusts brightness using a Quadratic Bezier Curve.
    P0 is always (0,0), P2 is always (255,255).
    The user controls P1 (control_x, control_y) to pull the curve.
    User Input: Normalized 0.0 to 1.0
    Internal Math: Scaled 0 to 255
    """
    
    def __init__(self):        
        self.isGlobal = False
        self.scope = StrategyScope.LAYER # Applies to specific layer

    def get_metadata(self) -> Dict[str, tuple]:
        return {
            "control_x": {
                "type": "slider", 
                "range": (0.0, 1.0),    # Changed to normalized float
                "label": "From", 
                "default": 0.5          # Center is now 0.5
            },
            "control_y": {
                "type": "slider", 
                "range": (0.0, 1.0),    # Changed to normalized float
                "label": "To", 
                "default": 0.5          # Center is now 0.5
            }
        }

    def apply(self, patch: np.ndarray, 
              mask: np.ndarray, 
              params: Dict[str, float], 
              scale: float, 
              cache: Optional[Dict] = None,
              *args, **kwargs) -> np.ndarray:
        
        # 1. Fetch params (Default to normalized center 0.5)
        norm_cx = params.get("control_x", 0.5)
        norm_cy = params.get("control_y", 0.5)

        # 2. Scale up to 0-255 Pixel Space for the math
        cx = norm_cx * 255.0
        cy = norm_cy * 255.0
        
        # Optimization: If P1 is exactly on the diagonal (127.5, 127.5), it's a straight line (No-Op)
        # We allow a small epsilon for float imprecision
        if abs(cx - 127.5) < 1.0 and abs(cy - 127.5) < 1.0:
            return patch

        # 3. Check Cache
        # We use the scaled values for the key to maintain precision in the cache
        cache_key = f"bezier_{cx:.1f}_{cy:.1f}"
        
        if cache is not None and cache_key in cache:
            lut = cache[cache_key]
        else:
            lut = self._generate_lut(cx, cy)
            if cache is not None:
                cache[cache_key] = lut

        # 4. Apply
        return cv2.LUT(patch, lut)

    def _generate_lut(self, cx: float, cy: float) -> np.ndarray:
        """
        Generates a 256-value LUT by sampling the parametric Bezier curve
        and interpolating it to integer pixel slots.
        """
        # P0 = (0, 0)
        # P1 = (cx, cy)
        # P2 = (255, 255)
        
        # We define 't' with enough resolution to prevent gaps in the output
        # 512 steps is plenty for a 256-pixel wide range
        t = np.linspace(0, 1, 512)
        
        # Quadratic Bezier Formula: 
        # B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
        # Since P0 is 0, the first term vanishes.
        
        one_minus_t = 1 - t
        term_middle = 2 * one_minus_t * t
        term_end = t * t
        
        # Calculate X and Y coordinates along the curve
        x_values = (term_middle * cx) + (term_end * 255)
        y_values = (term_middle * cy) + (term_end * 255)
        
        # We need y for every integer x in [0..255].
        # Since the curve is parametric, we use linear interpolation to map 
        # the calculated (x, y) pairs back to a fixed integer grid.
        
        x_target = np.arange(256, dtype=np.float32)
        lut = np.interp(x_target, x_values, y_values)
        
        # Clip and Cast
        return np.clip(lut, 0, 255).astype(np.uint8)
    
