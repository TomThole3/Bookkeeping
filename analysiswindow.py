# -*- coding: utf-8 -*-
"""Analysis screen for the Muntenman bookkeeping application.

This module defines :class:`AnalysisWindow`, a PyQt6 widget that lets the
user pick a date range and a chart type, and then renders the corresponding
matplotlib chart using data supplied by :class:`AnalysisWindowBackend`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Sequence

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QDateEdit, QLabel,
)
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QStackedWidget
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from enumerations import Screen, Colours
from analysiswindowbackend import AnalysisWindowBackend

if TYPE_CHECKING:
    # Only needed for type-checking; avoids a hard runtime dependency/
    # circular import on the concrete database class.
    from database import DatabaseInteractions

# Chart registry: (display name, backend method name)
# Each entry maps a human-readable label shown in the chart selector combo
# box to the name of the ``AnalysisWindowBackend`` method that computes the
# data for that chart. The corresponding ``_draw_<method-without-get_>``
# method on this class is responsible for rendering it.
CHARTS: List[tuple[str, str]] = [
    ("Income vs Expenditure",           "get_income_vs_expenditure"),
    ("Category Breakdown",              "get_category_breakdown"),
    ("Spending per Category Over Time", "get_spending_per_category_over_time"),
    ("Top Counterparties",              "get_top_counterparties"),
    ("Running Balance",                 "get_running_balance"),
]


class AnalysisWindow(QWidget):
    """Screen that displays financial analysis charts.

    The user selects a date range and a chart type from the top bar; the
    corresponding chart is computed by :class:`AnalysisWindowBackend` and
    rendered onto an embedded matplotlib canvas.

    Attributes:
        backend: Backend object responsible for computing chart data.
        stack: The QStackedWidget that manages screen navigation.
        date_from: Date picker for the start of the analysis range.
        date_to: Date picker for the end of the analysis range.
        chart_selector: Combo box used to pick which chart to display.
        canvas: The currently displayed matplotlib canvas, or ``None`` if
            no chart is currently shown.
        canvas_widget: Container widget that hosts ``canvas``.
        canvas_container: Layout used to insert/remove ``canvas``.
        footer_widget: Widget hosting the bottom navigation bar.
        home_button: Button that returns the user to the main menu.
    """

    def __init__(self, stack: QStackedWidget, db: "DatabaseInteractions") -> None:
        """Initialise the analysis window.

        Args:
            stack: The QStackedWidget used for screen navigation.
            db: Database interactions object, passed through to the backend.
        """
        super().__init__()

        self.backend: AnalysisWindowBackend = AnalysisWindowBackend(db)
        self.stack: QStackedWidget = stack

        self.setWindowTitle("Muntenman Analyse")
        self.setGeometry(100, 100, 900, 600)

        # ── Main layout ─────────────────────────────────────────────
        layout = QVBoxLayout(self)

        self._add_top_bar(layout)
        self._add_canvas(layout)
        self._add_bottom_bar(layout)

    def _add_top_bar(self, layout: QVBoxLayout) -> None:
        """Build and add the top bar containing date pickers and chart selector.

        Args:
            layout: The parent layout to which the top bar is added.
        """
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("From:"))

        self.date_from: QDateEdit = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_from.dateChanged.connect(self._redraw)
        top_bar.addWidget(self.date_from)

        top_bar.addWidget(QLabel("To:"))

        self.date_to: QDateEdit = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self._redraw)
        top_bar.addWidget(self.date_to)

        top_bar.addWidget(QLabel("Chart:"))

        self.chart_selector: QComboBox = QComboBox()
        self.chart_selector.addItem("Select a chart…")
        for display_name, _ in CHARTS:
            self.chart_selector.addItem(display_name)
        self.chart_selector.currentIndexChanged.connect(self._on_chart_selected)
        top_bar.addWidget(self.chart_selector)

        top_bar.addStretch()
        layout.addLayout(top_bar)

    def _add_canvas(self, layout: QVBoxLayout) -> None:
        """Create the container that will host the matplotlib canvas.

        Args:
            layout: The parent layout to which the canvas container is added.
        """
        self.canvas: FigureCanvasQTAgg | None = None

        self.canvas_widget: QWidget = QWidget()
        self.canvas_container: QVBoxLayout = QVBoxLayout(self.canvas_widget)
        self.canvas_container.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.canvas_widget, 1)

    def _add_bottom_bar(self, layout: QVBoxLayout) -> None:
        """Build and add the bottom bar containing the "Return Home" button.

        Args:
            layout: The parent layout to which the bottom bar is added.
        """
        self.footer_widget: QWidget = QWidget()
        self.footer_widget.setStyleSheet("background-color: transparent;")  # optional

        bottom_bar = QHBoxLayout(self.footer_widget)
        bottom_bar.setContentsMargins(10, 10, 10, 10)

        bottom_bar.addStretch()

        self.home_button: QPushButton = QPushButton("Return Home")
        self.home_button.setMinimumHeight(40)
        self.home_button.clicked.connect(self._main_screen)
        bottom_bar.addWidget(self.home_button)

        layout.addWidget(self.footer_widget)

    # ── Data loading ───────────────────────────────────────────────────────

    def load(self) -> None:
        """Reset the screen to its initial state.

        Resets the chart selector to the placeholder entry and clears any
        chart currently displayed on the canvas. Called whenever this
        screen becomes active.
        """
        self.chart_selector.setCurrentIndex(0)
        self._clear_canvas()

    # ── Drawing ────────────────────────────────────────────────────────────

    def _on_chart_selected(self, index: int) -> None:
        """Handle a change of selection in the chart selector combo box.

        Args:
            index: The newly selected index in ``chart_selector``. Index 0
                corresponds to the "Select a chart…" placeholder.
        """
        if index == 0:
            self._clear_canvas()
        else:
            self._redraw()

    def _redraw(self) -> None:
        """Recompute chart data and redraw the currently selected chart.

        Does nothing if no chart is currently selected (i.e. the
        placeholder entry is active). Otherwise fetches fresh data from
        the backend for the selected date range and chart type, builds a
        new matplotlib :class:`~matplotlib.figure.Figure`, delegates
        drawing to the appropriate ``_draw_*`` method, and swaps it into
        the canvas.
        """
        if self.chart_selector.currentIndex() == 0:
            return

        date_from: str = self.date_from.date().toString("yyyy-MM-dd")
        date_to: str = self.date_to.date().toString("yyyy-MM-dd")
        _, method_name = CHARTS[self.chart_selector.currentIndex() - 1]  # offset for placeholder

        data: Dict[str, Any] = getattr(self.backend, method_name)(date_from, date_to)

        fig = Figure(figsize=(9, 5), tight_layout=True)
        ax = fig.add_subplot(111)

        draw_fn: Callable[[Axes, Dict[str, Any]], None] = getattr(
            self, f"_draw_{method_name.removeprefix('get_')}"
        )
        draw_fn(ax, data)

        self._replace_canvas(fig)

    def _clear_canvas(self) -> None:
        """Remove and dispose of the currently displayed canvas, if any."""
        if self.canvas is not None:
            self.canvas_container.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None

    def _replace_canvas(self, fig: Figure) -> None:
        """Replace the current canvas with one showing the given figure.

        Args:
            fig: The matplotlib figure to display.
        """
        self._clear_canvas()
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas_container.insertWidget(0, self.canvas)
        self.canvas.draw()

    # ── Chart renderers ────────────────────────────────────────────────────

    def _draw_income_vs_expenditure(self, ax: Axes, data: Dict[str, Any]) -> None:
        """Draw a grouped bar chart comparing monthly income and expenditure.

        Args:
            ax: The matplotlib axes to draw on.
            data: Dict with keys ``"months"`` (list of ``"YYYY-MM"`` strings),
                ``"income"`` (list of floats), and ``"expenditure"``
                (list of floats), as returned by
                :meth:`AnalysisWindowBackend.get_income_vs_expenditure`.
        """
        months = data["months"]
        income = data["income"]
        expenditure = data["expenditure"]

        if self._no_data_check(months, ax):
            return

        x = range(len(months))
        width = 0.35
        ax.bar([i - width / 2 for i in x], income,      width, label="Income",      color=Colours.COLOUR1)
        ax.bar([i + width / 2 for i in x], expenditure, width, label="Expenditure", color=Colours.COLOUR2)
        self._set_x_ticks(ax, months, x)
        ax.set_ylabel("Amount (€)")
        ax.set_title("Income vs Expenditure per Month")
        ax.legend()

    def _draw_category_breakdown(self, ax: Axes, data: Dict[str, Any]) -> None:
        """Draw a pie chart of expenditure broken down by top-level category.

        Args:
            ax: The matplotlib axes to draw on.
            data: Dict with keys ``"categories"`` (list of category names)
                and ``"amounts"`` (list of floats), as returned by
                :meth:`AnalysisWindowBackend.get_category_breakdown`.
        """
        categories = data["categories"]
        amounts    = data["amounts"]

        if self._no_data_check(categories, ax):
            return

        ax.pie(
            amounts,
            labels=categories,
            autopct="%1.1f%%",
            startangle=140,
        )
        ax.set_title("Expenditure by Top-Level Category")

    def _draw_spending_per_category_over_time(self, ax: Axes, data: Dict[str, Any]) -> None:
        """Draw a multi-line chart of monthly spending per top-level category.

        Args:
            ax: The matplotlib axes to draw on.
            data: Dict with keys ``"months"`` (list of ``"YYYY-MM"`` strings)
                and ``"series"`` (dict mapping category name to a list of
                monthly amounts), as returned by
                :meth:`AnalysisWindowBackend.get_spending_per_category_over_time`.
        """
        months = data["months"]
        series = data["series"]

        if self._no_data_check(months, ax):
            return

        x = range(len(months))
        for category, amounts in series.items():
            ax.plot(list(x), amounts, marker="o", label=category)

        self._set_x_ticks(ax, months, x)
        ax.set_ylabel("Amount (€)")
        ax.set_title("Monthly Spending per Category")
        ax.legend(loc="upper left", fontsize="small")

    def _draw_top_counterparties(self, ax: Axes, data: Dict[str, Any]) -> None:
        """Draw a horizontal bar chart of the top counterparties by expenditure.

        Args:
            ax: The matplotlib axes to draw on.
            data: Dict with keys ``"counterparties"`` (list of names) and
                ``"amounts"`` (list of floats), as returned by
                :meth:`AnalysisWindowBackend.get_top_counterparties`.
        """
        counterparties = data["counterparties"]
        amounts        = data["amounts"]

        if self._no_data_check(counterparties, ax):
            return

        # Horizontal bar chart — names can be long
        y = range(len(counterparties))
        ax.barh(list(y), amounts, color=Colours.COLOUR1)
        ax.set_yticks(list(y))
        ax.set_yticklabels(counterparties)
        ax.invert_yaxis()  # Largest at top
        ax.set_xlabel("Amount (€)")
        ax.set_title("Top Counterparties by Expenditure")

    def _draw_running_balance(self, ax: Axes, data: Dict[str, Any]) -> None:
        """Draw the cumulative net balance over time as a filled line chart.

        Args:
            ax: The matplotlib axes to draw on.
            data: Dict with keys ``"dates"`` (list of ``"YYYY-MM-DD"``
                strings) and ``"balance"`` (list of cumulative floats), as
                returned by :meth:`AnalysisWindowBackend.get_running_balance`.
        """
        dates   = data["dates"]
        balance = data["balance"]

        if self._no_data_check(dates, ax):
            return

        ax.plot(dates, balance, color=Colours.COLOUR3, linewidth=1.5)
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.fill_between(dates, balance, 0,
                         where=[b >= 0 for b in balance], alpha=0.15, color=Colours.COLOUR1)
        ax.fill_between(dates, balance, 0,
                         where=[b < 0  for b in balance], alpha=0.15, color=Colours.COLOUR2)

        n = max(1, len(dates) // 10)
        ax.set_xticks(dates[::n])
        ax.set_xticklabels(dates[::n], rotation=45, ha="right")
        ax.set_ylabel("Balance (€)")
        ax.set_title("Running Balance Over Time")

    def _no_data_check(self, data: Sequence[Any], ax: Axes) -> bool:
        """Show a "No data" placeholder message if ``data`` is empty.

        Args:
            data: The sequence to check for emptiness (e.g. months, dates,
                or category names for the chart currently being drawn).
            ax: The matplotlib axes on which to display the placeholder
                message, if needed.

        Returns:
            ``True`` if ``data`` was empty (and a placeholder was drawn),
            ``False`` otherwise.
        """
        if not data:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return True
        return False

    def _set_x_ticks(self, ax: Axes, months: Sequence[str], x: range) -> None:
        """Set rotated x-axis tick labels for month-based charts.

        Args:
            ax: The matplotlib axes whose x-ticks are being configured.
            months: The month labels (e.g. ``"YYYY-MM"``) to display.
            x: The numeric tick positions corresponding to ``months``.
        """
        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha="right")

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self) -> None:
        """Navigate back to the main menu screen."""
        self.stack.setCurrentIndex(Screen.MENU)