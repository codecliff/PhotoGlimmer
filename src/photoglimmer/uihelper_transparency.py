
# import backend
import os
import photoglimmer_backend as backend
# all backend variable set by frontend have to be provided as funciton parameters 


class  UIHelper:


    def  __init__(self, uiobject):
          self.ui=uiobject


    def  convert_and_copy_to_clipboard(self, bgra_image):
            from PySide2.QtGui import QImage, QPixmap,QClipboard
            from PySide2.QtWidgets import QApplication
            rgba_image = backend.cv2.cvtColor(bgra_image, backend.cv2.COLOR_BGRA2RGBA)
            height, width, channels = rgba_image.shape
            bytes_per_line = channels * width 
            qimage = QImage(rgba_image.data, width, height, bytes_per_line, 
                            QImage.Format_RGBA8888)
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(QPixmap(qimage), QClipboard.Clipboard) 
            return 


    def  transparency_to_clipboard( self, tempdirpath,originalImgPath):
            mskpath=os.path.join(tempdirpath,
                                        backend.fname_maskImgBlurred)
            if not os.path.exists( mskpath ):
                self.ui.showMessage(  title="No Mask", message= "Edit image a bit and try again" , 
                                text="Edit something first")
                return
            img= backend.cv2.imread(originalImgPath)
            msk= backend.cv2.imread(mskpath)    
            img_bgra= backend.saveTransparentImage(
                imgbgr= img,
                mask_graybgr=msk,
                outfpath=None 
            )
            self.convert_and_copy_to_clipboard( img_bgra)