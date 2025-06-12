
## class to save paramters for bg and fg images current state
## images will be saved in this state anyway, but this
## will be useful for-
## 1) loading parameters on bg-fg switch
## and 2) when apllying to whole image for save
import numpy as np


class  ImgParams:
    #static variables common to bg and fg images
    seg_threshold: float = 0.5
    blendweight_img1: float = 0.5
    blur_edge: float = 10.0
    #booleans
    postprocess_it: bool = True


    def  __init__(self, imgpath: str) :
        self.imgpath= imgpath
        self.brightness = 1.0
        self.saturation = 1.0
        self.denoise_it = False 
        self.LUT= None


    def  setValues(  self, 
            seg_threshold: float,
            blendweight_img1: float,
            blur_edge: float,
            postprocess_it: bool,
            brightness: float,
            saturation: float,
            denoise_it: bool,
            lut:np.ndarray
            ):
        ImgParams.seg_threshold = seg_threshold
        ImgParams.blendweight_img1 = blendweight_img1
        ImgParams.blur_edge = blur_edge
        ImgParams.postprocess_it = postprocess_it
        self.brightness = brightness
        self.saturation = saturation
        self.denoise_it = denoise_it        
        self.LUT= lut