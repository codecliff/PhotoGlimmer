# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

class ActionSetup:
    def __init__(self, window):
        """
        Creates QActions and attaches them to the main window instance.
        Args:
            window: The MainWindow instance (self).
        """
        
        # 1. File Actions
        window.act_open = QAction("📂 Open", window)
        window.act_open.setShortcut("Ctrl+O")
        window.act_open.setStatusTip("Open a new image")
        window.act_open.triggered.connect(window.on_open_image)

        window.act_export = QAction("💾 Export", window)
        window.act_export.setShortcuts(["Ctrl+E", "Ctrl+S"])
        window.act_export.setStatusTip("Export final image to disk")
        window.act_export.triggered.connect(window.on_export)

        window.act_quit = QAction("Exit", window)
        window.act_quit.setShortcut("Ctrl+Q")
        window.act_quit.setStatusTip("Exit Application")
        window.act_quit.triggered.connect(window.close)

        # 2. History Actions
        window.act_undo = QAction("↶ Undo", window)
        window.act_undo.setShortcut("Ctrl+Z")
        window.act_undo.triggered.connect(window.on_undo)

        window.act_redo = QAction("↷ Redo", window)
        window.act_redo.setShortcut("Ctrl+Y")
        window.act_redo.triggered.connect(window.on_redo)

        window.act_toggle_overlays = QAction("👁 Hide Frames", window)
        window.act_toggle_overlays.setCheckable(True)
        window.act_toggle_overlays.setShortcut("H") 
        window.act_toggle_overlays.setStatusTip("Hide layer boundaries to see the clean image")
        window.act_toggle_overlays.toggled.connect(window.on_toggle_overlays)

        # 3. Zoom Actions
        window.act_zoom_in = QAction("🔍+ In", window)
        window.act_zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        # Note: We use lambda to call the canvas method on the window
        window.act_zoom_in.triggered.connect(lambda: window.canvas.zoom_in())

        window.act_zoom_out = QAction("🔍- Out", window)
        window.act_zoom_out.setShortcut("Ctrl+-")
        window.act_zoom_out.triggered.connect(lambda: window.canvas.zoom_out())

        window.act_zoom_fit = QAction("🔍 Fit", window)
        window.act_zoom_fit.setShortcut("Ctrl+0")
        window.act_zoom_fit.triggered.connect(lambda: window.canvas.zoom_reset())

        # 4. Tools Actions
        window.act_open_location = QAction("📂 Open Containing Folder", window)
        window.act_open_location.setStatusTip("Open the folder containing the current image")
        window.act_open_location.triggered.connect(window.on_open_file_location)

        window.act_launch_img = QAction("Open Original in System Viewer", window)
        window.act_launch_img.setStatusTip("Open the source file in default OS application")
        window.act_launch_img.triggered.connect(window.open_original_in_system_viewer)
        
        window.act_prefs = QAction("⚙ Preferences...", window)
        window.act_prefs.setShortcut("Ctrl+P") 
        window.act_prefs.triggered.connect(window.on_open_preferences)

        # 5. Help Actions
        window.act_help = QAction("User Guide", window)
        window.act_help.setShortcuts(["F1", "Ctrl+G"])
        window.act_help.triggered.connect(window.open_help)

        window.act_about = QAction("About", window)
        window.act_about.triggered.connect(window.show_about)
        