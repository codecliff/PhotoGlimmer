# ######################################################################################
# Sone utility fucntion for UI
# TODO: shift more fucntions to here 
# ######################################################################################

import os
import sys
import subprocess
import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

class GuiUtils:
    """
    Static helper methods for UI operations.
    Includes High-Performance Zero-Copy Image Conversion.
    """

    @staticmethod
    def convert_cv_to_qpixmap(cv_img):
        """
        Converts an OpenCV image (BGR) to a QPixmap.
        OPTIMIZED: Uses Format_BGR888 and direct memory access to avoid 
        unnecessary copies and color swapping.
        """
        if cv_img is None: return QPixmap()

        # 1. Ensure Memory is Contiguous
        # QImage requires scanlines to be packed sequentially. 
        # If the array is a slice (e.g. img[:, 10:20]), it might not be contiguous.
        if not cv_img.flags['C_CONTIGUOUS']:
            cv_img = np.ascontiguousarray(cv_img)

        # 2. Handle Grayscale
        if len(cv_img.shape) == 2:
            h, w = cv_img.shape
            bytes_per_line = cv_img.strides[0]
            
            # Zero-Copy Wrap
            q_img = QImage(
                cv_img.data, 
                w, h, 
                bytes_per_line, 
                QImage.Format.Format_Grayscale8
            )
            return QPixmap.fromImage(q_img)

        # 3. Handle Color (BGR)
        h, w, ch = cv_img.shape
        bytes_per_line = cv_img.strides[0]
        
        # Zero-Copy Wrap using BGR888 (No cvtColor needed!)
        q_img = QImage(
            cv_img.data, 
            w, h, 
            bytes_per_line, 
            QImage.Format.Format_BGR888
        )
        
        # 4. Upload to GPU/Window System
        # QPixmap.fromImage triggers the copy to display memory.
        # Once this returns, we don't need the QImage or numpy array anymore.
        return QPixmap.fromImage(q_img)

    @staticmethod
    def open_browser(path_to_open):
        """
        Opens the system file browser at the given location.
        Adapts to Windows (os.startfile), MacOS (open), and Linux (xdg-open).
        """
        import subprocess, platform
        
        # 1. Ensure we are opening the FOLDER, not the image file
        if os.path.isfile(path_to_open):
            folder_path = os.path.dirname(path_to_open)
        else:
            folder_path = path_to_open

        osname = platform.system()
        
        try:
            if osname == 'Windows':
                os.startfile(folder_path)
            elif osname == 'Darwin': # macOS
                subprocess.Popen(['open', folder_path])
            else: # Linux
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            print(f"Error opening browser: {e}")

    @staticmethod
    def set_busy_state(window, is_busy):
        """
        Temporarily locks/unlocks the UI.
        """
        if is_busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

        # Disable main interaction points if they exist
        if hasattr(window, 'central_widget'):
            window.central_widget.setEnabled(not is_busy)
        if hasattr(window, 'menuBar'):
            window.menuBar().setEnabled(not is_busy)
            
        QApplication.processEvents()