# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ##############################################################################
# Shadow/ Midtone / Highlight balancer  
#  
# ##############################################################################

import cv2
import numpy as np
from ..Interfaces import AdjustmentStrategy

class TonalBalanceStrategy(AdjustmentStrategy):
    """
    High-performance Tonal Balance strategy optimized for 50MP+ images.
    Uses 1D Lookup Tables and Direct BGR Saturation to minimize RAM spikes.
    """

    def get_metadata(self):
        return {
            "shadows":    {"type": "slider", "range": (0.5, 1.5), "default": 1.0, "label": "Shadows"},
            "midtones":   {"type": "slider", "range": (0.5, 1.5), "default": 1.0, "label": "Midtones"},
            "highlights": {"type": "slider", "range": (0.5, 1.5), "default": 1.0, "label": "Highlights"},
            "m_sat":      {"type": "slider", "range": (0.0, 2.0), "default": 1.0, "label": "Midtone Sat"}
        }

    def apply(self, image, mask, params, scale_factor, cache=None):
        s_gain = params.get("shadows", 1.0)
        m_gain = params.get("midtones", 1.0)
        h_gain = params.get("highlights", 1.0)
        m_sat  = params.get("m_sat", 1.0)

        # 1. Quick Exit if no changes requested
        if all(abs(v - 1.0) < 0.01 for v in [s_gain, m_gain, h_gain, m_sat]):
            return image

        # --- STEP A: PRE-CALCULATE 1D LOOKUP TABLE (LUMINANCE) ---
        # We process 256 values instead of 50 million pixels.
        indices = np.arange(256, dtype=np.float32)
        norm_idx = indices / 255.0
        inv_idx = 1.0 - norm_idx
        
        # Calculate weight curves (Quadratic for smooth transitions)
        s_w = inv_idx * inv_idx
        h_w = norm_idx * norm_idx
        m_w = np.clip(1.0 - s_w - h_w, 0, 1)

        # Final gain curve
        lut_gain = (s_w * s_gain) + (m_w * m_gain) + (h_w * h_gain)
        lut_uint8 = np.clip(indices * lut_gain, 0, 255).astype(np.uint8)
        
        # Apply Tonal Curve (RAM Efficient: Single pass, uint8)
        processed = cv2.LUT(image, lut_uint8)

        # --- STEP B: OPTIMIZED MIDTONE SATURATION (DIRECT BGR) ---
        if abs(m_sat - 1.0) > 0.01:
            # We target midtones by using a grayscale version as the "Zero Saturation" base
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            gray_3c = cv2.merge([gray, gray, gray])
            
            # Use OpenCV to perform the weighted saturation blend in C++
            # processed_sat = processed * m_sat + gray_3c * (1 - m_sat)
            saturated = cv2.addWeighted(processed, m_sat, gray_3c, 1.0 - m_sat, 0)
            
            # Generate a 50MP Midtone weight map via LUT
            m_weight_uint8 = (m_w * 255).astype(np.uint8)
            pixel_weights = cv2.LUT(gray, m_weight_uint8)
            
            # Selectively apply the saturation only to the midtone regions
            # This replaces the original image (processed) where the mask (pixel_weights) is white
            cv2.copyTo(src=saturated, mask=pixel_weights, dst=processed)
            
            # Explicitly clear temporary large buffers
            del gray, gray_3c, saturated, pixel_weights

        return processed