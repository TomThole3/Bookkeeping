# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog


class ProcessingWindowBackend:

    def __init__(self, stack):
        self.fileselector = FileSelectScreen(stack)
        
    def add_entries(self):
        path = self.fileselector.select_file()
        

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
    
        if file_path:  # empty string if user cancels
            self.file_path = file_path
            self.label.setText(f"Selected: {file_path}")
        return file_path