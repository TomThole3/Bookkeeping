# -*- coding: utf-8 -*-
"""Application entry point for the bookkeeping application.

This module defines :class:`MainWindow`, the top-level widget hosting
the main menu and every screen (Processing, Journal, Balance, Analysis,
Settings) in a :class:`QStackedWidget`, and the ``if __name__ ==
"__main__"`` block that boots the Qt application.
"""

from __future__ import annotations

import sys
from typing import Callable, List, Optional, Tuple

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QStackedWidget
from database import DatabaseInteractions
from processingwindow import ProcessingWindow
from balancewindow import BalanceWindow
from journalwindow import JournalWindow
from analysiswindow import AnalysisWindow
from settingswindow import SettingsWindow, load_settings, apply_theme
from enumerations import Screen


class MainWindow(QWidget):
    """Top-level application window hosting the main menu and all screens.

    Owns the single :class:`DatabaseInteractions` instance shared by
    every screen, and a :class:`QStackedWidget` used to switch between
    the main menu and each feature screen.

    Attributes:
        stack: The stacked widget managing all screens, indexed
            according to :class:`enumerations.Screen`.
        db: The shared database interactions object.
        processing_window: The transaction processing screen.
        journal_window: The journal (filterable transaction list) screen.
        balance_window: The balance (category totals) screen.
        analysis_window: The analysis (charts) screen.
        settings_window: The settings screen.
    """

    def __init__(self) -> None:
        """Build the main menu, construct every screen, and assemble the stack."""
        super().__init__()
        self.setWindowTitle("Bookkeeping")
        self.resize(1800, 1000)
        self.stack: QStackedWidget = QStackedWidget()

        main_menu = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addStretch()

        buttons: List[Tuple[str, Screen]] = [
            ("Process transactions", Screen.PROCESSING),
            ("Journal", Screen.JOURNAL),
            ("Balance", Screen.BALANCE),
            ("Analysis", Screen.ANALYSIS),
            ("Settings", Screen.SETTINGS),
        ]
        for label, screen in buttons:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, s=screen: self.navigate(s))
            main_layout.addWidget(btn)

        main_menu.setLayout(main_layout)

        # ---------------------------
        # OTHER SCREENS
        # ---------------------------
        self.db: DatabaseInteractions = DatabaseInteractions()
        self.processing_window: ProcessingWindow = ProcessingWindow(self.stack, self.db)
        self.journal_window: JournalWindow = JournalWindow(self.stack, self.db)
        self.balance_window: BalanceWindow = BalanceWindow(self.stack, self.db)
        self.analysis_window: AnalysisWindow = AnalysisWindow(self.stack, self.db)
        self.settings_window: SettingsWindow = SettingsWindow(self.stack)

        # Add all screens to stack
        self.stack.addWidget(main_menu)               # index 0
        self.stack.addWidget(self.processing_window)  # index 1
        self.stack.addWidget(self.journal_window)     # index 2
        self.stack.addWidget(self.balance_window)     # index 3
        self.stack.addWidget(self.analysis_window)    # index 4
        self.stack.addWidget(self.settings_window)    # index 5

        # Set initial screen
        self.stack.setCurrentIndex(Screen.MENU)

        # Root layout
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.stack)
        self.setLayout(root_layout)

    def navigate(self, screen: Screen) -> None:
        """Switch the stack to the given screen, reloading its data first.

        Screens that maintain their own cached/loaded state
        (Processing, Journal, Balance) are refreshed via their
        respective ``load_*`` method before becoming visible, so the
        user always sees current data. Analysis and Settings don't need
        a reload trigger here (Analysis loads lazily per chart
        selection; Settings reads on construction).

        Args:
            screen: The screen to navigate to.
        """
        reload: Optional[Callable[[], None]] = {
            Screen.PROCESSING: self.processing_window.load_transactions,
            Screen.JOURNAL: self.journal_window.load_transactions,
            Screen.BALANCE: self.balance_window.load_categories,
        }.get(screen)
        if reload:
            reload()
        self.stack.setCurrentIndex(screen)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Restore the saved theme before showing any window
    saved = load_settings()
    apply_theme(saved.get("theme", "dark_teal.xml"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())