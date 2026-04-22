import sys
import os
import threading
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QLineEdit, QListWidget, QSystemTrayIcon, QMenu
)

from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Qt

from watcher import start_watching


class SmartSorterUI(QWidget):

    log_signal = Signal(str)

    def __init__(self):
        super().__init__()

        self.log_signal.connect(self.log)

        self.setWindowTitle("SmartSorter")
        self.setMinimumSize(950, 650)

        self.root = QHBoxLayout()

        # ================= LEFT PANEL =================
        self.left = QVBoxLayout()
        self.left.addSpacing(40)

        ascii_logo = r"""
 $$$$$$\                       $$\     $$\      $$\           
$$  __$$\                      $$ |    $$$\    $$$ |          
$$ /  \__| $$$$$$\   $$$$$$\ $$$$$$\   $$$$\  $$$$ | $$$$$$\  
\$$$$$$\  $$  __$$\ $$  __$$\\_$$  _|  $$\$$\$$ $$ |$$  __$$\ 
 \____$$\ $$ /  $$ |$$ |  \__| $$ |    $$ \$$$  $$ |$$$$$$$$ |
$$\   $$ |$$ |  $$ |$$ |       $$ |$$\ $$ |\$  /$$ |$$   ____|
\$$$$$$  |\$$$$$$  |$$ |       \$$$$  |$$ | \_/ $$ |\$$$$$$$\ 
 \______/  \______/ \__|        \____/ \__|     \__| \_______|
"""

        logo = QLabel(ascii_logo)
        logo.setAlignment(Qt.AlignLeft)
        self.left.addWidget(logo)

        subtitle = QLabel("Smart File Sorting System")
        subtitle.setAlignment(Qt.AlignCenter)
        self.left.addWidget(subtitle)

        self.left.addSpacing(10)

        separator = QLabel("═════════════  SORT ENGINE  ═════════════")
        separator.setAlignment(Qt.AlignCenter)
        self.left.addWidget(separator)

        self.left.addSpacing(25)

        # BUTTONS
        self.select_btn = QPushButton("📁 Select Folder")
        self.select_btn.clicked.connect(self.select_folder)

        self.start_btn = QPushButton("🚀 START")
        self.start_btn.clicked.connect(self.start_sorting)

        self.stop_btn = QPushButton("🛑 STOP")
        self.stop_btn.clicked.connect(self.stop_sorting)

        self.start_btn.setStyleSheet("""
            border: 2px solid #22c55e;
            background-color: #022c22;
            font-weight: bold;
        """)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)

        self.left.addWidget(self.select_btn)
        self.left.addLayout(btn_row)

        self.left.addSpacing(15)

        # RULE INPUT
        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("Rule name (e.g. Matematika)")
        self.left.addWidget(self.rule_name)

        self.rule_keywords = QLineEdit()
        self.rule_keywords.setPlaceholderText("Keywords (comma separated)")
        self.left.addWidget(self.rule_keywords)

        self.rule_path = QLineEdit()
        self.rule_path.setPlaceholderText("Target folder (full path!)")
        self.left.addWidget(self.rule_path)

        self.left.addSpacing(10)

        self.add_btn = QPushButton("➕ Add / Save rule")
        self.edit_btn = QPushButton("✏️ Edit selected rule")
        self.delete_btn = QPushButton("🗑 Delete rule")

        self.add_btn.clicked.connect(self.add_rule)
        self.edit_btn.clicked.connect(self.edit_rule)
        self.delete_btn.clicked.connect(self.delete_rule)

        self.left.addWidget(self.add_btn)
        self.left.addWidget(self.edit_btn)
        self.left.addWidget(self.delete_btn)

        self.left.addStretch(1)

        # ================= RIGHT PANEL =================
        self.right = QVBoxLayout()

        self.status = QLabel("🔴 Stopped")
        self.right.addWidget(self.status)

        self.folder = QLabel("📁 -")
        self.right.addWidget(self.folder)

        self.count = QLabel("📦 0")
        self.right.addWidget(self.count)

        self.last = QLabel("⚡ -")
        self.right.addWidget(self.last)

        self.right.addWidget(QLabel("📂 Rules"))

        self.rules_list = QListWidget()
        self.rules_list.itemDoubleClicked.connect(self.load_rule_to_inputs)
        self.right.addWidget(self.rules_list)

        # TOGGLE
        self.view_mode = "log"

        toggle_layout = QHBoxLayout()

        self.log_btn = QPushButton("LOG")
        self.history_btn = QPushButton("HISTORY")

        self.log_btn.clicked.connect(self.show_log)
        self.history_btn.clicked.connect(self.show_history)

        toggle_layout.addWidget(self.log_btn)
        toggle_layout.addWidget(self.history_btn)

        self.right.addLayout(toggle_layout)

        # LOG BOX
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.right.addWidget(self.log_box)

        self.root.addLayout(self.left, 35)
        self.root.addLayout(self.right, 65)

        self.setLayout(self.root)

        # ================= DATA =================
        self.config = {
            "watch_folder": "",
            "rules": []
        }

        self.running = False
        self.edit_index = -1

        # ================= TRAY =================
        self.tray = QSystemTrayIcon(self)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.tray.setIcon(QIcon(icon_path))

        menu = QMenu()
        menu.addAction("Open", self.show)
        menu.addAction("Exit", self.exit_app)

        self.tray.setContextMenu(menu)
        self.tray.show()

        # ================= LOAD =================
        self.load_config()
        self.refresh_rules()

        # ================= STYLE =================
        self.setStyleSheet("""
        QWidget {
            background-color: #020617;
            color: #22c55e;
            font-family: Consolas;
        }

        QPushButton {
            border: 1px solid #22c55e;
            padding: 7px;
            background-color: transparent;
        }

        QPushButton:hover {
            background-color: #22c55e;
            color: black;
        }

        QTextEdit, QLineEdit, QListWidget {
            background-color: black;
            border: 1px solid #22c55e;
        }
        """)

    # ================= LOG =================
    def log(self, msg):
        if self.view_mode == "log":
            self.log_box.append(msg)
        print(msg)

    def thread_log(self, msg):
        self.log_signal.emit(msg)

    # ================= HISTORY =================
    def add_to_history(self, file, destination):

        entry = {
            "file": file,
            "destination": destination,
            "time": datetime.now().strftime("%H:%M:%S")
        }

        path = self.get_app_path("history.json")

        history = []

        if os.path.exists(path):
            with open(path, "r") as f:
                history = json.load(f)

        history.append(entry)
        history = history[-50:]

        with open(path, "w") as f:
            json.dump(history, f, indent=4)

    def refresh_history(self):
        self.log_box.clear()

        if not os.path.exists(self.get_app_path("history.json")):
            return

        with open(self.get_app_path("history.json"), "r") as f:
            history = json.load(f)

        for item in reversed(history):
            folder = os.path.dirname(item['destination'])
            folder_name = os.path.basename(folder)

            line = f"[{item['time']}] {item['file']} → {folder_name}"
            self.log_box.append(line)

    def show_log(self):
        self.view_mode = "log"
        self.log_box.clear()

    def show_history(self):
        self.view_mode = "history"
        self.refresh_history()

    # ================= STATUS =================
    def update_status(self, status):
        self.status.setText("🟢 Running" if status.get("running") else "🔴 Stopped")
        self.count.setText(f"📦 {status.get('processed_count', 0)}")
        self.last.setText(f"⚡ {status.get('last_action', '-')}")
        self.folder.setText(f"📁 {status.get('folder', '-')}")

    # ================= NOTIFY =================
    def notify(self, title, message, level="info"):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)

    # ================= WATCHER =================
    def start_sorting(self):
        if not self.config["watch_folder"]:
            self.log("❌ Select folder first!")
            return

        self.running = True

        def run():
            start_watching(
                self.config["watch_folder"],
                self.config,
                lambda: self.running,
                self.thread_log,
                self.update_status,
                self.notify,
                self.add_to_history
            )

        threading.Thread(target=run, daemon=True).start()

    def stop_sorting(self):
        self.running = False

    # ================= FOLDER =================
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")

        if folder:
            self.config["watch_folder"] = folder
            self.save_config()
            self.folder.setText(f"📁 {folder}")

    def get_app_path(self, filename):
        base = os.path.join(os.path.dirname(__file__), "SortMeData")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, filename)

    # ================= CONFIG =================
    def save_config(self):
        with open(self.get_app_path("config.json"), "w") as f:
            json.dump(self.config, f, indent=4)

    def load_config(self):
        path = self.get_app_path("config.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                self.config = json.load(f)

    # ================= RULES =================
    def add_rule(self):
        rule = {
            "name": self.rule_name.text(),
            "keywords": [k.strip() for k in self.rule_keywords.text().split(",")],
            "path": self.rule_path.text()
        }

        if self.edit_index >= 0:
            self.config["rules"][self.edit_index] = rule
            self.edit_index = -1
        else:
            self.config["rules"].append(rule)

        self.save_config()
        self.refresh_rules()

    def edit_rule(self):
        idx = self.rules_list.currentRow()
        if idx < 0:
            return

        rule = self.config["rules"][idx]

        self.rule_name.setText(rule["name"])
        self.rule_keywords.setText(", ".join(rule["keywords"]))
        self.rule_path.setText(rule["path"])

        self.edit_index = idx

    def load_rule_to_inputs(self):
        self.edit_rule()

    def delete_rule(self):
        idx = self.rules_list.currentRow()

        if idx >= 0:
            self.config["rules"].pop(idx)
            self.save_config()
            self.refresh_rules()

    def refresh_rules(self):
        self.rules_list.clear()
        for r in self.config["rules"]:
            self.rules_list.addItem(f"{r['name']} → {r['path']}")

    # ================= LOG =================
    def log(self, msg):
        if self.view_mode == "log":
            self.log_box.append(msg)

        print(msg)

        with open(self.get_app_path("log.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    # ================= EXIT =================
    def exit_app(self):
        self.running = False
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("SmartSorter", "Running in background", QSystemTrayIcon.Information, 2000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SmartSorterUI()
    w.show()
    sys.exit(app.exec())