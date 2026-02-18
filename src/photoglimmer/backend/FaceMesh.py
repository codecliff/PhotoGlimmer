# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# This file  providees spcialized masks like skin, face , and eyes  
# We are not using downloaded models like multi-class
# all these are being generated fromt mediapipe's inbuilt selfie segmentation model
# #######################################################################


# ================================================================================
# FACEMESH SERVICE (SINGLETON)
# ================================================================================
# Note: Use this for face-specific edits. For a general mask of all people 
#       in a layer, use the standard Segmenter instead.
# How it works:
# 1. AI logic runs only ONCE per unique image buffer (Layer or Patch).  (Patch=numpy array)
# 2. The render loop selects one Layer at a time and applies all the Strategies using same 
#    Shared _mask_cache. 
# 3. This cache is overwritten when next layer is processed ` .
# 4. All masks returned match the input image dimensions (uint8).
#
# Usage:
#   service = FaceMeshService() # will get the already running singleton instance
#   mask = service.get_skin_mask(image_bgr) # will get cached , or oen will be created   
#
# ================================================================================


import cv2
import numpy as np
import mediapipe as mp
# from memory_profiler import profile

class FaceMeshService:
    _instance = None # flag for Singleton class
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceMeshService, cls).__new__(cls)
            cls._instance.mp_face_mesh = mp.solutions.face_mesh
            cls._instance.face_mesh = cls._instance.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True, 
                min_detection_confidence=0.5
            )
            cls._instance._mask_cache = {}
            cls._instance._current_img_id = None
        return cls._instance

    # def _check_cache(self, image_bgr):
    #    memory id based cache test was too unreliable 
    #     """ change the _current_img_id if we have switched image(layer) """
    #     # img_id = id(image_bgr)
    #     # if img_id != self._current_img_id:
    #     #     self._mask_cache.clear()
    #     #     self._current_img_id = img_id
    #     ## memory based id() was too unreliable!


    def _check_cache(self, image_bgr):    
        """
        Fingerprint the image to see if we are still on the same layer.
        
        Fingerprining needed because we have to guess layer from the image.
        uses size and corners and saves fingerprint as id        
        """
        h, w = image_bgr.shape[:2]
        # Hash shape + corner pixels + center pixel
        # This is extremely fast and much more reliable than id()
        img_fingerprint = (h, w, image_bgr[0,0,0], image_bgr[h//2, w//2, 0])
        
        if img_fingerprint != self._current_img_id:
            self._mask_cache.clear()
            self._current_img_id = img_fingerprint

    def _get_landmarks_px(self, image_bgr):
        """return cached mask or generate new and cache it as well"""
        self._check_cache(image_bgr)
        if "landmarks" in self._mask_cache:
            return self._mask_cache["landmarks"]

        h, w = image_bgr.shape[:2]
        if h == 0 or w == 0: return None
        
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark
        pts = [(int(pt.x * w), int(pt.y * h)) for pt in landmarks]
        
        self._mask_cache["landmarks"] = pts
        return pts

    def get_eye_masks(self, image_bgr):
        """Returns (sclera_mask, iris_mask) with internal caching."""
        self._check_cache(image_bgr)
        if "eye_masks" in self._mask_cache:
            return self._mask_cache["eye_masks"]

        pts = self._get_landmarks_px(image_bgr)
        if pts is None: return None

        h, w = image_bgr.shape[:2]
        s_mask = np.zeros((h, w), dtype=np.uint8)
        i_mask = np.zeros((h, w), dtype=np.uint8)

        # MediaPipe Refinement Indices
        # Sclera (Eye Opening)
        l_eye = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        r_eye = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        # Iris (Center Circle)
        l_iris = [468, 469, 470, 471, 472]
        r_iris = [473, 474, 475, 476, 477]

        for eye in [l_eye, r_eye]:
            cv2.fillPoly(s_mask, [np.array([pts[i] for i in eye], np.int32)], 255)
        for iris in [l_iris, r_iris]:
            cv2.fillPoly(i_mask, [np.array([pts[i] for i in iris], np.int32)], 255)

        res = (s_mask, i_mask)
        self._mask_cache["eye_masks"] = res
        return res

    
    
    # we are not using it  now. only face skin is smoothed d
    def get_full_body_skin_mask(self, image_bgr):
        self._check_cache(image_bgr)
        if "full_skin" in self._mask_cache:
            return self._mask_cache["full_skin"]

        print("Generating ADAPTIVE full_skin mask...")
        ycrcb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2YCrCb)
        
        # 1. Get landmarks to find a "Skin Reference"
        pts = self._get_landmarks_px(image_bgr)
        
        if pts:
            # Indices for Forehead (10) and Cheeks (117, 346)
            # We take a small 5x5 average around these points to get the "True Skin" color
            sample_points = [pts[10], pts[117], pts[346]]
            crs, cbs = [], []
            for px, py in sample_points:
                # Basic bounds check
                if 0 <= py < ycrcb.shape[0] and 0 <= px < ycrcb.shape[1]:
                    region = ycrcb[max(0, py-2):py+2, max(0, px-2):px+2]
                    crs.append(np.mean(region[:, :, 1]))
                    cbs.append(np.mean(region[:, :, 2]))
            
            avg_cr = np.mean(crs)
            avg_cb = np.mean(cbs)
            
            # Adaptive window: tighten if lighting is harsh, loosen if skin is varied
            lower_skin = np.array([0, int(avg_cr - 12), int(avg_cb - 12)], dtype=np.uint8)
            upper_skin = np.array([255, int(avg_cr + 12), int(avg_cb + 12)], dtype=np.uint8)
        else:
            # Fallback to broader range if no face is visible
            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)

        color_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        face_mask = self.get_skin_mask(image_bgr)
        
        # Combine
        full_mask = cv2.bitwise_or(color_mask, face_mask) if face_mask is not None else color_mask

        # Morphology to remove noise (clothing specs) and fill holes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        full_mask = cv2.morphologyEx(full_mask, cv2.MORPH_OPEN, kernel) # Remove small noise
        full_mask = cv2.dilate(full_mask, kernel, iterations=1)         # Close small gaps
        
        self._mask_cache["full_skin"] = full_mask
        cv2.imwrite("full_body_skin_mask.jpg", full_mask)
        return full_mask
    

    


    def get_skin_mask(self, image_bgr):
        """Returns a mask of the skin ONLY (Face + Neck extension, minus Features)."""
        self._check_cache(image_bgr)
        if "face_skin" in self._mask_cache:
            return self._mask_cache["face_skin"]

        pts = self._get_landmarks_px(image_bgr)
        if pts is None: return None
        
        h, w = image_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        # 1. MAIN FACE OVAL
        face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
        cv2.fillPoly(mask, [np.array([pts[i] for i in face_oval], np.int32)], 255)
        
        # 2. DYNAMIC NECK EXTENSION
        # Calculate 'Face Height' to make neck size relative to the person
        face_height = np.linalg.norm(np.array(pts[10]) - np.array(pts[152]))
        neck_depth = int(face_height * 0.4) # Project neck down by 40% of face height
        
        # Bottom jaw arc: Right to Left
        bottom_jaw = [58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288]
        jaw_pts = [pts[i] for i in bottom_jaw]
        
        # Project points downward
        neck_base_pts = []
        for i in bottom_jaw:
            px, py = pts[i]
            # Ensure we don't go out of image bounds
            neck_base_pts.append((px, min(h - 1, py + neck_depth)))
        
        # Create and fill the neck polygon (Jaw points + Projected points in reverse)
        neck_poly = np.array(jaw_pts + neck_base_pts[::-1], np.int32)
        cv2.fillPoly(mask, [neck_poly], 255)

        # 3. KEEP-OUT ZONES (Eyes, Lips, Brows)
        features = [
            [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398], # L Eye
            [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],    # R Eye
            [276, 283, 300, 293, 334, 296, 336, 285],                                         # L Brow
            [46, 53, 52, 65, 55, 70, 63, 105],                                                # R Brow
            [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 61]                            # Lips
        ]
        for zone in features:
             cv2.fillPoly(mask, [np.array([pts[i] for i in zone], np.int32)], 0)

        # 4. SMOOTH THE TRANSITION
        # A tiny bit of blur on the mask itself prevents hard edges at the bottom of the neck
        mask = cv2.GaussianBlur(mask, (15, 15), 0)

        self._mask_cache["face_skin"] = mask
        return mask
    

    def get_landmarks_3d(self, image_bgr):
        self._check_cache(image_bgr)
        if "landmarks_3d" in self._mask_cache:
            return self._mask_cache["landmarks_3d"]

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        if not results.multi_face_landmarks: return None

        landmarks = results.multi_face_landmarks[0].landmark
        res = [(pt.x, pt.y, pt.z) for pt in landmarks]
        self._mask_cache["landmarks_3d"] = res
        return res
    
    def get_lighting_mask(self, image_bgr):
        """
        Used by Gaffer Strategy.
        Returns T-Zone/Cheeks mask (uint8) with internal caching.
        """
        self._check_cache(image_bgr)
        if "lighting_mask" in self._mask_cache:
            return self._mask_cache["lighting_mask"]

        pts = self._get_landmarks_px(image_bgr)
        if pts is None: return None
        
        h, w = image_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        # Indices for T-Zone and Cheeks
        t_zone = [10, 109, 4, 338]
        left_cheek = [116, 117, 118, 123, 50]
        right_cheek = [345, 346, 347, 352, 280]

        # Draw regions with varying intensities for a natural 'Fill' feel
        cv2.fillPoly(mask, [np.array([pts[i] for i in t_zone], np.int32)], 255)
        cv2.fillPoly(mask, [np.array([pts[i] for i in left_cheek], np.int32)], 180)
        cv2.fillPoly(mask, [np.array([pts[i] for i in right_cheek], np.int32)], 180)
        
        self._mask_cache["lighting_mask"] = mask
        return mask
    
    def clear_cache(self):
        """Safely wipes the cache."""        
        self._mask_cache.clear()
        self._current_img_id = None
        