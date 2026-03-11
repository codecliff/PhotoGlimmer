# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# Backend class that provides the rendering of final, full-sized image,
#  and saves it to disk , along with exif 
# Frontend will geneally make sure to call it as a separate thread
# Has to be abortable by user 
# RenderEngine : For rendering proxy image 
# ExportRenderEngine: For rendering the final image , then saving them with Exif.
#                     Uses RenderEngine.apply_layer_pipeline to apply strategies 
# #######################################################################

import os
import time
import cv2
import numpy as np
import gc

import piexif

from .BlendEngine import BlendEngine

#from memory_profiler import profile


try:
    import psutil
except ImportError:
    psutil = None

class ExportrenderEngine:
    """
    Handles the High-Resolution Export process.
    Responsible for:
    1. Upscaling coordinates (Proxy -> Full Res)
    2. Managing Memory (GC, RAM checks)
    3. Orchestrating the RenderEngine and MaskEngine for the final output
    4. Safe atomic file saving
    """
    
    def __init__(self):
        self._abort_flag = False
        self.logger = None # Will be injected or configured

    def set_logger(self, logger):
        self.logger = logger

    def abort(self):
        """Signals the export loop to stop."""
        print("ExportrenderEngine: aborting")
        self._abort_flag = True
    


    
    def run(self, source_img, sorted_layers, proxy_size,
             output_path, render_engine, mask_engine, abort_check_callback=None,
               max_timeout=120, image_quality=95, exif_dict=None):
        
        if self.logger: self.logger.info(f"Starting export to {output_path}...")
        
        self._abort_flag = False
        start_time = time.time()

        full_h, full_w = source_img.shape[:2]
        proxy_w, proxy_h = proxy_size 
        scale_x = full_w / float(proxy_w)
        scale_y = full_h / float(proxy_h)

        canvas_tmp = None 

        try:
            # GLOBAL PRE-PROCESSING
            # We apply White Balance/Global effects to the whole high-res source ONCE.
            bg_layer = next((l for l in sorted_layers if l.is_background), None)
            
            # Start with the raw source
            base_pixels = source_img 

            # process bakground layer

            if bg_layer and bg_layer.state.adjustments_enabled:
                if self.logger: self.logger.info("Baking global adjustments into source...")
                for s_key, strategy in render_engine.strategies.items():
                    if getattr(strategy, 'isGlobal', False):
                        global_params = bg_layer.state.adjustments.get(s_key)
                        if global_params:
                            # Apply directly to the full-res source (in-place if strategy allows)
                            base_pixels = strategy.apply(
                                base_pixels, None, global_params, scale_x, cache=None
                            )
            
            # process other layers
            
            for layer in sorted_layers:
                #  Check for user  abort at the start of every layer ---
                #if self._abort_flag: raise InterruptedError("Export cancelled.")
                # Check the callback from imagesession to see if user has requested cancellation 
                if abort_check_callback and abort_check_callback(): 
                    raise InterruptedError("Export cancelled by User.")
            
                if time.time() - start_time > max_timeout: raise TimeoutError("Timed out.")
                
                if psutil and psutil.virtual_memory().percent > 95: 
                    gc.collect()
                    if psutil.virtual_memory().percent > 95: raise MemoryError("RAM Critical.")

                if not layer.visible: continue
                
                # --- Upscaling Logic ---
                if getattr(layer, 'is_background', False):
                    bx, by, bw, bh = 0, 0, full_w, full_h
                else:
                    px, py, pw, ph = layer.bounds
                    cx_proxy = px + (pw / 2.0)
                    cy_proxy = py + (ph / 2.0)
                    target_w, target_h = int(round(pw * scale_x)), int(round(ph * scale_y))
                    cx_full, cy_full = cx_proxy * scale_x, cy_proxy * scale_y
                    bx, by = int(round(cx_full - (target_w / 2.0))), int(round(cy_full - (target_h / 2.0)))
                    bw, bh = target_w, target_h
                    bx, by = max(0, bx), max(0, by)
                    bw, bh = min(bw, full_w - bx), min(bh, full_h - by)
                
                if bw <= 0 or bh <= 0: continue

                # --- Mask Generation ---
                if self._abort_flag: raise InterruptedError("Export cancelled.")
                
                if getattr(layer, 'is_background', False):
                    refined_mask = np.full((bh, bw), 255, dtype=np.uint8)
                else:
                    target_mask_size = (bw, bh)
                    raw_mask_full = cv2.resize(layer.raw_mask, target_mask_size, interpolation=cv2.INTER_LINEAR)
                    combined_raw_full = raw_mask_full
                    if layer.user_added_mask is not None:
                        add_full = cv2.resize(layer.user_added_mask, target_mask_size, interpolation=cv2.INTER_NEAREST)
                        combined_raw_full = cv2.bitwise_or(combined_raw_full, add_full)
                    if layer.user_subtracted_mask is not None:
                        sub_full = cv2.resize(layer.user_subtracted_mask, target_mask_size, interpolation=cv2.INTER_NEAREST)
                        combined_raw_full = cv2.bitwise_and(combined_raw_full, cv2.bitwise_not(sub_full))
                    refined_mask = mask_engine.process_high_res_mask(combined_raw_full, layer.state, scale_x)

                # Extract Patch & Apply Pipeline 
                if self._abort_flag: raise InterruptedError("Export cancelled.")
                
                # Use base_pixels (already color corrected) instead of source_img (raw)
                original_patch = np.ascontiguousarray(base_pixels[by:by+bh, bx:bx+bw])
                
                # Call pipeline WITHOUT bg_layer_state. 
                # The corrected pixels are already in 'original_patch'.
                processed_uint8 = render_engine.apply_layer_pipeline(
                    original_patch, 
                    refined_mask, 
                    layer, 
                    scale_x
                )

                # --- COMPOSITING ---
                if canvas_tmp is None:
                    if bw == full_w and bh == full_h:
                        canvas_tmp = processed_uint8.copy() 
                    else:
                        canvas_tmp = np.zeros((full_h, full_w, 3), dtype=np.uint8)
                        canvas_tmp[by:by+bh, bx:bx+bw] = processed_uint8
                    del original_patch, processed_uint8, refined_mask
                    continue

                roi_view = canvas_tmp[by:by+bh, bx:bx+bw]
                render_engine.blend_overlay_tiled(
                    canvas_roi=roi_view, 
                    fg=processed_uint8, 
                    mask=refined_mask, 
                    opacity=layer.state.opacity
                )

                del roi_view, processed_uint8, refined_mask
                gc.collect()

            if self._abort_flag: raise InterruptedError("Export cancelled.")
            if canvas_tmp is not None:
                self._safe_save_image(canvas_tmp, output_path, image_quality, exif_dict)

        except Exception as e:
            # If we crash mid-export, we SHOULD clear cache to free up RAM 
            # so the UI can at least recover.
            # Note : A user abort also raises InterruptedError  
            from ..FaceMesh import FaceMeshService
            FaceMeshService().clear_cache()
            raise e        

        finally:
            #  Explicitly release the high-res buffer memory.
            if canvas_tmp is not None:
                del canvas_tmp
                canvas_tmp = None
            ################ 
	        #Do not flush large masks yet, user might re-export immediately    
            # It will be clered when user adds new image
            # # 2. FLUSH THE FACEMESH SINGLETON (The New Step)
            # # This releases the full sized skin/eye/lighting masks from RAM.
            # try:
            #     from ..FaceMesh import FaceMeshService
            #     FaceMeshService().clear_cache()
            #     if self.logger: self.logger.info("FaceMeshService cache cleared post-export.")
            # except Exception as e:
            #     if self.logger: self.logger.error(f"Failed to clear FaceMesh cache: {e}")
            ###################

            gc.collect()
    
    # end of run method        
        
        
        

    def _safe_save_image(self, image_bgr, output_path, image_quality=95, exif_dict=None):
        """
        Safely saves an image to disk using the temp-file ,then atomic-replace .
        Injects EXIF data from the original source if available.
        """
        output_dir = os.path.dirname(output_path)
        if not output_dir: output_dir = "." 
        
        ext = os.path.splitext(output_path)[1].lower()
        if not ext: ext = ".jpg"
        
        temp_filename = f".export_temp_{int(time.time())}{ext}"
        temp_path = os.path.join(output_dir, temp_filename)
        
        # Local ref to allow explicit deletion
        img_ref = image_bgr
        
        try:
            # 1. Save Pixel Data (Strips Metadata)
            # This is the last time we need the massive numpy array
            success = cv2.imwrite(temp_path, img_ref, [int(cv2.IMWRITE_JPEG_QUALITY), image_quality])
            
            #
            # Sever the reference to the 150MB+ buffer immediately.
            # Allows the  memory to be freed while we process EXIF.
            del img_ref
            image_bgr = None 
            # ---------------------------

            if not success:
                raise IOError(f"OpenCV failed to write to {temp_path}")

            # 2. EXIF Injection (The Sandwich Strategy)
            if ext in ['.jpg', '.jpeg', '.webp']:
               if exif_dict:
                try:
                    # Inject "Branding" right before dumping
                    exif_dict["0th"][piexif.ImageIFD.Software] = "Photoglimmer"
                    exif_bytes = piexif.dump(exif_dict)
                    piexif.insert(exif_bytes, temp_path)
                    del exif_bytes # Clean up the binary blob
                    exif_bytes= None
                except Exception as e:
                    self.logger.warning(f"Metadata injection failed: {e}")
                #End EXIF injection     

            # 3. Atomic Replace
            os.replace(temp_path, output_path)
            if self.logger: self.logger.info(f"Export successful: {output_path}")

        except Exception as e:
            if self.logger: self.logger.error(f"Export failed: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError: pass 
            raise e
        
        finally:
            # Final sweep to ensure no large local variables survived
            img_ref = None
            gc.collect()

            