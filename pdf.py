# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 09:21:01 2026

@author: tthol
"""

import pdfplumber

class PDFData:
    
    def test(self, path):
        rows = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }
                tables = page.extract_tables(table_settings)
                for table in tables:
                    for row in table:
                        rows.append(row)
        return rows
    
    def cleanup_table(self, table):
        for 
            
path = input('path ').strip('"')
pdf = PDFData()
pdf.test(path)