# -*- coding: utf-8 -*-
"""Category management dialog.

This module defines :class:`AddCategoryDialog`, a modal dialog that lets
the user view existing categories, add new ones (optionally nested under
a parent), and remove existing ones.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QComboBox,
)
from PyQt6.QtCore import Qt
from ui.backends.categorydialogbackend import CategoryDialogBackend


class AddCategoryDialog(QDialog):
    """Modal dialog for adding, listing, and removing categories.

    Displays the full flat list of categories, a form for adding a new
    category (with an optional parent), and a button to remove the
    currently selected category (along with its subcategories, per the
    backend's cascading removal behaviour).

    Attributes:
        backend: Backend object used to fetch, add, and remove
            categories.
        label_list: Header label above the category list.
        category_list: List widget showing all existing categories.
        btn_remove: Button that removes the selected category.
        label_name: Label for the new-category name input.
        input: Text field for the new category's name.
        label_parent: Label for the parent category selector.
        parent_combo: Combo box for picking an optional parent category.
        btn_add: Button that adds a new category.
    """

    def __init__(self) -> None:
        """Initialise the dialog and load the current category list."""
        super().__init__()
        self.backend: CategoryDialogBackend = CategoryDialogBackend()
        self.setWindowTitle("Change categories")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.label_list: QLabel = QLabel("Categories:")
        layout.addWidget(self.label_list)

        self.category_list: QListWidget = QListWidget()
        layout.addWidget(self.category_list)

        self.btn_remove: QPushButton = QPushButton("Remove selected")
        self.btn_remove.clicked.connect(self._remove_category)
        layout.addWidget(self.btn_remove)

        self.label_name: QLabel = QLabel("New category name:")
        layout.addWidget(self.label_name)

        self.input: QLineEdit = QLineEdit()
        layout.addWidget(self.input)

        self.label_parent: QLabel = QLabel("Parent category (optional):")
        layout.addWidget(self.label_parent)

        self.parent_combo: QComboBox = QComboBox()
        layout.addWidget(self.parent_combo)

        self.btn_add: QPushButton = QPushButton("Add")
        self.btn_add.clicked.connect(self._add_category)
        layout.addWidget(self.btn_add)

        self.setLayout(layout)
        self._load_categories()

    def _load_categories(self) -> None:
        """Refresh the category list and parent combo box from the backend.

        Clears and repopulates both ``category_list`` (each item tagged
        with its category ID via ``Qt.ItemDataRole.UserRole``) and
        ``parent_combo`` (prefixed with a ``"None"`` entry representing
        "no parent").
        """
        self.category_list.clear()
        self.parent_combo.clear()
        self.parent_combo.addItem("None", None)
    
        for category in self.backend.get_categories():
            list_item = QListWidgetItem(category.name)
            list_item.setData(Qt.ItemDataRole.UserRole, category.id)
            self.category_list.addItem(list_item)
            self.parent_combo.addItem(category.name, category.id)

    def _add_category(self) -> None:
        """Add a new category using the entered name and selected parent.

        Does nothing if the name field is blank. Shows a warning message
        box if the backend rejects the name as a duplicate; otherwise
        clears the input field and reloads the category list.
        """
        name = self.input.text().strip()
        if not name:
            return
        parent_id: Optional[int] = self.parent_combo.currentData()
        if self.backend.add_category(name, parent_id) is None:
            QMessageBox.warning(self, "Duplicate name", f"A category named '{name}' already exists.")
            return
        self.input.clear()
        self._load_categories()

    def _remove_category(self) -> None:
        """Remove the currently selected category, after confirmation.

        Does nothing if no category is selected. On confirmation, asks
        the backend to remove the category (which cascades to
        subcategories and decategorises affected transactions) and
        reloads the category list.
        """
        selected = self.category_list.currentItem()
        if selected:
            confirm = QMessageBox.question(
                self,
                "Confirm removal",
                f"Are you sure you want to remove '{selected.text().strip()}'?\nThis will also remove all subcategories and decategorize affected transactions.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                category_id: int = selected.data(Qt.ItemDataRole.UserRole)
                self.backend.remove_category(category_id)
                self._load_categories()