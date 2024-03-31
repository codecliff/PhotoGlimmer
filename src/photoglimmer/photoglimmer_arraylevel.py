
import numpy as np
import cv2


def  showArryProperties(xlist, caption= "showArryProperties"):
    print("_"*30)
    for x in xlist:
        print(f"{caption}: {x.shape}, {x.dtype} ")
    print("_"*30)


def  bgr2h_s_v_32(imgbgr):
    imghsv = cv2.cvtColor(imgbgr, cv2.COLOR_BGR2HSV).astype("float32") 
    h, s, v = cv2.split(imghsv)
    return h,s,v


def  hsv2bgr(h,s,v):
    imghsv = cv2.merge([h.astype(v.dtype), s, v])   
    img_bgr = cv2.cvtColor(imghsv.astype("uint8"), 
                           cv2.COLOR_HSV2BGR)    
    return img_bgr


def  stitchFGBGOneLayer( arr_fg, arr_bg,  blurred_mask_graybgr_v ):
    msk_norm= (blurred_mask_graybgr_v.astype("float32"))/255
    v_res= msk_norm*arr_fg + (1.0-msk_norm)*arr_bg 
    v_res=np.clip(v_res, 0, 255)
    return v_res 


def  stackStitchedLayers(h,s_res,v_res):
    im_res_bgr= cv2.cvtColor(cv2.merge( [h.astype(v_res.dtype),s_res,v_res]).astype("uint8"), 
                           cv2.COLOR_HSV2BGR)  
    return im_res_bgr


def  blendMaskedValues2D( arr_fg, arr_bg,  msk_norm2D_f32 ):
    invmask= 1.0-msk_norm2D_f32
    sum32= msk_norm2D_f32*(arr_fg.astype("float32")) +        invmask*(arr_bg.astype("float32")) 
    sum8=(sum32.clip(0,255)).astype("uint8")
    return sum8


def  stackNMask_HSV_u8( img_bgr, fg_image_bgr , 
                   bg_image_bgr , blurred_mask_gray_bgr ):    
    imghsv_fg = cv2.cvtColor(fg_image_bgr, cv2.COLOR_BGR2HSV)
    imghsv_bg = cv2.cvtColor(bg_image_bgr, cv2.COLOR_BGR2HSV)
    imghsv_res= cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask_reshaped2D= cv2.resize(blurred_mask_gray_bgr, fg_image_bgr.shape[1::-1])[:,:,-1]
    msk_norm2D= mask_reshaped2D.astype(np.float32)/255  
    imghsv_res[:,:,1]= blendMaskedValues2D( imghsv_fg[:,:,1], imghsv_bg[:,:,1],  
                                           msk_norm2D )
    imghsv_res[:,:,2]= blendMaskedValues2D( imghsv_fg[:,:,2], imghsv_bg[:,:,2], 
                                           msk_norm2D )    
    im_res= cv2.cvtColor(imghsv_res,  cv2.COLOR_HSV2BGR)  
    return im_res