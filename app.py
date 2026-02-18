import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QVBoxLayout, QGridLayout, QLabel,
                             QDialog, QDialogButtonBox, QLineEdit,
                             QPlainTextEdit, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QAction
from pynput import keyboard

# --- Worker Thread for Input Listening ---
class KeyboardWorker(QObject):
    """
    Runs in a background thread to listen for global key events
    so the GUI doesn't freeze.
    """
    key_pressed = pyqtSignal(str)
    key_released = pyqtSignal(str)

    def start_listening(self):
        # We use pynput's listener
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        key_name = self.get_key_name(key)
        self.key_pressed.emit(key_name)

    def on_release(self, key):
        key_name = self.get_key_name(key)
        self.key_released.emit(key_name)

    def get_key_name(self, key):
        """Normalize pynput key objects to string identifiers."""
        if hasattr(key, 'vk') and key.vk is not None:
            # Numpad 0-9 (VK 96-105)
            if 96 <= key.vk <= 105:
                return f"NUM_{key.vk - 96}"
            # Numpad Symbols
            if key.vk == 106: return "NUM_*"
            if key.vk == 107: return "NUM_+"
            if key.vk == 109: return "NUM_-"
            if key.vk == 110: return "NUM_."
            if key.vk == 111: return "NUM_/"

        if hasattr(key, 'char') and key.char:
            return key.char.upper()
        elif hasattr(key, 'name'):
            # Maps Key.space to "SPACE", Key.enter to "ENTER", etc.
            return key.name.upper()
        else:
            return str(key)

# --- Custom UI Widget for a Single Key ---
class KeyWidget(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.default_style = """
            background-color: #2d2d2d;
            color: #ffffff;
            border-radius: 6px;
            border: 1px solid #3e3e3e;
        """
        self.active_style = """
            background-color: #0078d4; 
            color: #ffffff;
            border-radius: 6px;
            border: 2px solid #60cdff;
        """
        self.setStyleSheet(self.default_style)
        self.setFixedSize(50, 50) # Default size
        self.draggable = False
        self._drag_start_pos = None
        self.on_drag_finished = None

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.draggable and self._drag_start_pos:
            self.move(self.pos() + event.pos() - self._drag_start_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.draggable:
            self._drag_start_pos = None
            if self.on_drag_finished:
                self.on_drag_finished()
        super().mouseReleaseEvent(event)

    def animate_press(self):
        self.setStyleSheet(self.active_style)

    def animate_release(self):
        self.setStyleSheet(self.default_style)

# --- Main Application Window ---
class KeyboardVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keystroke Visualizer")
        self.settings_file = "user_settings.json"
        self.setGeometry(100, 100, 1350, 450)
        
        # Set window background to dark (Win 11 style)
        self.setStyleSheet("background-color: #1e1e1e;")

        # Main container
        container = QWidget()
        self.setCentralWidget(container)
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Dictionary to store references to key widgets: {'A': widget_object}
        self.key_widgets = {}
        
        # Define Full Layout Data
        self.full_layout_data = [
            # Row 0 (Function Keys)
            ('ESC', 0, 0, 1, 1), 
            ('F1', 0, 2, 1, 1), ('F2', 0, 3, 1, 1), ('F3', 0, 4, 1, 1), ('F4', 0, 5, 1, 1),
            ('F5', 0, 6, 1, 1), ('F6', 0, 7, 1, 1), ('F7', 0, 8, 1, 1), ('F8', 0, 9, 1, 1),
            ('F9', 0, 10, 1, 1), ('F10', 0, 11, 1, 1), ('F11', 0, 12, 1, 1), ('F12', 0, 13, 1, 1),
            ('PRTSC', 0, 15, 1, 1), ('SCRLK', 0, 16, 1, 1), ('PAUSE', 0, 17, 1, 1),

            # Row 1 (Numbers)
            ('`', 1, 0, 1, 1), ('1', 1, 1, 1, 1), ('2', 1, 2, 1, 1), ('3', 1, 3, 1, 1), 
            ('4', 1, 4, 1, 1), ('5', 1, 5, 1, 1), ('6', 1, 6, 1, 1), ('7', 1, 7, 1, 1), 
            ('8', 1, 8, 1, 1), ('9', 1, 9, 1, 1), ('0', 1, 10, 1, 1), ('-', 1, 11, 1, 1), 
            ('=', 1, 12, 1, 1), ('BACKSPACE', 1, 13, 1, 2),
            ('INS', 1, 15, 1, 1), ('HOME', 1, 16, 1, 1), ('PGUP', 1, 17, 1, 1),
            ('NUM_LOCK', 1, 19, 1, 1), ('NUM_/', 1, 20, 1, 1), ('NUM_*', 1, 21, 1, 1), ('NUM_-', 1, 22, 1, 1),
            
            # Row 2
            ('TAB', 2, 0, 1, 2), ('Q', 2, 2, 1, 1), ('W', 2, 3, 1, 1), ('E', 2, 4, 1, 1), 
            ('R', 2, 5, 1, 1), ('T', 2, 6, 1, 1), ('Y', 2, 7, 1, 1), ('U', 2, 8, 1, 1), 
            ('I', 2, 9, 1, 1), ('O', 2, 10, 1, 1), ('P', 2, 11, 1, 1), ('[', 2, 12, 1, 1), 
            (']', 2, 13, 1, 1), ('\\', 2, 14, 1, 1),
            ('DEL', 2, 15, 1, 1), ('END', 2, 16, 1, 1), ('PGDN', 2, 17, 1, 1),
            ('NUM_7', 2, 19, 1, 1), ('NUM_8', 2, 20, 1, 1), ('NUM_9', 2, 21, 1, 1), ('NUM_+', 2, 22, 2, 1),

            # Row 3
            ('CAPS_LOCK', 3, 0, 1, 2), ('A', 3, 2, 1, 1), ('S', 3, 3, 1, 1), ('D', 3, 4, 1, 1), 
            ('F', 3, 5, 1, 1), ('G', 3, 6, 1, 1), ('H', 3, 7, 1, 1), ('J', 3, 8, 1, 1), 
            ('K', 3, 9, 1, 1), ('L', 3, 10, 1, 1), (';', 3, 11, 1, 1), ("'", 3, 12, 1, 1), 
            ('ENTER', 3, 13, 1, 2),
            ('NUM_4', 3, 19, 1, 1), ('NUM_5', 3, 20, 1, 1), ('NUM_6', 3, 21, 1, 1),

            # Row 4
            ('SHIFT', 4, 0, 1, 3), ('Z', 4, 3, 1, 1), ('X', 4, 4, 1, 1), ('C', 4, 5, 1, 1), 
            ('V', 4, 6, 1, 1), ('B', 4, 7, 1, 1), ('N', 4, 8, 1, 1), ('M', 4, 9, 1, 1), 
            (',', 4, 10, 1, 1), ('.', 4, 11, 1, 1), ('/', 4, 12, 1, 1), ('SHIFT_R', 4, 13, 1, 2),
            ('UP', 4, 16, 1, 1),
            ('NUM_1', 4, 19, 1, 1), ('NUM_2', 4, 20, 1, 1), ('NUM_3', 4, 21, 1, 1), ('NUM_ENTER', 4, 22, 2, 1),

            # Row 5
            ('CTRL', 5, 0, 1, 2), ('CMD', 5, 2, 1, 1), ('ALT', 5, 3, 1, 1), 
            ('SPACE', 5, 4, 1, 7), 
            ('ALT_R', 5, 11, 1, 1), ('FN', 5, 12, 1, 1), ('CTRL_R', 5, 13, 1, 2),
            ('LEFT', 5, 15, 1, 1), ('DOWN', 5, 16, 1, 1), ('RIGHT', 5, 17, 1, 1),
            ('NUM_0', 5, 19, 1, 2), ('NUM_.', 5, 21, 1, 1)
        ]

        self.templates = {
            "Full Keyboard": self.full_layout_data,
            "WASD + Arrows": [
                ('A', 0, 0, 1, 1), ('S', 0, 1, 1, 1), ('D', 0, 2, 1, 1), ('F', 0, 3, 1, 1),
                ('Z', 1, 0, 1, 1), ('X', 1, 1, 1, 1), ('C', 1, 2, 1, 1), ('V', 1, 3, 1, 1),
                ('UP', 3, 1, 1, 1),
                ('LEFT', 4, 0, 1, 1), ('DOWN', 4, 1, 1, 1), ('RIGHT', 4, 2, 1, 1)
            ]
        }
        self.current_template = "Full Keyboard"

        # Setup Menu
        self.init_menu()
        
        # Load settings and then draw UI
        self.load_settings()
        self.init_keyboard_ui()

        # Setup Input Listening Thread
        self.thread = QThread()
        self.worker = KeyboardWorker()
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.start_listening)
        self.worker.key_pressed.connect(self.handle_key_press)
        self.worker.key_released.connect(self.handle_key_release)
        
        self.thread.start()

    def init_menu(self):
        """Initialize the menu bar with settings."""
        menu_bar = self.menuBar()
        # Style the menu to match the dark theme
        menu_bar.setStyleSheet("""
            QMenuBar { background-color: #2d2d2d; color: #ffffff; }
            QMenuBar::item:selected { background-color: #3e3e3e; }
            QMenu { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e3e; }
            QMenu::item:selected { background-color: #0078d4; }
        """)
        
        settings_menu = menu_bar.addMenu("Settings")
        
        self.always_on_top_action = QAction("Always on Top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.triggered.connect(self.toggle_always_on_top)
        settings_menu.addAction(self.always_on_top_action)

        self.view_menu = menu_bar.addMenu("View")
        self.refresh_view_menu()

    def refresh_view_menu(self):
        self.view_menu.clear()
        for name in self.templates:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self.change_view_mode(n))
            self.view_menu.addAction(action)
        
        self.view_menu.addSeparator()
        add_action = QAction("Add Custom Template...", self)
        add_action.triggered.connect(self.open_add_template_dialog)
        self.view_menu.addAction(add_action)

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
        
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                
            if "custom_templates" in data:
                for name, layout in data["custom_templates"].items():
                    # Convert lists back to tuples
                    self.templates[name] = [tuple(item) for item in layout]
            
            if "current_template" in data and data["current_template"] in self.templates:
                self.current_template = data["current_template"]
                
            if "always_on_top" in data:
                self.always_on_top_action.setChecked(data["always_on_top"])
                self.toggle_always_on_top(data["always_on_top"])
            
            self.refresh_view_menu()
                
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        data = {
            "current_template": self.current_template,
            "always_on_top": self.always_on_top_action.isChecked(),
            "custom_templates": {}
        }
        
        for name, layout in self.templates.items():
            if name != "Full Keyboard":
                data["custom_templates"][name] = layout
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def open_add_template_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Template")
        dialog.resize(400, 300)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Template Name:"))
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        layout.addWidget(QLabel("Keys to Include (comma separated):\n(e.g., Z=JUMP, X=SHOOT, SPACE, ENTER)"))
        keys_input = QPlainTextEdit()
        layout.addWidget(keys_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            keys_text = keys_input.toPlainText()
            if name and keys_text:
                self.create_custom_template(name, keys_text)

    def create_custom_template(self, name, keys_text):
        wanted_items = {}
        for item in keys_text.split(','):
            item = item.strip()
            if not item: continue
            if '=' in item:
                k, v = item.split('=', 1)
                wanted_items[k.strip().upper()] = v.strip()
            else:
                wanted_items[item.strip().upper()] = None

        found_keys = []
        
        for key_def in self.full_layout_data:
            key_id = key_def[0]
            
            alias = None
            is_match = False
            
            if key_id in wanted_items:
                is_match = True
                alias = wanted_items[key_id]
            elif key_id.startswith("NUM_") and key_id.replace("NUM_", "") in wanted_items:
                is_match = True
                alias = wanted_items[key_id.replace("NUM_", "")]
            
            if is_match:
                new_def = list(key_def)
                if alias:
                    new_def.append(alias)
                found_keys.append(tuple(new_def))

        if not found_keys:
            QMessageBox.warning(self, "Error", "No valid keys found in selection.")
            return

        min_row = min(k[1] for k in found_keys)
        min_col = min(k[2] for k in found_keys)
        
        final_layout = []
        for k in found_keys:
            # k is (ID, row, col, rspan, cspan, [alias])
            item = list(k)
            item[1] -= min_row
            item[2] -= min_col
            final_layout.append(tuple(item))
        
        self.templates[name] = final_layout
        self.refresh_view_menu()
        self.change_view_mode(name)

    def toggle_always_on_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.save_settings()

    def change_view_mode(self, mode):
        self.current_template = mode
        self.init_keyboard_ui()
        self.save_settings()

    def init_keyboard_ui(self):
        """Defines the layout of the keyboard."""
        # Clear existing layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    widget_item = item.layout().takeAt(0)
                    if widget_item.widget():
                        widget_item.widget().deleteLater()
                item.layout().deleteLater()
        self.key_widgets.clear()

        keys_layout = self.templates.get(self.current_template, [])

        # Container for keys
        self.board = QWidget()
        self.main_layout.addWidget(self.board)
        
        is_full = (self.current_template == "Full Keyboard")
        
        # Calculate dynamic size
        if keys_layout:
            max_row = max(k[1] + k[3] for k in keys_layout)
            max_col = max(k[2] + k[4] for k in keys_layout)
            # Approx 55px per unit + margins
            board_w = int(max_col * 55)
            board_h = int(max_row * 55)
            self.resize(board_w + 50, board_h + 50)
            
            if not is_full:
                self.board.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.board.setStyleSheet("background-color: #252525; border: 1px dashed #3e3e3e; border-radius: 5px;")

        grid = None
        if is_full:
            self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid = QGridLayout(self.board)
            grid.setSpacing(5)
            grid.setContentsMargins(0, 0, 0, 0)
        else:
            self.main_layout.setAlignment(Qt.AlignmentFlag(0))

        for key_info in keys_layout:
            key_id = key_info[0]
            row = key_info[1]
            col = key_info[2]
            r_span = key_info[3]
            c_span = key_info[4]
            
            label_text = key_id
            
            # Check for custom alias (6th element)
            if len(key_info) > 5:
                label_text = key_info[5]
            # Strip NUM_ prefix for display, but keep key_id for lookup
            elif key_id.startswith("NUM_") and key_id != "NUM_LOCK":
                label_text = key_id.replace("NUM_", "")
            
            key_widget = KeyWidget(label_text)
            
            # Adjust width for special keys
            if c_span > 1:
                key_widget.setFixedWidth(50 * c_span + (5 * (c_span - 1)))
            
            if is_full:
                grid.addWidget(key_widget, row, col, r_span, c_span)
            else:
                key_widget.setParent(self.board)
                key_widget.draggable = True
                key_widget.on_drag_finished = self.update_board_min_size
                # Calculate absolute position (50px size + 5px gap)
                key_widget.move(int(col * 55), int(row * 55))
                key_widget.show()
            
            # Map the label to the widget for lookup later
            # Use a list to support multiple keys with same label (e.g. '7' and Numpad '7')
            if key_id not in self.key_widgets:
                self.key_widgets[key_id] = []
            self.key_widgets[key_id].append(key_widget)
            
        if not is_full:
            self.update_board_min_size()

    def update_board_min_size(self):
        if not hasattr(self, 'board') or not self.board:
            return
        
        max_x = 0
        max_y = 0
        
        for child in self.board.children():
            if isinstance(child, QWidget) and child.isVisible():
                geo = child.geometry()
                right = geo.x() + geo.width()
                bottom = geo.y() + geo.height()
                if right > max_x: max_x = right
                if bottom > max_y: max_y = bottom
        
        # Add a small margin
        self.board.setMinimumSize(max_x + 20, max_y + 20)

        # Update template data if in custom mode to persist dragged positions
        if self.current_template != "Full Keyboard":
            current_layout = self.templates.get(self.current_template, [])
            new_layout = []
            
            # Use iterators to handle duplicate keys correctly
            widget_iters = {k: iter(v) for k, v in self.key_widgets.items()}
            
            for item in current_layout:
                key_id = item[0]
                if key_id in widget_iters:
                    try:
                        widget = next(widget_iters[key_id])
                        # Convert pixel position back to grid units (float)
                        new_col = widget.x() / 55.0
                        new_row = widget.y() / 55.0
                        new_item = list(item)
                        new_item[1] = new_row
                        new_item[2] = new_col
                        new_layout.append(tuple(new_item))
                    except StopIteration:
                        new_layout.append(item)
                else:
                    new_layout.append(item)
            
            self.templates[self.current_template] = new_layout
            self.save_settings()

    def handle_key_press(self, key_name):
        """Slot to handle key press signal."""
        # Handle specific mappings from pynput to our UI labels
        target = self.map_pynput_to_ui(key_name)
        if target in self.key_widgets:
            for widget in self.key_widgets[target]:
                widget.animate_press()

    def handle_key_release(self, key_name):
        """Slot to handle key release signal."""
        target = self.map_pynput_to_ui(key_name)
        if target in self.key_widgets:
            for widget in self.key_widgets[target]:
                widget.animate_release()

    def map_pynput_to_ui(self, key_name):
        """Helper to map pynput names to our UI labels."""
        # Common mismatches
        mapping = {
            "~": "`",
            "SHIFT": "SHIFT",
            "SHIFT_L": "SHIFT",
            "SHIFT_R": "SHIFT_R",
            "CTRL_L": "CTRL",
            "CTRL_R": "CTRL_R",
            "ALT_L": "ALT",
            "ALT_GR": "ALT_R",
            "CAPS_LOCK": "CAPS_LOCK",
            "BACKSPACE": "BACKSPACE",
            "ENTER": "ENTER",
            "SPACE": "SPACE",
            "TAB": "TAB",
            "ESC": "ESC",
            "CMD": "CMD",
            "CMD_L": "CMD",
            "CMD_R": "CMD",
            "PRINT_SCREEN": "PRTSC",
            "SCROLL_LOCK": "SCRLK",
            "PAUSE": "PAUSE",
            "INSERT": "INS",
            "HOME": "HOME",
            "PAGE_UP": "PGUP",
            "DELETE": "DEL",
            "END": "END",
            "PAGE_DOWN": "PGDN",
            "UP": "UP",
            "LEFT": "LEFT",
            "DOWN": "DOWN",
            "RIGHT": "RIGHT",
            "NUM_LOCK": "NUM_LOCK"
        }
        
        # Check direct match
        if key_name in self.key_widgets:
            return key_name
        
        # Check mapped match
        if key_name in mapping:
            return mapping[key_name]
            
        # Check if it's a raw key like "KEY.SHIFT" that needs stripping
        clean_name = key_name.replace("KEY.", "")
        if clean_name in self.key_widgets:
            return clean_name
            
        return key_name

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KeyboardVisualizer()
    window.show()
    sys.exit(app.exec())
