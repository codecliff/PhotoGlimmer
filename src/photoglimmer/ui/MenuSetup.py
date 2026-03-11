# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


import os
from PySide6.QtWidgets import QMenu

class MenuSetup:
    @staticmethod
    def setup(window):
        """
        Builds the Menu Bar for the main window.
        """
        window.menu_bar = window.menuBar()
        
        # 1. File Menu
        file_menu = window.menu_bar.addMenu("&File")
        file_menu.addAction(window.act_open)
        
        # Recent Files Submenu 
        window.menu_recent = file_menu.addMenu("Open Recent")
        
        # [CHANGE] Call the logic method defined below
        MenuSetup.update_recent_menu(window) 
        
        file_menu.addSeparator()        
        file_menu.addAction(window.act_export)
        
        file_menu.addSeparator()
        file_menu.addAction(window.act_quit)

        # 2. Edit Menu
        edit_menu = window.menu_bar.addMenu("Edit")
        edit_menu.addAction(window.act_undo)
        edit_menu.addAction(window.act_redo)

        # 3. Tools Menu
        tools_menu = window.menu_bar.addMenu("&Tools")       
        tools_menu.addAction(window.act_open_location)
        tools_menu.addSeparator()
        tools_menu.addAction(window.act_launch_img)
        tools_menu.addSeparator()
        tools_menu.addAction(window.act_prefs)
        
        # 4. View Menu
        view_menu = window.menu_bar.addMenu("View")
        view_menu.addAction(window.act_zoom_in)
        view_menu.addAction(window.act_zoom_out)
        view_menu.addAction(window.act_zoom_fit)

        # 5. Help Menu
        help_menu = window.menu_bar.addMenu("He&lp")
        help_menu.addAction(window.act_help)
        help_menu.addAction(window.act_about)

    # ============================================================
    # "RECENT FILES" Menu     
    # ============================================================
    @staticmethod
    def update_recent_menu(window):
        """
        Rebuilds the Open Recent submenu from Settings.
        Args:
            window: The MainWindow instance.
        """
        # Safety check: Menu might not be created yet if setup failed
        if not hasattr(window, 'menu_recent'): return

        window.menu_recent.clear()
        
        # Access list directly from the window's SettingsManager
        recent_files = window.settings_manager.recent_files 
        
        if not recent_files:
            action = window.menu_recent.addAction("No recent files")
            action.setEnabled(False)
            return

        for path in recent_files:
            # We must use 'window._attempt_load_image'
            receiver = lambda checked=False, p=path: window._attempt_load_image(p)
            
            display_name = os.path.basename(path)
            action = window.menu_recent.addAction(display_name)
            action.setStatusTip(path)
            action.triggered.connect(receiver)
            
        window.menu_recent.addSeparator()
        act_clear = window.menu_recent.addAction("Clear History")
        
        # Connect to the static method below, passing 'window'
        act_clear.triggered.connect(lambda: MenuSetup.on_clear_recent(window))

    @staticmethod
    def on_clear_recent(window):
        window.settings_manager.clear_recent_files()
        MenuSetup.update_recent_menu(window)