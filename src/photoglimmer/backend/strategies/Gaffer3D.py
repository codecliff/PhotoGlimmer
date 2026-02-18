# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ##############################################################################
# A strategy to directly shed light on face
# Presented to user as Facelight3D  (as set by  PropertiesManager)
# ##############################################################################

import cv2
import numpy as np
from ..FaceMesh import FaceMeshService
from ..Interfaces import AdjustmentStrategy, StrategyScope
from ..engines.BlendEngine import BlendEngine

class Gaffer3DStrategy(AdjustmentStrategy):
    def __init__(self):
        self.scope = StrategyScope.FACE
        self.priority = 4  # Runs after smoothing

    def get_metadata(self):
        return {
            "light_strength": {"type": "slider", "range": (0.0, 1.5), "default": 0.0, "label": "Intensity"},
            "light_warmth":   {"type": "slider", "range": (-1.0, 1.0), "default": 0.9, "label": "Warmth"},
            "light_angle":    {"type": "slider", "range": (-180, 180), "default": -90, "label": "Angle (Deg)"},
            "light_pitch":    {"type": "slider", "range": (-90, 90), "default": 0, "label": "Pitch (Up/Down)"},
            "light_softness": {"type": "slider", "range": (0.1, 2.0), "default": 1.0, "label": "Softness"},
        }

    # from memory_profiler import profile
    # @profile #about 3x the layer size 
    def apply(self, image, mask, params, scale_factor=1.0, cache=None, *args, **kwargs):
        strength = params.get("light_strength", 0.0) # also works as on/off 
        angle    = params.get("light_angle", -90)
        pitch    = params.get("light_pitch", 0)
        softness = params.get("light_softness", 1.0)
        warmth   = params.get("light_warmth", 0.9)

        if strength < 0.01: return image

        h, w = image.shape[:2]
        
        # --- 1. MASK HANDLING ---
        # We still use the 'cache' (layer.strategy_cache) for the specific 3D geometry 
        # since it's unique to this specific Angle/Pitch combination.
        cache_key = f"gaffer3d_geo_{angle}_{pitch}"
        raw_mask = None
        
        if cache is not None and cache_key in cache:
            cached_m = cache[cache_key]
            if cached_m.shape[:2] == (h, w):
                raw_mask = cached_m

        if raw_mask is None:
            raw_mask = self._generate_3d_mask(image, angle, pitch)
            if cache is not None and raw_mask is not None:
                cache[cache_key] = raw_mask

        if raw_mask is None: return image

        # Refine edges
        ksize = int(max(h, w) * 0.08 * softness) | 1
        refined_mask = cv2.GaussianBlur(raw_mask, (ksize, ksize), 0)

        # --- 2. THE GOLDEN LIGHT CALCULATION ---
        b, g, r = 255, 255, 255
        
        if warmth > 0:
            b = int(b * (1 - warmth * 0.5))
            g = int(g * (1 - warmth * 0.2)) # Subtle green drop for warmer gold
        elif warmth < 0:
            r = int(r * (1 - abs(warmth) * 0.5))
            g = int(g * (1 - abs(warmth) * 0.2))

        # Apply Intensity Dimming (Luminance safety)
        intensity_dim = 1 - (abs(warmth) * 0.1)
        light_color = np.full((h, w, 3), (int(b*intensity_dim), int(g*intensity_dim), int(r*intensity_dim)), dtype=np.uint8)

        # 3. Final Screen Blend
        return BlendEngine.fast_screen_blend(image, light_color, refined_mask, strength)

    def _generate_3d_mask(self, image, angle, pitch):
        h, w = image.shape[:2]
        service = FaceMeshService()
        landmarks = service.get_landmarks_3d(image)
        if landmarks is None: return None

        # 1. Setup Light Vector
        yaw_rad, pitch_rad = np.radians(angle), np.radians(pitch)
        lx = np.cos(pitch_rad) * np.sin(yaw_rad)
        ly = -np.sin(pitch_rad)
        lz = np.cos(pitch_rad) * np.cos(yaw_rad)
        light_vec = np.array([lx, ly, lz], dtype=np.float32)

        # 2. Get Face Bounds for the 'Dome'
        pts_x = [p[0] for p in landmarks]
        pts_y = [p[1] for p in landmarks]
        min_x, max_x = int(min(pts_x) * w), int(max(pts_x) * w)
        min_y, max_y = int(min(pts_y) * h), int(max(pts_y) * h)
        
        pad = 30
        min_x, max_x = max(0, min_x-pad), min(w, max_x+pad)
        min_y, max_y = max(0, min_y-pad), min(h, max_y+pad)
        bw, bh = max_x - min_x, max_y - min_y
        if bw <= 0 or bh <= 0: return None

        # 3. Dome Shading (Lambertian)
        yy, xx = np.mgrid[-1:1:complex(0, bh), -1:1:complex(0, bw)]
        dist_sq = xx**2 + yy**2
        zz = np.sqrt(np.clip(1.0 - dist_sq, 0, 1))
        
        shading = (xx * light_vec[0] + yy * light_vec[1] + zz * light_vec[2])
        shading = (np.clip(shading, 0, 1) * 255).astype(np.uint8)

        # 4. Final Clip to SHARED Skin Mask
        full_mask = np.zeros((h, w), dtype=np.uint8)
        full_mask[min_y:max_y, min_x:max_x] = shading
        
        # This call is now cached inside the service!
        skin_mask = service.get_skin_mask(image)
        if skin_mask is not None:
            full_mask = cv2.bitwise_and(full_mask, skin_mask)
            
        return full_mask
    