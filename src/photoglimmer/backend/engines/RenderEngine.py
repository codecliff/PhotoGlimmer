# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# #######################################################################

# RenderEngine is called every time  the canvas image has to be rendered anew
# render_scene : ImageSession's render_proxy calls RenderEngine's render_scene
# apply_layer_pipeline : is the block where all strategies are actually applied to image
#                        Both this file and ExportRenderEngine use  apply_layer_pipeline
#
# RenderEngine : For rendering proxy image 
# ExportRenderEngine: For rendering the final image                           
# #######################################################################


import cv2
import numpy as np
# from memory_profiler import profile
from ..Interfaces import StrategyScope

class RenderEngine:
    """
    Handles the Pixel Pipeline:
    1. Applying Strategy Effects (Color, Blur, etc.)
    2. Blending Layers (Composite)
    3. Tiled Blending for high-res stability
    """
    
    def __init__(self, strategies_registry):
        # We need the registry to know which strategy classes to run
        self.strategies = strategies_registry

    


    def apply_layer_pipeline(self, raw_patch, mask, layer, scale_factor):
        """
        Optimized pipeline that stays in uint8 to prevent memory spikes.
        Global Inheritance (White Balance, etc.) is now pre-baked into raw_patch.
        
        Returns: uint8 BGR image.
        """
        # Safety copy for the "Clean Source"
        working_patch = raw_patch.copy()

        # --- A. LOCAL STRATEGIES ---
        if layer.state.adjustments_enabled:
            strategies_to_run = []
            for s_key, strategy in self.strategies.items():
                # We skip 'Global' strategies here for non-background layers 
                # because they were already applied in the render_scene pre-process.
                if getattr(strategy, 'isGlobal', False) : #and not layer.is_background:
                    continue
                
                params = layer.state.adjustments.get(s_key)
                if params:
                    prio = getattr(strategy, 'priority', 50)
                    strategies_to_run.append((prio, strategy, params))
            
            strategies_to_run.sort(key=lambda x: x[0])
            
            # Start applying edits
            processed_uint8 = working_patch 
            
            for _, strategy, params in strategies_to_run:
                # --- RESCUE VALIDATION ---
                # Before applying, we check if the mask and patch have become de-synced
                # during a resize event (on_geometry_changed).
                current_mask = mask
                if current_mask is not None:
                    ph, pw = processed_uint8.shape[:2]
                    mh, mw = current_mask.shape[:2]
                    
                    if (ph, pw) != (mh, mw):
                        # If sizes don't match, we skip high-compute strategies 
                        # like SmartSkin to avoid the OpenCV mismatch crash.
                        if getattr(strategy, 'scope', None) == StrategyScope.FACE:
                            continue 
                        
                        # For general strategies, we do a quick rescue resize
                        current_mask = cv2.resize(current_mask, (pw, ph), interpolation=cv2.INTER_NEAREST)

                processed_uint8 = strategy.apply(
                        processed_uint8, current_mask, params, scale_factor, cache=layer.strategy_cache
                    )
            
            # --- B. MIX STRENGTH (uint8 optimization) ---
            strength = layer.state.effect_strength
            
            # Use cv2.addWeighted to blend without allocating float32 arrays
            if abs(strength - 1.0) < 0.01:
                return processed_uint8
            elif strength < 0.01:
                return working_patch
            else:
                # Returns uint8 directly
                return cv2.addWeighted(processed_uint8, strength, working_patch, 1.0 - strength, 0)
        else:
            return working_patch
        
        


    


    def render_scene(self, sorted_layers, proxy_size, scale_factor, mask_engine, show_overlay=False):
        """
        Renders the full proxy image.
        Args:
            sorted_layers: List of Layer objects (already sorted by area/z-index).
            mask_engine: Reference to the MaskEngine to fetch masks on demand.
        """
        # 1. Initialize Canvas (Black, float32)
        w, h = proxy_size
        canvas = np.zeros((h, w, 3), dtype=np.float32)
        
        # --- A. GLOBAL PRE-PROCESSING (Bake-Once) ---
        # Identify Background and create a globally corrected source for all layers.
        bg_layer = next((l for l in sorted_layers if l.is_background), None)
        bg_state = bg_layer.state if bg_layer else None
        
        # This will be the "Golden Source" that all layers crop from.
        if bg_layer is not None:
            # We start with the raw background pixels
            base_pixels = bg_layer.proxy_patch.copy()
            
            # Apply ONLY 'isGlobal' strategies (like White Balance) once to the whole image.
            # This prevents 5 layers from re-calculating the same math 5 times.
            if bg_state and bg_state.adjustments_enabled:
                for s_key, strategy in self.strategies.items():
                    if getattr(strategy, 'isGlobal', False):
                        global_params = bg_state.adjustments.get(s_key)
                        if global_params:
                            base_pixels = strategy.apply(
                                base_pixels, None, global_params, scale_factor, cache=None
                            )
        else:
            base_pixels = np.zeros((h, w, 3), dtype=np.uint8)

        # --- B. START LAYER LOOP ---
        for layer in sorted_layers: 
            if not layer.visible:
                continue

            # --- MASK RETRIEVAL ---
            if layer.is_background:
                mask_arr = layer.raw_mask
            else:
                # Delegate to MaskEngine
                mask_arr = mask_engine.get_refined_mask(layer)

            if mask_arr is None: continue

            # --- PREPARE PIXELS ---
            # Instead of the raw file patch, we crop from our 'base_pixels'.
            # This ensures 'Face' and 'Body' layers have identical color/exposure.
            x, y, cw, ch = layer.bounds
            
            if layer.is_background:
                original_patch = base_pixels
            else:
                # We crop the region corresponding to this layer from the baked base
                original_patch = base_pixels[y:y+ch, x:x+cw]

            # --- C. APPLY PIPELINE ---
            # We no longer pass bg_state here because globals are already baked into original_patch
            processed_uint8 = self.apply_layer_pipeline(
                original_patch,
                mask_arr,
                layer,
                scale_factor
            )

            # Convert back to Float32 (0.0 - 1.0) for the Proxy Canvas
            processed_f = processed_uint8.astype(np.float32) / 255.0

            # --- D. COMPOSITING (OPTIMIZED) ---
            # 1. Background Shortcut
            if layer.is_background and layer.state.opacity >= 0.99:
                canvas[y:y+ch, x:x+cw] = processed_f
                continue

            # 2. Optimized Blending
            alpha_single = (mask_arr.astype(np.float32) / 255.0) * layer.state.opacity
            alpha_3c = cv2.merge([alpha_single, alpha_single, alpha_single])
            
            roi = canvas[y:y+ch, x:x+cw]
            
            # In-place blending logic
            cv2.multiply(processed_f, alpha_3c, dst=processed_f)
            cv2.subtract((1.0, 1.0, 1.0, 0.0), alpha_3c, dst=alpha_3c)
            cv2.multiply(roi, alpha_3c, dst=roi)
            cv2.add(processed_f, roi, dst=roi)
            
            # --- E. OPTIONAL RED OVERLAY ---
            if show_overlay and not layer.is_background:
                red_tint = np.zeros_like(roi)
                red_tint[:, :] = [0, 0, 1.0] 
                overlay_weight = cv2.subtract((1.0, 1.0, 1.0, 0.0), alpha_3c)
                cv2.multiply(overlay_weight, 0.4, dst=overlay_weight)
                red_part = cv2.multiply(red_tint, overlay_weight)
                cv2.subtract((1.0, 1.0, 1.0, 0.0), overlay_weight, dst=overlay_weight)
                cv2.multiply(roi, overlay_weight, dst=roi)
                cv2.add(red_part, roi, dst=roi)

        # --- 3. FINALIZE ---
        return (np.clip(canvas * 255, 0, 255)).astype(np.uint8)
    

    #@profile
    def blend_overlay_tiled_old(self, canvas_roi, fg, mask, opacity, tile_size=2048):
        """
        Blends 'fg' onto 'canvas_roi' using 'mask' and 'opacity' in small tiles.
        Uses float32 math to ensure 100% consistency with the live render proxy.
        Modifies canvas_roi in-place.
        """
        h, w = canvas_roi.shape[:2]
        
        if opacity <= 0:
            return

        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                y1 = y
                y2 = min(h, y + tile_size)
                x1 = x
                x2 = min(w, x + tile_size)
                
                # Extract Slices (Views)
                bg_tile = canvas_roi[y1:y2, x1:x2]
                fg_tile = fg[y1:y2, x1:x2]
                mask_tile = mask[y1:y2, x1:x2]

                # --- 1. Expand Mask ---
                if len(mask_tile.shape) == 2:
                    m_view = mask_tile[:, :, None]
                else:
                    m_view = mask_tile

                # --- 2. Convert to Float32 ---
                bg_f = bg_tile.astype(np.float32)
                fg_f = fg_tile.astype(np.float32)
                
                # Calculate Alpha
                alpha = (m_view.astype(np.float32) / 255.0) * opacity

                # --- 3. Blend ---
                blended = (fg_f * alpha) + (bg_f * (1.0 - alpha))
                
                # --- 4. Write Result ---
                canvas_roi[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)


    # faster , memory efficient version of above 
    def blend_overlay_tiled(self, canvas_roi, fg, mask, opacity, tile_size=2048):
        """
        Corrected High-Performance Integer Blender.
        Mathematically identical to the float32 version but much leaner.
        """
        h, w = canvas_roi.shape[:2]
        if opacity <= 0: return

        # Pre-scale opacity to 0-255 range
        opacity_int = int(opacity * 255)

        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                y2, x2 = min(h, y + tile_size), min(w, x + tile_size)
                
                bg_tile = canvas_roi[y:y2, x:x2]
                fg_tile = fg[y:y2, x:x2]
                m_tile  = mask[y:y2, x:x2]

                # 1. Expand Mask View
                m_view = m_tile[:, :, None] if m_tile.ndim == 2 else m_tile

                # 2. Calculate Alpha (0-65025 range)
                # We use uint32 briefly for the multiplication to ensure NO overflow
                # Combined Alpha = Mask (0-255) * Layer Opacity (0-255)
                alpha = m_view.astype(np.uint32) * opacity_int
                inv_alpha = 65025 - alpha # 65025 is 255 * 255

                # 3. Blend and Normalize
                # Formula: (FG * alpha + BG * inv_alpha) / 65025
                # This handles feathering exactly like float32 does.
                res = (fg_tile.astype(np.uint32) * alpha + 
                    bg_tile.astype(np.uint32) * inv_alpha + 32512) // 65025
                
                canvas_roi[y:y2, x:x2] = res.astype(np.uint8)

    # end of fn blend_overlay_tiled_fixed            