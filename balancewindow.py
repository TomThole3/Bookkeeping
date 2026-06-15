# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

class BalanceWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Muntenman Balans")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.setLayout(layout)