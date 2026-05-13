import sys
import os
import threading
import json
import subprocess
import platform
import uuid
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QLineEdit, QListWidget, QSystemTrayIcon, QMenu,
    QListWidgetItem, QMessageBox, QAbstractItemView
)

from PySide6.QtGui import QIcon, QCursor
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

        self.select_btn = QPushButton("📁 Select Folder")
        self.select_btn.clicked.connect(self.select_folder)

        self.start_btn = QPushButton("🚀 START")
        self.start_btn.clicked.connect(self.start_sorting)

        self.stop_btn = QPushButton("🛑 STOP")
        self.stop_btn.clicked.connect(self.stop_sorting)
        self.stop_btn.setEnabled(False)

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

        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("Rule name (e.g. Matematika)")
        self.left.addWidget(self.rule_name)

        self.rule_keywords = QLineEdit()
        self.rule_keywords.setPlaceholderText("Keywords (comma separated)")
        self.left.addWidget(self.rule_keywords)

        self.rule_path = QLineEdit()
        self.rule_path.setPlaceholderText("Target folder")

        self.browse_rule_btn = QPushButton("📂 Browse")
        self.browse_rule_btn.clicked.connect(self.select_rule_folder)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.rule_path)
        path_layout.addWidget(self.browse_rule_btn)

        self.left.addLayout(path_layout)

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
        self.rules_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.rules_list.setDefaultDropAction(Qt.MoveAction)

        # =========================
        # DRAG & DROP RULE PRIORITY
        # =========================
        self.rules_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.rules_list.setDefaultDropAction(Qt.MoveAction)

        self.rules_list.model().rowsMoved.connect(self.save_rule_order)
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

        self.clear_history_btn = QPushButton("🗑 Clear History")
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.clear_history_btn.hide()
        toggle_layout.addWidget(self.clear_history_btn)

        self.right.addLayout(toggle_layout)

        # LOG BOX
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.right.addWidget(self.log_box)

        # HISTORY LIST (nové)
        self.history_list = QListWidget()
        self.history_list.hide()

        self.history_list.itemDoubleClicked.connect(self.open_selected_folder)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_context_menu)

        self.right.addWidget(self.history_list)

        self.root.addLayout(self.left, 35)
        self.root.addLayout(self.right, 65)

        self.setLayout(self.root)

        # DATA
        self.config = {"watch_folder": "", "rules": []}
        self.running = False
        self.watcher_thread = None
        self.edit_index = -1
        self.edit_rule_id = None

        # TRAY
        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.tray.setIcon(QIcon(icon_path))

        menu = QMenu()
        menu.addAction("Open", self.show)
        menu.addAction("Exit", self.exit_app)

        self.tray.setContextMenu(menu)
        self.tray.show()

        self.load_config()
        self.refresh_rules()

        # STYLE (nezmenené)
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

    # ================= HISTORY =================
    def refresh_history(self):
        self.history_list.clear()

        path = self.get_app_path("history.json")
        if not os.path.exists(path):
            return

        try:
            with open(path, "r") as f:
                history = json.load(f)

        except Exception as e:

            self.log(f"❌ History load failed: {e}")
            history = []

        for item in reversed(history):
            if not isinstance(item, dict):
                continue

            file_name = item.get("file") or item.get("source") or "unknown"
            destination = item.get("destination", "")

            folder = os.path.dirname(destination)
            folder_name = os.path.basename(folder)

            text = f"[{item.get('time', '-')}] {file_name} → {folder_name}"

            list_item = QListWidgetItem(text)
            list_item.setData(Qt.UserRole, {
                "file": file_name,
                "folder": folder,
                "destination": destination
            })

            self.history_list.addItem(list_item)

    def open_selected_folder(self, item):
        data = item.data(Qt.UserRole)
        self.open_folder(data["folder"])

    def show_history_context_menu(self, position):
        item = self.history_list.itemAt(position)
        if not item:
            return

        data = item.data(Qt.UserRole)

        menu = QMenu()

        open_folder = menu.addAction("📂 Open folder")
        show_file = menu.addAction("📄 Show file")
        copy_path = menu.addAction("📋 Copy path")

        action = menu.exec(QCursor.pos())

        if action == open_folder:
            self.open_folder(data["folder"])
        elif action == show_file:
            self.show_file_in_explorer(data["file"])
        elif action == copy_path:
            QApplication.clipboard().setText(data["file"])

    def open_folder(self, path):
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def show_file_in_explorer(self, file_path):
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", file_path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(file_path)])

    # ================= VIEW =================
    def show_log(self):
        self.view_mode = "log"

        self.history_list.hide()
        self.log_box.show()

        self.clear_history_btn.hide()

    def show_history(self):
        self.view_mode = "history"

        self.log_box.hide()
        self.history_list.show()

        self.clear_history_btn.show()

        self.refresh_history()

    def clear_history(self):

        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear history?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        path = self.get_app_path("history.json")

        try:
            with open(path, "w") as f:
                json.dump([], f)

            self.history_list.clear()

            self.log("🗑 History cleared")

        except Exception as e:
            self.log(f"❌ Failed to clear history: {e}")

    # ================= LOG =================
    def log(self, msg):
        if self.view_mode == "log":
            self.log_box.append(msg)

        print(msg)

        with open(self.get_app_path("log.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def thread_log(self, msg):
        self.log_signal.emit(msg)

    # ================= WATCHER =================
    def start_sorting(self):

        if self.running:
            self.log("⚠️ Watcher already running")
            return

        if self.watcher_thread and self.watcher_thread.is_alive():
            self.log("⚠️ Watcher thread already exists")
            return

        if not self.config["watch_folder"]:
            self.log("❌ Select folder first!")
            return

        self.running = True

        # UI LOCK
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

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
            self.watcher_thread = None

        self.watcher_thread = threading.Thread(
            target=run,
            daemon=True
        )

        self.watcher_thread.start()

    def stop_sorting(self):

        if not self.running:
            return

        self.running = False
        self.watcher_thread = None

        # UI UNLOCK
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ================= HISTORY SAVE =================
    def add_to_history(self, file, destination):
        entry = {
            "file": file,
            "destination": destination,
            "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        }

        path = self.get_app_path("history.json")

        history = []
        if os.path.exists(path):

            try:
                with open(path, "r") as f:
                    history = json.load(f)

            except Exception as e:

                self.log(f"❌ History read failed: {e}")
                history = []

        history.append(entry)
        history = history[-50:]

        tmp_path = path + ".tmp"

        with open(tmp_path, "w") as f:
            json.dump(history, f, indent=4)

        os.replace(tmp_path, path)

    # ================= STATUS =================
    def update_status(self, status):
        self.status.setText("🟢 Running" if status.get("running") else "🔴 Stopped")
        self.count.setText(f"📦 {status.get('processed_count', 0)}")
        self.last.setText(f"⚡ {status.get('last_action', '-')}")
        self.folder.setText(f"📁 {status.get('folder', '-')}")

    def notify(self, title, message, level="info"):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)

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

    def select_rule_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select target folder")

        if folder:
            self.rule_path.setText(folder)

    # ================= CONFIG =================
    def save_config(self):

        path = self.get_app_path("config.json")
        temp_path = path + ".tmp"

        try:

            # write temporary file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)

            # atomic replace
            os.replace(temp_path, path)

        except Exception as e:

            self.log(f"❌ Config save failed: {e}")

            # cleanup temp file if exists
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    def load_config(self):

        path = self.get_app_path("config.json")

        if not os.path.exists(path):
            return

        try:
            with open(path, "r") as f:
                self.config = json.load(f)

        except Exception as e:

            self.log(f"❌ Config load failed: {e}")

            self.config = {
                "watch_folder": "",
                "rules": []
            }

    # ================= RULES =================
    def add_rule(self):

        name = self.rule_name.text().strip()
        keywords = [k.strip() for k in self.rule_keywords.text().split(",")]
        path = self.rule_path.text().strip()

        # =========================
        # VALIDATION
        # =========================

        if not name:
            self.log("❌ Rule name is empty")
            return

        if not keywords or keywords == [""]:
            self.log("❌ Keywords are empty")
            return

        if not path:
            self.log("❌ Path is empty")
            return

        # normalize path
        path = os.path.normpath(path)

        # create folder if not exists
        try:
            if not os.path.exists(path):
                os.makedirs(path)
                self.log(f"📁 Created missing folder: {path}")
        except Exception as e:
            self.log(f"❌ Invalid path: {e}")
            return

        rule = {
            "id": str(uuid.uuid4()),
            "name": name,
            "keywords": keywords,
            "path": path
        }

        if self.edit_index >= 0:
            for i, r in enumerate(self.config["rules"]):
                if r.get("id") == self.edit_rule_id:
                    self.config["rules"][i] = rule
                    break

            self.edit_index = -1
            self.edit_rule_id = None
        else:
            self.config["rules"].append(rule)

        self.save_config()
        self.refresh_rules()

        # =========================
        # RESET INPUTS AFTER SAVE
        # =========================
        self.rule_name.clear()
        self.rule_keywords.clear()
        self.rule_path.clear()
        self.edit_index = -1
        self.edit_rule_id = None

    def edit_rule(self):

        idx = self.rules_list.currentRow()
        if idx < 0:
            return

        # =========================
        # SAFE RULE ACCESS
        # =========================
        try:
            rule = self.config["rules"][idx]
            self.edit_rule_id = rule.get("id")
        except Exception as e:
            self.log(f"❌ Rule load error: {e}")
            return

        # =========================
        # VALIDATION / SANITIZATION
        # =========================
        name = rule.get("name", "")
        keywords = rule.get("keywords", [])
        path = rule.get("path", "")

        # fix keywords if broken
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]

        # =========================
        # SET UI VALUES
        # =========================
        self.rule_name.setText(name)
        self.rule_keywords.setText(", ".join(keywords))
        self.rule_path.setText(path)

        # =========================
        # CHECK PATH WARNING (NOT BLOCKING)
        # =========================
        if path and not os.path.exists(path):
            self.log(f"⚠️ Warning: path does not exist → {path}")

        # =========================
        # SET EDIT MODE
        # =========================
        self.edit_index = idx

    def load_rule_to_inputs(self):
        self.edit_rule()

    def delete_rule(self):
        idx = self.rules_list.currentRow()

        if idx >= 0:
            self.config["rules"].pop(idx)
            self.save_config()
            self.refresh_rules()

    def move_rule_up(self):

        idx = self.rules_list.currentRow()

        if idx <= 0:
            return

        self.config["rules"][idx], self.config["rules"][idx - 1] = (
            self.config["rules"][idx - 1],
            self.config["rules"][idx]
        )

        self.save_config()
        self.refresh_rules()

        self.rules_list.setCurrentRow(idx - 1)

    def move_rule_down(self):

        idx = self.rules_list.currentRow()

        if idx < 0 or idx >= len(self.config["rules"]) - 1:
            return

        self.config["rules"][idx], self.config["rules"][idx + 1] = (
            self.config["rules"][idx + 1],
            self.config["rules"][idx]
        )

        self.save_config()
        self.refresh_rules()

        self.rules_list.setCurrentRow(idx + 1)

    def refresh_rules(self):

        self.rules_list.clear()

        for i, r in enumerate(self.config["rules"], start=1):
            self.rules_list.addItem(f"[{i}] {r['name']} → {r['path']}")

    def save_rule_order(self):

        new_rules = []

        for i in range(self.rules_list.count()):

            text = self.rules_list.item(i).text()

            # odstráni [1], [2], ...
            text = text.split("] ", 1)[1]

            rule_name = text.split(" → ")[0]

            for rule in self.config["rules"]:
                if rule.get("name") == rule_name:
                    new_rules.append(rule)
                    break

        self.config["rules"] = new_rules
        self.save_config()

        self.refresh_rules()

    # ================= EXIT =================
    def exit_app(self):

        self.log("🛑 Shutting down...")

        # stop watcher
        self.running = False

        # wait for thread to finish
        if self.watcher_thread and self.watcher_thread.is_alive():

            self.log("⌛ Waiting for watcher thread...")

            self.watcher_thread.join(timeout=3)

            if self.watcher_thread.is_alive():
                self.log("⚠️ Watcher did not close in time")
            else:
                self.log("✅ Watcher stopped cleanly")

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