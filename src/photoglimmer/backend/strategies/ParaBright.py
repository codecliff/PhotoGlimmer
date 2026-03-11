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
from typing import Dict, Tuple, Optional
from ..Interfaces import AdjustmentStrategy, StrategyScope

class ParaBrightStrategy(AdjustmentStrategy):
    """
    Applies a custom Parabolic Curve adjustment.
    Algorithm based on rotated conic sections to maintain smooth highlight/shadow rolloff.
    """
    
    def __init__(self):
        self.priority = 2 # standard priority
        self.isGlobal = False
        self.scope = StrategyScope.LAYER # Available for any layer

    def get_metadata(self) -> Dict[str, tuple]:
        return {
            "h": {
                "type": "slider", 
                "range": (-60, 60), 
                "label": "Parabola", 
                "default": 0
            }
        }

    def apply(self, patch: np.ndarray, 
              mask: np.ndarray, 
              params: Dict[str, float], 
              scale: float, 
              cache: Optional[Dict] = None,
              *args, **kwargs) -> np.ndarray:
        
        h = params.get("h", 0)
        
        # Optimization: If h is near zero, return original (no-op)
        if abs(h) < 0.1:
            return patch

        # Check Cache for LUT to avoid recalculating math per-frame
        # We use a tuple of (h_value) as the cache key
        cache_key = f"parabright_{h:.2f}"
        
        if cache is not None and cache_key in cache:
            lut = cache[cache_key]
        else:
            lut = self._generate_lut(h)
            if cache is not None:
                cache[cache_key] = lut

        # Apply LUT
        # cv2.LUT is highly optimized and works on multi-channel images automatically
        return cv2.LUT(patch, lut)

    def _generate_lut(self, h: float) -> np.ndarray:
        """
        Generates the 256-element lookup table based on the rotated parabola logic.
        """
        # 1. Use the precise center of the 0-255 range
        center = 127.5
        
        # 2. Recalculate R based on distance from 127.5 to 0 (or 255)
        # Distance = 127.5 * sqrt(2)
        R = 127.5 * np.sqrt(2)
        
        x_in = np.arange(256, dtype="float32")
        
        # --- The Math (Rotated Conic Section) ---
        sqrt2 = np.sqrt(2)
        
        # Coefficients for At^2 + Bt + C = 0
        A = h / (sqrt2 * R**2)
        B = 1.0 / sqrt2
        C = center - x_in - (h / sqrt2)
        
        # Solve Quadratic: t is distance along the diagonal
        discriminant = np.maximum(B**2 - 4 * A * C, 0)
        t = (-B + np.sqrt(discriminant)) / (2 * A)
        
        # Calculate height z perpendicular to diagonal
        z = h * (1 - (t / R)**2)
        
        # Map back to y (output pixel)
        y_out = center + (t + z) / sqrt2
        
        lut = np.clip(y_out, 0, 255).astype("uint8")

        # 3. EXPLICIT ANCHORING (The Safety Net)
        lut[0] = 0
        lut[255] = 255
        
        return lut
    
    