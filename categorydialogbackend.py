# -*- coding: utf-8 -*-
from database import DatabaseInteractions
from category import Category

class CategoryDialogBackend:
    def __init__(self):
        self.db = DatabaseInteractions()

    def get_categories(self):
        return self.db.get_categories()

    def add_category(self, name, parent_id=None):
        self.db.add_category(Category(name=name, parent_id=parent_id))

    def remove_category(self, category_id):
        self.db.remove_category(category_id)