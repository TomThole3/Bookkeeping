# -*- coding: utf-8 -*-
from database import DatabaseInteractions

class CategoryDialogBackend:
    
    def __init__(self):
        self.db = DatabaseInteractions()
        
    def add_category(self, name):
        self.db.add_category(name)
    
    def get_categories(self):
        return self.db.get_categories()
    
    def remove_category(self, name):
        self.db.remove_category(name)