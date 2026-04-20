import sys
import os
import threading
import json

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QTextEdit,
    QLineEdit, QListWidget,
    QSystemTrayIcon, QMenu
)

from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, Signal

from watcher import start_watching


class SmartSorterUI(QWidget):

    # =========================
    # 🔥 QT SIGNAL (FIX LOG THREADING)
    # =========================
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()

        # connect signal -> UI log
        self.log_signal.connect(self.log)

        # ---------------- WINDOW ----------------
        self.setWindowTitle("SmartSorter")
        self.setFixedSize(420, 650)

        self.layout = QVBoxLayout()

        self.label = QLabel("SMART SORTER")
        self.label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.label)

        self.sub_label = QLabel("File Automation System")
        self.layout.addWidget(self.sub_label)

        # ---------------- FOLDER ----------------
        self.select_btn = QPushButton("📁 Vybrať SortMe priečinok")
        self.select_btn.clicked.connect(self.select_folder)
        self.layout.addWidget(self.select_btn)

        self.create_btn = QPushButton("➕ Vytvoriť SortMe priečinok")
        self.create_btn.clicked.connect(self.create_sortme_folder)
        self.layout.addWidget(self.create_btn)

        # ---------------- RULES ----------------
        self.rules_list = QListWidget()
        self.layout.addWidget(self.rules_list)

        self.rule_name = QLineEdit()
        self.rule_name.setPlaceholderText("Názov (MAT, ENG, ...)")
        self.layout.addWidget(self.rule_name)

        self.rule_keywords = QLineEdit()
        self.rule_keywords.setPlaceholderText("Keywords (MAT, ALGEBRA)")
        self.layout.addWidget(self.rule_keywords)

        self.rule_path = QLineEdit()
        self.rule_path.setPlaceholderText("Cieľ (School/Matematika)")
        self.layout.addWidget(self.rule_path)

        self.add_rule_btn = QPushButton("➕ Pridať pravidlo")
        self.add_rule_btn.clicked.connect(self.add_rule)
        self.layout.addWidget(self.add_rule_btn)

        # ---------------- CONTROL ----------------
        self.start_btn = QPushButton("🚀 Spustiť sledovanie")
        self.start_btn.clicked.connect(self.start_sorting)
        self.layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("🛑 STOP")
        self.stop_btn.clicked.connect(self.stop_sorting)
        self.layout.addWidget(self.stop_btn)

        # ---------------- LOG ----------------
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

        self.setLayout(self.layout)

        # ---------------- CONFIG ----------------
        self.config = {
            "watch_folder": "",
            "rules": []
        }

        # ---------------- THREAD ----------------
        self._running = False

        # ---------------- STYLE ----------------
        self.setStyleSheet("""
            QWidget {
                background-color: #020617;
                color: #22c55e;
                font-family: Consolas;
            }

            QPushButton {
                border: 1px solid #22c55e;
                padding: 6px;
                background-color: #020617;
            }

            QPushButton:hover {
                background-color: #22c55e;
                color: black;
            }

            QTextEdit, QLineEdit {
                background-color: black;
                border: 1px solid #22c55e;
                color: #22c55e;
            }
        """)

        # ---------------- TRAY ----------------
        self.tray = QSystemTrayIcon(self)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.tray.setIcon(QIcon(icon_path))

        menu = QMenu()

        show_action = QAction("Otvoriť", self)
        show_action.triggered.connect(self.show)

        exit_action = QAction("Ukončiť", self)
        exit_action.triggered.connect(self.exit_app)

        menu.addAction(show_action)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

        # ---------------- LOAD ----------------
        self.load_config()

    # =========================
    # 🔥 LOG SYSTEM (MAIN THREAD ONLY)
    # =========================
    def log(self, msg):
        self.log_output.append(msg)
        print(msg)

    def thread_log(self, msg):
        # THREAD SAFE EMIT
        self.log_signal.emit(msg)

    # =========================
    # WATCHER
    # =========================
    def start_sorting(self):

        if not self.config["watch_folder"]:
            self.log("❌ Vyber folder!")
            return

        self._running = True
        self.log("🚀 START")

        def run():
            start_watching(
                self.config["watch_folder"],
                self.config,
                lambda: self._running,
                self.thread_log
            )

        threading.Thread(target=run, daemon=True).start()

    def stop_sorting(self):
        self._running = False
        self.log("🛑 STOP")

    # =========================
    # FOLDER
    # =========================
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Vyber priečinok")

        if folder:
            self.config["watch_folder"] = folder
            self.save_config()
            self.log(f"📁 {folder}")

    def create_sortme_folder(self):
        base = QFileDialog.getExistingDirectory(self, "Vyber miesto")

        if base:
            path = os.path.join(base, "SortMe")
            os.makedirs(path, exist_ok=True)

            self.config["watch_folder"] = path
            self.save_config()
            self.log(f"📁 {path}")

    # =========================
    # RULES
    # =========================
    def add_rule(self):

        if not self.rule_name.text() or not self.rule_keywords.text() or not self.rule_path.text():
            self.log("❌ Missing fields")
            return

        self.config["rules"].append({
            "name": self.rule_name.text(),
            "keywords": [k.strip() for k in self.rule_keywords.text().split(",")],
            "path": self.rule_path.text()
        })

        self.save_config()
        self.refresh_rules()

        self.log("✅ Rule added")

    def refresh_rules(self):
        self.rules_list.clear()

        for r in self.config["rules"]:
            self.rules_list.addItem(f"{r['name']} → {r['path']}")

    # =========================
    # CONFIG
    # =========================
    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                self.config = json.load(f)

            self.refresh_rules()
            self.log("📂 Config loaded")

    # =========================
    # EXIT
    # =========================
    def exit_app(self):
        self._running = False
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartSorterUI()
    window.show()
    sys.exit(app.exec())