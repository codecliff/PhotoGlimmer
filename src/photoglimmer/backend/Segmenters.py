      
# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################

 
# Mediapipe is the only Segmentation backend we are using 
# There too, we are only using the inbuilt selfie segmenter 
# IF we use a downlaoded model like mediapipe multi-segmenter,
# place the tflite file in asstes/models/ folder  
         
import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Any

import logging
from  .Interfaces import APP_NAME #, SegmenterStrategy

logger = logging.getLogger(APP_NAME)



# class MediaPipeSelfieSegmenter(SegmenterStrategy):
class MediaPipeSelfieSegmenter():      #just to avoid a reference , for now
    def __init__(self, model_selection: int = 0):
        """
        model_selection: 0 for general, 1 for landscape (faster/closer)
        """
        self.mp_selfie = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie.SelfieSegmentation(model_selection=model_selection)

    

    def segment(self, bgr_patch: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Returns the RAW Probability Map (0-255).
        No thresholding here. We preserve the AI's full 'opinion'.
        """
        # 1. Prepare
        rgb_patch = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2RGB)

        # 2. Run AI
        results = self.segmenter.process(rgb_patch)
        
        # 3. Extract Confidence Map (float 0.0 - 1.0)
        if results.segmentation_mask is not None:
            confidence_map = results.segmentation_mask
        else:
            return np.zeros(bgr_patch.shape[:2], dtype=np.uint8)

        # 4. Convert to Grayscale Range (0-255)
        # We DO NOT apply a threshold here. We want the gradients.
        soft_mask = (confidence_map * 255).astype(np.uint8)

        return soft_mask
    

    def __del__(self):
        self.segmenter.close()
        