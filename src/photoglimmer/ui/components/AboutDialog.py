# ######################################################################################
# The About Dialog for our applicaiton
# All the content text is inside this file itself
# ######################################################################################

import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt, QSize, QEvent
from PySide6.QtGui import QPixmap, QFont

from ..managers.ThemeManager import ThemeManager
from ..managers.SettingsManager import SettingsManager
from ...backend.Interfaces import APP_NAME, APP_VERSION # Assuming you have an APP_VERSION constant there too?

# If you don't have a version constant, define it here
VERSION = f"V{APP_VERSION} (Beta)"

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(f"About {APP_NAME}")
        
        # Fixed size for a consistent "Card" look
        self.setFixedSize(400, 500) 
        self.setWindowOpacity(0.95)
        
        # Window Flags: Keep standard OS frame (Title bar + Close X), 
        # but remove the "What's this?" (?) button if present.
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # --- LAYOUT ---
        # We use a central layout with high spacing to let elements breathe
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(40, 60, 40, 40)
        self.layout.setSpacing(10)

        # 1. HERO ICON
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load and scale the icon
        # Adjust path as needed based on your folder structure
        icon_path = os.path.join(os.path.dirname(__file__), "../../icons/appicon-512.png")
        
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            # Scale to 128x128 for a nice "Hero" size
            scaled_pix = pix.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(scaled_pix)
        else:
            self.icon_lbl.setText("Thinking...") # Fallback
            
        self.layout.addWidget(self.icon_lbl)
        
        # Spacer (20px)
        self.layout.addSpacing(20)

        # 2. APP TITLE
        self.title_lbl = QLabel(APP_NAME)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Font styling is done in refresh_theme() via CSS
        self.layout.addWidget(self.title_lbl)

        # 3. VERSION
        self.ver_lbl = QLabel(VERSION)
        self.ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.ver_lbl)

        # Spacer
        self.layout.addSpacing(30)

        # 4. DESCRIPTION
        desc_text = (
            "<b>Privacy-focused Portrait Editor.</b><br>"
            "Photoglimmer uses local AI to understand your photos "
            "without sending a single pixel to the cloud."
        )
        self.desc_lbl = QLabel(desc_text)
        self.desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setOpenExternalLinks(True)
        self.layout.addWidget(self.desc_lbl)
        
        # Spacer (Push footer to bottom)
        self.layout.addStretch()

        # 5. FOOTER (Copyright & Links)
        footer_text = (
            "© 2026 Rahul Singh<br>"
            "<a href=https://github.com/codecliff/PhotoGlimmer' style='text-decoration:none;'>GitHub</a> &bull; "            
            "<a href='https://codecliff.github.io/photoglimmer/feedback.html' style='text-decoration:none;'>Feedback</a>"
        )
        self.footer_lbl = QLabel(footer_text)
        self.footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_lbl.setOpenExternalLinks(True)
        self.layout.addWidget(self.footer_lbl)

        # Apply Theme
        self.refresh_theme()

    def refresh_theme(self):
        """
        Applies current theme colors to fonts and background.
        """
        settings = SettingsManager()
        palette = ThemeManager.PALETTES.get(settings.theme, ThemeManager.PALETTES["Dark"])
        
        bg_color = palette.get("@bg_primary", "#1e1e1e")
        text_primary = palette.get("@text_primary", "#E0E0E0")
        text_secondary = palette.get("@text_secondary", "#888888")
        accent = "#4da6ff" # You could add this to ThemeManager if you want

        # Apply Stylesheet
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                background-color: transparent;
                color: {text_primary};
            }}
        """)
        
        # Specific Font Styling
        # Title: Large, Bold
        self.title_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {text_primary};")
        
        # Version: Monospace, Muted
        self.ver_lbl.setStyleSheet(f"font-family: monospace; font-size: 14px; color: {text_secondary};")
        
        # Description: Normal
        self.desc_lbl.setStyleSheet(f"font-size: 14px; line-height: 1.4; color: {text_primary};")
        
        # Footer: Small, Muted, with Link styling
        self.footer_lbl.setStyleSheet(f"""
            QLabel {{
                font-size: 11px; 
                color: {text_secondary};
            }}
            /* Qt supports basic HTML link styling within the label text itself, 
               but we set the base color here */
        """)

    def changeEvent(self, event):
        """Handle Theme Swaps instantly"""        
        if not hasattr(self, 'title_lbl'):
            super().changeEvent(event)
            return

        if event.type() == QEvent.Type.StyleChange:
            self.refresh_theme()
            
        super().changeEvent(event)