
# ###############################################################################
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.
# Description :
# Multiple options to alter Image Color, Saturation, applying LUT to images, etc
# ###############################################################################
import numpy as np
import cv2
import splines
# from memory_profiler import profile
from line_profiler import profile
 #/* FUNCTIONS TO ALTER IMAGE BRIGHTNESS */#
# @profile


def  adjustImageLUT2025(image_bgr, lut):
        if not lut:
             return image_bgr
        if lut == [i for i in range (0,256)]: 
             return image_bgr
        lut_np = np.array(lut, dtype=np.uint8)
        img_to_process = image_bgr
        alpha_channel = None
        if img_to_process.ndim == 3 and img_to_process.shape[2] == 4:
             print("Separating alpha channel for processing.")
             alpha_channel = img_to_process[:, :, 3]
             img_to_process = img_to_process[:, :, :3] 
        if img_to_process.dtype != np.uint8:
             print(f"Warning: Converting image from {img_to_process.dtype} to uint8 for LUT application.")
             if np.issubdtype(img_to_process.dtype, np.floating):
                  img_to_process = (img_to_process * 255).clip(0, 255).astype(np.uint8)
             elif np.issubdtype(img_to_process.dtype, np.integer):
                  max_val = np.iinfo(img_to_process.dtype).max
                  img_to_process = (img_to_process / max_val * 255).astype(np.uint8)
             else:
                  print(f"Error: Unsupported image dtype {img_to_process.dtype} for LUT.")
        try:
            processed_bgr = cv2.LUT(img_to_process, lut_np)
            return processed_bgr 
        except cv2.error as e:
            print(f"OpenCV LUT Error: {e}")            
            return None


def  adjustImageHSV(image_bgr, saturation_fact=1.0, value_fact=1):
    imghsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV) 
    imghsv[:,:,1]=((imghsv[:,:,1].astype("float32")
                    )*(1+saturation_fact/200)).clip(0,255).astype("uint8")      
    imghsv[:,:,2]=adjustAsColorCurve_u8( imghsv[:,:,2], value_fact) 
    return cv2.cvtColor(imghsv, cv2.COLOR_HSV2BGR) 


def  adjustImagePillowEnhance( image_bgr,  value_fact=1) :
    from PIL import Image, ImageTk, ImageEnhance  
    value= (value_fact+200.0)/200 
    image=  Image.fromarray( cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB) )
    brightness = float(value) 
    enhancer = ImageEnhance.Brightness(image)
    bright_image = enhancer.enhance(brightness)
    return cv2.cvtColor(np.array(bright_image), cv2.COLOR_RGB2BGR) 


def  adjustImageBGR(image_bgr,  value_fact=1):
    im=image_bgr.copy().astype(np.float32)
    im= adjustAsColorCurve(image_bgr, value_fact)
    im=np.clip(im,1,255)
    return im.astype(np.uint8)


def  adjustAsColorCurve(Xmat2D, h ):    
    y= np.add( (-1* ( (h*np.square(Xmat2D-128))/(128**2) )),Xmat2D) +h 
    y=np.clip(y,0,255 )
    return y


def  adjustAsColorCurve_u8(Xmat2D_u8, h ):    
    X= Xmat2D_u8.astype("float32")
    y= np.add( (-1* ( (h*np.square(X-128))/(128**2) )),X) +h 
    y=np.clip(y,0,255 )
    return y.astype("uint8")


def  splineStretch( imgbgr ,  xvals = [0, 64, 128,  192, 255],
                  yvals = [0, 56,  128, 220, 255]):
    res = splines.CatmullRom(yvals, xvals)
    LUT = np.uint8(res.evaluate(range(0,256)))    
    stretched_bgr = cv2.LUT(imgbgr, LUT)
    return stretched_bgr


def  deNoiseImage(imgrgb):
    return cv2.fastNlMeansDenoisingColored(imgrgb, None, 4, 4, 7, 15)


def  denoiseImageBilatF(imgbgr):
    return cv2.bilateralFilter(imgbgr, 9, 35, 35)


def  blurImage(imgBGR, k=9 ):
    res = cv2.GaussianBlur(imgBGR, (k, k), 0)
    return res
if __name__ == '__main__':
    import math
    img_bgr=cv2.imread("your_image_path")  
    _= blurImage(img_bgr, k=9)
    _= deNoiseImage(img_bgr)
    _=denoiseImageBilatF(img_bgr)
    _=adjustImageHSV(img_bgr, saturation_fact=1.0, value_fact=1)
    s_curve_lut = [int(round(255 * (0.5 * (math.sin((i / 255.0 - 0.5) * math.pi) + 1)))) for i in range(256)]
    _=adjustImageLUT2025(img_bgr, s_curve_lut)