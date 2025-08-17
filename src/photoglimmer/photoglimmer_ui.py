
# ###############################################################################
# Copyright : Rahul Singh
# URL       : https://github.com/codecliff/PhotoGlimmer
# License   : LGPL
# email     : codecliff@users.noreply.github.com
# Disclaimer: No warranties, stated or implied.
#  Description:
# Entry point for the applicaiton.
# Handles all UI related activities and some ui stylization, even though
# the UI is almost entirely defined in a .ui file created using QT Designer
# ###############################################################################
import traceback 
#imports
import os, sys, shutil, time, tempfile
# QT
from PySide6 import QtWidgets,  QtCore
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QPixmap, QIcon, QMovie, QKeySequence, QAction
from PySide6.QtCore import QThreadPool, QFile,QSettings,QStandardPaths
from PySide6.QtWidgets import QStyle, QMessageBox, QGridLayout,QLabel, QDialog
# Only if using qdarktheme style
import  qdarktheme
# This application
import photoglimmer.photoglimmer_backend as photoglimmer_backend
from photoglimmer.threadwork import *
import photoglimmer.customfiledialog as customfiledialog
import photoglimmer.uihelper_transparency 
import cv2
#2025
from photoglimmer.imagewidget import ImageLabel
from photoglimmer.colorcurverwidget import SmoothCurveWidget
# --- Import the configuration and Preferences Dialog ---
from photoglimmer.prefs.settings_config import SettingsConfig
from photoglimmer.prefs.preferences_dialog import PreferencesDialog
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
progbarpath = "resources/spinner3_8.gif"
tempdir = None
tempImage_original = "tmp_original.jpg"
preferSystemFileDlg= False 


class  CustomUiLoader(QUiLoader):


    def  createWidget(self, className, parent=None, name=""):        
        if className == "ImageLabel":
            widget = ImageLabel(parent)
            widget.setObjectName(name)
            return widget
        elif className == "SmoothCurveWidget":
            widget = SmoothCurveWidget(parent)
            widget.setObjectName(name)
            return widget
        return super(CustomUiLoader, self).createWidget(className, parent, name)


class  Ui(QtWidgets.QMainWindow):
    tempimage = photoglimmer_backend.fname_resultimg


    def  __init__(self):
        super(Ui, self).__init__()
        self.loader = CustomUiLoader()   
        uifile= QFile(self.getAbsolutePathForFile("./photoglimmer_qt.ui"))
        self.ui= self.loader.load(uifile)
        self.setCentralWidget(self.ui) 
        uifile.close()
        self.setAcceptDrops(True)
        self.settings = QSettings(SettingsConfig.ORGANIZATION_NAME,
                                  SettingsConfig.APPLICATION_NAME)
        self.load_application_settings()
        self.setUpMyUI()
        self.displaySliderValues()
        self.is_state_dirty = False
        self.is_segmentation_needed= True
        self.is_tweaking_needed= True
        self.createTempDir()
        photoglimmer_backend.initializeImageObjects() 
        self.thread_pool = QThreadPool()
        self.setWindowTitle(f"{appname}: Illuminate Me! ")
        self.showMaximized()
        self.disableSliders()
        self.setStatus(f"Open an image to edit.")
        if len(sys.argv) > 1:
            arg_img = sys.argv[-1]
            if (os.path.exists(arg_img) and  self.isImageURL(arg_img )) :
                photoglimmer_backend.originalImgPath = arg_img
                self.setupBrowsedImage()


    def  setupStackedWidget(self):
        if self._brightness_mode and self._brightness_mode ==              SettingsConfig.BrightnessMode.COLOR_CURVE :
            self.stckTweak.setCurrentIndex(1)
        else:
            self.stckTweak.setCurrentIndex(0)


    def  updateDenoiseCheckbox(self):
        if  self.checkBoxDenoise and self._denoise_on_load is not None:
            self.checkBoxDenoise.setChecked( self._denoise_on_load )        


    def  setUpMyUI(self):
        self.statusBar = self.findChild(QtWidgets.QStatusBar, "statusbar")
        self.buttonBrowse = self.findChild(QtWidgets.QPushButton,
                                           "button2Browse")
        self.buttonBrowse.clicked.connect(self.goBrowse)
        self.buttonReset = self.findChild(QtWidgets.QPushButton,
                                            "buttonReset")
        self.buttonReset.clicked.connect(self.goReset)
        self.buttonSave = self.findChild(QtWidgets.QPushButton, 
                                         "button2Save")
        self.buttonSave.clicked.connect(self.goSave)
        self.labelImg = self.ui.findChild(QtWidgets.QLabel, 'imageLabel') 
        self.labelImg.setStyleSheet("QLabel { color: rgb(119, 118, 123); }");
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
        self.slideBlurEdge = self.findChild(QtWidgets.QAbstractSlider,
                                        'slider_bluredge')
        self.slideBgBlur = self.findChild(QtWidgets.QAbstractSlider,
                                        'slider_bgblur')
        self.slideBgBlur.setEnabled(True) 
        self.labelImg.rectangles_changed.connect(self.handle_rect_changes) 
        self.lcdThresh = self.findChild(QtWidgets.QLCDNumber, 'lcd_thresh')
        self.lcdSaturat = self.findChild(QtWidgets.QLCDNumber, 'lcd_satur')
        self.lcdBrightness = self.findChild(QtWidgets.QLCDNumber, 'lcd_bright')
        self.lcdBlur = self.findChild(QtWidgets.QLCDNumber, 'lcd_blur')
        self.lcdBlendwt1 = self.findChild(QtWidgets.QLCDNumber, 'lcd_blendwt1')
        self.lcdBgBlur = self.findChild(QtWidgets.QLCDNumber, 'lcd_bgblur')
        self.stckTweak= self.findChild(QtWidgets.QStackedWidget, 'stackedWidgetTweak')
        self.setupStackedWidget()
        self.checkBoxPP.setChecked(False)
        self.controlBox = self.findChild(QtWidgets.QFrame, 'frameSliders')
        if self._denoise_on_load:
            self.checkBoxDenoise.setChecked(self._denoise_on_load)
        icon_save = self.style().standardIcon(QStyle.SP_DriveFDIcon)
        self.buttonSave.setIcon(icon_save)
        icon_open = self.style().standardIcon(QStyle.SP_DirIcon)
        icon_reset=  self.style().standardIcon(QStyle.SP_MediaSkipBackward)
        self.buttonBrowse.setIcon(icon_open)
        self.buttonReset.setIcon(icon_reset)
        self.appicon = QIcon(self.getAbsolutePathForFile(iconpath))
        self.setWindowIcon(self.appicon)
        self.labelImg.installEventFilter(self)
        self.sliderSegMode.sliderReleased.connect(self.handleSegModeSliderRelease)
        self.slideSaturat.sliderReleased.connect(self.handleTweakSlidersRelease)
        self.slideBrightness.sliderReleased.connect(self.handleTweakSlidersRelease)
        self.slideBgBlur.sliderReleased.connect(self.handleTweakSlidersRelease)
        self.slideThresh.sliderReleased.connect(self.handleSegmentationSlidersRelease)
        self.slideBlurEdge.sliderReleased.connect(self.handleSegmentationSlidersRelease)
        self.slideBelndwt1.sliderReleased.connect(self.handleSliderRelesedEvent)
        for slider in self.findChildren(QtWidgets.QSlider):
            slider.valueChanged.connect(self.updateLCDValues)
        self.checkBoxPP.stateChanged.connect(self.handleCheckBoxeEvents)
        self.checkBoxDenoise.stateChanged.connect(self.handleCheckBoxeEvents)
        self.fameColorCurve = self.ui.findChild(QtWidgets.QFrame, 'frameScurve')
        self.widgColorCurve = self.ui.findChild(QtWidgets.QWidget, 'widget_colcurve') 
        self.buttonScurveReset= self.ui.findChild(QtWidgets.QPushButton, 'buttonScurveReset') 
        self.widgColorCurve.curveChanged.connect(self.handle_lut_update)
        self.buttonScurveReset.clicked.connect(self.handle_curve_reset_button)
        self.statusBar.setStyleSheet("QStatusBar { color: #808080; }") 
        self.saveUiDefaults()
        self.setUpMenubar()


    def  getImagesDirectory(self):
        from  PySide6.QtCore import QStandardPaths
        pth=QStandardPaths.PicturesLocation
        sysimgfolder= str(QStandardPaths.writableLocation(pth) )
        if os.path.exists(sysimgfolder):
            return sysimgfolder
        return None


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
        self.menuHelp = self.findChild(QAction, "action_help")
        self.menuGuide = self.findChild(QAction, "action_guide")
        self.menuParFolder = self.findChild(QAction, "action_ParentFolder")
        self.menuTranspExp= self.findChild(QAction, "actionExportTransparency")
        self.menuPrefs= self.findChild(QAction, "actionPreferences")
        self.menuOpen.triggered.connect(self.goBrowse)
        self.menuOpen.setShortcut(QKeySequence("Ctrl+O"))
        self.menuSave.triggered.connect(self.goSave)
        self.menuSave.setShortcut(QKeySequence("Ctrl+S"))
        self.menuQuit.triggered.connect(self.close) 
        self.menuQuit.setShortcut(QKeySequence("Ctrl+Q"))
        self.menuParFolder.triggered.connect(self.openSystemExplorer)
        self.menuAbout.triggered.connect(self.openHelpURL)  
        self.menuHelp.triggered.connect(self.openHelpURL)
        self.menuGuide.triggered.connect(self.openHelpURL)
        self.menuTranspExp.triggered.connect(self.exportTransparency)
        self.menuPrefs.triggered.connect(self.show_preferences_dialog)


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


    def  showMessage(self, title="", text="Message About" ,
                    message="Some message shown"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(text)
        msg.setInformativeText(message)
        title=f"{appname}: {title} "
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
        chks= self.findChildren(QtWidgets.QCheckBox)
        self.slider_defaults=[]
        self.checkbx_defaults=[]
        for s in slds:
            self.slider_defaults.append(s.value())
        for c in chks:
            self.checkbx_defaults.append(c.checkState())    


    def  resetUiToDefaults(self):
        try:
            sliders= self.findChildren(QtWidgets.QSlider)
            checkbxs= self.findChildren(QtWidgets.QCheckBox)
            for x in list(zip(sliders, self.slider_defaults)):
                x[0].setValue(x[1])
            for c in list(zip(checkbxs, self.checkbx_defaults)):
                c[0].setCheckState(c[1])
        except Exception as e:
            print(f"Error in resetUiToDefaults: {e}")


    def  saveSliderValues(self):
        slds= self.findChildren(QtWidgets.QSlider)
        sldvals=[]
        for s in slds:
            sldvals.append(s.value())
        return sldvals


    def  setSliderValues(self, sldvals):
        sliders= self.findChildren(QtWidgets.QSlider)
        for x in list(zip(sliders, sldvals)):
            if (x[0] is not self.sliderSegMode):
                x[0].setValue(x[1])
        self.displaySliderValues()


    def  eventFilter(self, obj, event):
        if event.type( 
        ) == QtCore.QEvent.MouseButtonPress and self.is_state_dirty and self.isUIEnabled            and  event.button() == QtCore.Qt.RightButton :
            self.showImage(photoglimmer_backend.scaledImgpath)
            return True
        elif event.type(
        ) == QtCore.QEvent.MouseButtonRelease and self.is_state_dirty and self.isUIEnabled            and  event.button() == QtCore.Qt.RightButton :
            self.showImage(self.tempimage)
            return True
        return False


    def  raiseSegmentationFlag(self, value:bool):
        self.is_segmentation_needed= value


    def  raiseTweakFlag(self, value:bool):
        self.is_tweaking_needed= value


    def  disableSliders(self):
        self.isUIEnabled=False 
        self.controlBox.setEnabled(False)
        self.sliderSegMode.setEnabled(False)
        self.buttonSave.setEnabled(False)
        self.buttonReset.setEnabled(False)
        self.menuSave.setEnabled(False)
        self.buttonSave.setStyleSheet("border-color:gray; color:gray")
        self.fameColorCurve.setEnabled(False)


    def  enableSliders(self):
        self.isUIEnabled=True
        self.controlBox.setEnabled(True)
        self.sliderSegMode.setEnabled(True)
        self.buttonSave.setEnabled(True)
        self.buttonReset.setEnabled(True)
        self.menuSave.setEnabled(True)
        self.buttonSave.setStyleSheet("border-color:white; color:white")
        self.fameColorCurve.setEnabled(True)


    def  updateLCDValues(self,val):
        sld = self.sender()
        if sld is self.slideBrightness :
            self.lcdBrightness.display(val)
        elif sld is self.slideSaturat :
            self.lcdSaturat.display(val)
        elif sld is self.slideThresh :
            self.lcdThresh.display(val)
        elif sld is self.slideBelndwt1 :
            self.lcdBlendwt1.display(val)
        elif sld is self.slideBlurEdge :
            self.lcdBlur.display(val)
        elif sld is self.slideBgBlur :
            self.lcdBgBlur.display(val)    


    def  displaySliderValues(self):
        self.lcdThresh.display(self.slideThresh.value())
        self.lcdBlendwt1.display(self.slideBelndwt1.value())
        self.lcdBlur.display(self.slideBlurEdge.value())
        self.lcdBrightness.display(self.slideBrightness.value())
        self.lcdSaturat.display(self.slideSaturat.value())
        self.lcdBgBlur.display(self.slideBgBlur.value())


    def  handleSegModeSliderRelease(self) :
        new_seg_mode = ('BG', 'FORE')[int(
            self.sliderSegMode.value())]
        photoglimmer_backend.switchImgLayer(new_seg_mode)
        self.restoreUIValuesToLayer( photoglimmer_backend.currImg)
        self.widgColorCurve.toggle_curve_state()


    def  handleSegmentationSlidersRelease(self):
        self.raiseSegmentationFlag(True)
        self.handleSliderRelesedEvent()


    def  handleTweakSlidersRelease(self):
        self.raiseTweakFlag(True)
        self.handleSliderRelesedEvent()


    def  handleCheckBoxeEvents(self):
        self.setBackendVariables()  
        if (photoglimmer_backend.scaledImgpath ): 
            self.processImage()


    def  handleSliderRelesedEvent(self):
        self.setBackendVariables()
        self.processImage()


    def  setImageAdjustMode(self):
        photoglimmer_backend.imageAdjustMode = "HSV"


    def  showImage(self, fname , fresh_image=False):
        if (fresh_image):
           self.labelImg.set_image(fname)
        else :            
            self.labelImg.change_image(fname)
        self.setStatus("Press 'Save' when done | Original: Right-click |  Rectangles : (H) Show/Hide , (DEL) Delete  ")
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
        self.spinnerLabel=QLabel(self.labelImg)
        self.spinnerLabel.setMovie(self.progressmovie)
        self.spinnerLabel.setFixedSize(200,  200)
        mid= ( (self.labelImg.width()-self.spinnerLabel.width())//2,
            (self.labelImg.height()-self.spinnerLabel.height())//2 )
        self.spinnerLabel.move(mid[0], mid[1])
        self.labelImg.setEnabled(False)
        self.progressmovie.start()
        self.spinnerLabel.show()


    def  stopBusySpinner(self):
        if (self.progressmovie is not None):
            self.progressmovie.stop()
        if (self.spinnerLabel is not None):
            self.spinnerLabel.hide()
        self.labelImg.setEnabled(True)


    def  goBrowse(self):
        from os.path import expanduser
        homedir = self._start_folder_path  or self.getImagesDirectory() or expanduser("~")
        if (photoglimmer_backend.originalImgPath and
            photoglimmer_backend.originalImgPath.strip() and
            os.path.exists(photoglimmer_backend.originalImgPath)):
            homedir= os. path. dirname(photoglimmer_backend.originalImgPath)
        fname=[""]
        if self.systemFileDialogPreferred() :
            fname = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption=f"{appname}: open image file",
            dir= homedir,
            filter=("Image Files (*.png *.jpg *.bmp *.webp *.JPG *.jpeg *.JPEG )"))
        else:
            fname = customfiledialog.QFileDialogPreview.getOpenFileName(parent=self,dir= homedir )
        if not fname[0]: 
            return
        if not self.isImageURL(  fname[0] ):
            self.showMessage(title="Error!", text="Invalid file",message=f"Not an image?: {fname[0]}  ")
            return
        try:
            self.openNewImage(fname[0])
        except Exception as e:
            traceback.print_exc() 
            self.showMessage("Error", "Not an image?", type(e).__name__)


    def  openNewImage(self, imgpath):
        photoglimmer_backend.initializeImageObjects()
        photoglimmer_backend.originalImgPath = imgpath
        self.setupBrowsedImage() 
        self.resetUiToDefaults() 
        self.widgColorCurve.reset_curve(new_image=True)        
        self.setBackendVariables() 
        self.setLastOpenedLocationPref(imgpath) 


    def  setupBrowsedImage(self):
        self.emptyTempDir()
        self.createWorkingImage()
        self.is_state_dirty = False
        self.is_segmentation_needed=True
        self.is_tweaking_needed=True
        self.labelMask.clear()        
        self.showImage(photoglimmer_backend.resultImgPath , fresh_image=True)
        self.enableSliders()
        self.setStatus(f"Press Save when done. Mouse draw Rectangles : (H) Hide/Show  (DEL) Delete  ")


    def  goReset(self):
        photoglimmer_backend.resetBackend()
        self.openNewImage(photoglimmer_backend.originalImgPath)
        self.restoreUIValuesToLayer( photoglimmer_backend.currImg)


    def  goSave(self):
        if (not self.is_state_dirty):
            self.showMessage(message="Nothing Edited Yet!",
                             text="Unedited",
                             title="Nothing To Save!")
            return
        self.disableSliders()
        self.setStatus("Saving image..this takes longer than normal edit")
        self.startBusySpinner()
        photoglimmer_backend.backupScaledImages()
        worker = Worker(self._goSave_bgstuff)
        worker.signals.finished.connect(self._showSaveDialog)
        self.thread_pool.start(worker)


    def  _goSave_bgstuff(self, progress_callback=None):
        result_image = photoglimmer_backend.processImageFinal(
            isOriginalImage=True, isSegmentationNeeded= False,
            isTweakingNeeded=True , isLUTneeded= self.curveEditPreferred())
        self.tempimage = self.createTempFile(fname=tempImage_original,
                                             img=result_image, jpegqual=97)
        return


    def  _showSaveDialog(self):
        fname=None
        newfile= self.appendToFilePath( photoglimmer_backend.originalImgPath)
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption=f"{appname}: Save File",
            dir=newfile,  
            filter=("Image Files (*.jpg, *.png)")) 
        if fileName:
            _, ext = os.path.splitext(self.tempimage)
            print( f"going to save {self.tempimage} , extension {ext}")
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
            photoglimmer_backend.transferAlteredExif( photoglimmer_backend.originalImgPath,
                                                            fname )
            self.showMessage( text="File Saved",  message=f"Saved {fname}" )
        self.enableSliders()
        photoglimmer_backend.RestoreScaledImages() 
        self.tempimage=photoglimmer_backend.resultImgPath 
        self.showImage(self.tempimage)                 
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
        if not isinstance(self.sender(), QAction):
            return
        helpurl= "https://github.com/codecliff/PhotoGlimmer"
        actname= self.sender().objectName()
        if actname=="action_guide":
            helpurl="https://codecliff.github.io/photoglimmer/photoglimmer_guide.html"
        elif actname == "action_help" :
            helpurl="https://codecliff.github.io/photoglimmer/photoglimmer_help.html"
        self.openBrowser(helpurl)


    def  openBrowser(self, path_to_open):
        import subprocess, platform
        osname= platform.system()
        if (osname in ['Windows', 'windows', 'win32']):
            os.startfile(path_to_open)
            return
        opener = "open" if osname in ["darwin", "Darwin"] else "xdg-open"
        subprocess.call([opener, path_to_open])


    def  getScreenSize( self ):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QScreen
        desktop = QDesktopWidget()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        print(f"Screen Width: {screen_width}")
        print(f"Screen Height: {screen_height}")


    def  createWorkingImage(self):
        img_bgr = photoglimmer_backend.cv2.imread(
            photoglimmer_backend.originalImgPath)
        if img_bgr is None:
            raise TypeError("Not an Image! ")
        h = 900 
        w = 1200 
        scaledimg_bgr = img_bgr
        if (img_bgr.shape[0] > w or img_bgr.shape[1] > h):
            scaledimg_bgr = photoglimmer_backend.resizeImageToFit(img_bgr, w, h)
        photoglimmer_backend.setupWorkingImages(scaledimg_bgr)


    def  setTempDir(self, tempd):
        global tempdir
        tempdir = tempd


    def  createTempDir(self):
        global tempdir
        tempd = tempfile.TemporaryDirectory(prefix=f"{appname}_")
        tempdir = tempd
        photoglimmer_backend.tempdirpath = tempd.name


    def  createTempFile(self, fname, img,jpegqual=100):
        f = os.path.join(tempdir.name, fname)
        if (img.shape[-1]==4):
            f+=".png"
        photoglimmer_backend.cv2.imwrite(img=img, filename=f, 
                                         params=[cv2.IMWRITE_JPEG_QUALITY, jpegqual] )
        return f


    def  emptyTempDir(self):
        try:
            for fl in os.listdir(tempdir.name):
                os.remove(f"{tempdir.name}/{fl}")
        except Exception as err:
            print(err)


    def  setBackendVariables(self):
        seg_threshold = float(
            self.slideThresh.value()) / 100
        blendweight_img1 = float(
            self.slideBelndwt1.value()) / 100
        brightness = int(self.slideBrightness.value())
        saturation = int(self.slideSaturat.value())
        blur_edge = int(self.slideBlurEdge.value())
        seg_mode = ('BG', 'FORE')[int(
            self.sliderSegMode.value())]
        denoise_it= bool(self.checkBoxDenoise.isChecked())
        postprocess_it= bool(self.checkBoxPP.isChecked())           
        photoglimmer_backend.blurfactor_bg= int( self.slideBgBlur.value() )   
        lut= self.widgColorCurve.get_lut()     
        photoglimmer_backend.setCurrValues(
            seg_threshold,
            blendweight_img1,
            blur_edge ,
            postprocess_it ,
            brightness ,
            saturation ,
            denoise_it,
            lut
            )
        self.setImageAdjustMode()


    def  restoreUIValuesToLayer( self, imgpar ):
        self.slideThresh.setValue( int(100*imgpar.seg_threshold ))
        self.slideBelndwt1.setValue( int(100*imgpar.blendweight_img1 ))
        self.slideBrightness.setValue(imgpar.brightness)
        self.slideSaturat.setValue(imgpar.saturation)
        self.slideBlurEdge.setValue(imgpar.blur_edge)
        self.checkBoxDenoise.setChecked(imgpar.denoise_it)
        self.checkBoxPP.setChecked(imgpar.postprocess_it)       
        self.displaySliderValues()


    def  exportTransparency( self):
        self.old_status= self.statusBar.currentMessage()
        self.setStatus("Copying Foreground , Wait! ")
        worker2 = Worker(self._transparencyToClipboard)
        worker2.signals.finished.connect(self._displayTransparencyCompleted)
        self.thread_pool.start(worker2)        


    def  _transparencyToClipboard(self, progress_callback=None):
        helper_transp= photoglimmer.uihelper_transparency.UIHelper(self)       
        helper_transp.transparency_to_clipboard(  
                                           originalImgPath= photoglimmer_backend.originalImgPath,
                                           tempdirpath=photoglimmer_backend.tempdirpath)


    def  _displayTransparencyCompleted(self, progress_callback=None):
        self.showMessage( "Foreground Copied To Clipboard", 
                            "Paste it to your favourite image Editor")
        self.setStatus(self.old_status)
        self.old_status=""


    def  processImage(self):
        self.disableSliders()
        if (photoglimmer_backend.scaledImgpath == None
                or not os.path.exists(photoglimmer_backend.scaledImgpath)):
            self.showMessage("Error!","Empty", "You haven't Opened any Image! ")
            return
        worker2 = Worker(self._processImage_bgstuff)
        worker2.signals.finished.connect(self._endImageProcessing)
        self.thread_pool.start(worker2)


    def  _processImage_bgstuff(self, progress_callback=None):
        rects= self.labelImg.get_all_rectangles() 
        result_image = photoglimmer_backend.processImageFinal(
            isOriginalImage=False,
            isSegmentationNeeded=self.is_segmentation_needed,
            isTweakingNeeded= self.is_tweaking_needed,
            isLUTneeded= self.curveEditPreferred(),
            rects = rects
            )
        self.tempimage = self.createTempFile(fname=photoglimmer_backend.fname_resultimg,
                                             img=result_image)


    def  _endImageProcessing(self):
        self.showImage(self.tempimage)
        self.showMask(
            os.path.join(photoglimmer_backend.tempdirpath,
                         photoglimmer_backend.fname_maskImgBlurred))
        self.enableSliders()
        self.is_state_dirty = True
        self.raiseSegmentationFlag(False)
        self.raiseTweakFlag(False)


    def  handle_rect_changes(self):
        self.is_segmentation_needed= True
        self.processImage()


    def  handle_lut_update(self):
        self.is_segmentation_needed= False
        self.setBackendVariables()
        self.processImage()


    def  handle_curve_reset_button(self):
        self.widgColorCurve.reset_curve(new_image=False)


    def  load_application_settings(self):
        print("Main App: Loading settings...")
        self._file_dialog_type = self.settings.value(
            SettingsConfig.Keys.FILE_DIALOG_TYPE,
            SettingsConfig.Defaults.FILE_DIALOG_TYPE, str
        )
        self._denoise_on_load = self.settings.value(
            SettingsConfig.Keys.DENOISE_ENABLED,
            SettingsConfig.Defaults.DENOISE_ENABLED, bool
        )
        self._brightness_mode = self.settings.value(
            SettingsConfig.Keys.BRIGHTNESS_MODE,
            SettingsConfig.Defaults.BRIGHTNESS_MODE, str
        )
        choice = self.settings.value(
            SettingsConfig.Keys.START_FOLDER_CHOICE,
            SettingsConfig.Defaults.START_FOLDER_CHOICE, str
        )
        custom_path = self.settings.value(
            SettingsConfig.Keys.START_FOLDER_CUSTOM_PATH,
            SettingsConfig.Defaults.START_FOLDER_CUSTOM_PATH, str
        )
        last_opened_path = self.settings.value(
            SettingsConfig.Keys.LAST_OPENED_PATH,
            SettingsConfig.Defaults.LAST_OPENED_PATH, str
        )
        if choice == SettingsConfig.StartFolderChoice.PICTURES:
            self._start_folder_path = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        elif choice == SettingsConfig.StartFolderChoice.HOME:
            self._start_folder_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        elif choice == SettingsConfig.StartFolderChoice.LAST_OPENED:
            self._start_folder_path = last_opened_path if os.path.isdir(last_opened_path) else SettingsConfig.Defaults.LAST_OPENED_PATH
        elif choice == SettingsConfig.StartFolderChoice.CUSTOM:
            self._start_folder_path = custom_path if os.path.isdir(custom_path) else SettingsConfig.Defaults.START_FOLDER_CUSTOM_PATH
        else: 
            self._start_folder_path = SettingsConfig.Defaults.START_FOLDER_CUSTOM_PATH
        print(" Settings loaded.")  


    def  systemFileDialogPreferred(self):
        ft= self.settings.value(SettingsConfig.Keys.FILE_DIALOG_TYPE, SettingsConfig.FileDialogType.SYSTEM)  
        return ft == SettingsConfig.FileDialogType.SYSTEM


    def  curveEditPreferred(self):
        m= self.settings.value(SettingsConfig.Keys.BRIGHTNESS_MODE, SettingsConfig.BrightnessMode.SLIDERS)  
        return m == SettingsConfig.BrightnessMode.COLOR_CURVE


    def  setLastOpenedLocationPref(self, fpath):
        dpath= os.path.dirname(fpath) 
        self.settings.setValue(SettingsConfig.Keys.LAST_OPENED_PATH, dpath)     


    def  show_preferences_dialog(self):
        dialog = PreferencesDialog(self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            print("Preferences Accepted. Reloading settings in main app...")
            self.load_application_settings()
            self.setupStackedWidget() 
            self.updateDenoiseCheckbox()
            print(f"Preferences Updated. File Dialog: {self._file_dialog_type}, Denoise: {self._denoise_on_load}, Brightness: {self._brightness_mode}")
        else:
            print("Preferences Cancelled.")


def  main():
    global app,tempdir
    if len(sys.argv)>1 and str.strip(sys.argv[1]) in ["-v","--version" ]:
        print(f"PhotoGlimmer Version 0.4.0")
        sys.exit(0)
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