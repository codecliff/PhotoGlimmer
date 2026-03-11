# ######################################################################################
# The Help Dialog for our applicaiton
# Supports find and zoom 
# The content text is laoded from resources.help_content ,which too is a python file
# ######################################################################################


from PySide6.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, QTextBrowser, QPushButton, 
                               QHBoxLayout, QLineEdit, QLabel, QFrame)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QTextDocument, QTextCursor

from ..managers.ThemeManager import ThemeManager
from ..managers.SettingsManager import SettingsManager
from ...resources.help_content import get_help_html

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Photoglimmer Help")
        self.setObjectName("HelpDialog") 

        # rahul : do not cache this after it's quit
        self.setWindowFlags(Qt.WindowType.Dialog) # this will fire changeEvnet !! fixed
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  

        self.setMinimumSize(600,400)
        self.resize(700, 800)
        self.setWindowOpacity(0.95)
        
        # --- STATE TRACKING ---
        self.current_font_size = 14 # Default size in px
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --- SEARCH BAR ---
        search_container = QWidget()
        search_container.setObjectName("SearchContainer")
        
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 8, 10, 8)
        search_layout.setSpacing(8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find...")
        self.search_input.returnPressed.connect(self.on_search_return)
        
        # Clear error state immediately when user types
        self.search_input.textChanged.connect(self.clear_search_state)
        
        # Buttons
        self.btn_prev = QPushButton("U") 
        self.btn_prev.setFixedSize(32, 32)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.search_prev)
        
        self.btn_next = QPushButton("N") 
        self.btn_next.setFixedSize(32, 32)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.search_next)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #ff6b6b; font-weight: bold; font-size: 11px;")

        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.VLine)
        self.sep.setFrameShadow(QFrame.Shadow.Sunken)
        self.sep.setFixedHeight(20)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(32, 32)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl -)")
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(32, 32)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl +)")
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_prev)
        search_layout.addWidget(self.btn_next)
        search_layout.addWidget(self.status_lbl)
        
        search_layout.addSpacing(10)
        search_layout.addWidget(self.sep)
        search_layout.addWidget(self.btn_zoom_out)
        search_layout.addWidget(self.btn_zoom_in)
        
        self.layout.addWidget(search_container)

        # --- MAIN BROWSER ---
        self.browser = QTextBrowser()
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.layout.addWidget(self.browser)
        
        # Initial Load
        self.refresh_content(reload_html=True)

    # --- ZOOM LOGIC (CSS BASED) ---
    def zoom_in(self):
        self.current_font_size += 2
        if self.current_font_size > 32: self.current_font_size = 32
        self.refresh_content(reload_html=False) # Only update style

    def zoom_out(self):
        self.current_font_size -= 2
        if self.current_font_size < 10: self.current_font_size = 10
        self.refresh_content(reload_html=False) # Only update style

    def zoom_reset(self):
        self.current_font_size = 14
        self.refresh_content(reload_html=False)

    def keyPressEvent(self, event):
        # 1. Ctrl + F
        if event.key() == Qt.Key.Key_F and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.search_input.setFocus()
            self.search_input.selectAll()
            event.accept()
            return
        
        # 2. Ctrl + Plus / Equal
        if (event.key() in [Qt.Key.Key_Plus, Qt.Key.Key_Equal]) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.zoom_in()
            event.accept()
            return

        # 3. Ctrl + Minus
        if event.key() == Qt.Key.Key_Minus and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.zoom_out()
            event.accept()
            return

        # 4. Ctrl + 0
        if event.key() == Qt.Key.Key_0 and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.zoom_reset()
            event.accept()
            return

        super().keyPressEvent(event)

    def refresh_content(self, reload_html=True):
        """
        Applies Theme Colors and Font Size via Stylesheet.
        reload_html: Set to False when zooming to preserve scroll position.
        """
        settings = SettingsManager()
        current_theme_name = settings.theme 
        palette = ThemeManager.PALETTES.get(current_theme_name, ThemeManager.PALETTES["Dark"])

        # 1. Load HTML (Only if needed, e.g. theme change or init)
        if reload_html:
            final_html = get_help_html(palette)
            self.browser.setHtml(final_html)
        
        # 2. Extract Palette
        bg_primary = palette.get("@bg_primary", "#1e1e1e")
        bg_secondary = palette.get("@bg_secondary", "#2d2d2d")
        bg_tertiary = palette.get("@bg_tertiary", "#333333") 
        text_primary = palette.get("@text_primary", "#E0E0E0")
        border_color = palette.get("@border", "#444")

        # 3. APPLY STYLE (Includes Dynamic Font Size)
        #  use CSS font-size to force the zoom. This works reliably.
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_primary}; 
                border: none;
                font-size: {self.current_font_size}px;
            }}
        """)

        # Style Container
        self.findChild(QWidget, "SearchContainer").setStyleSheet(f"""
            #SearchContainer {{
                background-color: {bg_primary};
                border-bottom: 1px solid {border_color};
            }}
        """)

        self.sep.setStyleSheet(f"color: {border_color};")

        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid #4da6ff; 
            }}
            QLineEdit[has_error="true"] {{
                border: 1px solid #ff6b6b;
            }}
        """)

        btn_style = f"""
            QPushButton {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {border_color}; 
            }}
            QPushButton:pressed {{
                background-color: #000;
            }}
        """
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_zoom_in.setStyleSheet(btn_style)
        self.btn_zoom_out.setStyleSheet(btn_style)

    def changeEvent(self, event):
        # SAFETY GUARD: 
        # Don't try to refresh content if the browser widget doesn't exist yet.
        # This handles the early event fired by setWindowFlags/setAttribute.
        if not hasattr(self, 'browser'):
            super().changeEvent(event)
            return

        if event.type() == QEvent.Type.StyleChange:
            # Theme changed? Reload everything including HTML colors
            self.refresh_content(reload_html=True)
            
        super().changeEvent(event)


    # --- SEARCH LOGIC ---

    def clear_search_state(self):
        """Clears error red border and label when user types"""
        self.status_lbl.setText("")
        self._set_error_state(False)

    def search_next(self):
        self._do_search(backward=False)

    def search_prev(self):
        self._do_search(backward=True)

    def on_search_return(self):
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.search_prev()
        else:
            self.search_next()

    # def _do_search(self, backward=False):
    #     query = self.search_input.text()
    #     if not query:
    #         return

    #     flags = QTextDocument.FindFlag(0)
    #     if backward:
    #         flags |= QTextDocument.FindFlag.FindBackward

    #     found = self.browser.find(query, flags)

    #     if found:
    #         self.status_lbl.setText("")
    #         self._set_error_state(False)
    #     else:
    #         self.status_lbl.setText("Not found")
    #         self._set_error_state(True)
            
    #         # Wrap Around Logic
    #         cursor = self.browser.textCursor()
    #         if backward:
    #             cursor.movePosition(QTextCursor.MoveOperation.End)
    #         else:
    #             cursor.movePosition(QTextCursor.MoveOperation.Start)
    #         self.browser.setTextCursor(cursor)

    def _do_search(self, backward=False):
        query = self.search_input.text()
        if not query:
            return

        flags = QTextDocument.FindFlag(0)
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward

        # 1. Try to find from current position
        found = self.browser.find(query, flags)

        # 2. If NOT found, Wrap Around and Try Again automatically
        if not found:
            # Move cursor to Start (if Forward) or End (if Backward)
            cursor = self.browser.textCursor()
            if backward:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            self.browser.setTextCursor(cursor)
            
            # search again to fix stop at bottom of page!
            found = self.browser.find(query, flags)

        # 3. Process Result (Success or True Failure)
        if found:
            self.status_lbl.setText("")
            self._set_error_state(False)
            
            # UX Polish: Ensure the found text is centered in view
            # (QTextBrowser usually does this, but this forces it)
            self.browser.ensureCursorVisible() 
        else:
            # If it fails TWICE, the word truly isn't there.
            self.status_lbl.setText("Not found")
            self._set_error_state(True)


    def _set_error_state(self, is_error):
        """for the not-found situation"""
        self.search_input.setProperty("has_error", is_error)
        self.search_input.style().unpolish(self.search_input)
        self.search_input.style().polish(self.search_input)

    def show_guide(self):
        """called by MainWindow"""
        self.show()
        self.raise_()
        self.activateWindow()

