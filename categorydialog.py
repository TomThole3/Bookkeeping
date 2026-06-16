# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QListWidget, QMessageBox
from categorydialogbackend import CategoryDialogBackend

class AddCategoryDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.backend = CategoryDialogBackend()
        self.setWindowTitle("Change categories")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        # existing categories list
        self.label_list = QLabel("Categories:")
        layout.addWidget(self.label_list)

        self.category_list = QListWidget()
        layout.addWidget(self.category_list)

        self.btn_remove = QPushButton("Remove selected")
        self.btn_remove.clicked.connect(self.remove_category)
        layout.addWidget(self.btn_remove)

        # add new category
        self.label = QLabel("New category name:")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        layout.addWidget(self.input)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_category)
        layout.addWidget(self.btn_add)

        self.setLayout(layout)
        self.load_categories()

    def load_categories(self):
        self.category_list.clear()
        for category in self.backend.get_categories():
            self.category_list.addItem(category)

    def add_category(self):
        name = self.input.text().strip()
        if name:
            self.backend.add_category(name)
            self.input.clear()
            self.load_categories()

    def remove_category(self):
        selected = self.category_list.currentItem()
        if selected:
            confirm = QMessageBox.question(
                self,
                "Confirm removal",
                f"Are you sure you want to remove '{selected.text()}'?\nThis will decategorize all Transactions with this category",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.backend.remove_category(selected.text())
                self.load_categories()
