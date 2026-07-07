# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QDateEdit, QLabel,
)
from PyQt6.QtCore import QDate
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from enumerations import Screen
from analysiswindowbackend import AnalysisWindowBackend

# Chart registry: (display name, backend method name)
CHARTS = [
    ("Income vs Expenditure",           "get_income_vs_expenditure"),
    ("Category Breakdown",              "get_category_breakdown"),
    ("Spending per Category Over Time", "get_spending_per_category_over_time"),
    ("Top Counterparties",              "get_top_counterparties"),
    ("Running Balance",                 "get_running_balance"),
]

class AnalysisWindow(QWidget):
    def __init__(self, stack):
        super().__init__()

        self.backend = AnalysisWindowBackend()
        self.stack = stack

        self.setWindowTitle("Muntenman Analyse")
        self.setGeometry(100, 100, 900, 600)

        # ── Main layout ─────────────────────────────────────────────
        layout = QVBoxLayout(self)

        self._add_top_bar(layout)
        self._add_canvas(layout)
        self._add_bottom_bar(layout)
        
    def _add_top_bar(self, layout):
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("From:"))

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_from.dateChanged.connect(self._redraw)
        top_bar.addWidget(self.date_from)

        top_bar.addWidget(QLabel("To:"))

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self._redraw)
        top_bar.addWidget(self.date_to)

        top_bar.addWidget(QLabel("Chart:"))

        self.chart_selector = QComboBox()
        self.chart_selector.addItem("Select a chart…")
        for display_name, _ in CHARTS:
            self.chart_selector.addItem(display_name)
        self.chart_selector.currentIndexChanged.connect(self._on_chart_selected)
        top_bar.addWidget(self.chart_selector)

        top_bar.addStretch()
        layout.addLayout(top_bar)
        
    def _add_canvas(self, layout):
        self.canvas = None

        self.canvas_widget = QWidget()
        self.canvas_container = QVBoxLayout(self.canvas_widget)
        self.canvas_container.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.canvas_widget, 1)
        
    def _add_bottom_bar(self, layout):
        self.footer_widget = QWidget()
        self.footer_widget.setStyleSheet("background-color: transparent;")  # optional
        
        bottom_bar = QHBoxLayout(self.footer_widget)
        bottom_bar.setContentsMargins(10, 10, 10, 10)
        
        bottom_bar.addStretch()
        
        self.home_button = QPushButton("Return Home")
        self.home_button.setMinimumHeight(40)  # optional: makes it feel like a footer button
        self.home_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        bottom_bar.addWidget(self.home_button)
        
        layout.addWidget(self.footer_widget)
        
    # ── Data loading ───────────────────────────────────────────────────────

    def load(self):
        self.chart_selector.setCurrentIndex(0)
        self._clear_canvas()

    # ── Drawing ────────────────────────────────────────────────────────────

    def _on_chart_selected(self, index):
        if index == 0:
            self._clear_canvas()
        else:
            self._redraw()

    def _redraw(self):
        if self.chart_selector.currentIndex() == 0:
            return

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to   = self.date_to.date().toString("yyyy-MM-dd")
        _, method_name = CHARTS[self.chart_selector.currentIndex() - 1]  # offset for placeholder

        data = getattr(self.backend, method_name)(date_from, date_to)

        fig = Figure(figsize=(9, 5), tight_layout=True)
        ax = fig.add_subplot(111)

        draw_fn = getattr(self, f"_draw_{method_name.removeprefix('get_')}")
        draw_fn(ax, data)

        self._replace_canvas(fig)

    def _clear_canvas(self):
        if self.canvas is not None:
            self.canvas_container.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None

    def _replace_canvas(self, fig: Figure):
        self._clear_canvas()
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas_container.insertWidget(0, self.canvas)
        self.canvas.draw()

    # ── Chart renderers ────────────────────────────────────────────────────

    def _draw_income_vs_expenditure(self, ax, data):
        months      = data["months"]
        income      = data["income"]
        expenditure = data["expenditure"]

        if not months:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        x = range(len(months))
        width = 0.35
        ax.bar([i - width / 2 for i in x], income,      width, label="Income",      color="#4caf50")
        ax.bar([i + width / 2 for i in x], expenditure, width, label="Expenditure", color="#f44336")
        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Amount (€)")
        ax.set_title("Income vs Expenditure per Month")
        ax.legend()

    def _draw_category_breakdown(self, ax, data):
        categories = data["categories"]
        amounts    = data["amounts"]

        if not categories:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        ax.pie(
            amounts,
            labels=categories,
            autopct="%1.1f%%",
            startangle=140,
        )
        ax.set_title("Expenditure by Top-Level Category")

    def _draw_spending_per_category_over_time(self, ax, data):
        months = data["months"]
        series = data["series"]

        if not months:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        x = range(len(months))
        for category, amounts in series.items():
            ax.plot(list(x), amounts, marker="o", label=category)

        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Amount (€)")
        ax.set_title("Monthly Spending per Category")
        ax.legend(loc="upper left", fontsize="small")

    def _draw_top_counterparties(self, ax, data):
        counterparties = data["counterparties"]
        amounts        = data["amounts"]

        if not counterparties:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        # Horizontal bar chart — names can be long
        y = range(len(counterparties))
        ax.barh(list(y), amounts, color="#800080")
        ax.set_yticks(list(y))
        ax.set_yticklabels(counterparties)
        ax.invert_yaxis()  # Largest at top
        ax.set_xlabel("Amount (€)")
        ax.set_title("Top Counterparties by Expenditure")

    def _draw_running_balance(self, ax, data):
        dates   = data["dates"]
        balance = data["balance"]

        if not dates:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        ax.plot(dates, balance, color="#314159", linewidth=1.5)
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.fill_between(dates, balance, 0,
                         where=[b >= 0 for b in balance], alpha=0.15, color="#4caf50")
        ax.fill_between(dates, balance, 0,
                         where=[b < 0  for b in balance], alpha=0.15, color="#f44336")

        # Show every Nth date label to avoid crowding
        n = max(1, len(dates) // 10)
        ax.set_xticks(dates[::n])
        ax.set_xticklabels(dates[::n], rotation=45, ha="right")
        ax.set_ylabel("Balance (€)")
        ax.set_title("Running Balance Over Time")

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self):
        self.stack.setCurrentIndex(Screen.MENU)
