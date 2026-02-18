# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# Python end of our Theme Management 
# Its main job is to translate @ noation in  the theme.qss (in assets/ folder) 
# Also - 1.  sets a base theme on which othe rthemes are built 
#        2.  any new themse will be defined and implemneted here 
# ######################################################################################
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication

class ThemeManager:
    """
    Manages the application's visual style.
    Merges 'Common' variables with 'Theme Specific' variables to generate the final sheet.
    Implements new Themes 
    """
    
    # 1. CONSTANTS (Shared across ALL themes)
    COMMON = {
        "@font_family": '"Segoe UI", "Helvetica Neue", sans-serif',
        # "@font_size_base": "13px",
        "@radius_std": "4px",
        "@radius_lg": "6px",
        
        # Brand Colors that stick regardless of theme
        "@accent": "#8caa97" ,       # signature Color 
        "@accent_hover":  "#9bb988", # "#0088cc",
        "@success": "#00C853", 
        "@danger": "#FF4444"
    }

    # 2. THEMES (Specific overrides)
    PALETTES = {
        "Dark": {
            "@bg_primary": "#1e1e1e",      # Main Window
            "@bg_secondary": "#2d2d2d",    # Sidebars / Panels
            "@bg_tertiary": "#3a3a3a",     # Inputs / List Items
            
            "@text_primary": "#ffffff",    # Main Text
            "@text_secondary": "#aaaaaa",  # Labels
            "@text_disabled": "#666666",
            
            "@border": "#444444",          # Borders
            "@scrollbar_handle": "#4A4A4A"
        },
        
        "Light": {
            "@bg_primary": "#f5f5f5",      # Main Window (Light Gray)
            "@bg_secondary": "#ffffff",    # Sidebars (White)
            "@bg_tertiary": "#e0e0e0",     # Inputs (Slightly darker for contrast)
            
            "@text_primary": "#333333",    # Dark Gray (Never use pure black)
            "@text_secondary": "#666666",  # Medium Gray
            "@text_disabled": "#a0a0a0",
            
            "@border": "#cccccc",          # Light Borders
            "@scrollbar_handle": "#999999"
        },

        "Ocean": {
            "@bg_primary": "#0f172a",      # Deep Blue Background
            "@bg_secondary": "#1e293b",    # Lighter Blue Panels
            "@bg_tertiary": "#334155",     # Input fields
            
            "@text_primary": "#e2e8f0",    # Off-white text
            "@text_secondary": "#94a3b8",  # Muted blue-grey text
            "@text_disabled": "#475569",
            
            "@border": "#334155",          # Subtle border
            "@scrollbar_handle": "#475569"
        },

        "Gallery": {
            "@bg_primary": "#ede9e6",      # Warm "Bone" white
            "@bg_secondary": "#f7f5f3",    # Clean paper white panels
            "@bg_tertiary": "#dfdbd8",     # Slightly darker inputs
            
            "@text_primary": "#1a1a1a",    # Rich near-black
            "@text_secondary": "#7c726a",  # Warm taupe labels
            "@text_disabled": "#b5ada5",
            
            "@border": "#d1ccc8",          # Soft clay borders
            "@scrollbar_handle": "#c0b7af"
        }

    }

    @staticmethod
    def apply_theme(app, theme_name="Dark"):
        """
        Merges Common + Specific palette, replaces placeholders in main.qss, 
        and applies to app.
        """
        if theme_name not in ThemeManager.PALETTES.keys(): # ["Dark", "Light"]:
            theme_name = "Dark"
        
        specific_palette = ThemeManager.PALETTES.get(theme_name)
        if not specific_palette:
            print(f"Error: Theme '{theme_name}' not found.")
            return

        # --- THE MERGE LOGIC ---
        # 1. Start with Common
        final_palette = ThemeManager.COMMON.copy()
        # 2. Update with Specific (overwrites conflicts if any)
        final_palette.update(specific_palette)

        # Locate the QSS file
        current_dir = Path(__file__).parent.resolve()
        # Adjust '..' count based on your exact file structure.
        # If in ui/managers: .parent(ui) -> .parent(photoglimmer) -> assets
        project_root = current_dir.parent.parent 
        qss_path = project_root / "assets" / "styles" / "main.qss"

        try:

            if not qss_path.exists():
                print(f" ❌ CRITICAL QSS ERROR: Stylesheet not found at {qss_path}")
                raise Exception(f"FileNotFound {qss_path}") 
        
            with open(qss_path, "r") as f:
                qss_content = f.read()

            # Important: SORT BY LENGTH DESCENDING  to avoid changing prematurely
            # We sort keys so longer placeholders (e.g. @accent_hover) are processed 
            # BEFORE shorter substrings (e.g. @accent).
            sorted_keys = sorted(final_palette.keys(), key=len, reverse=True)

            # Replace All Placeholders using sorted order
            for key in sorted_keys:
                value = final_palette[key]
                qss_content = qss_content.replace(key, value)

            # Apply
            app.setStyleSheet(qss_content)
            print(f"Theme '{theme_name}' applied successfully.")
            
        except Exception as e:
            print(f"Error applying theme: {e}")            
            print(f" ⚠️ Developer check recommended")




   