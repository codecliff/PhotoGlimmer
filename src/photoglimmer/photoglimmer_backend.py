
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL 
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.   
#  Description : 
# Backend for the applicaiton. 
# Is totally frontend-agnostic and can be plugged in with another UI  
# Multithreading is to be handled by the frontend 
import cv2
import mediapipe as mp
import numpy as np
import os
import splines
from math import exp 
# from memory_profiler import profile
mp_drawing = mp.solutions.drawing_utils
mp_selfie_segmentation = mp.solutions.selfie_segmentation
seg_mode="FORE" 
seg_threshold = 0.5
blendweight_img1 = 0.5
contrast = 1.0
brightness = 1.0
saturation = 1.0
alpha = 1.0
beta = 50
gamma = 0.4
blur_edge=10.0
postprocess_it=True
denoise_it =True
imageAdjustMode = "HSV"  
tempdirpath= ""
originalImgPath="" 
scaledImgpath = "" 
fname_maskImg="mask.jpg"
fname_maskImgBlurred="blurred_mask.jpg"
scaleFactor=1.0


def  adjustImageHSV(image_bgr, saturation_fact=1.0, value_fact=1):
    imghsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype("float32")
    h, s, v = cv2.split(imghsv)
    s= adjustAsColorCurve(s,h=saturation_fact )
    s= np.clip(s, 0,255)
    v= adjustAsColorCurve(v,h=value_fact )
    v= np.clip(v, 0,255) 
    imghsv = cv2.merge([h, s, v])   
    img_bgr = cv2.cvtColor(imghsv.astype("uint8"), cv2.COLOR_HSV2BGR)    
    return img_bgr


def  adjustAsColorCurve(Xmat2D, h ):    
    y= np.add( (-1* ( (h*np.square(Xmat2D-128))/(128**2) )),Xmat2D) +h 
    y=np.clip(y,0,255 )
    return y


def  splineStretch( imgbgr ,  xvals = [0, 64, 128,  192, 255],
                  yvals = [0, 56,  128, 220, 255]):
    res = splines.CatmullRom(yvals, xvals)
    LUT = np.uint8(res.evaluate(range(0,256)))    
    stretched_bgr = cv2.LUT(imgbgr, LUT)
    return stretched_bgr


def  deNoiseImage(imgrgb):
    return cv2.fastNlMeansDenoisingColored(imgrgb, None, 4, 4, 7, 15)


def  bilateralBlurFilter(imgbgr, i=15, j=80, k=75):
    bbimg= cv2.bilateralFilter(imgbgr, i, j, k)
    return bbimg


def  resizeImageToFit(img_bgr, maxwidth=1200, maxheight=800):
    global scaleFactor
    h, w, _ = img_bgr.shape     
    if (w<=maxwidth) and (h<=maxheight):
        return img_bgr    
    scalefactor= min( maxwidth/w , maxheight/h) 
    scaleFactor= scalefactor       
    dim2=( int(w*scalefactor), int(h*scalefactor) )
    return cv2.resize(img_bgr, dim2, cv2.INTER_CUBIC )


def  _createSegmentationMask(imgpath, thresh):
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


def  createSegmentationMask_Improved(imgpath, thresh ):
    image_copy_bgr = cv2.imread(imgpath)  
    height,width,_= image_copy_bgr.shape
    mask_image_graybgr= _createSegmentationMask(imgpath,thresh)
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
    croppedimg_mask_graybgr= _createSegmentationMask( croppedimgpath, thresh)
    mask_image_graybgr[Y:Y+H, X:X+W] = croppedimg_mask_graybgr    
    if(seg_mode=='BG'):
        mask_image_graybgr = cv2.bitwise_not(mask_image_graybgr) 
    cv2.imwrite(os.path.join(tempdirpath,fname_maskImg), mask_image_graybgr)         
    return mask_image_graybgr    


def  createMaskedBrightness(sourceimg_bgr, maskimgimg_graybgr , originalImage=False):
    mask_graybgr = cv2.resize(maskimgimg_graybgr, sourceimg_bgr.shape[1::-1]) 
    bright_image_bgr= None   
    bright_image_bgr = adjustImageHSV(sourceimg_bgr, saturation_fact=saturation, value_fact=brightness)
    if (denoise_it):        
        bright_image_bgr = deNoiseImage(bright_image_bgr )     
    blur_edge_tmp= blur_edge
    if (originalImage) : 
        blur_edge_tmp = int(blur_edge/scaleFactor)
    blurred_mask_graybgr = cv2.blur(mask_graybgr, (blur_edge_tmp, blur_edge_tmp),
                            anchor=(-1,-1),borderType= cv2.BORDER_DEFAULT) 
    cv2.imwrite(os.path.join(tempdirpath, fname_maskImgBlurred), blurred_mask_graybgr)
    bright_masked_bgr=None
    max_image_bgr = None
    if (brightness>0): 
        msk_bgr= blurred_mask_graybgr/255
        bright_masked_bgr= np.uint8(bright_image_bgr * msk_bgr)
        bright_masked_bgr= np.clip(bright_masked_bgr, 0, 255)
        max_image_bgr = cv2.max(sourceimg_bgr, bright_masked_bgr) 
    else: 
        blurred_mask_graybgr=cv2.bitwise_not(blurred_mask_graybgr) 
        bright_masked_bgr = cv2.max(bright_image_bgr, blurred_mask_graybgr) 
        max_image_bgr = cv2.min(sourceimg_bgr, bright_masked_bgr) 
    addWted_bgr = cv2.addWeighted(sourceimg_bgr,
                              blendweight_img1,
                              max_image_bgr, (1.0 - blendweight_img1),
                              gamma=0)
    if postprocess_it: 
        addWted_bgr=splineStretch(addWted_bgr)   
    return addWted_bgr


def  processImageFinal(isOriginalImage=False , isSegmentationNeeded=True  ):
    image_bgr= None
    maskimg_graybgr= cv2.imread(os.path.join(tempdirpath,fname_maskImg))
    if isOriginalImage: 
        image_bgr = cv2.imread(originalImgPath)
    else: 
        image_bgr = cv2.imread(scaledImgpath)
        if (isSegmentationNeeded):
            maskimg_graybgr= createSegmentationMask_Improved(scaledImgpath, seg_threshold) 
    result_bgr = createMaskedBrightness(sourceimg_bgr=image_bgr,
                                    maskimgimg_graybgr=maskimg_graybgr , originalImage= isOriginalImage)
    return result_bgr