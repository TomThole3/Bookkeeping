# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

class JournalWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Muntenman Journaal")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.btn_add_transaction = QPushButton("Add new transactions")
        self.btn_add_transaction.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_transaction)

        self.setLayout(layout)

    def add_entries(self):
        pass