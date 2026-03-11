# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# Toolbar at the top of ManWindow
# Includes a subtoolbar for manual mask editing 
# which is provided by components.MaskToolbar

from PySide6.QtWidgets import QToolBar, QToolButton, QWidget, QSizePolicy
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
import os

# Import custom components 
# (Adjust import path if these files are in siblings)
from .components.MaskToolbar import MaskToolbar

class ToolbarSetup:
    @staticmethod
    def setup(window):
        """
        Builds the Main Toolbar.
        """
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("toolbar_main")
        window.addToolBar(toolbar)

        # 1. Custom Import Button
        btn_import = QToolButton()
        btn_import.setDefaultAction(window.act_open)
        btn_import.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon) 
        btn_import.setObjectName("BtnToolbarImport") 
        toolbar.addWidget(btn_import)

        toolbar.addAction(window.act_export)
        toolbar.addSeparator()
        
        # 2. History
        toolbar.addAction(window.act_undo)
        toolbar.addAction(window.act_redo)
        toolbar.addSeparator()
        
        # 3. Zoom
        toolbar.addAction(window.act_zoom_in)
        toolbar.addAction(window.act_zoom_out)
        toolbar.addAction(window.act_zoom_fit)

        toolbar.addSeparator()
        toolbar.addAction(window.act_toggle_overlays)

        # 4. Mask Editing Group
        toolbar.addSeparator()
        
        # We attach the mask toolbar to window so logic can access it
        window.mask_toolbar = MaskToolbar()
        window.mask_toolbar.mode_toggled.connect(window.on_mask_mode_toggled)
        window.mask_toolbar.tool_changed.connect(window.on_brush_tool_changed)
        window.mask_toolbar.size_changed.connect(window.on_brush_size_changed)
        toolbar.addWidget(window.mask_toolbar)

        # 5. Branding (Moved here from setup_branding to keep toolbar logic together)
        # Or you can call setup_branding() separately if you prefer.
        ToolbarSetup._add_branding_link(window, toolbar)

    @staticmethod
    def _add_branding_link(window, toolbar):
        """Internal helper to add the GitHub link on the right"""
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent; border:none")
        toolbar.addWidget(spacer)

        # Link Button
        # Logic to find icon path (Copied from your code)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "nano3.png") 

        if os.path.exists(icon_path):
            link_btn = QToolButton()
            link_btn.setIcon(QIcon(icon_path)) 
            link_btn.setToolTip("Visit Application Website")
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            link_btn.setObjectName("linkButton")
            link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/codecliff/PhotoGlimmer")))
            toolbar.addWidget(link_btn)

            