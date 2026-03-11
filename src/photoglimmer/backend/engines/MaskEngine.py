# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# """
# ================================================================================
# MASK ENGINE - SPATIAL REFINEMENT & COMPOSITING of masks 
# ================================================================================
# Purpose:
#     Post-Processes raw probability maps from segmenter into refined alpha masks. Handles the 
#     mathematical transition from AI detections to render-ready buffers.

# Key Responsibilities:
#     - Binarization: Thresholding soft AI maps into hard masks.
#     - Component Merging: Integrating 'user_added_mask' and 'user_subtracted_mask' 
#       with automated detections via bitwise operations.
#     - Geometric Scaling: Maintaining visual consistency of 'Expand' and 'Feather' 
#       parameters across different resolutions (Proxy vs. 50MP Export).
#     - Hybrid Feathering: Ensuring smooth edge transitions while preventing 
#       boundary artifacts through internal padding and box-filtering.

# Usage for Strategy Developers:
#     - Call 'get_refined_mask(layer)' during UI sessions for real-time preview.
#     - Call 'process_high_res_mask()' during export to apply resolution-corrected 
#       refinements.
#     - Use 'blur_mask_hybrid()' directly if a strategy requires internal 
#       softening of custom-generated geometry.

# Technical Note:
#     All calculations are optimized for uint8 to minimize memory footprint. 
#     The engine uses dynamic radius calculation based on the image's maximum 
#     dimension to ensure that a normalized slider value (e.g., 5.0) yields 
#     proportionally identical results regardless of image scale.
# ================================================================================
# """



import cv2
import numpy as np

class MaskEngine:

     
    """
    Handles all mask refinement logic (Blur, Threshold, Merge, Expand).
    Extracted from ImageSession to isolate complex OpenCV math.
    """

    def get_refined_mask(self, layer):
        """
        Refines the raw_mask (Probability Map) using Threshold, Feather, Expand.
        """
        if layer.raw_mask is None: return None

        # 1. Get the Soft Mask (Probability Map)
        # We work on a copy to avoid modifying the stored source
        mask = layer.raw_mask.copy()

        # 2. APPLY THRESHOLD (The New Step)
        # Convert Soft Mask -> Hard Mask based on slider
        # Slider is 0.0 to 1.0. We map to 0-255.
        threshold_val = getattr(layer.state, 'mask_threshold', 0.5) * 255
        
        # cv2.threshold returns (retval, dst). We need dst.
        # THRESH_BINARY: Values > threshold become 255, else 0.
        _, mask = cv2.threshold(mask, threshold_val, 255, cv2.THRESH_BINARY)
        
        # 3. MERGE USER EDITS
        # Now that we have a binary mask, we can safely add/subtract user strokes
        mask = self._merge_mask_components(layer, mask)

        # 4. Standard Refinements (Expand, Feather, Choke)
        state = layer.state
        expand = int(state.mask_expand)
        #feather = int(state.mask_feather) # we now use normalization
        harden = float(state.mask_contrast)
        feather_px = self._calculate_dynamic_radius(state.mask_feather, mask.shape)

        if expand != 0:
            k_size = abs(expand)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
            mask = cv2.dilate(mask, kernel) if expand > 0 else cv2.erode(mask, kernel)

        # if feather > 0:
        if feather_px > 0:
            mask = self.blur_mask_hybrid(mask, feather_amount=feather_px)
            # mask = self.blur_mask_hybrid(mask, feather)
            #mask= self.blur_mask_oldstyle(mask, feather)

        if abs(harden - 1.0) > 0.001:
            mask = cv2.convertScaleAbs(mask, alpha=harden, beta=0)

        return mask
    

    def _calculate_dynamic_radius(self, val_norm, shape):
        """
        Helper: Converts a normalized slider value (0-100) into pixels 
        based on the active mask's dimensions.
        Scale Factor: 1000.0 (Slider 10.0 = 1% of image size)
        """
        if val_norm <= 0: return 0
        
        h, w = shape[:2]
        max_dim = max(h, w)
        
        # Formula: (Value / 1000) * ImageSize
        # Example: 5.0 / 1000.0 * 1000px = 5px
        radius_px = int((val_norm / 1000.0) * max_dim)
        
        return radius_px
    

    def process_high_res_mask(self, mask_arr, state, scale):
        """
        Add featering etc to high-res mask with best possible resource management 
        Called by ImageSesion
        """
        # Expand is precise, so we scale it explicitly
        expand = int(state.mask_expand * scale)
        
        # --- NEW: DYNAMIC FEATHER CALCULATION ---
        # We DO NOT multiply by scale here.
        # Instead, we recalculate based on 'mask_arr.shape' (the High Res shape).
        # This automatically handles the scaling!
        feather_px = self._calculate_dynamic_radius(state.mask_feather, mask_arr.shape)
        
        harden = float(state.mask_contrast)

        mask = mask_arr.copy()

        if expand != 0:
            k_size = abs(expand)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
            mask = cv2.dilate(mask, kernel) if expand > 0 else cv2.erode(mask, kernel)

        if feather_px > 0:
            mask = self.blur_mask_hybrid(mask, feather_px)

        if harden != 1.0:
            f_mask = mask.astype(np.float32) / 255.0
            f_mask = np.clip((f_mask - 0.5) * harden + 0.5, 0, 1)
            mask = (f_mask * 255).astype(np.uint8)

        return mask
    

    

    def _merge_mask_components(self, layer, base_mask):
        """
        Combines AI mask + User Add - User Subtract.
        Formula: (Base | Add) & ~Sub
        """
        final_mask = base_mask.copy()
        
        # 1. ADDITION (Union)
        if layer.user_added_mask is not None:
            # Safety resize (in case logic drifted)
            if layer.user_added_mask.shape != final_mask.shape:
                layer.user_added_mask = cv2.resize(layer.user_added_mask, (final_mask.shape[1], final_mask.shape[0]))
            
            final_mask = cv2.bitwise_or(final_mask, layer.user_added_mask)
            
        # 2. SUBTRACTION (Difference)
        if layer.user_subtracted_mask is not None:
            if layer.user_subtracted_mask.shape != final_mask.shape:
                layer.user_subtracted_mask = cv2.resize(layer.user_subtracted_mask, (final_mask.shape[1], final_mask.shape[0]))
            
            # Subtraction is: Mask AND (NOT Sub_Mask)
            final_mask = cv2.bitwise_and(final_mask, cv2.bitwise_not(layer.user_subtracted_mask))
            
        return final_mask

    def blur_mask_hybrid(self, mask, feather_amount):
        """
        Hybrid Feathering:
        1. 'Inner Cut': Clears a thin strip inside the edge to create a buffer.
        2. 'Padding': Adds black border outside for the blur math to work.
        3. 'Box Blur': Runs 3 fast passes.
        
        Result: A smooth fade that is guaranteed to reach 0 opacity at the layer boundary.
        """
        if feather_amount <= 0:
            return mask

        h, w = mask.shape[:2]
        
        # --- PARAMETERS ---
        # 1. Inner Buffer: How much we erase inside the image.
        # We use half the feather amount. This creates space for the fade to 'land' on 0.
        inner_gap = int(feather_amount * 0.5) 
        
        # Safety Check: Don't erase the whole image
        if inner_gap * 2 >= min(h, w):
            inner_gap = (min(h, w) // 2) - 1
        
        # 2. Blur Radius
        box_radius = int(feather_amount * 0.75)
        if box_radius < 1: box_radius = 1
        k_size = (box_radius * 2) + 1
        
        # 3. Outer Padding: Needs to be large enough to catch the blur
        pad = box_radius * 4#2

        # --- STEP A: INNER CUT (Create Buffer) ---
        # Work on a copy so we don't modify the source in place yet
        temp = mask.copy()
        if inner_gap > 0:
            temp[0:inner_gap, :] = 0        # Top
            temp[-inner_gap:, :] = 0        # Bottom
            temp[:, 0:inner_gap] = 0        # Left
            temp[:, -inner_gap:] = 0        # Right

        # --- STEP B: PAD ---
        padded = cv2.copyMakeBorder(
            temp, 
            pad, pad, pad, pad, 
            cv2.BORDER_CONSTANT, 
            value=0
        )

        # --- STEP C: 3-PASS BOX BLUR (Fast Gaussian Approx) ---
        for _ in range(3):
            padded = cv2.boxFilter(
                padded, 
                -1, 
                (k_size, k_size), 
                borderType=cv2.BORDER_CONSTANT
            )

        # --- STEP D: CROP & COPY (Contiguous Memory) ---
        # We crop back to the original size.
        # Because of the Inner Cut + Padding, the pixels at these edges 
        # are mathematically guaranteed to be extremely close to 0.
        return padded[pad:pad+h, pad:pad+w].copy()
    


    # def blur_mask_oldstyle(self, mask, feather_amount):
    #     """this is how the old software does it"""
    #     print(f"feather_amount= {feather_amount}")
    #     blurred_mask_graybgr = cv2.blur(mask, (feather_amount, feather_amount),
    #                         anchor=(-1,-1),borderType= cv2.BORDER_DEFAULT) #9)
    #     return blurred_mask_graybgr
        
    