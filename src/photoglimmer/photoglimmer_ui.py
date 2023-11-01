
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL 
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.   
#  Description:  
# Entry point for the applicaiton. 
# Handles all UI related activities and some ui stylization, 
# Though the UI is almost entirely defined in a .ui file generated with QT Designer 
import os, sys, shutil, time, tempfile
# QT 
from PySide2 import QtWidgets,  QtCore 
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QPixmap, QIcon, QMovie 
from PySide2.QtCore import QThreadPool, QFile 
from PySide2.QtWidgets import QStyle, QMessageBox, QAction, QGridLayout
# Only if using qdarktheme style 
import  qdarktheme
# This application
# import imagebrighener_backend
# from threadwork import *
import photoglimmer.photoglimmer_backend as photoglimmer_backend
from photoglimmer.threadwork import *
#/**   START Patch FOR cv2+qt plugin **/
# https://forum.qt.io/post/654289
ci_build_and_not_headless = False
try:
    from cv2.version import ci_build, headless
    ci_and_not_headless = ci_build and not headless
except Exception as err:
    print(f"Error loading patch for cv2+qt : {err}")
if sys.platform.startswith("linux") and ci_and_not_headless:
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH")    
if sys.platform.startswith("linux") and ci_and_not_headless:
    os.environ.pop("QT_QPA_FONTDIR")
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
appname = "PhotoGlimmer"
iconpath = "resources/appicon.png"
progbarpath = "resources/spinner.gif"
tempdir = None  
tempImage_original = "tmp_original.jpg"


class  Ui(QtWidgets.QMainWindow):
    tempimage = 'tmp.jpg' 


    def  __init__(self):
        super(Ui, self).__init__()
        self.loader = QUiLoader()
        uifile= QFile(self.getAbsolutePathForFile("./photoglimmer_qt.ui"))        
        self.window= self.loader.load(uifile)         
        self.setCentralWidget(self.window) 
        uifile.close()
        self.setAcceptDrops(True)        
        self.setUpMyUI()
        self.displaySliderValues()
        self.is_state_dirty = False
        self.is_segmentation_needed= True 
        self.createTempDir()
        self.thread_pool = QThreadPool()
        self.getScreenSize()
        self.setWindowTitle(f"{appname}: Illuminate Me! ")
        self.showMaximized()  
        self.disableSliders()
        self.setStatus(f"Open an image to edit.")
        if len(sys.argv) > 1:
            arg_img = sys.argv[-1]
            if (os.path.exists(arg_img) and  self.isImageURL(arg_img )) :
                photoglimmer_backend.originalImgPath = arg_img
                self.setupBrowsedImage()


    def  setUpMyUI(self):
        self.statusBar = self.findChild(QtWidgets.QStatusBar, "statusbar")
        self.buttonBrowse = self.findChild(QtWidgets.QPushButton,
                                           "button2Browse")
        self.buttonBrowse.clicked.connect(self.goBrowse)
        self.buttonReset = self.findChild(QtWidgets.QPushButton,
                                            "buttonReset")
        self.buttonReset.clicked.connect(lambda : 
            self.openNewImage(photoglimmer_backend.originalImgPath)) 
        self.buttonSave = self.findChild(QtWidgets.QPushButton, "button2Save")
        self.buttonSave.clicked.connect(self.goSave)
        self.labelImg = self.findChild(QtWidgets.QLabel, 'label_mainimage')
        self.labelMask = self.findChild(QtWidgets.QLabel, 'label_maskimage')
        self.checkBoxDenoise= self.findChild(QtWidgets.QCheckBox, 'check_blur')
        self.checkBoxPP= self.findChild(QtWidgets.QCheckBox, 'check_pp')
        self.sliderSegMode = self.findChild(QtWidgets.QAbstractSlider,
                                            'sliderModeToggle')
        self.slideThresh = self.findChild(QtWidgets.QAbstractSlider,
                                          'slider_thresh')
        self.slideSaturat = self.findChild(QtWidgets.QAbstractSlider,
                                           'slider_saturation')
        self.slideBelndwt1 = self.findChild(QtWidgets.QAbstractSlider,
                                            'slider_blendwt1')
        self.slideBrightness = self.findChild(QtWidgets.QAbstractSlider,
                                              'slider_bright')
        self.slideBlur = self.findChild(QtWidgets.QAbstractSlider,
                                        'slider_blur')
        self.lcdThresh = self.findChild(QtWidgets.QLCDNumber, 'lcd_thresh')
        self.lcdSaturat = self.findChild(QtWidgets.QLCDNumber, 'lcd_satur')
        self.lcdBrightness = self.findChild(QtWidgets.QLCDNumber, 'lcd_bright')
        self.lcdBlur = self.findChild(QtWidgets.QLCDNumber, 'lcd_blur')
        self.lcdBlendwt1 = self.findChild(QtWidgets.QLCDNumber, 'lcd_blendwt1')
        self.checkBoxPP.setChecked(False)
        self.controlBox = self.findChild(QtWidgets.QFrame, 'frameSliders')
        icon_save = self.style().standardIcon(QStyle.SP_DriveFDIcon)
        self.buttonSave.setIcon(icon_save)
        icon_open = self.style().standardIcon(QStyle.SP_DirIcon)
        icon_reset=  self.style().standardIcon(QStyle.SP_MediaSkipBackward)
        self.buttonBrowse.setIcon(icon_open)
        self.buttonReset.setIcon(icon_reset)
        self.appicon = QIcon(self.getAbsolutePathForFile(iconpath))
        self.setWindowIcon(self.appicon)
        self.labelImg.installEventFilter(self)
        self.sliderSegMode.sliderReleased.connect(self.handleSliderEvent)
        self.slideSaturat.sliderReleased.connect(self.handleSliderEvent)
        self.slideBelndwt1.sliderReleased.connect(self.handleSliderEvent)
        self.slideBlur.sliderReleased.connect(self.handleSliderEvent)
        self.slideBrightness.sliderReleased.connect(self.handleSliderEvent)
        self.slideThresh.sliderReleased.connect(self.handleSliderEvent)
        self.checkBoxPP.stateChanged.connect(self.processImage)
        self.checkBoxDenoise.stateChanged.connect(self.processImage)
        self.sliderSegMode.valueChanged.connect(self.raiseSegmentationFlag)
        self.slideThresh.valueChanged.connect(self.raiseSegmentationFlag)
        self.slideBlur.valueChanged.connect(self.raiseSegmentationFlag)
        self.saveUiDefaults()
        self.setUpMenubar()


    def  setAppStyleSheets(self):
        self.sliderSegMode.setStyleSheet('''
                                         QSlider::handle:horizontal {
                                             color:white; background: white;
                                             border: 2px solid #5c5c5c;
                                             border-radius: 10px;}                                         
                                         ''')
        self.buttonBrowse.setStyleSheet("border-color:white ")
        self.buttonSave.setStyleSheet("border-color:gray; color:gray")


    def  setUpMenubar(self):
        self.menuOpen = self.findChild(QAction, "action_open")
        self.menuSave = self.findChild(QAction, "action_save")
        self.menuQuit = self.findChild(QAction, "action_quit")
        self.menuAbout = self.findChild(QAction, "action_about")
        self.menuParFolder = self.findChild(QAction, "action_ParentFolder")                 
        self.menuOpen.triggered.connect(self.goBrowse)
        self.menuSave.triggered.connect(self.goSave)
        self.menuQuit.triggered.connect(self.close) 
        self.menuParFolder.triggered.connect(self.openSystemExplorer)
        self.menuAbout.triggered.connect(self.openHelpURL) 


    def  dragEnterEvent(self, event):          
        isImage= self.isImageURL(event.mimeData().urls()[0].toLocalFile())
        if(isImage):
            event.acceptProposedAction()      
        else:
            event.ignore()      


    def  dropEvent(self, event):       
       isImage= self.isImageURL(event.mimeData().urls()[0].toLocalFile())
       if(isImage):           
           fname= event.mimeData().urls()[0].toLocalFile()
           self.openNewImage(fname)
       else:
           event.ignore()     


    def  isImageURL(self,  url:str ):
        from  mimetypes import MimeTypes        
        t,enc= MimeTypes().guess_type(url, strict=True) 
        if t is None:
            return False
        if t.startswith("image/"):            
            return True
        return False


    def  setStatus(self, msg):
        self.statusBar.showMessage(msg)


    def  showMessage(self, title=f"{appname}! ", text="Message About" ,
                    message="Some message shown"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(text)
        msg.setInformativeText(message)
        msg.setWindowTitle(title)    
        msg.exec_()


    def  showConfirmationBox(self, titl="Confirm", questn="really?"):
        reply = QMessageBox.question(self, 
                                     titl, 
                                     questn,
                                      QMessageBox.Yes | QMessageBox.No, 
                                      QMessageBox.No)        
        result= False
        result= True if reply == QMessageBox.Yes else False                
        return result    


    def  saveUiDefaults(self):
        slds= self.findChildren(QtWidgets.QSlider)
        self.slider_defaults=[]
        for s in slds:            
            self.slider_defaults.append(s.value())


    def  resetUiToDefaults(self):
        sliders= self.findChildren(QtWidgets.QSlider)        
        for x in list(zip(sliders, self.slider_defaults)):
            x[0].setValue(x[1])            
        self.displaySliderValues()
        self.checkBoxPP.checked=False
        self.checkBoxDenoise.checked=True


    def  eventFilter(self, obj, event):
        if event.type(
        ) == QtCore.QEvent.MouseButtonPress and self.is_state_dirty and self.isUIEnabled:
            self.showImage(photoglimmer_backend.scaledImgpath)
            return True
        elif event.type(
        ) == QtCore.QEvent.MouseButtonRelease and self.is_state_dirty and self.isUIEnabled:
            self.showImage(self.tempimage)
            return True
        return False


    def  raiseSegmentationFlag(self, value):
        self.is_segmentation_needed= True  


    def  disableSliders(self):
        self.isUIEnabled=False 
        self.controlBox.setEnabled(False)
        self.sliderSegMode.setEnabled(False)
        self.buttonSave.setEnabled(False)
        self.buttonReset.setEnabled(False)
        self.menuSave.setEnabled(False)
        self.buttonSave.setStyleSheet("border-color:gray; color:gray") 


    def  enableSliders(self):
        self.isUIEnabled=True 
        self.controlBox.setEnabled(True)
        self.sliderSegMode.setEnabled(True)
        self.buttonSave.setEnabled(True)
        self.buttonReset.setEnabled(True)
        self.menuSave.setEnabled(True)
        self.buttonSave.setStyleSheet("border-color:white; color:white") 


    def  displaySliderValues(self):
        self.lcdThresh.display(self.slideThresh.value())
        self.lcdBlendwt1.display(self.slideBelndwt1.value())
        self.lcdBlur.display(self.slideBlur.value())
        self.lcdBrightness.display(self.slideBrightness.value())
        self.lcdSaturat.display(self.slideSaturat.value())


    def  handleSliderEvent(self):
        self.displaySliderValues()
        self.processImage()


    def  setImageAdjustMode(self):
        photoglimmer_backend.imageAdjustMode = "HSV"


    def  showImage(self, fname):
        self.pixmap = QPixmap(fname)
        myScaledPixmap = self.pixmap
        self.labelImg.setPixmap(myScaledPixmap)
        self.setStatus("Press 'Save' when you have finished editing your image")
        if (fname is not self.tempimage):
            self.labelImg.setProperty("toolTip",
                                      photoglimmer_backend.originalImgPath)


    def  showMask(self, fname):
        self.pixmap = QPixmap(fname)
        self.myScaledMask = self.pixmap.scaledToHeight(
            self.labelMask.height() - 20,  
            QtCore.Qt.SmoothTransformation)  
        self.labelMask.setPixmap(self.myScaledMask)


    def  startBusySpinner(self):
        self.progressmovie = QMovie(self.getAbsolutePathForFile(progbarpath))
        self.labelImg.setMovie(self.progressmovie) 
        self.progressmovie.start()


    def  stopBusySpinner(self):
        if (self.progressmovie is not None):
            self.progressmovie.stop()


    def  goBrowse(self):
        from os.path import expanduser
        homedir = expanduser("~")
        if (photoglimmer_backend.originalImgPath and 
            photoglimmer_backend.originalImgPath.strip() and  
            os.path.exists(photoglimmer_backend.originalImgPath)):
                homedir= os. path. dirname(photoglimmer_backend.originalImgPath)
        fname = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption=f"{appname}: open image file",
            dir= homedir, 
            filter=("Image Files (*.png *.jpg *.bmp *.webp *.JPG *.jpeg *.JPEG )"))
        if (fname[0] == ''):
            return
        if not self.isImageURL(  fname[0] ):
            self.showMessage(title="Error!", text="Invalid file",message=f"Not an image?: {fname[0]}  ")
            return
        try: 
            self.openNewImage(fname[0])
        except Exception as e: 
            self.showMessage("Error", "Not an image?", type(e).__name__)    


    def  openNewImage(self, imgpath):
        photoglimmer_backend.originalImgPath = imgpath
        self.resetUiToDefaults()
        self.setupBrowsedImage()


    def  setupBrowsedImage(self):
        self.emptyTempDir()
        self.createWorkingImage()
        self.is_state_dirty = False
        self.is_segmentation_needed=True
        self.labelMask.clear()
        self.showImage(photoglimmer_backend.scaledImgpath)
        self.enableSliders()
        self.setStatus(f"Edit using sliders. Press Save when done.")


    def  goSave(self):
        if (not self.is_state_dirty):
            self.showMessage(message="Nothing Edited Yet!",
                             text="Unedited",
                             title="Nothing To Save!")
            return
        self.disableSliders()
        self.setStatus("Saving image..this takes longer than normal edit")
        self.startBusySpinner()        
        worker = Worker(self._goSave_bgstuff)
        worker.signals.finished.connect(self._showSaveDialog)
        self.thread_pool.start(worker)


    def  _goSave_bgstuff(self, progress_callback=None):
        result_image = photoglimmer_backend.processImageFinal(
            isOriginalImage=True, isSegmentationNeeded= False)
        self.tempimage = self.createTempFile(fname=tempImage_original,
                                             img=result_image)
        return


    def  _showSaveDialog(self):
        fname=None        
        newfile= self.appendToFilePath( photoglimmer_backend.originalImgPath)       
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption=f"{appname}: Save File",
            dir=newfile,  
            filter=("Image Files (*.jpg)")) 
        if fileName:
            ext= "jpg"                        
            fname = f"{fileName}"
            if not fname.endswith(ext) :             
                fname = f"{fileName}.{ext}"
                if(os.path.exists(fname)): 
                    fname=f"{fileName}_{appname}_{time.time()}.{ext}"                
            with open(fname, 'w') as f:
                try:
                    shutil.copy(self.tempimage, fname)                    
                except Exception as e:
                    print(f"An error occurred: {e}")
                    self.showMessage(  title= "Error!", 
                                     text="Error saving file", 
                                     message=e)
        else:
            pass   
        self.stopBusySpinner()
        if(fname is not None):
            self.showMessage( text="File Saved",  message=f"Saved {fname}" )
        self.enableSliders()
        self.processImage()  
        return


    def  closeEvent(self, event):
        res= self.showConfirmationBox(titl="Quit?", 
                                      questn="Are you sure you want to quit?")
        if not res:
            event.ignore()
        else:
            event.accept() 


    def  appendToFilePath(self,fpath):
        name, ext = os.path.splitext(fpath)
        file_name = f"{name}_{appname}{ext}"
        return file_name
    basedir=os.path.dirname(__file__)


    def  getAbsolutePathForFile(self, fname:str):        
        f= os.path.abspath(__file__)
        d= os.path.dirname(f)      
        abspth=os.path.join(self.basedir, fname)
        return abspth


    def  openSystemExplorer(self):
        if photoglimmer_backend.originalImgPath :
            dirpath = os.path.abspath(os.path.dirname(
                photoglimmer_backend.originalImgPath))
            self.openBrowser(dirpath)


    def  openHelpURL(self):
        helpurl= "https://github.com/codecliff/PhotoGlimmer"
        self.openBrowser(helpurl)        


    def  openBrowser(self, dirpath):
        import subprocess, platform
        osname= platform.system()
        if (osname in ['Windows', 'windows', 'win32']):
                os.startfile(dirpath)
                return
        opener = "open" if osname in ["darwin", "Darwin"] else "xdg-open"
        subprocess.call([opener, dirpath])


    def  getScreenSize( self ):
        from PySide2.QtWidgets import QApplication, QDesktopWidget        
        desktop = QDesktopWidget()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()        
        print(f"Screen Width: {screen_width}")
        print(f"Screen Height: {screen_height}")


    def  createWorkingImage(self):
        h = min(self.labelImg.height(),1200)
        w = min(self.labelImg.width(),1200)
        img_bgr = photoglimmer_backend.cv2.imread(
            photoglimmer_backend.originalImgPath)
        if img_bgr is None:
            raise TypeError("Not an Image! ")
        scaledimg_bgr = img_bgr
        if (img_bgr.shape[0] > w or img_bgr.shape[1] > h):
            scaledimg_bgr = photoglimmer_backend.resizeImageToFit(img_bgr, w, h)
        photoglimmer_backend.scaledImgpath = os.path.join(
            photoglimmer_backend.tempdirpath, "working_image.jpg")
        photoglimmer_backend.cv2.imwrite(
            photoglimmer_backend.scaledImgpath, scaledimg_bgr)


    def  createTempDir(self):
        global tempdir
        tempd = tempfile.TemporaryDirectory(prefix=f"{appname}_")
        tempdir = tempd
        photoglimmer_backend.tempdirpath = tempd.name


    def  createTempFile(self, fname, img):
        f = os.path.join(tempdir.name, fname)
        photoglimmer_backend.cv2.imwrite(img=img, filename=f)        
        return f


    def  emptyTempDir(self):
        try:
            for fl in os.listdir(tempdir.name):
                os.remove(f"{tempdir.name}/{fl}")
        except Exception as err:
            print(err)    


    def  setBackendVariables(self):
        photoglimmer_backend.seg_threshold = float(
            self.slideThresh.value()) / 100
        photoglimmer_backend.blendweight_img1 = float(
            self.slideBelndwt1.value()) / 100
        photoglimmer_backend.brightness = int(self.slideBrightness.value())
        photoglimmer_backend.saturation = int(self.slideSaturat.value())
        photoglimmer_backend.blur_edge = int(self.slideBlur.value())
        photoglimmer_backend.seg_mode = ('BG', 'FORE')[int(
            self.sliderSegMode.value())]
        photoglimmer_backend.denoise_it= bool(self.checkBoxDenoise.isChecked())
        photoglimmer_backend.postprocess_it= bool(self.checkBoxPP.isChecked())
        self.setImageAdjustMode()


    def  processImage(self):
        self.setBackendVariables()
        self.disableSliders()
        self.startBusySpinner()
        if (photoglimmer_backend.scaledImgpath == None
                or not os.path.exists(photoglimmer_backend.scaledImgpath)):
            self.showMessage("Error!","Empty", "You haven't Opened any Image! ")
            return
        self.startBusySpinner()
        worker2 = Worker(self._processImage_bgstuff)
        worker2.signals.finished.connect(self._endImageProcessing)
        self.thread_pool.start(worker2)


    def  _processImage_bgstuff(self, progress_callback=None):
        result_image = photoglimmer_backend.processImageFinal(
            isOriginalImage=False,
            isSegmentationNeeded=self.is_segmentation_needed)
        self.tempimage = self.createTempFile(fname="temp.jpg",
                                             img=result_image)


    def  _endImageProcessing(self):
        time.sleep(1)
        self.stopBusySpinner()
        self.showImage(self.tempimage)
        self.showMask(
            os.path.join(photoglimmer_backend.tempdirpath,
                         photoglimmer_backend.fname_maskImgBlurred))
        self.enableSliders()
        self.is_state_dirty = True
        self.is_segmentation_needed=False 


def  main():
    global app,tempdir
    app = QtWidgets.QApplication(sys.argv)    
    qdarktheme.setup_theme("dark")        
    qdarktheme.setup_theme(custom_colors={"primary":"#ABCDEF" , 
                                              "foreground>slider.disabledBackground":"#535c66"}) 
    window = Ui()    
    window.setAppStyleSheets() 
    app.exec_()
    tempdir.cleanup()
    sys.exit(0)
if __name__ == '__main__':
    main()