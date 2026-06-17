# -*- coding: utf-8 -*-

class Category:
    def __init__(self, name, id=None, parent_id=None):
        self.id = id
        self.name = name
        self.parent_id = parent_id  # raw foreign key from DB
        self.parent = None          # set by build_tree
        self.children = []          # set by build_tree

    def full_path(self):
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path()} > {self.name}"
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def build_tree(categories):
        lookup = {c.id: c for c in categories}
        for c in categories:
            if c.parent_id is not None:
                parent = lookup[c.parent_id]
                c.parent = parent
                parent.children.append(c)
        return [c for c in categories if c.parent_id is None]