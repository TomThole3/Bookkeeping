# -*- coding: utf-8 -*-
"""Settings screen and persisted-settings helpers for Muntenman Centraal.

This module provides:

* Module-level helpers (:func:`load_settings`, :func:`save_settings`,
  :func:`apply_theme`) for reading/writing ``settings.json`` and
  applying a qt-material theme to the running application.
* :class:`SettingsWindow`, the UI screen letting the user pick a theme
  and toggle AI few-shot categorisation, with live theme preview and
  cancel/save semantics.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QCheckBox, QApplication,
    QStackedWidget,
)
from PyQt6.QtCore import Qt
import qt_material
from util.enumerations import Screen

#: Absolute path to the settings JSON file, stored alongside this module.
SETTINGS_FILE: str = os.path.join(os.path.dirname(__file__), "settings.json")

#: Settings applied when no settings file exists yet or it can't be read.
DEFAULT_SETTINGS: Dict[str, Any] = {"theme": "dark_teal.xml", "use_examples": True}

# All themes shipped with qt-material
THEMES: List[str] = qt_material.list_themes()


def load_settings() -> Dict[str, Any]:
    """Load persisted settings from disk.

    If the file is missing or unreadable, create it with default
    settings and return those.

    Returns:
        The parsed settings dict, or a copy of :data:`DEFAULT_SETTINGS`
        if the file didn't exist or couldn't be parsed.
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist settings to disk.

    Args:
        settings: The settings dict to write to :data:`SETTINGS_FILE`
            as indented JSON.

    Note:
        Failures are logged to stdout rather than raised, so a
        read-only filesystem or permissions issue won't crash the
        caller.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError as e:
        print(f"Could not save settings: {e}")


def apply_theme(theme: str) -> None:
    """Apply a qt-material theme to the running QApplication.

    Args:
        theme: Name of a theme from :data:`THEMES` (e.g.
            ``"dark_teal.xml"``).

    Note:
        Does nothing if there is no running :class:`QApplication`
        instance (e.g. called before the app is constructed).
    """
    app = QApplication.instance()
    if app is not None:
        qt_material.apply_stylesheet(app, theme=theme)


class SettingsWindow(QWidget):
    """
    Settings screen for the bookkeeping application.

    Usage – add to your stack just like the other windows:

        from settingswindow import SettingsWindow, load_settings, apply_theme

        # In MainWindow.__init__, after creating the other windows:
        self.settings_window = SettingsWindow(self.stack)
        self.stack.addWidget(self.settings_window)   # index 5

    And add a navigation method + button:

        def settings(self):
            self.stack.setCurrentIndex(5)

    Call apply_theme(load_settings()["theme"]) once during startup
    (before window.show()) so the saved theme is restored automatically.

    Attributes:
        stack: The QStackedWidget that manages screen navigation.
        theme_combo: Dropdown for selecting a qt-material theme; changes
            are previewed live.
        chk_examples: Checkbox toggling whether few-shot examples are
            used for AI categorisation.
        btn_save: Button that persists the current selections and
            returns to the main menu.
        btn_cancel: Button that reverts to the last saved settings and
            returns to the main menu.
    """

    def __init__(self, stack: QStackedWidget, parent: Optional[QWidget] = None) -> None:
        """Initialise the settings screen.

        Args:
            stack: The QStackedWidget used for screen navigation.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.stack: QStackedWidget = stack
        self._settings: Dict[str, Any] = load_settings()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the settings form: title, appearance group, and AI group.

        Populates ``theme_combo`` from the saved theme (falling back to
        the qt-material default if the saved value isn't a known
        theme), and ``chk_examples`` from the saved ``use_examples``
        flag.
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        root.addWidget(title)

        # ── Theme group ────────────────────────────────────────────────
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(12)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setFixedWidth(80)
        theme_row.addWidget(theme_label)

        self.theme_combo: QComboBox = QComboBox()
        self.theme_combo.addItems(THEMES)
        current = self._settings.get("theme", "dark_teal.xml")
        if current in THEMES:
            self.theme_combo.setCurrentText(current)
        self.theme_combo.currentTextChanged.connect(self._on_theme_preview)
        theme_row.addWidget(self.theme_combo, stretch=1)

        theme_layout.addLayout(theme_row)
        root.addWidget(theme_group)

        # ── AI / categorisation group ──────────────────────────────────
        ai_group = QGroupBox("Categorisation")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(12)

        self.chk_examples: QCheckBox = QCheckBox("Use transaction examples (few-shot learning)")
        self.chk_examples.setChecked(self._settings.get("use_examples", True))
        self.chk_examples.setToolTip(
            "When enabled, past categorised transactions are included in the prompt "
            "to guide the AI. Disable to let the model rely on category names only."
        )
        ai_layout.addWidget(self.chk_examples)

        root.addWidget(ai_group)

        # ── Buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_save: QPushButton = QPushButton("Save & apply")
        self.btn_save.clicked.connect(self._save_and_apply)
        btn_row.addWidget(self.btn_save)

        self.btn_cancel: QPushButton = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    def _on_theme_preview(self, theme: str) -> None:
        """Preview the theme live as the user scrolls through the list.

        Args:
            theme: The newly selected theme name, applied immediately
                without waiting for "Save & apply".
        """
        apply_theme(theme)

    def _save_and_apply(self) -> None:
        """Persist the current theme and examples selections, then navigate home.

        Applies the selected theme (redundant if already previewed, but
        ensures consistency), updates the in-memory settings dict,
        writes it to disk, and returns to the main menu.
        """
        theme = self.theme_combo.currentText()
        apply_theme(theme)
        self._settings["theme"] = theme
        self._settings["use_examples"] = self.chk_examples.isChecked()
        save_settings(self._settings)
        self.stack.setCurrentIndex(0)

    def _cancel(self) -> None:
        """Revert to the last saved settings and navigate home.

        Re-applies the previously saved theme (undoing any live
        preview), resets both controls to their saved values, and
        returns to the main menu without writing anything to disk.
        """
        # Revert both controls to the last saved state
        saved_theme = self._settings.get("theme", "dark_teal.xml")
        apply_theme(saved_theme)
        self.theme_combo.setCurrentText(saved_theme)
        self.chk_examples.setChecked(self._settings.get("use_examples", True))
        self.stack.setCurrentIndex(Screen.MENU)