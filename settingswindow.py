import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt
import qt_material

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DEFAULT_SETTINGS = {"theme": "dark_teal.xml", "use_examples": True}

# All themes shipped with qt-material
THEMES = qt_material.list_themes()


def load_settings() -> dict:
    """Load persisted settings from disk. If the file is missing or
    unreadable, create it with default settings and return those."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Persist settings to disk."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError as e:
        print(f"Could not save settings: {e}")


def apply_theme(theme: str) -> None:
    """Apply a qt-material theme to the running QApplication."""
    app = QApplication.instance()
    if app is not None:
        qt_material.apply_stylesheet(app, theme=theme)


class SettingsWindow(QWidget):
    """
    Settings screen for Muntenman Centraal.

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
    """

    def __init__(self, stack, parent=None):
        super().__init__(parent)
        self.stack = stack
        self._settings = load_settings()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
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

        self.theme_combo = QComboBox()
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

        self.chk_examples = QCheckBox("Use transaction examples (few-shot learning)")
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

        self.btn_save = QPushButton("Save & apply")
        self.btn_save.clicked.connect(self._save_and_apply)
        btn_row.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    def _on_theme_preview(self, theme: str) -> None:
        """Preview the theme live as the user scrolls through the list."""
        apply_theme(theme)

    def _save_and_apply(self) -> None:
        theme = self.theme_combo.currentText()
        apply_theme(theme)
        self._settings["theme"] = theme
        self._settings["use_examples"] = self.chk_examples.isChecked()
        save_settings(self._settings)
        self.stack.setCurrentIndex(0)

    def _cancel(self) -> None:
        # Revert both controls to the last saved state
        saved_theme = self._settings.get("theme", "dark_teal.xml")
        apply_theme(saved_theme)
        self.theme_combo.setCurrentText(saved_theme)
        self.chk_examples.setChecked(self._settings.get("use_examples", True))
        self.stack.setCurrentIndex(0)