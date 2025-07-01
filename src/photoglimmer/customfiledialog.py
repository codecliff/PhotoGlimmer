
# ###############################################################################
# originally sourced from  https://stackoverflow.com/a/47599536/5132823
# by https://stackoverflow.com/users/6622587/eyllanesc
# File license CC BY-SA 3.0
# ###############################################################################
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QLabel, QDialog
import  qdarktheme


class  QFileDialogPreview(QFileDialog):


    def  __init__(self, *args, **kwargs):
        QFileDialog.__init__(self, *args, **kwargs)
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setOption(QFileDialog.HideNameFilterDetails, True)      
        self.setWindowTitle("PhotoGlimmer: Open an Image")        
        layoutV = QVBoxLayout()
        layoutV.setAlignment(Qt.AlignVCenter )
        layoutV.setMargin(10)
        self.setBaseSize(self.width() + 350, self.height())
        self.setSizeGripEnabled(True)
        self.setNameFilter('Images (*.png *.jpg *.bmp *.webp *.JPG *.jpeg *.JPEG )')
        self.mpPreview = QLabel("Preview", self)
        self.mpPreview.setFixedSize(250, 250)
        self.mpPreview.setAlignment(Qt.AlignCenter)
        self.mpPreview.setObjectName("labelPreview")
        self.mpPreview.setStyleSheet('''border: 2px solid gray;
                                        border-radius: 10px;
                                        padding: 8px 8px;                                        
                                        background: 666666;''')
        layoutV.addStretch()
        layoutV.addWidget(self.mpPreview)
        layoutV.addStretch()
        lt=self.layout()        
        lt.addLayout(  layoutV ,1,4) 
        self.currentChanged.connect(self.onChange)
        self.fileSelected.connect(self.onFileSelected)
        self.filesSelected.connect(self.onFilesSelected)
        self._fileSelected = None
        self._filesSelected = None 


    def  onChange(self, path):
        pixmap = QPixmap(path)
        if(pixmap.isNull()):
            self.mpPreview.setText("Preview")
        else:
            self.mpPreview.setPixmap(pixmap.scaled(self.mpPreview.width(), self.mpPreview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


    def  onFileSelected(self, file):
        self._fileSelected = file        


    def  onFilesSelected(self, files):
        self._filesSelected = files


    def  getFileSelected(self):
        return self._fileSelected


    def  getFilesSelected(self):
        return self._filesSelected
    @staticmethod


    def  getOpenFileName( parent, dir:str):
        fdlg = QFileDialogPreview(parent)
        if (parent != None):
            nWidth=int(parent.width()*0.8)
            nHeight=int(parent.height()*0.8)
            parentPos = parent.mapToGlobal(parent.pos())  
            fdlg.setGeometry(parentPos.x() + parent.width()/2 - nWidth/2,
                    parentPos.y() + parent.height()/2 - nHeight/2,
                    nWidth, nHeight);
            fdlg.setDirectory(dir)
        dlgresult= fdlg.exec_()
        selectedimg = ''
        if dlgresult == QDialog.Accepted :
            selectedimg =fdlg.getFileSelected()
        print(selectedimg)
        return (selectedimg,dlgresult == QDialog.Accepted)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QFileDialogPreview()
    window.show()
    sys.exit(app.exec_())