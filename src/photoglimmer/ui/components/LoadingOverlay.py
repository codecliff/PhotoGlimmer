# ######################################################################################
# Spinner Overlay to be shown during final export . Also supports Cancel 
# ######################################################################################

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QMovie
from pathlib import Path

# TODO: Rename this class and file 
class LoadingOverlay(QWidget):
    """
    Transparent overlay that blocks UI interaction during long tasks.
    Shows only a spinner and a status message.
    Captures ESC key to trigger cancellation.
    """
    canceled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ID for Theme Manager
        self.setObjectName("LoadingOverlay")

        # 1. Block mouse clicks
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # 2. Key Focus (Catch ESC)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 3. Visuals (AutoFill must be True for QSS background to work, 
        #    even if that background is 'transparent')
        self.setAutoFillBackground(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # --- SPINNER ---
        # Locate asset relative to this file: ui/components/LoadingOverlay.py
        current_dir = Path(__file__).parent.resolve()
        # Go up: components -> ui -> src -> root -> assets
        asset_path = current_dir.parent.parent / "assets" / "spinner200.gif"

        self.lbl_spinner = QLabel()
        self.lbl_spinner.setObjectName("LoadingSpinner")
        self.movie = QMovie(str(asset_path)) 
        
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(150, 150)) # Adjust size as needed
            self.lbl_spinner.setMovie(self.movie)
        else:
            self.lbl_spinner.setText("⏳") 
            # Font styling handled in QSS
        
        layout.addWidget(self.lbl_spinner)

        # --- STATUS TEXT ---
        self.lbl_text = QLabel("Processing... (Press ESC to Cancel)")
        self.lbl_text.setObjectName("LoadingText")
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #layout.addWidget(self.lbl_text)

    def start(self):
        """Show overlay and start animation."""
        self.lbl_text.setText("Processing... (Press ESC to Cancel)")
        self.show()
        self.raise_()
        self.setFocus()
        if self.movie.isValid():
            self.movie.start()

    def stop(self):
        """Hide overlay and stop animation."""
        if self.movie.isValid():
            self.movie.stop()
        self.hide()

    def on_cancel(self):
        """Handle cancellation request.
           self.cancelled signal is handled by ExportWorker.cancel
           This connection is made by ExportManager
        
        """
        self.lbl_text.setText("Cancelling...")
        self.canceled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:            
            self.on_cancel()
        else:
            super().keyPressEvent(event)
