# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

class ProcessingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Bookkeeping")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.btn_add_transaction = QPushButton("Process transactions")
        self.btn_add_transaction.clicked.connect(self.processing)
        layout.addWidget(self.btn_add_transaction)

        self.btn_view_reports = QPushButton("Journal")
        self.btn_view_reports.clicked.connect(self.journal)
        layout.addWidget(self.btn_view_reports)

        self.btn_settings = QPushButton("Balance")
        self.btn_settings.clicked.connect(self.balance)
        layout.addWidget(self.btn_settings)

        self.setLayout(layout)

    def processing(self):
        pass

    def journal(self):
        pass

    def balance(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessingWindow()
    window.show()
    sys.exit(app.exec())