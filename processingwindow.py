# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

class ProcessingWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Muntenman Schuifwerk")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.btn_add_transaction = QPushButton("we gaan schuiven")
        self.btn_add_transaction.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_transaction)

        self.setLayout(layout)

    def add_entries(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessingWindow()
    window.show()
    sys.exit(app.exec())