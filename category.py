# -*- coding: utf-8 -*-

class Category:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        if parent is not None:
            parent.children.append(self)

    def full_path(self):
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path()} > {self.name}"
    
    def __str__(self):
        return self.name