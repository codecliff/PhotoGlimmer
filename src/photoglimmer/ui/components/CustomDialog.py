# ######################################################################################
# Instead of showing defualt alert and confirm dialogues, we use this
# ######################################################################################

 

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QWidget, QToolButton)
from PySide6.QtCore import Qt, QPoint

class CustomDialog(QDialog):
    def __init__(self, parent, title, message, btn_ok_text="OK", btn_cancel_text="Cancel"):
        super().__init__(parent)
        
        # ID for Theme Manager
        self.setObjectName("CustomDialog")
        
        # 1. FRAMELESS SETUP
        # remove OS title bar so we can build our own
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.setWindowOpacity(0.95) 
        
        # Main Layout (No margins, so header touches edges)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- A. CUSTOM TITLE BAR ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DialogTitleBar") # Styled in QSS
        self.title_bar.setFixedHeight(32) # Slim header
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 5, 0)
        
        # Title Text
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("DialogTitleText")
        title_layout.addWidget(self.lbl_title)
        
        title_layout.addStretch()
        
        # Close 'X' Button (Optional, mostly for visual completeness)
        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setObjectName("DialogCloseBtn")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self.reject)
        title_layout.addWidget(self.btn_close)
        
        self.main_layout.addWidget(self.title_bar)

        # --- B. CONTENT BODY ---
        self.content_widget = QWidget()
        self.content_widget.setObjectName("DialogContent") # Styled in QSS
        
        body_layout = QVBoxLayout(self.content_widget)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(15)

        # Message Label
        self.lbl_message = QLabel(message)
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setObjectName("DialogMessage")
        body_layout.addWidget(self.lbl_message)

        # Button Row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch() 

        if btn_cancel_text:
            self.btn_cancel = QPushButton(btn_cancel_text)
            self.btn_cancel.setObjectName("BtnDialogCancel")
            self.btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_cancel)

        if btn_ok_text:
            self.btn_ok = QPushButton(btn_ok_text)
            self.btn_ok.setObjectName("BtnDialogOK")
            self.btn_ok.clicked.connect(self.accept)
            self.btn_ok.setDefault(True)
            self.btn_ok.setFocus()
            btn_layout.addWidget(self.btn_ok)

        body_layout.addLayout(btn_layout)
        self.main_layout.addWidget(self.content_widget)
        
        # Sizing
        self.setMinimumWidth(350)
        
        # Drag State
        self._drag_pos = None

               
       
        if parent:
            self.center_on_parent()


    # ==========================================
    # DRAGGING LOGIC (Since we have no OS bar)
    # ==========================================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only allow dragging if clicking the header or background (not buttons)
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # ==========================================
    # STATIC METHODS (Unchanged)
    # ==========================================
    @staticmethod
    def _run_with_dimming(parent, dlg_instance):
        if hasattr(parent, 'toggle_canvas_dimming'):
            parent.toggle_canvas_dimming(True)
        try:
            return dlg_instance.exec()
        finally:
            if hasattr(parent, 'toggle_canvas_dimming'):
                parent.toggle_canvas_dimming(False)

    @staticmethod
    def info(parent, title, message):
        dlg = CustomDialog(parent, title, message, btn_ok_text="OK", btn_cancel_text=None)
        return CustomDialog._run_with_dimming(parent, dlg)

    @staticmethod
    def warning(parent, title, message):
        dlg = CustomDialog(parent, title, message, btn_ok_text="Understood", btn_cancel_text=None)
        return CustomDialog._run_with_dimming(parent, dlg)

    @staticmethod
    def error(parent, title, message):
        dlg = CustomDialog(parent, title, message, btn_ok_text="Close", btn_cancel_text=None)
        return CustomDialog._run_with_dimming(parent, dlg)

    @staticmethod
    def question(parent, title, message, ok_text="Confirm", cancel_text="Cancel"):
        dlg = CustomDialog(parent, title, message, btn_ok_text=ok_text, btn_cancel_text=cancel_text)
        result_code = CustomDialog._run_with_dimming(parent, dlg)
        return result_code == QDialog.DialogCode.Accepted
    
    def center_on_parent(self):
        """
        Moves this dialog to the visual center of the top-level main window.
       ignpore  sub-widget or another dialog like file open .
        """
        if self.parent():
            # 1. Find the true top-level window (MainWindow)
            # .window() walks up the tree until it finds the root window
            top_level = self.parent().window() 
            
            # 2. Get Geometry of that main window
            parent_geo = top_level.geometry()
            
            # 3. Calculate Center
            self_geo = self.geometry()
            self_geo.moveCenter(parent_geo.center())
            
            # 4. Apply
            self.move(self_geo.topLeft())


    # Force centering every time .show() or .exec() is called
    def showEvent(self, event):
        self.center_on_parent()
        super().showEvent(event)
                          

        
        
        
