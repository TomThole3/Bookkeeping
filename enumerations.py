# -*- coding: utf-8 -*-
from enum import IntEnum, Enum

class Screen(IntEnum):
    MENU = 0
    PROCESSING = 1
    JOURNAL = 2
    BALANCE = 3
    ANALYSIS = 4
    SETTINGS = 5
    
class TransactionColumns(IntEnum):
    REFERENCE = 0
    CRDTDBT = 1
    AMOUNT = 2
    DATE = 3
    COUNTERPARTY = 4
    DESCRIPTION = 5
    CATEGORY = 6
    SPLIT = 7
    
class Colours(str, Enum):
    COLOUR1 = '#800080'
    COLOUR2 = '#314159'
    COLOUR3 = '#DE0DAB'
    COLOUR4 = '#008080'
    COLOUR5 = '#808000'