# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################



# An independent widget to display image and manipulate layers with mouse 
# This makes the main,  central area of our applicaiton
#supports- image display, zoom , pan, rectangle-drawing, moving, deletion 
# is a dumb view which leaves out almost all the control logic and  bookkeeping is done by backend (ImageSession)


from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsPixmapItem, QGraphicsEllipseItem
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QCursor, QPixmap, QImage ,\
                            QDragEnterEvent, QDropEvent,QDragMoveEvent
from PySide6.QtCore import Qt, Signal, QRectF, QPointF

# =============================================================
# CLASS 0: MASK OVERLAY (red overlay)
# =============================================================
class MaskOverlayItem(QGraphicsPixmapItem):
    """
    Visualizes the AI Mask + User Edits inside the Layer Box.
    It sits as a child of LayerRectItem.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        # Sits above the background image but below the selection handles
        self.setZValue(5) 
        self.setOpacity(0.6) # Semi-transparent

# =============================================================
# CLASS 1:  SMART RECTANGLE (corresponds to one Layer Item)
# =============================================================
class LayerRectItem(QGraphicsRectItem):
    """
    A Smart Rectangle that handles its own highlighting, 
    moving, and resizing logic.
    """
    handle_size = 16.0 #10.0
    
    # Enum for interaction modes
    MODE_NONE = 0
    MODE_MOVE = 1
    MODE_RESIZE_TL = 2 # Top-Left
    MODE_RESIZE_TR = 3 # Top-Right
    MODE_RESIZE_BL = 4 # Bottom-Left
    MODE_RESIZE_BR = 5 # Bottom-Right

    def __init__(self, x, y, w, h, layer):
        super().__init__(0, 0, w, h) # Local coordinates are 0,0 based
        self.setPos(x, y) # Position in scene
        
        self.layer_id = layer.layer_id 
        self.layer=layer
        
        # Appearance
        self.setPen(QPen(QColor("#00AAFF"), 2)) # Blue default
        self.setBrush(QBrush(QColor(0, 0, 0, 0))) # Transparent fill
        
        # Flags
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        self.current_mode = self.MODE_NONE

        self.lock_color = QColor("#EC250B")

        # --- MASK OVERLAY ---
        # Child item to display the red mask tint
        self.mask_item = MaskOverlayItem(self)


    def set_mask_pixmap(self, pixmap):
        """Updates the red overlay visualization."""
        self.mask_item.setPixmap(pixmap)
        # Ensure it fits the rect exactly (scaling if necessary)
        if not pixmap.isNull():
            # We assume the pixmap matches the rect size, but we can enforce scale if needed
            pass 

    def boundingRect(self):
        """
        Define the outer bounds of the item, including the custom handles.
        Prevents rendering artifacts (trails) when moving.
        """
        # Get the standard box
        rect = super().boundingRect()
        
        # Calculate padding needed for handles
        # Handles are centered on corners, so they stick out by half their size.
        pad = self.handle_size / 2
        
        # Add a little extra for the pen width (e.g., 2px) to be safe
        pad += 2.0 
        
        # Expand the rect in all directions
        return rect.adjusted(-pad, -pad, pad, pad)
        

    

    def paint(self, painter, option, widget):
        # 1. Draw the main selection box (Yellow Dashed)
        super().paint(painter, option, widget)
        
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFFF00"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())
            
            # 2. Draw Handles (Hollow: White Fill + Black Border)
            # This contrast ensures visibility on ANY image background
            painter.setBrush(QBrush(QColor("white"))) 
            painter.setPen(QPen(QColor("black"), 1, Qt.PenStyle.SolidLine))
            
            r = self.rect()
            hs = self.handle_size
            
            # Draw handles centered on corners
            handles = [
                (r.left(), r.top()),      # TL
                (r.right(), r.top()),     # TR
                (r.left(), r.bottom()),   # BL
                (r.right(), r.bottom())   # BR
            ]
            
            for x, y in handles:
                # Square Handle
                #painter.drawRect(x - hs/2, y - hs/2, hs, hs)
                
                # OPTIONAL: Circular Handle (Uncomment to try)
                painter.drawEllipse(QPointF(x, y), hs/2, hs/2)

            if self.layer.is_frozen:
             self._draw_lock_icon(painter, self.rect().topLeft())    



    

    def _draw_lock_icon(self, painter, top_left_pos):
        """
        Draws a geometric lock inside rect bound to indicate that layer is locked
        """
        painter.save()
        
        # 1. Setup Position (Inside top-left)
        margin = 6
        x = int(top_left_pos.x() + margin)
        y = int(top_left_pos.y() + margin)
        
        # 2. Draw Shackle (The Loop)
        # We draw this first so it goes 'behind' the body if they overlap
        shackle_pen = QPen(self.lock_color, 2) # 2px thick line
        painter.setPen(shackle_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # drawArc takes arguments in 1/16th of a degree
        # (x+2, y) to offset it slightly inside the body width
        painter.drawArc(x + 2, y, 8, 10, 0 * 16, 180 * 16) 

        # 3. Draw Body (The Square)
        painter.setPen(Qt.PenStyle.NoPen) # No outline
        painter.setBrush(self.lock_color) # Solid fill
        
        # Rect(x, y+offset, width, height, radius, radius)
        painter.drawRoundedRect(x, y + 5, 12, 9, 2, 2)
        
        painter.restore()
        



    def hoverMoveEvent(self, event):
        """repurpsed to change cursor based on mouse position (Center vs Corner handles)."""
        if not self.isSelected():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            return
        
        # TODO: : Override cursor if in Brush Mode (handled by parent Canvas usually, 
        # For now, we rely on Canvas overriding cursor).

        pos = event.pos()
        r = self.rect()
        
        # Check corners for resize cursor
        if self._is_near(pos, r.topLeft()) or self._is_near(pos, r.bottomRight()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._is_near(pos, r.topRight()) or self._is_near(pos, r.bottomLeft()):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor) # Move cursor

        super().hoverMoveEvent(event)

    def mouseMoveEvent(self, event):
        """Handle custom resizing logic with MINIMUM SIZE constraints."""
        
        # Define Minimum Size (in pixels)
        MIN_SIZE = 20.0 

        # CASE 1: Standard Move (Drag entire box)
        if self.current_mode == self.MODE_MOVE:
            super().mouseMoveEvent(event) 
            
        # CASE 2: Resize (Change width/height)
        elif self.current_mode != self.MODE_NONE:
            
            pos = event.pos()
            r = self.rect()
            
            # We calculate coordinates manually to enforce constraints
            # r.left(), r.right(), r.top(), r.bottom()
            
            new_left = r.left()
            new_right = r.right()
            new_top = r.top()
            new_bottom = r.bottom()
            
            # 1. Update the coordinate based on which handle is dragged
            if self.current_mode == self.MODE_RESIZE_TL:
                new_left = pos.x()
                new_top = pos.y()
            elif self.current_mode == self.MODE_RESIZE_TR:
                new_right = pos.x()
                new_top = pos.y()
            elif self.current_mode == self.MODE_RESIZE_BL:
                new_left = pos.x()
                new_bottom = pos.y()
            elif self.current_mode == self.MODE_RESIZE_BR:
                new_right = pos.x()
                new_bottom = pos.y()
            
            # 2. ENFORCE MINIMUM SIZE (Clamping)
            
            # Check Width
            if (new_right - new_left) < MIN_SIZE:
                # If we are dragging the LEFT handle, limit it relative to the RIGHT
                if self.current_mode in [self.MODE_RESIZE_TL, self.MODE_RESIZE_BL]:
                    new_left = new_right - MIN_SIZE
                # If dragging RIGHT handle, limit it relative to the LEFT
                else:
                    new_right = new_left + MIN_SIZE

            # Check Height
            if (new_bottom - new_top) < MIN_SIZE:
                # If dragging TOP handle
                if self.current_mode in [self.MODE_RESIZE_TL, self.MODE_RESIZE_TR]:
                    new_top = new_bottom - MIN_SIZE
                # If dragging BOTTOM handle
                else:
                    new_bottom = new_top + MIN_SIZE

            # 3. Apply the constrained rect
            self.prepareGeometryChange()
            self.setRect(QRectF(new_left, new_top, new_right - new_left, new_bottom - new_top).normalized())
            self.update()

    def mousePressEvent(self, event):
        """Decide if we are Moving or Resizing based on click location."""

        #ignore every button event other than left button 
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore() # Tell Qt we didn't handle this
            return
        
        else:
            
            # CASE A: Item is ALREADY selected.
            # Handles are visible, so we check if user clicked one.
            if self.isSelected():
                pos = event.pos()
                r = self.rect()
                
                if self._is_near(pos, r.topLeft()):
                    self.current_mode = self.MODE_RESIZE_TL
                elif self._is_near(pos, r.topRight()):
                    self.current_mode = self.MODE_RESIZE_TR
                elif self._is_near(pos, r.bottomLeft()):
                    self.current_mode = self.MODE_RESIZE_BL
                elif self._is_near(pos, r.bottomRight()):
                    self.current_mode = self.MODE_RESIZE_BR
                else:
                    self.current_mode = self.MODE_MOVE
                    super().mousePressEvent(event) # Pass to Qt for drag handling

            # CASE B: Item is NOT selected (First Click).
            # Handles are invisible, so we assume the user just wants to Grab & Move.
            else:
                self.current_mode = self.MODE_MOVE
                # super() will select the item for us and initialize the drag
                super().mousePressEvent(event)
                
            #   HIDE MASK OVERLAY DURING INTERACTION 
            # This allows the user to see the exact boundaries/content while moving
            if self.current_mode != self.MODE_NONE:
                self.mask_item.setVisible(False)


   

    def mouseReleaseEvent(self, event):
        self.current_mode = self.MODE_NONE
        
        #   RESTORE MASK OVERLAY  
        self.mask_item.setVisible(True)
        
        super().mouseReleaseEvent(event)

    def _is_near(self, p1, p2):
        return (p1 - p2).manhattanLength() < self.handle_size


# ==========================================
# CLASS 3: THE   CANVAS VIEW ( Widget)

# Note : Deliberately not maintaining a dict of layer positions here 
# keep this view dumb, all layer data is maitained ONLY by the backend (ImageSession)
# See canvas test script for how to do it  
# some signals are sent to mainwindow 
# ==========================================
class InteractiveCanvas(QGraphicsView):
    

    # Signals for MainWindow
    # Currently , we are not handling ony of these signals in this class itself  
    # We use 'object' for the ID to support String IDs from the backend
    geometry_created = Signal(int, int, int, int) # x, y, w, h    
    
    geometry_changed = Signal(object, int, int, int, int) # id, x, y, w, h
    layer_selected = Signal(object) # id
    layer_deleted = Signal(object) # id
    selection_cleared = Signal() # user has clciked outside all layers, id not needed

    # SIGNAL: Brush Stroke Finished
    # Emits: (layer_id, stroke_image_QImage, mode_string)
    mask_stroke_finished = Signal(object, object, str) 

    # Notifies MainWindow when a file is dropped here
    file_dropped = Signal(str)
    # Notifies MainWindow that visibility changed (so the button can update)
    ui_visibility_changed = Signal(bool)
    # Signal that can be used for  displaying zoom level to user
    zoom_changed = Signal(float)


    MAX_LAYERS=5
    layers_limit_reached = Signal(int) # Emits the limit number (e.g., 5)


    def __init__(self, parent=None):
        super().__init__(parent)

        
        
        # 1. Setup Scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        #self.scene.setBackgroundBrush(QColor("#1a1a1a")) 
        
        # Enable Scrollbars for Panning ---
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        
        # 2. View Settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag) 
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Enable Mouse Tracking for showing Custom Cursor  
        self.setMouseTracking(True) 

        # ### Track Panning State ---
        self._is_panning = False
        #  

        
        # 3. State
        self.bg_item = None #QGraphicsPixmapItem
        self.original_bg_item = None #QGraphicsPixmapItem
        self.drawing_rect_item = None
        self.start_point = None
        self.items_hidden = False
        
        # ### BRUSH STATE (New)
        self.brush_active = False # Master toggle
        self.brush_mode = 'add' # 'add' or 'erase'
        self.brush_size = 20 # pixels
        self.current_stroke_img = None # QImage scratchpad
        self.current_stroke_item = None # Visual line while dragging

        #  SOFTWARE CURSOR (The Circle) 
        # A simple ellipse item that follows the mouse in brush mode
        self.brush_cursor_item = QGraphicsEllipseItem()
        self.brush_cursor_item.setPen(QPen(QColor("white"), 1, Qt.PenStyle.SolidLine)) # Solid white
        self.brush_cursor_item.setBrush(Qt.BrushStyle.NoBrush)
        self.brush_cursor_item.setZValue(100) # Always on top
        self.brush_cursor_item.hide()
        self.scene.addItem(self.brush_cursor_item)


        # Track start positions for "geometry_changed" logic
        self._drag_start_geometry = {} 
        
        # 4. Listen to Scene Selection Changes
        self.scene.selectionChanged.connect(self.on_selection_change)


        # 5. Enable Drops on the Canvas
        self.setAcceptDrops(True)

    # --- API exposed to  MainWindow  ---

    def set_brush_params(self, active, mode='add', size=20):
        """Called by Toolbar to toggle paint mode."""
        self.brush_active = active
        self.brush_mode = mode
        self.brush_size = size
        
        # Update Cursor Size immediately
        if self.brush_active:
            r = self.brush_size / 2
            self.brush_cursor_item.setRect(-r, -r, self.brush_size, self.brush_size)
            self.brush_cursor_item.show()
            # Force system cursor hidden inside viewport
            self.viewport().setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.brush_cursor_item.hide()
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def set_pixmap(self, pixmap):
        if not pixmap: return
        if not self.bg_item:
            self.bg_item = QGraphicsPixmapItem(pixmap)
            self.bg_item.setZValue(0) # Bottom
            self.scene.addItem(self.bg_item)
        else:
            self.bg_item.setPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

    def set_original_pixmap(self, pixmap):
        if not pixmap: return
        if not self.original_bg_item:
            self.original_bg_item = QGraphicsPixmapItem(pixmap)
            self.original_bg_item.setZValue(-1) 
            self.scene.addItem(self.original_bg_item)
        else:
            self.original_bg_item.setPixmap(pixmap)
        
        # IMPORTANT: Hide it by default. We only show it when peeking.
        self.original_bg_item.setVisible(False)    

    

    

    def set_layers(self, layer_dict, active_id):
        """
        Syncs the Canvas visual state with the Backend data.

        Args:
            layer_dict (dict): A dictionary mapping {layer_id: LayerObject}.
                               The LayerObject MUST provide:
                               1. .is_background (bool): If True, no box is drawn.
                               2. .bounds (tuple): (x, y, w, h) in pixels.
            active_id (hashable): The ID of the currently selected layer.
        """
        self.scene.blockSignals(True)
        
        # 1. Clear old boxes
        for item in self.scene.items():
            if isinstance(item, LayerRectItem):
                self.scene.removeItem(item)
                
        # 2. Draw new boxes
        for lid, layer in layer_dict.items():
            # Contract Check: Skip background
            if getattr(layer, 'is_background', False): 
                continue 
            
            # Contract Check: Read geometry from .bounds
            if not hasattr(layer, 'bounds'):
                continue
                
            x, y, w, h = layer.bounds
            
            # Create the Visual Item
            rect_item = LayerRectItem(x, y, w, h, layer)
            rect_item.setZValue(10) # Ensure it sits on top
            
            if self.items_hidden: 
                rect_item.setVisible(False)
            
            self.scene.addItem(rect_item)
            
            # Handle Selection
            if lid == active_id: 
                rect_item.setSelected(True)
                
        self.scene.blockSignals(False)
        

    def set_active_layer(self, layer_id):        
        self.scene.blockSignals(True)
        for item in self.scene.items():
            if isinstance(item, LayerRectItem):
                item.setSelected(item.layer_id == layer_id)
        self.scene.blockSignals(False)

    def update_layer_mask_preview(self, layer_id, mask_pixmap):
        """Called by MainWindow to update the red overlay after AI/Manual edits."""
        for item in self.scene.items():
            if isinstance(item, LayerRectItem) and item.layer_id == layer_id:
                item.set_mask_pixmap(mask_pixmap)
                break

    def _get_safe_rect(self, rect_f):
        """
        Clamps a rect to the strict bounds of the Background Image.
        Crucial for preventing 65GB memory crashes and OpenCV empty-image errors.
        """
        # 1. If no image is loaded, no geometry is valid.
        if not self.bg_item:
            return QRectF()
            
        # 2. Get the rigid bounds of the image itself
        # (We trust the image, not the scene, which can grow infinitely)
        image_bounds = self.bg_item.boundingRect()
        
        # 3. Intersect
        # to clip overflow if user draws outide the iameg bound 
        safe_rect = rect_f.intersected(image_bounds)
        
        return safe_rect.normalized()
    

    # ==========================================
    # SHARED VISIBILITY LOGIC
    # ==========================================
    def toggle_overlay_visibility(self, force_hide=None):
        """
        Shows or hides the user-drawn Rectangles 
        force_hide: If True, forces Hiding. If False, forces Showing. If None, Toggles.
        """
        if force_hide is not None:
            # If we are already in the desired state, do nothing
            if self.items_hidden == force_hide:
                return
            new_state_hidden = force_hide
        else:
            new_state_hidden = not self.items_hidden

        # 1. PAUSE SIGNALS
        self.scene.blockSignals(True)
        
        if not self.items_hidden and new_state_hidden:
            # GOING TO HIDE: Cache Selection
            selected = self.scene.selectedItems()
            self._cached_selection_id = selected[0].layer_id if selected else None
        
        # 2. Update State
        self.items_hidden = new_state_hidden
        
        # 3. Update Items
        for item in self.scene.items():
            if isinstance(item, LayerRectItem):
                item.setVisible(not self.items_hidden)
                
        # 4. RESTORE SELECTION (If Unhiding)
        if not self.items_hidden and hasattr(self, '_cached_selection_id'):
            if self._cached_selection_id is not None:
                for item in self.scene.items():
                    if isinstance(item, LayerRectItem) and item.layer_id == self._cached_selection_id:
                        item.setSelected(True)
                        break
        
        # 5. RESUME SIGNALS
        self.scene.blockSignals(False)
        
        # 6. Notify Parent (so Toolbar Button syncs)
        # Note: We emit 'visible' status (True = Showing UI), so we invert 'hidden'
        self.ui_visibility_changed.emit(not self.items_hidden)    


   

    def on_selection_change(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            item = selected_items[0]
            if isinstance(item, LayerRectItem):
                self.layer_selected.emit(item.layer_id)
        # Emit cleared signal if nothing is selected
        else:
            self.selection_cleared.emit()        

    # #######################################################################
    # --- INPUT EVENTS ---
    # Note: Qt graphicsview has no mouse click event
    # ########################################################################

    def mousePressEvent(self, event):


        # middle button to peek the unedited image 
        # --- PEEK LOGIC (Mouse) ---
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.bg_item and self.original_bg_item:
                self.bg_item.setVisible(False)        # Hide Edited
                self.original_bg_item.setVisible(True) # Show Original
            return # Consume event
        
        # left button has lots to do

        # --- 2. PANNING LOGIC (New Priority) ---
        # Fix for Bug 2: Prevent Drawing when Spacebar is held
        # Fix for Bug 1: Allow Panning even if layers are hidden
        if self._is_panning:
            super().mousePressEvent(event) # Let Qt handle the scroll drag
            return # Stop here! Don't select, don't draw.

        #  if Layers are Hidden Canvas will not   mouse interactions, return to block them ! 
        if self.items_hidden:
            return
        
        # --- 3. BRUSH LOGIC (Paint Mode) ---
        # Priority: Pan > Brush > Move/Resize > Draw New
        if self.brush_active and event.button() == Qt.MouseButton.LeftButton:
            
            # Find which layer we are painting on
            # We assume painting happens on the CURRENTLY SELECTED layer
            selected_items = self.scene.selectedItems()
            if not selected_items or not isinstance(selected_items[0], LayerRectItem):
                return # Can't paint if nothing selected
            
            target_layer = selected_items[0]
            
            # Prepare the "Scratchpad" QImage
            # This image matches the Layer Box size
            rect = target_layer.rect()
            w, h = int(rect.width()), int(rect.height())
            
            if w > 0 and h > 0:
                self.current_stroke_img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
                self.current_stroke_img.fill(Qt.GlobalColor.transparent)
                
                # Start point in Layer Coordinates
                self.start_point = target_layer.mapFromScene(self.mapToScene(event.pos()))
                
                # We consume the event so we don't drag the box
                event.accept() 
                return 

        
        # --- SMART SELECTION: PICK SMALLEST LAYER ---
        # 1. Get all items under the mouse cursor
        sp = self.mapToScene(event.pos())
        items_under_mouse = self.scene.items(sp)
        
        # 2. Filter for just our LayerRectItems
        layer_candidates = [
            item for item in items_under_mouse 
            if isinstance(item, LayerRectItem)
        ]
        
        # 3. If multiple layers overlap here, prioritize the smallest one
        if len(layer_candidates) > 1:
            # Sort by Area (Width * Height) ascending
            layer_candidates.sort(key=lambda x: x.rect().width() * x.rect().height())
            
            smallest_item = layer_candidates[0]
            
            # 4. Bring smallest to front (Z=20) and push others back (Z=10)
            # This ensures 'super()' picks the smallest item as the target.
            for item in layer_candidates:
                item.setZValue(10) 
            smallest_item.setZValue(20)

        # --- STANDARD QT PROCESSING ---
        # Now that Z-Order is correct, Qt will handle the selection/drag logic for the top item.
        super().mousePressEvent(event)

        ### end smart sortng and proceed with the selected 

        # CASE A: User has clicked a Layer Box -> Select/Move/Resize
        sp_check = self.mapToScene(event.pos()) # Re-map for check
        item = self.scene.itemAt(sp_check, self.transform()) #reassigning 

        if isinstance(item, LayerRectItem):
            # Pass to LayerRectItem.mousePressEvent
            super().mousePressEvent(event)
            
            # Snapshot geometry for "geometry_changed" check later
            self._drag_start_geometry = {}
            for sel_item in self.scene.selectedItems():
                if isinstance(sel_item, LayerRectItem):
                    r = sel_item.rect()
                    abs_rect = sel_item.mapRectToScene(r)
                    safe_rect = self._get_safe_rect(abs_rect)
                    self._drag_start_geometry[sel_item.layer_id] = (
                        int(safe_rect.x()), int(safe_rect.y()), 
                        int(safe_rect.width()), int(safe_rect.height())
                    )
            return
        
        # Done handling click inside box 

        # CASE B: User clicked Background (or nothing) -> Start Drawing (adding layer)
        if event.button() == Qt.MouseButton.LeftButton:
            # Note: We do NOT call super() here to avoid rubber-band selection

            # First thing we check that user is not adding too many layers 
            # Count current LayerRectItems in the scene
            layer_count = sum(1 for item in self.scene.items() if isinstance(item, LayerRectItem))
            
            if layer_count >= self.MAX_LAYERS:
                # Optionally print or trigger a signal for the UI
                print(f"Layer limit reached: {layer_count}/5")
                self.layers_limit_reached.emit(5) 
                return # EXIT HERE: Do not create drawing_rect_item
            
            self.start_point = sp
            self.drawing_rect_item = QGraphicsRectItem()
            self.drawing_rect_item.setPen(QPen(Qt.GlobalColor.green, 2, Qt.PenStyle.DashLine))
            self.scene.addItem(self.drawing_rect_item)
            self.scene.clearSelection()

    def mouseMoveEvent(self, event):

        if self.items_hidden and not self._is_panning:
            return
        
        #  UPDATE CURSOR POSITION 
        if self.brush_active:
            scene_pos = self.mapToScene(event.pos())
            self.brush_cursor_item.setPos(scene_pos)
            self.viewport().setCursor(Qt.CursorShape.BlankCursor) # Ensure system cursor is gone
        
        
        # --- BRUSH DRAWING ---
        if self.brush_active and self.current_stroke_img and not self._is_panning:
            selected_items = self.scene.selectedItems()
            if selected_items and isinstance(selected_items[0], LayerRectItem):
                target_layer = selected_items[0]
                
                # Get new point in Layer Local Coords
                new_point = target_layer.mapFromScene(self.mapToScene(event.pos()))
                
                # Paint on QImage
                painter = QPainter(self.current_stroke_img)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Visual Color (Red for Add, White/Cyan for Erase just to see it)
                color = QColor("red") if self.brush_mode == 'add' else QColor("cyan")
                pen = QPen(color, self.brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                
                painter.drawLine(self.start_point, new_point)
                painter.end()
                
                # Update Start Point
                self.start_point = new_point
                
                # Update Visual Overlay (So user sees the stroke)
                # Note: We are overlaying the stroke on top of the existing mask
                target_layer.mask_item.setPixmap(QPixmap.fromImage(self.current_stroke_img))
                
            return # Stop processing (don't drag box)


        # 1. Pass event to Items (this triggers LayerRectItem.mouseMoveEvent)
        super().mouseMoveEvent(event)
        
        # 2. Handle Drawing (View Logic)
        if self.drawing_rect_item and self.start_point and not self._is_panning:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            # Visual Clamp
            clamped = self._get_safe_rect(rect)
            self.drawing_rect_item.setRect(clamped)

    # ###  RESET CURSOR ON LEAVE ###
    def leaveEvent(self, event):
        # When mouse leaves the widget, restore standard cursor so it isn't "missing" in the sidebar
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.brush_cursor_item.hide()
        super().leaveEvent(event)
    
    def enterEvent(self, event):
        # When mouse enters, if brush active, re-hide system cursor and show brush cursor
        if self.brush_active:
             self.viewport().setCursor(Qt.CursorShape.BlankCursor)
             self.brush_cursor_item.show()
        super().enterEvent(event)


    def mouseReleaseEvent(self, event):
        

        if event.button() == Qt.MouseButton.MiddleButton:
            if self.bg_item and self.original_bg_item:
                self.bg_item.setVisible(True)          # Restore Edited
                self.original_bg_item.setVisible(False) # Hide Original again
            return
        
        # 2. Block logic if layers are hidden
        # but allow release if panning
        if self.items_hidden and not self._is_panning:
            return
        
        # --- FINISH BRUSH STROKE ---
        if self.brush_active and self.current_stroke_img:
            selected_items = self.scene.selectedItems()
            if selected_items:
                lid = selected_items[0].layer_id
                
                # Emit the QImage stroke to Backend
                self.mask_stroke_finished.emit(lid, self.current_stroke_img, self.brush_mode)
            
            # Reset Scratchpad
            self.current_stroke_img = None
            self.start_point = None
            return # Stop here
        

        # 3. Pass to system (handles selection states)
        super().mouseReleaseEvent(event)
        
        # --- A. FINISH DRAWING (Creation) ---
        if self.drawing_rect_item:
            raw_rect = self.drawing_rect_item.rect()
            self.scene.removeItem(self.drawing_rect_item)
            self.drawing_rect_item = None
            self.start_point = None
            
            final_rect = self._get_safe_rect(raw_rect)
            if final_rect.width() > 10 and final_rect.height() > 10:
                self.geometry_created.emit(
                    int(final_rect.x()), int(final_rect.y()), 
                    int(final_rect.width()), int(final_rect.height())
                )
            return # Stop here
                
        # --- B. FINISH EDITING (Move/Resize) ---
        for item in self.scene.selectedItems():
            if isinstance(item, LayerRectItem):

                # do not bother if we are outside all layers
                # ie when mouse press has not set _drag_start_geometry at all 
                start_geo = self._drag_start_geometry.get(item.layer_id)
                if start_geo is None:
                    continue


                r = item.rect()
                abs_rect = item.mapRectToScene(r)
                safe_rect = self._get_safe_rect(abs_rect)
                
                current_geo = (
                    int(safe_rect.x()), int(safe_rect.y()), 
                    int(safe_rect.width()), int(safe_rect.height())
                )
                
                start_geo = self._drag_start_geometry.get(item.layer_id)
                if current_geo != start_geo:
                    self.geometry_changed.emit(
                        item.layer_id, 
                        current_geo[0], current_geo[1], 
                        current_geo[2], current_geo[3]
                    )
        
        self._drag_start_geometry = {}

    def keyPressEvent(self, event):

        #  Spacebar Panning ---
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if not self._is_panning:
                self._is_panning = True
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                # B. CRITICAL : Disable Item Interaction
                # This ensures the click goes to the "Hand", not the "Box".
                self.setInteractive(False)
            event.accept()
            return
        #  

        # DELETE Layer (but Block if hidden)
        if event.key() == Qt.Key.Key_Delete:
            if not self.items_hidden:
                for item in self.scene.selectedItems():
                    if isinstance(item, LayerRectItem):
                        self.layer_deleted.emit(item.layer_id)
        
        # HIDE UI (Always allow toggling)
        # we also  need to hide any signal that unselects curecnt layer 
        # else mainwindow will disable stuff 
        elif event.key() == Qt.Key.Key_H:

            self.toggle_overlay_visibility()
            
        # PEEK  ON '\' key (Always allow)
        # PEEK START (Backslash)
        elif event.key() == Qt.Key.Key_Backslash:
            if self.bg_item and self.original_bg_item:
                self.bg_item.setVisible(False)         # Hide Top
                self.original_bg_item.setVisible(True) # Show Bottom
        
        else:
            super().keyPressEvent(event)



    def keyReleaseEvent(self, event):

        # Spacebar Release ---
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self._is_panning:
                self._is_panning = False
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                
                # B. Restore Item Interaction
                self.setInteractive(True)
            event.accept()
            return
        #  
        # \ Key Release 
        if event.key() == Qt.Key.Key_Backslash:
            #print("going to show original : peek ")
            if self.bg_item and self.original_bg_item:
                #print("  peek should be ready")
                self.bg_item.setVisible(True)           # Restore Top
                self.original_bg_item.setVisible(False) # Hide Bottom
        
        super().keyReleaseEvent(event)

        # KeyRelease ends here 



    # # ============================================================
    # # ZOOM & PAN API (LIMITED)
    # # ============================================================
    
    

    # #### End zoom and pan ##

    # ============================================================
    # DRAG & DROP SUPPORT
    # ============================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Allow entry if it's a valid image file."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                path = urls[0].toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Crucial: QGraphicsView requires this to confirm drag position."""
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Extract path and signal the Main Window."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.file_dropped.emit(path) # <--- Send to Parent
            event.acceptProposedAction()



    
# ... (Imports and Class definitions remain identical up to ZOOM API) ...

    # ============================================================
    # ZOOM & PAN API (Dynamic Limits)
    # ============================================================
    
    # Absolute Hard Limits
    # We remove MIN_ZOOM constant because it is now dynamic
    MAX_ZOOM = 4.0

    def _get_current_scale(self):
        # m11() returns the horizontal scale factor of the transform matrix
        return self.transform().m11()

    def _get_fit_scale(self):
        """
        Calculates the scale factor required to fit the entire image 
        into the current viewport size.
        """
        if not self.bg_item: 
            return 1.0
            
        view_rect = self.viewport().rect()
        scene_rect = self.bg_item.boundingRect()
        
        if scene_rect.width() == 0 or scene_rect.height() == 0:
            return 1.0
            
        ratio_w = view_rect.width() / scene_rect.width()
        ratio_h = view_rect.height() / scene_rect.height()
        
        # We need the smaller ratio to ensure BOTH dimensions fit
        return min(ratio_w, ratio_h)

    def _apply_zoom(self, factor):
        """
        Helper to apply zoom with dynamic bounds checking.
        """
        current_scale = self._get_current_scale()
        
        # 1. Determine Dynamic Minimum
        # The floor is EITHER 75% OR the "Fit to Screen" size, whichever is SMALLER.
        # This prevents the "Blow Up" effect on large vertical images.
        fit_scale = self._get_fit_scale()
        min_allowed = min(0.75, fit_scale) 
        
        # Calculate where we would be if we applied the zoom
        future_scale = current_scale * factor
        
        # 2. Clamp Logic
        if future_scale < min_allowed:
            # Prevent zooming out past the limit
            # But allow snapping TO the limit if we are close
            factor = min_allowed / current_scale
            
        elif future_scale > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / current_scale
            
        # 3. Apply (only if meaningful)
        if abs(factor - 1.0) > 0.001:
            self.scale(factor, factor)
            
            # Emit the NEW scale (current * factor)
            self.zoom_changed.emit(self._get_current_scale())    

    def zoom_in(self):
        self._apply_zoom(1.25)

    def zoom_out(self):
        self._apply_zoom(0.8) # 1 / 1.25

    def zoom_reset(self):
        self.resetTransform()
        if self.bg_item:
            self.fitInView(self.bg_item, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Update the status bar with the new "Fit" scale
            self.zoom_changed.emit(self._get_current_scale())

    def wheelEvent(self, event):
        """Handle Mouse Wheel Zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            
            # Standard Step
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            if event.angleDelta().y() > 0:
                self._apply_zoom(zoom_in_factor)
            else:
                self._apply_zoom(zoom_out_factor)
            
            event.accept()
        else:
            super().wheelEvent(event)


    def _get_layer_count(self):
        """Counts how many LayerRectItems are currently in the scene.
           We use it to stop user from adding too many layers 
        """
        return sum(1 for item in self.scene.items() if isinstance(item, LayerRectItem))


            