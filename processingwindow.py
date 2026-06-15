# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog
from processingwindowbackend import ProcessingWindowBackend

class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        
        self.stack = stack
        self.backend = ProcessingWindowBackend(self.stack)
        
        self.setWindowTitle("Muntenman Schuifwerk")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_entries)

        self.setLayout(layout)

    def add_entries(self):
        self.backend.add_entries()
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessingWindow()
    window.show()
    sys.exit(app.exec())