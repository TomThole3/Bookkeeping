import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QStackedWidget)
from processingwindow import ProcessingWindow
from balancewindow import BalanceWindow
from journalwindow import JournalWindow


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Muntenman Centraal")
        self.setGeometry(0, 0, 1800, 1000)

        # ---------------------------
        # STACKED WIDGET (navigation)
        # ---------------------------
        self.stack = QStackedWidget()
        main_menu = QWidget()
        main_layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        main_layout.addWidget(self.label)

        self.btn_add_transaction = QPushButton("Process transactions")
        self.btn_add_transaction.clicked.connect(self.processing)
        main_layout.addWidget(self.btn_add_transaction)

        self.btn_view_reports = QPushButton("Journal")
        self.btn_view_reports.clicked.connect(self.journal)
        main_layout.addWidget(self.btn_view_reports)

        self.btn_settings = QPushButton("Balance")
        self.btn_settings.clicked.connect(self.balance)
        main_layout.addWidget(self.btn_settings)

        main_menu.setLayout(main_layout)

        # ---------------------------
        # OTHER SCREENS
        # ---------------------------
        self.processing_window = ProcessingWindow(self.stack)
        self.journal_window = JournalWindow(self.stack)
        self.balance_window = BalanceWindow()

        # Add all screens to stack
        self.stack.addWidget(main_menu)               # index 0
        self.stack.addWidget(self.processing_window)  # index 1
        self.stack.addWidget(self.journal_window)     # index 2
        self.stack.addWidget(self.balance_window)     # index 3

        # Set initial screen
        self.stack.setCurrentIndex(0)

        # Root layout
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.stack)
        self.setLayout(root_layout)

    # ---------------------------
    # NAVIGATION METHODS
    # ---------------------------
    def processing(self):
        self.stack.setCurrentIndex(1)

    def journal(self):
        self.journal_window.load_transactions()
        self.stack.setCurrentIndex(2)

    def balance(self):
        self.stack.setCurrentIndex(3)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())