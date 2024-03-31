
import piexif, piexif.helper
# piexif has no dependencies 


def  transferAlteredExif(sourceimgpath:str , outputimgpath:str  ):
    try:
    #read exif 
        exif_dict = piexif.load(sourceimgpath) 
        #if original image has no exif, do nothing 
        if len(exif_dict['0th'])==0 :
            return    
        new_comment= u"PhotoGlimmer"
        if exif_dict['Exif'].get(37510) is not None:
            old_comment= str(exif_dict['Exif'][37510] , "utf-8")
            print(f"old comment was {old_comment} ") 
            new_comment= u"PhotoGlimmer, " + old_comment.strip()                        
        else:
            print("no userComment entry")
        print(f"new_comment will be {new_comment}")                
        newcomment= piexif.helper.UserComment.dump(new_comment)    
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = newcomment
        exif_bytes = piexif.dump(exif_dict)    
        piexif.insert(exif_bytes, outputimgpath)
    except Exception as e:
        print(f"transferAlteredExif: {e}")    