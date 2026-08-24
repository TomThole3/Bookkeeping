# Bookkeeping
This bookkeeping program is a personal bookkeeping desktop application built with PyQt6. It imports bank statements (CAMT.053 XML), lets you categorize transactions manually or with AI assistance, and gives you a journal, a rolled-up category balance overview, and a set of analysis charts to understand your income and spending over time. A local SQLite database is used for storage, and an optional local LLM (via Ollama) can suggest categories for new transactions, using few-shot learning to optimize its performance.

## Features
- Import bank transactions from CAMT.053 XML statement files
- Manually categorize transactions, or split a single transaction across multiple categories
- AI-assisted categorization using a local LLM (via Ollama), with optional few-show learning corrections
- Journal screen with live filtering by reference, side, category, counterparty, description, amount range, and date range
- Balance screen showing a nested category tree with rolled-up income, expenditure, and net totals, with drill-down to the underlying transactions
- Analysis screen with five chart types: income vs. expenditure, category breakdown, spending per category over time, top counterparties, and running balance
- Memorial (manual journal) transactions for entries that don't come from a bank statement
- Selectable qt-material themes, saved between sessions

## Requirements
Python 3.10+
A CAMT.053 bank statement export (most European banks can produce these)
Optional: [Ollama](https://ollama.com) running locally with the `phi4-mini` model pulled, for AI-assisted categorization

Install the Python dependencies with:
```
pip install -r requirements.txt
```

If you want AI-assisted categorization, install Ollama separately and pull the model it expects:
```
ollama pull phi4-mini
```
The app works without Ollama running — the "Auto-categorize (AI)" button will simply show an error if it can't reach it, and all transactions can still be categorized manually.

## Explanation of example files
The app reads its configuration from `settings.json` in the project root. If the file is missing, it's created automatically with default values, so no manual setup is required. It has the following attributes, see also `settings.example.json`:
```
{
  "theme": "dark_teal.xml",
  "use_examples": true
}
```
`theme` is any theme name shipped with `qt-material`, selectable from the in-app Settings screen. `use_examples` controls whether past categorization corrections are included in the AI prompt as few-shot examples.

Transaction and category data is stored in `transactions.db`, a SQLite database created automatically in the project root on first run. This file is not included in the repository (see `.gitignore`) since it contains personal financial data once you start using the app.

## Running the application
The application is run from `startwindow.py`:
```
python startwindow.py
```
On first launch, use "Process transactions" to import a CAMT.053 file, then assign a category to each transaction (or split it across several) before booking it. Once booked, transactions appear in the Journal and are reflected in the Balance and Analysis screens.

## How it works (High level)
- Settings are loaded and the saved theme is applied
- A CAMT.053 file is parsed into individual transactions, deduplicated by reference, and stored as unbooked
- Unbooked transactions are shown for categorization, either picked manually or suggested by the local LLM
- On booking, single transactions update in place; transactions split into multiple parts are validated so their amounts sum back to the original total, then stored as separate linked rows
- User-confirmed categorizations are saved as examples to guide future AI suggestions
- The Journal, Balance, and Analysis screens all read from the same booked-transaction data, filtered or aggregated differently per screen
- Unbooking a transaction (from Journal or Balance) clears its category; unbooking a split transaction reverts all of its parts, and deleting a memorial entry removes both of its legs

## Notes
LLMs aided with a large part of the project and its documentation.

## Limitations
The project has several limitations. Firstly, the CAMT.053 parser is pinned to a specific XML namespace version (`camt.053.001.02`); statements exported in a different version may need a small adjustment to `camt_parser.py` before they'll parse correctly. Secondly, AI-assisted categorization requires a local Ollama installation and is only as accurate as the underlying model and the quality of past corrections it's been given as examples. It should be treated as a starting suggestion, not a final answer. Thirdly, all amounts are formatted in Euros; other currencies aren't currently supported. Finally, the application is single-user and single-database by design, with no built-in export, backup or multi-currency functionality.
