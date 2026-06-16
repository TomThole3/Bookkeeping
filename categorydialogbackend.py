# -*- coding: utf-8 -*-
from database import DatabaseInteractions

class CategoryDialogBackend:
    
    def __init__(self):
        self.db = DatabaseInteractions()
        
    def add_category(self, category):
        self.db.add_category(category)
    
    def get_categories(self):
        return self.db.get_categories()