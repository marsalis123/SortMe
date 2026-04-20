import sys
import os
import threading
import json

from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QLineEdit, QListWidget, QSystemTrayIcon, QMenu
)

from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Signal, QTimer, Qt

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

        # ===== ASCII LOGO =====
        self.left.addSpacing(60)
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

        self.logo_label = QLabel(ascii_logo)
        self.logo_label.setStyleSheet("""
            font-family: Consolas;
            font-size: 10px;
        """)
        self.logo_label.setAlignment(Qt.AlignLeft)

        self.left.addWidget(self.logo_label)

        # ===== SUBTITLE =====
        subtitle = QLabel("Smart File Sorting System")
        subtitle.setStyleSheet("font-size: 11px; color: #16a34a;")
        subtitle.setAlignment(Qt.AlignCenter)

        self.left.addWidget(subtitle)

        self.left.addSpacing(10)

        # ===== SEPARATOR =====
        self.left.addSpacing(20)
        separator = QLabel("═════════════  SORT ENGINE  ═════════════")
        separator.setStyleSheet("""
            color: #22c55e;
            font-weight: bold;
        """)
        separator.setAlignment(Qt.AlignCenter)

        self.left.addWidget(separator)
        self.left.addStretch(2)

        # ===== BUTTONS =====
        self.select_btn = QPushButton("📁 Select Folder")
        self.select_btn.clicked.connect(self.select_folder)
        self.left.addWidget(self.select_btn)

        self.start_btn = QPushButton("🚀 START")
        self.start_btn.clicked.connect(self.start_sorting)
        self.left.addWidget(self.start_btn)

        self.stop_btn = QPushButton("🛑 STOP")
        self.stop_btn.clicked.connect(self.stop_sorting)
        self.left.addWidget(self.stop_btn)

        # ===== RULE INPUT =====
        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("Rule name (e.g. Matematika)")
        self.left.addWidget(self.rule_name)

        self.rule_keywords = QLineEdit()
        self.rule_keywords.setPlaceholderText("Keywords (comma separated)")
        self.left.addWidget(self.rule_keywords)

        self.rule_path = QLineEdit()
        self.rule_path.setPlaceholderText("Target folder (e.g. School/Math)")
        self.left.addWidget(self.rule_path)

        self.add_btn = QPushButton("➕ Add / Save rule")
        self.add_btn.clicked.connect(self.add_rule)
        self.left.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Edit selected rule")
        self.edit_btn.clicked.connect(self.edit_rule)
        self.left.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑 Delete rule")
        self.delete_btn.clicked.connect(self.delete_rule)
        self.left.addWidget(self.delete_btn)

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

        # ================= NOTIFICATIONS =================
        self.notif_buffer = {
            "success": [],
            "warning": []
        }

        self.notif_timer = QTimer()
        self.notif_timer.timeout.connect(self.flush_notifications)
        self.notif_timer.start(5000)

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
                padding: 6px;
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
        self.log_box.append(msg)
        print(msg)

    def thread_log(self, msg):
        self.log_signal.emit(msg)

    # ================= STATUS =================
    def update_status(self, status):
        self.status.setText("🟢 Running" if status["running"] else "🔴 Stopped")
        self.count.setText(f"📦 {status.get('processed_count', 0)}")
        self.last.setText(f"⚡ {status.get('last_action', '-')}")
        self.folder.setText(f"📁 {status.get('folder', '-')}")

    # ================= NOTIFICATIONS =================
    def notify(self, title, message, level="info"):

        if level == "error":
            self.tray.showMessage(title, message, QSystemTrayIcon.Critical, 3000)
            return

        self.notif_buffer[level].append(message)

    def flush_notifications(self):

        if self.notif_buffer["success"]:
            count = len(self.notif_buffer["success"])
            self.tray.showMessage("Sorted", f"{count} file(s) moved", QSystemTrayIcon.Information, 3000)
            self.notif_buffer["success"].clear()

        if self.notif_buffer["warning"]:
            count = len(self.notif_buffer["warning"])
            self.tray.showMessage("Unsorted", f"{count} file(s) moved to Nezaradene", QSystemTrayIcon.Warning, 3000)
            self.notif_buffer["warning"].clear()

    # ================= WATCHER =================
    def start_sorting(self):

        if not self.config["watch_folder"]:
            return

        self.running = True

        def run():
            start_watching(
                self.config["watch_folder"],
                self.config,
                lambda: self.running,
                self.thread_log,
                self.update_status,
                self.notify
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

    # ================= CONFIG =================
    def save_config(self):
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                self.config = json.load(f)

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