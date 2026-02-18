# ######################################################################################
# Custom  Splash Screen for our applicaiotn 
# Is called before MainWindow , form __main.py__
# ideally should be shown even before heavy imports like cv2 are made 
# Qt's built in Spalsh Screen is not used , it is too unreeliable 
# ######################################################################################

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt, QRect, QPropertyAnimation,QEasingCurve

class SplashScreen(QWidget):
    def __init__(self, pixmap_path):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        maxsize=256

        # Content container (needed for Drop Shadow to work on a transparent widget)
        container = QWidget(self)
        container.setStyleSheet("background: transparent;") 

        # 1. Image
        image_lbl = QLabel()
        pix = QPixmap(str(pixmap_path))
        # Optional: Scale it if your source image is huge
        if pix.width() > maxsize:
            pix = pix.scaled(maxsize, maxsize, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
        image_lbl.setPixmap(pix)
        image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Text
        status = QLabel("Photo.glimmer")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setFont(QFont("Segoe UI", 10))
        status.setStyleSheet("color: #DDDDDD; margin-bottom: 5px;")

        # 3. Layouts
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20) # Padding for shadow
        layout.addWidget(image_lbl)
        layout.addWidget(status)
        
        

        # 4. Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        container.setGraphicsEffect(shadow)

        outer_layout = QVBoxLayout(self) # for dropshadow 
        
        # We need margins larger than the shadow blur radius + offset
        # Blur is 30, Offset is 8. Margin 40 is safe.
        outer_layout.setContentsMargins(40, 40, 40, 40)         
        outer_layout.addWidget(container)

        

        self.adjustSize()

        # Animation Setup
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(1000) # 500ms fade out
        #self._fade.setEasingCurve(QEasingCurve.OutQuad) # quadratic - fast to slow
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.close)

        

    def center_on_screen(self):
        screen = self.screen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    def finish(self):
        """Triggers the fade out and close."""
        self._fade.start()

