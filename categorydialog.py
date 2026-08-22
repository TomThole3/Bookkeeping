# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QMessageBox, QComboBox
from PyQt6.QtCore import Qt
from categorydialogbackend import CategoryDialogBackend

class AddCategoryDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.backend = CategoryDialogBackend()
        self.setWindowTitle("Change categories")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.label_list = QLabel("Categories:")
        layout.addWidget(self.label_list)

        self.category_list = QListWidget()
        layout.addWidget(self.category_list)

        self.btn_remove = QPushButton("Remove selected")
        self.btn_remove.clicked.connect(self._remove_category)
        layout.addWidget(self.btn_remove)

        self.label_name = QLabel("New category name:")
        layout.addWidget(self.label_name)

        self.input = QLineEdit()
        layout.addWidget(self.input)

        self.label_parent = QLabel("Parent category (optional):")
        layout.addWidget(self.label_parent)

        self.parent_combo = QComboBox()
        layout.addWidget(self.parent_combo)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self._add_category)
        layout.addWidget(self.btn_add)

        self.setLayout(layout)
        self._load_categories()

    def _load_categories(self):
        self.category_list.clear()
        self.parent_combo.clear()
        self.parent_combo.addItem("None", None)
    
        for category in self.backend.get_categories():
            list_item = QListWidgetItem(category.name)
            list_item.setData(Qt.ItemDataRole.UserRole, category.id)
            self.category_list.addItem(list_item)
            self.parent_combo.addItem(category.name, category.id)

    def _add_category(self):
        name = self.input.text().strip()
        if not name:
            return
        parent_id = self.parent_combo.currentData()
        if self.backend.add_category(name, parent_id) is None:
            QMessageBox.warning(self, "Duplicate name", f"A category named '{name}' already exists.")
            return
        self.input.clear()
        self._load_categories()

    def _remove_category(self):
        selected = self.category_list.currentItem()
        if selected:
            confirm = QMessageBox.question(
                self,
                "Confirm removal",
                f"Are you sure you want to remove '{selected.text().strip()}'?\nThis will also remove all subcategories and decategorize affected transactions.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                category_id = selected.data(Qt.ItemDataRole.UserRole)
                self.backend.remove_category(category_id)
                self._load_categories()