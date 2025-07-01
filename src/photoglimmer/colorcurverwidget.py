import sys
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout, QHBoxLayout, QPushButton # Added layouts/button
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPalette
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
import math
from pympler import asizeof
# import copy # Needed for deep copying QPointF list during save/load if necessary
# Make sure QPointF and other Qt elements are available
# (Assuming they are imported correctly in the context where this class is used)


def  _catmull_rom_interpolate(p0, p1, p2, p3, t):
    # --- (Catmull-Rom implementation remains the same) ---
    t2 = t * t; t3 = t2 * t
    out_x = 0.5 * ((2 * p1.x()) + (-p0.x() + p2.x()) * t + (2 * p0.x() - 5 * p1.x() + 4 * p2.x() - p3.x()) * t2 + (-p0.x() + 3 * p1.x() - 3 * p2.x() + p3.x()) * t3)
    out_y = 0.5 * ((2 * p1.y()) + (-p0.y() + p2.y()) * t + (2 * p0.y() - 5 * p1.y() + 4 * p2.y() - p3.y()) * t2 + (-p0.y() + 3 * p1.y() - 3 * p2.y() + p3.y()) * t3)
    return QPointF(out_x, out_y)
# --- SmoothCurveWidget Class ---


class  SmoothCurveWidget(QWidget):
    curveChanged = Signal()
    CURVE_COLOR = QColor(171, 205, 239) #QColor(Qt.white)


    def  __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(256 + 20, 256 + 20)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._points = [QPointF(0, 0), QPointF(255, 255)]
        self._dragging_point_index = -1
        self._selected_point_index = -1
        self._point_radius = 5
        self._padding = 10
        self._spline_resolution = 10
        self._cached_lut = None # <-- ADDED: Cache for loaded LUT
        # create variables to help switch between bg and fg image 
        self._prev_state = None
        self._tmp_state = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Window, QColor(40, 40, 40))
        self.setPalette(pal)
        self.setFocusPolicy(Qt.StrongFocus)


    def  _invalidate_cache(self):
        if self._cached_lut is not None:
            self._cached_lut = None


    def  get_points(self):
        return list(self._points) 


    def  reset_curve(self, new_image=False):
        try:
            self._points = [QPointF(0, 0), QPointF(255, 255)]
            self._dragging_point_index = -1
            self._selected_point_index = -1
            self._invalidate_cache() 
            if new_image and (self._prev_state is not None):
                self._prev_state = None 
            if not new_image:
                self.curveChanged.emit()
            self.update()
        except Exception as e:
            print(f"Error in reset_curve: {e}")


    def  set_curve_to_lut_list(self, lut_list):
        if not isinstance(lut_list, (list, tuple)) or len(lut_list) != 256:
            print(f"Error: lut_list must be a list or tuple of 256 numbers. "
                  f"Received type: {type(lut_list)}, length: {len(lut_list) if isinstance(lut_list, (list, tuple)) else 'N/A'}")
            return


        def  generate_lut_from_points(points, size=256):
            local_lut = [0] * size
            if not points or len(points) < 2:
                 return [int(round(i * 255.0 / (size - 1))) for i in range(size)]
            dense_spline_points = self._generate_spline_points(points, max(self._spline_resolution * 2, 32))
            if not dense_spline_points or len(dense_spline_points) < 2:
                p_start, p_end = points[0], points[-1]
                for i in range(size):
                    x_target = i * 255.0 / (size - 1)
                    y = 0.0
                    if abs(p_end.x() - p_start.x()) < 1e-6: y = p_start.y()
                    else:
                        t = max(0.0, min(1.0, (x_target - p_start.x()) / (p_end.x() - p_start.x())))
                        y = p_start.y() + t * (p_end.y() - p_start.y())
                    local_lut[i] = max(0, min(255, int(round(y))))
                return local_lut
            current_segment_index = 0
            num_spline_points = len(dense_spline_points)
            for i in range(size):
                x_target = i * 255.0 / (size - 1)
                while current_segment_index < num_spline_points - 2 and                      x_target > dense_spline_points[current_segment_index + 1].x():
                    current_segment_index += 1
                p1 = dense_spline_points[current_segment_index]
                p2 = dense_spline_points[min(current_segment_index + 1, num_spline_points - 1)]
                y = 0.0
                dx = p2.x() - p1.x()
                if x_target <= p1.x(): y = p1.y()
                elif x_target >= p2.x(): y = p2.y()
                elif abs(dx) < 1e-6: y = (p1.y() + p2.y()) / 2.0
                else:
                    t = (x_target - p1.x()) / dx
                    y = p1.y() + t * (p2.y() - p1.y())
                local_lut[i] = max(0, min(255, int(round(y))))
            return local_lut
        clamped_lut = [max(0.0, min(255.0, float(val))) for val in lut_list]
        new_points = [QPointF(0.0, clamped_lut[0]), QPointF(255.0, clamped_lut[255])]
        max_control_points = 16
        max_iterations = max_control_points - 2
        error_threshold = 3.0
        for iteration in range(max_iterations):
            current_generated_lut = generate_lut_from_points(new_points)
            max_error = 0.0
            error_index = -1
            for i in range(1, 255):
                error = abs(clamped_lut[i] - current_generated_lut[i])
                if error > max_error:
                    max_error = error
                    error_index = i
            if max_error <= error_threshold: break
            if error_index == -1: break
            new_control_point = QPointF(float(error_index), clamped_lut[error_index])
            new_points.append(new_control_point)
            new_points.sort(key=lambda p: p.x())
            if len(new_points) >= max_control_points: break
        self._points = new_points
        self._dragging_point_index = -1
        self._selected_point_index = -1
        self._invalidate_cache() 
        self.curveChanged.emit()
        self.update()


    def  _generate_spline_points(self, points, steps_per_segment):
        if len(points) < 2: return []
        spline_points = []
        n = len(points)
        sorted_points = sorted(points, key=lambda p: p.x())
        if n == 2:
             p0, p1 = sorted_points[0], sorted_points[1]
             for i in range(steps_per_segment + 1):
                t = float(i) / steps_per_segment
                x = p0.x() + (p1.x() - p0.x()) * t
                y = p0.y() + (p1.y() - p0.y()) * t
                clamped_y = max(0.0, min(y, 255.0))
                spline_points.append(QPointF(x, clamped_y))
             return spline_points
        spline_points.append(sorted_points[0])
        for i in range(n - 1):
            p0 = sorted_points[max(0, i - 1)]
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]
            p3 = sorted_points[min(n - 1, i + 2)]
            for j in range(1, steps_per_segment + 1):
                t = float(j) / steps_per_segment
                ip = _catmull_rom_interpolate(p0, p1, p2, p3, t)
                clamped_x = max(p1.x(), min(ip.x(), p2.x()))
                clamped_y = max(0.0, min(ip.y(), 255.0))
                spline_points.append(QPointF(clamped_x, clamped_y))
        spline_points.sort(key=lambda p: p.x())
        unique_spline_points = []
        last_x = -1.0
        for pt in spline_points:
            if pt.x() > last_x + 1e-6 :
                 unique_spline_points.append(pt)
                 last_x = pt.x()
            elif not unique_spline_points:
                 unique_spline_points.append(pt)
                 last_x = pt.x()
            elif pt.x() >= 255.0 - 1e-6 and last_x < 255.0 - 1e-6:
                 if unique_spline_points and unique_spline_points[-1].x() < pt.x():
                     unique_spline_points[-1] = pt
                 elif not unique_spline_points:
                      unique_spline_points.append(pt)
                 last_x = pt.x()
        final_points = []
        if sorted_points[0].x() < 1e-6:
            first_ctrl_pt = sorted_points[0]
            if not unique_spline_points or unique_spline_points[0].x() > 1e-6:
                 final_points.append(QPointF(0.0, max(0.0, min(first_ctrl_pt.y(), 255.0))))
            elif unique_spline_points:
                 unique_spline_points[0].setY(max(0.0, min(first_ctrl_pt.y(), 255.0)))
        final_points.extend(unique_spline_points)
        if sorted_points[-1].x() > 255.0 - 1e-6:
            last_ctrl_pt = sorted_points[-1]
            if not final_points or final_points[-1].x() < 255.0 - 1e-6:
                 final_points.append(QPointF(255.0, max(0.0, min(last_ctrl_pt.y(), 255.0))))
            elif final_points:
                 final_points[-1].setX(255.0)
                 final_points[-1].setY(max(0.0, min(last_ctrl_pt.y(), 255.0)))
        unique_final_points = []
        last_x = -1.0
        for pt in sorted(final_points, key=lambda p: p.x()):
             if pt.x() > last_x + 1e-6:
                 unique_final_points.append(pt)
                 last_x = pt.x()
             elif not unique_final_points:
                 unique_final_points.append(pt)
                 last_x = pt.x()
             elif pt.x() >= 255.0 - 1e-6 and last_x < 255.0 - 1e-6:
                  if unique_final_points: unique_final_points[-1] = pt
                  else: unique_final_points.append(pt)
                  last_x = pt.x()
        return unique_final_points


    def  get_lut(self, size=256):
        if self._cached_lut is not None and size == 256:
            return list(self._cached_lut) 
        lut = [0] * size
        if not self._points:
             return [int(round(i * 255.0 / (size - 1))) for i in range(size)]
        if len(self._points) < 2:
            if self._points:
                 y_val = max(0.0, min(self._points[0].y(), 255.0))
                 lut = [int(round(y_val))] * size
                 if size == 256: self._cached_lut = list(lut) 
                 return lut
            else:
                 return [int(round(i * 255.0 / (size - 1))) for i in range(size)]
        dense_spline_points = self._generate_spline_points(self._points, max(self._spline_resolution * 2, 32))
        if not dense_spline_points or len(dense_spline_points) < 2:
            points = sorted(self._points, key=lambda p: p.x())
            p_start, p_end = points[0], points[-1]
            for i in range(size):
                 x_target = i * 255.0 / (size - 1)
                 y = 0.0
                 if abs(p_end.x() - p_start.x()) < 1e-6:
                     y = p_start.y()
                 else:
                     t = max(0.0, min(1.0, (x_target - p_start.x()) / (p_end.x() - p_start.x())))
                     y = p_start.y() + t * (p_end.y() - p_start.y())
                 lut[i] = max(0, min(255, int(round(y))))
            if size == 256: self._cached_lut = list(lut) 
            return lut
        current_segment_index = 0
        num_spline_points = len(dense_spline_points)
        for i in range(size):
            x_target = i * 255.0 / (size - 1)
            while current_segment_index < num_spline_points - 2 and                  x_target > dense_spline_points[current_segment_index + 1].x() + 1e-6:
                current_segment_index += 1
            p1 = dense_spline_points[current_segment_index]
            p2 = dense_spline_points[min(current_segment_index + 1, num_spline_points - 1)]
            y = 0.0
            dx = p2.x() - p1.x()
            if x_target <= p1.x() + 1e-6: y = p1.y()
            elif x_target >= p2.x() - 1e-6: y = p2.y()
            elif abs(dx) < 1e-6: y = (p1.y() + p2.y()) / 2.0
            else:
                t = (x_target - p1.x()) / dx
                t = max(0.0, min(1.0, t))
                y = p1.y() + t * (p2.y() - p1.y())
            lut[i] = max(0, min(255, int(round(y))))
        if size == 256:
            self._cached_lut = list(lut) 
        return lut


    def  save_state(self):
        try:
            control_points = [QPointF(p) for p in self._points] 
            current_lut = self.get_lut() 
            state = {
                'control_points': control_points,
                'lut': current_lut
            }
            s= asizeof.asizeof(state)/1e6
            return state
        except Exception as e:
            print(f"Error saving curve state: {e}")
            return None


    def  load_state(self, state_data):
        if not isinstance(state_data, dict):
            print("Error loading state: Input is not a dictionary.")
            return False
        if 'control_points' not in state_data or 'lut' not in state_data:
            print("Error loading state: Dictionary is missing required keys ('control_points', 'lut').")
            return False
        try:
            loaded_points = state_data['control_points']
            loaded_lut = state_data['lut']
            if not isinstance(loaded_points, list):
                 print("Error loading state: 'control_points' is not a list.")
                 return False
            if not all(isinstance(p, QPointF) for p in loaded_points):
                print("Error loading state: 'control_points' does not contain QPointF objects.")
                return False 
            if not isinstance(loaded_lut, list) or len(loaded_lut) != 256:
                print(f"Error loading state: 'lut' is not a list of 256 elements (found {len(loaded_lut)}).")
                return False
            if not all(isinstance(val, int) and 0 <= val <= 255 for val in loaded_lut):
                print("Error loading state: 'lut' contains invalid values (must be ints 0-255).")
                return False
            self._points = [QPointF(p) for p in loaded_points]
            self._cached_lut = list(loaded_lut) 
            self._dragging_point_index = -1
            self._selected_point_index = -1
            self._points.sort(key=lambda p: p.x())
            self.curveChanged.emit() 
            self.update() 
            return True
        except Exception as e:
            print(f"Error applying loaded state: {e}")
            return False


    def  toggle_curve_state(self):
        tmp_state= None
        if self._prev_state is not None:
            tmp_state= self._prev_state.copy()
        self._prev_state= self.save_state()
        if tmp_state is not None:
            self.load_state(tmp_state)
        else:
            self.reset_curve(new_image=False)        


    def  _get_curve_rect(self):
        return QRectF(self._padding, self._padding,
                      self.width() - 2 * self._padding,
                      self.height() - 2 * self._padding)


    def  _map_to_widget(self, logical_point):
        rect = self._get_curve_rect()
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
             return QPointF(self._padding, self.height() - self._padding)
        widget_x = rect.left() + (logical_point.x() / 255.0) * rect.width()
        widget_y = rect.bottom() - (logical_point.y() / 255.0) * rect.height()
        return QPointF(widget_x, widget_y)


    def  _map_from_widget(self, widget_point):
        rect = self._get_curve_rect()
        if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
             return QPointF(0, 0)
        clamped_x = max(rect.left(), min(widget_point.x(), rect.right()))
        clamped_y = max(rect.top(), min(widget_point.y(), rect.bottom()))
        logical_x = (clamped_x - rect.left()) / rect.width() * 255.0
        logical_y = (rect.bottom() - clamped_y) / rect.height() * 255.0
        logical_x = max(0.0, min(logical_x, 255.0))
        logical_y = max(0.0, min(logical_y, 255.0))
        return QPointF(logical_x, logical_y)


    def  _find_point_at(self, widget_pos):
        for i in range(len(self._points) - 1, -1, -1):
            point_widget_pos = self._map_to_widget(self._points[i])
            dist_sq = (widget_pos.x() - point_widget_pos.x())**2 + (widget_pos.y() - point_widget_pos.y())**2
            if dist_sq <= (self._point_radius * 1.5)**2:
                 return i
        return -1


    def  paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        curve_rect = self._get_curve_rect()
        if not curve_rect.isValid(): return
        grid_color = QColor(80, 80, 80)
        painter.setPen(QPen(grid_color, 0.5, Qt.SolidLine))
        grid_size = 4
        for i in range(1, grid_size):
            x = curve_rect.left() + curve_rect.width() * i / grid_size
            painter.drawLine(QPointF(x, curve_rect.top()), QPointF(x, curve_rect.bottom()))
            y = curve_rect.top() + curve_rect.height() * i / grid_size
            painter.drawLine(QPointF(curve_rect.left(), y), QPointF(curve_rect.right(), y))
        painter.setPen(QPen(grid_color.lighter(120), 1))
        painter.drawRect(curve_rect)
        if len(self._points) >= 2:
            spline_logical_points = self._generate_spline_points(self._points, self._spline_resolution)
            if spline_logical_points:
                path = QPainterPath()
                path.moveTo(self._map_to_widget(spline_logical_points[0]))
                for pt_logical in spline_logical_points[1:]:
                    path.lineTo(self._map_to_widget(pt_logical))
                painter.setPen(QPen(self.CURVE_COLOR, 1.5, Qt.SolidLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
        pen = QPen(self.CURVE_COLOR, 1.5, Qt.SolidLine)
        painter.setPen(pen)
        brush_color = QColor(self.CURVE_COLOR)
        painter.setBrush(QBrush(brush_color))
        radius = self._point_radius
        outline_pen = QPen(self.CURVE_COLOR.darker(150), 1)
        for i, point in enumerate(self._points):
            widget_p = self._map_to_widget(point)
            if i == self._dragging_point_index or (i == self._selected_point_index and self._dragging_point_index == -1):
                painter.setPen(QPen(Qt.yellow, 1.5))
                painter.setBrush(QBrush(Qt.yellow))
                painter.drawEllipse(widget_p, radius, radius)
            else:
                painter.setPen(outline_pen)
                painter.setBrush(QBrush(self.CURVE_COLOR))
                painter.drawEllipse(widget_p, radius - 1, radius - 1)


    def  mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            widget_pos = event.pos()
            curve_rect = self._get_curve_rect()
            point_added = False 
            if curve_rect.contains(widget_pos):
                clicked_point_index = self._find_point_at(widget_pos)
                if clicked_point_index != -1:
                    self._dragging_point_index = clicked_point_index
                    self._selected_point_index = clicked_point_index
                else:
                    logical_pos = self._map_from_widget(widget_pos)
                    if 0 <= logical_pos.x() <= 255 and 0 <= logical_pos.y() <= 255:
                        new_point = QPointF(logical_pos)
                        self._points.append(new_point)
                        self._points.sort(key=lambda p: p.x())
                        try:
                            new_index = self._points.index(new_point)
                            self._dragging_point_index = new_index
                            self._selected_point_index = new_index
                            point_added = True 
                        except ValueError:
                            print("Warning: Newly added point not found after sorting.")
                            self._dragging_point_index = -1
                            self._selected_point_index = -1
            else:
                self._selected_point_index = -1
            if point_added:
                 self._invalidate_cache() 
                 self.curveChanged.emit() 
            self.update()


    def  mouseMoveEvent(self, event):
        if self._dragging_point_index != -1 and (event.buttons() & Qt.LeftButton):
            if self._dragging_point_index >= len(self._points):
                 self._dragging_point_index = -1
                 self.update()
                 return
            try:
                 point_being_dragged = self._points[self._dragging_point_index]
            except IndexError:
                 self._dragging_point_index = -1
                 self.update()
                 return
            can_move_x = True
            is_start_or_end = False
            if self._dragging_point_index == 0 or self._dragging_point_index == len(self._points) - 1:
                can_move_x = False
                is_start_or_end = True
            widget_pos = event.pos()
            new_logical_pos = self._map_from_widget(widget_pos)
            final_x = new_logical_pos.x()
            if not can_move_x:
                final_x = point_being_dragged.x()
            elif not is_start_or_end:
                prev_x = self._points[self._dragging_point_index - 1].x()
                next_x = self._points[self._dragging_point_index + 1].x()
                epsilon = 0.01
                final_x = max(prev_x + epsilon, min(new_logical_pos.x(), next_x - epsilon))
                final_x = max(0.0 + epsilon, min(final_x, 255.0 - epsilon))
            point_being_dragged.setX(final_x)
            point_being_dragged.setY(new_logical_pos.y())
            self._points.sort(key=lambda p: p.x())
            try:
                self._dragging_point_index = self._points.index(point_being_dragged)
                self._selected_point_index = self._dragging_point_index
            except ValueError:
                self._dragging_point_index = -1
                self._selected_point_index = -1
            self.update()


    def  mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging_point_index != -1:
                current_point_ref = None
                if self._dragging_point_index < len(self._points):
                    current_point_ref = self._points[self._dragging_point_index]
                self._dragging_point_index = -1
                self._points.sort(key=lambda p: p.x())
                if current_point_ref:
                     try:
                         self._selected_point_index = self._points.index(current_point_ref)
                     except ValueError:
                          self._selected_point_index = -1
                else:
                    self._selected_point_index = -1
                self._invalidate_cache() 
                self.curveChanged.emit() 
                self.update()


    def  keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Delete or key == Qt.Key_Backspace:
             if self._selected_point_index > 0 and self._selected_point_index < len(self._points) - 1:
                 del self._points[self._selected_point_index]
                 self._selected_point_index = -1
                 self._dragging_point_index = -1
                 self._invalidate_cache() 
                 self.curveChanged.emit()
                 self.update()
        else:
             super().keyPressEvent(event)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    curve_widget = SmoothCurveWidget()
    layout.addWidget(curve_widget)
    button_layout = QHBoxLayout()
    layout.addLayout(button_layout)
    reset_button = QPushButton("Reset Curve")
    reset_button.clicked.connect(curve_widget.reset_curve)
    button_layout.addWidget(reset_button)
    inverse_lut = [255 - i for i in range(256)]
    gamma_lut = [int(round(pow(i / 255.0, 1/2.2) * 255.0)) for i in range(256)]
    s_curve_lut = [int(round(255 * (0.5 * (math.sin((i / 255.0 - 0.5) * math.pi) + 1)))) for i in range(256)]
    inverse_button = QPushButton("Set Inverse")
    inverse_button.clicked.connect(lambda: curve_widget.set_curve_to_lut_list(inverse_lut))
    button_layout.addWidget(inverse_button)
    gamma_button = QPushButton("Set Gamma 2.2")
    gamma_button.clicked.connect(lambda: curve_widget.set_curve_to_lut_list(gamma_lut))
    button_layout.addWidget(gamma_button)
    s_curve_button = QPushButton("Set S-Curve")
    s_curve_button.clicked.connect(lambda: curve_widget.set_curve_to_lut_list(s_curve_lut))
    button_layout.addWidget(s_curve_button)
    save_load_layout = QHBoxLayout()
    layout.addLayout(save_load_layout)
    saved_curve_state = None


    def  save_current_state():
        global saved_curve_state
        saved_curve_state = curve_widget.save_state()
        if not saved_curve_state:
            print("Failed to save curve state.")


    def  load_saved_state():
        global saved_curve_state
        if saved_curve_state:
            success = curve_widget.load_state(saved_curve_state)
            if not success:
                print("Failed to load curve state.")
        else:
            print("No curve state saved yet.")
    save_button = QPushButton("Save State")
    save_button.clicked.connect(save_current_state)
    save_load_layout.addWidget(save_button)
    load_button = QPushButton("Load State")
    load_button.clicked.connect(load_saved_state)
    save_load_layout.addWidget(load_button)
    print_lut_button = QPushButton("Print Current LUT")


    def  print_current_lut():
        print("--- Getting LUT ---")
        is_cached_before = curve_widget._cached_lut is not None
        print(f"Cache valid before get_lut(): {is_cached_before}")
        lut = curve_widget.get_lut()
        is_cached_after = curve_widget._cached_lut is not None
        print(f"Cache valid after get_lut(): {is_cached_after}")
        print(f"Current LUT ({len(lut)} points): {lut[:10]}...{lut[-10:]}")
        print("-" * 20)
    print_lut_button.clicked.connect(print_current_lut)
    save_load_layout.addWidget(print_lut_button)
    window.setWindowTitle("Smooth Curve Widget Test (Save/Load)")
    window.setGeometry(100, 100, 500, 500) 
    window.show()
    sys.exit(app.exec_())