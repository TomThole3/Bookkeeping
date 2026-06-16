# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel
from categorydialogbackend import CategoryDialogBackend

class AddCategoryDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(" Change categories")

        layout = QVBoxLayout()

        self.label = QLabel("New category name:")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        layout.addWidget(self.input)

        self.btn = QPushButton("Add")
        self.btn.clicked.connect(self.accept)
        layout.addWidget(self.btn)

        self.setLayout(layout)

    def get_value(self):
        return self.input.text().strip()
    
    def accept(self):
        pass

