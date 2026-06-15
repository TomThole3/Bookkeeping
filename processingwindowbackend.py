# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog
from camt_parser import CAMTParser
from database import DatabaseInteractions
from transaction import Transaction


class ProcessingWindowBackend:

    def __init__(self, stack):
        self.fileselector = FileSelectScreen(stack)
        self.parser = CAMTParser()
        self.db = DatabaseInteractions()
        
    def add_entries(self):
        path = self.fileselector.select_file()
        if path:
            transactions = self.parser.extract_camt_transactions(path)
            
            
        

class FileSelectScreen(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
    
        layout = QVBoxLayout()
    
        self.label = QLabel("No file selected")
        layout.addWidget(self.label)
    
        btn_select = QPushButton("Select File")
        btn_select.clicked.connect(self.select_file)
        layout.addWidget(btn_select)
    
        self.setLayout(layout)
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a file",          # dialog title
            "",                        # starting directory ("" = default)
            "CAMT Files (*.xml);;All Files (*)"  # file type filter
        )
        return file_path