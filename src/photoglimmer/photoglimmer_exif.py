
# ###############################################################################
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.
# Description :
# Alter image EXIF data to add app name to comment 
# ###############################################################################
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
            new_comment= u"PhotoGlimmer, " + old_comment.strip()                        
        else:
            print("no userComment entry")
        newcomment= piexif.helper.UserComment.dump(new_comment)    
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = newcomment
        exif_bytes = piexif.dump(exif_dict)    
        piexif.insert(exif_bytes, outputimgpath)
    except Exception as e:
        print(f"transferAlteredExif: {e}")    