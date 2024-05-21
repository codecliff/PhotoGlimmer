
import numpy as np
import cv2
import splines
 #/* FUNCTIONS TO ALTER IMAGE BRIGHTNESS */#


def  adjustImageHSV(image_bgr, saturation_fact=1.0, value_fact=1):
    imghsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV) 
    imghsv[:,:,1]=((imghsv[:,:,1].astype("float32")
                    )*(1+saturation_fact/200)).clip(0,255).astype("uint8")      
    imghsv[:,:,2]=adjustAsColorCurve_u8( imghsv[:,:,2], value_fact) 
    return cv2.cvtColor(imghsv, cv2.COLOR_HSV2BGR) 


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


def  blurImage(imgBGR, k=9 ):
    res = cv2.GaussianBlur(imgBGR, (k, k), 0)
    return res