import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QStackedWidget
from processingwindow import ProcessingWindow
from balancewindow import BalanceWindow
from journalwindow import JournalWindow
from analysiswindow import AnalysisWindow
from settingswindow import SettingsWindow, load_settings, apply_theme
from screen import Screen

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Muntenman Centraal")
        self.resize(1800, 1000)
        self.stack = QStackedWidget()

        main_menu = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addStretch()

        buttons = [
            ("Process transactions", Screen.PROCESSING),
            ("Journal", Screen.JOURNAL),
            ("Balance", Screen.BALANCE),
            ("Analysis", Screen.ANALYSIS),
            ("Settings", Screen.SETTINGS),
        ]
        for label, screen in buttons:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, s=screen: self.navigate(s))
            main_layout.addWidget(btn)

        main_menu.setLayout(main_layout)

        # ---------------------------
        # OTHER SCREENS
        # ---------------------------
        self.processing_window = ProcessingWindow(self.stack)
        self.journal_window = JournalWindow(self.stack)
        self.balance_window = BalanceWindow(self.stack)
        self.analysis_window = AnalysisWindow(self.stack)
        self.settings_window = SettingsWindow(self.stack)

        # Add all screens to stack
        self.stack.addWidget(main_menu)               # index 0
        self.stack.addWidget(self.processing_window)  # index 1
        self.stack.addWidget(self.journal_window)     # index 2
        self.stack.addWidget(self.balance_window)     # index 3
        self.stack.addWidget(self.analysis_window)    # index 4
        self.stack.addWidget(self.settings_window)    # index 5

        # Set initial screen
        self.stack.setCurrentIndex(0)

        # Root layout
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.stack)
        self.setLayout(root_layout)

    def navigate(self, screen: Screen):
        reload = {
            Screen.PROCESSING: self.processing_window.load_transactions,
            Screen.JOURNAL: self.journal_window.load_transactions,
            Screen.BALANCE: self.balance_window.load_categories,
        }.get(screen)
        if reload:
            reload()
        self.stack.setCurrentIndex(screen)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Restore the saved theme before showing any window
    saved = load_settings()
    apply_theme(saved.get("theme", "dark_teal.xml"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())