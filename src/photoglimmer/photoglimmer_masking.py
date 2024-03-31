
import os
import numpy as np
import cv2
import mediapipe as mp
mp_drawing = mp.solutions.drawing_utils
mp_selfie_segmentation = mp.solutions.selfie_segmentation


def  bilateralBlurFilter(imgbgr, i=15, j=80, k=75):
    bbimg= cv2.bilateralFilter(imgbgr, i, j, k)
    return bbimg


def  __createSegmentationMask(imgpath, thresh):
    BG_COLOR = (0, 0, 0)  
    MASK_COLOR = (255, 255, 255)  
    mask_image_rgb_solidcolor=None
    with mp_selfie_segmentation.SelfieSegmentation(
            model_selection=0) as selfie_segmentation:
        image_bgr = cv2.imread(imgpath)
        image_height, image_width, _ = image_bgr.shape
        image_bil_bgr=bilateralBlurFilter(image_bgr)        
        results_rgb = selfie_segmentation.process(
            cv2.cvtColor(image_bil_bgr, cv2.COLOR_BGR2RGB))      
        condition = np.stack(
            (results_rgb.segmentation_mask, ) * 3, axis=-1) > thresh  
        fg_image = np.zeros(image_bgr.shape, dtype=np.uint8)
        fg_image[:] = MASK_COLOR
        bg_image = np.zeros(image_bgr.shape, dtype=np.uint8)
        bg_image[:] = BG_COLOR
        mask_image_rgb_solidcolor = np.where( condition, fg_image,
                              bg_image)  
    return mask_image_rgb_solidcolor


def  createSegmentationMask_Improved(imgpath, thresh, 
                                    tempdirpath,fname_maskImg,  ):
    image_copy_bgr = cv2.imread(imgpath)  
    height,width,_= image_copy_bgr.shape
    mask_image_graybgr= __createSegmentationMask(imgpath,thresh)
    mask_copy_gray=cv2.cvtColor(mask_image_graybgr, cv2.COLOR_BGR2GRAY) 
    contours, hierarchy = cv2.findContours(mask_copy_gray, cv2.RETR_EXTERNAL, 
                                      cv2.CHAIN_APPROX_NONE)
    if len(contours)==0 :        
        return np.zeros((height,width,3), np.uint8)    
    x,y,w,h = cv2.boundingRect(contours[-1])
    dims= mask_image_graybgr.shape    
    (X,Y,W,H) =  (max(x-20,0),max(y-20, 0),min(w+40,dims[1]),min(h+40, dims[0]))        
    # https://stackoverflow.com/a/60869657/5132823 
    img_cropped= image_copy_bgr[Y:Y+H, X:X+W]    
    croppedimgpath= os.path.join(tempdirpath,"img_cropped.jpg") 
    cv2.imwrite(croppedimgpath, img_cropped)   
    croppedimg_mask_graybgr= __createSegmentationMask( croppedimgpath, thresh)
    mask_image_graybgr[Y:Y+H, X:X+W] = croppedimg_mask_graybgr    
    cv2.imwrite(os.path.join(tempdirpath,fname_maskImg), mask_image_graybgr)         
    return mask_image_graybgr    