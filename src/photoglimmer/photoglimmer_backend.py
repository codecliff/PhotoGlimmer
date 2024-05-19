
# ###############################################################################
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.
# Description :
# Backend for the applicaiton.
# Is totally frontend-agnostic and can be plugged in with another UI
# Multithreading is to be handled by the frontend
# ###############################################################################
import cv2
import mediapipe as mp
import numpy as np
import os, shutil
from math import exp
from photoglimmer.imgparams import *
from photoglimmer.photoglimmer_imgtweaker import *
from photoglimmer.photoglimmer_masking import *
from photoglimmer.photoglimmer_exif import *
from photoglimmer.photoglimmer_imagelayers import *
from photoglimmer.photoglimmer_arraylevel import *
# from memory_profiler import profile
seg_mode="FORE" 
imageAdjustMode = "HSV"  
tempdirpath= ""
originalImgPath="" 
scaledImgpath = "" 
resultImgPath="" 
fname_maskImg="mask.jpg"
fname_maskImgBlurred="blurred_mask.jpg"
scaleFactor=1.0 
fname_bgimg="bgtmp.png" 
fname_fgimg="fgtmp.png" 
fname_resultimg= "result_image.jpg"
fgImgpath=""
bgImgpath=""
bg_image_params= ImgParams( fgImgpath)
fg_image_params= ImgParams(bgImgpath )
currImg= fg_image_params
blurfactor_bg:int=0
transparency_only:bool=False


def  initializeImageObjects():
    global fgImgpath, bgImgpath, fg_image_params, bg_image_params, currImg
    if tempdirpath == "":
        raise Exception("Fatal! Temp directory not created ?!!  ")
    bgImgpath = os.path.join(tempdirpath, fname_bgimg)
    fgImgpath = os.path.join(tempdirpath, fname_fgimg)
    bg_image_params= ImgParams( bgImgpath)
    fg_image_params= ImgParams(fgImgpath )
    currImg= fg_image_params


def  setupWorkingImages(scaledimg_bgr):
    global scaledImgpath, resultImgPath
    scaledImgpath = os.path.join(tempdirpath, "working_image.jpg")
    cv2.imwrite(scaledImgpath, scaledimg_bgr, params=[cv2.IMWRITE_JPEG_QUALITY, 100])
    resultImgPath = os.path.join(tempdirpath, fname_resultimg)
    shutil.copyfile(src=scaledImgpath, dst=fgImgpath)
    shutil.copyfile(src=scaledImgpath, dst=bgImgpath)
    shutil.copyfile(src=scaledImgpath, dst=resultImgPath)


def  resizeImageToFit(img_bgr, maxwidth=1200, maxheight=800):
    global scaleFactor
    h, w = img_bgr.shape[0],img_bgr.shape[1] 
    if (w<=maxwidth) and (h<=maxheight):
        return img_bgr
    scalefactor= min( maxwidth/w , maxheight/h) 
    scaleFactor= scalefactor
    dim2=( int(w*scalefactor), int(h*scalefactor) )
    return cv2.resize(img_bgr, dim2, cv2.INTER_CUBIC )


def  blurBackground( k:int ):
    if (k%2==0):
        k+=1
    blurred_bg_bgr=blurImage(cv2.imread(scaledImgpath),
                                 k=k) 
    _ =tweakAndSaveImage( blurred_bg_bgr , bg_image_params)


def  tweakAndSaveImage( sourceimg_bgr , imglayer_param):
    result_bgr = adjustImageHSV(image_bgr=sourceimg_bgr,
                                          saturation_fact=imglayer_param.saturation,
                                          value_fact=imglayer_param.brightness)
    if currImg.denoise_it:
        result_bgr = deNoiseImage(result_bgr )
    cv2.imwrite( filename=imglayer_param.imgpath, img=result_bgr ,params=[cv2.IMWRITE_JPEG_QUALITY, 100] )
    return result_bgr


def  blurAndSaveMask(imglayer_param,mask_graybgr, originalImage=False ):
    blur_edge_tmp= imglayer_param.blur_edge
    if (originalImage) :
        blur_edge_tmp = int(imglayer_param.blur_edge/scaleFactor)
    blurred_mask_graybgr = cv2.blur(mask_graybgr, (blur_edge_tmp, blur_edge_tmp),
                            anchor=(-1,-1),borderType= cv2.BORDER_DEFAULT) 
    cv2.imwrite(os.path.join(tempdirpath, fname_maskImgBlurred), blurred_mask_graybgr, params=[cv2.IMWRITE_JPEG_QUALITY, 100])
    return blurred_mask_graybgr


def  createMaskedBrightness(sourceimg_bgr, maskimgimg_graybgr ,
                           originalImage=False, isTweakNeeded=True):
    bright_image_bgr=  sourceimg_bgr.copy()
    if (isTweakNeeded and not originalImage) :
        bright_image_bgr =tweakAndSaveImage( bright_image_bgr , currImg)
    if (originalImage) :
        _ =tweakAndSaveImage( bright_image_bgr , fg_image_params)
        _ =tweakAndSaveImage( bright_image_bgr , bg_image_params)
    bright_image_bgr=None
    if ( blurfactor_bg>1) : 
        blurBackground(k=blurfactor_bg)
    mask_graybgr = cv2.resize(maskimgimg_graybgr, sourceimg_bgr.shape[1::-1])
    blurred_mask_graybgr = blurAndSaveMask( currImg, mask_graybgr, originalImage )
    stacked_img_bgr = stackNMask_HSV_u8(
        img_bgr=sourceimg_bgr,
        fg_image_bgr=cv2.imread(fg_image_params.imgpath),
        bg_image_bgr=cv2.imread(bg_image_params.imgpath),
        blurred_mask_gray_bgr=blurred_mask_graybgr)
    addWted_bgr = blendImages(sourceimg_bgr,
                              stacked_img_bgr,
                              ImgParams.blendweight_img1)
    if ImgParams.postprocess_it:
        addWted_bgr=splineStretch(addWted_bgr)
    cv2.imwrite(filename=resultImgPath, img= addWted_bgr, params=[cv2.IMWRITE_JPEG_QUALITY, 95])
    return addWted_bgr


def  processImageFinal(isOriginalImage=False , isSegmentationNeeded=True , 
                      isTweakingNeeded=True
                      ):
    image_bgr= None
    maskimg_graybgr= cv2.imread(os.path.join(tempdirpath,fname_maskImg))
    if isOriginalImage: 
        image_bgr = cv2.imread(originalImgPath)
        setupWorkingImages(image_bgr)
    else: 
        image_bgr =  cv2.imread(scaledImgpath)        
        if (isSegmentationNeeded):
            maskimg_graybgr= createSegmentationMask_Improved(scaledImgpath,
                                                             ImgParams.seg_threshold,
                                                             tempdirpath,
                                                             fname_maskImg
                                                             )
    result_bgr=None  
    global transparency_only
    if (isOriginalImage and transparency_only):
        result_bgra= saveTransparentImage( image_bgr, maskimg_graybgr)
        transparency_only=False
        return result_bgra
    else: 
        result_bgr = createMaskedBrightness(sourceimg_bgr=image_bgr,
                                    maskimgimg_graybgr=maskimg_graybgr,
                                    originalImage= isOriginalImage)
    return result_bgr


def  setCurrValues(seg_threshold, blendweight_img1, blur_edge, postprocess_it,
                  brightness, saturation, denoise_it):
    currImg.setValues(seg_threshold, blendweight_img1, blur_edge,
                      postprocess_it, brightness, saturation, denoise_it)


def  switchImgLayer( new_seg_mode ): 
    global currImg
    if new_seg_mode not in ["FORE", "BG"]:
        print(f"invalid seg_mode {new_seg_mode}")
        return
    currImg = bg_image_params if (new_seg_mode=="BG")            else fg_image_params


def  backupScaledImages():
    shutil.copyfile(fgImgpath, f"{fgImgpath}_bk")
    shutil.copyfile(bgImgpath, f"{bgImgpath}_bk")
    shutil.copyfile(scaledImgpath, f"{scaledImgpath}_bk")
    shutil.copyfile(resultImgPath, f"{resultImgPath}_bk")


def  RestoreScaledImages():  
    if (not os.path.exists(f"{fgImgpath}_bk"))  :
        return False
    shutil.move( f"{fgImgpath}_bk", fgImgpath) 
    shutil.move(f"{bgImgpath}_bk" , bgImgpath )
    shutil.move(f"{scaledImgpath}_bk", scaledImgpath)
    shutil.move(f"{resultImgPath}_bk", resultImgPath)
    return True


def  saveTransparentImage(imgbgr, mask_graybgr , outfpath:str=None):
    if outfpath:
        assert outfpath.endswith(".png") , "saveTransparentImage can only save .png images"
    if(mask_graybgr.shape[0] != imgbgr.shape[0] or mask_graybgr.shape[1] != imgbgr.shape[1] ):
        mask_graybgr= cv2.resize(mask_graybgr, imgbgr.shape[1::-1])
    im_gbra= createTrasnparentImage(imgbgr=imgbgr,  
                                  blurredmaskbgr= mask_graybgr)  
    if outfpath:
        cv2.imwrite(outfpath, im_gbra, params=[cv2.IMWRITE_JPEG_QUALITY, 100])  
    return im_gbra


def  resetBackend():
    switchImgLayer("FORE")
    initializeImageObjects()