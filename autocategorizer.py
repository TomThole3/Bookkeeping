# -*- coding: utf-8 -*-
"""AI-assisted transaction categorisation.

This module defines :class:`AutoCategorizer`, which asks a local Ollama
model to assign a category to each unbooked transaction, optionally guided
by past user-confirmed categorisation examples (few-shot prompting).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import ollama

if TYPE_CHECKING:
    # Only needed for type-checking; avoids a hard runtime dependency/
    # circular import on the concrete Category and Transaction classes.
    from category import Category
    from transaction import Transaction

# A single past categorisation example, as stored by the database:
# (counterparty, description, amount, side, category_id)
ExampleTuple = Tuple[Optional[str], Optional[str], float, str, int]


class AutoCategorizer:
    """Assigns categories to transactions using a local LLM via Ollama.

    Transactions are sent to the model in batches, along with the list of
    valid category names and (optionally) a block of past examples used
    for few-shot guidance. The model's JSON response is parsed and
    validated against the known category names before being returned.

    Attributes:
        MODEL: Name of the Ollama model used for categorisation.
        BATCH_SIZE: Maximum number of transactions sent to the model per
            request.
        categories: The list of available :class:`Category` objects.
        examples: Past categorisation examples used for few-shot guidance.
        use_examples: Whether the examples block should be included in
            the prompt.
    """

    MODEL: str = "phi4-mini"
    BATCH_SIZE: int = 20

    def __init__(
        self,
        categories: List["Category"],
        examples: Optional[List[ExampleTuple]] = None,
        use_examples: bool = True,
    ) -> None:
        """Initialise the categorizer.

        Args:
            categories: The list of available categories a transaction can
                be assigned to.
            examples: Past categorisation examples, each shaped as
                ``(counterparty, description, amount, side, category_id)``.
                Defaults to an empty list if not provided.
            use_examples: If ``True``, ``examples`` are included in the
                prompt to guide the model. If ``False``, examples are
                ignored even if provided.
        """
        self.categories: List["Category"] = categories
        self._category_map: Dict[str, int] = {cat.name: cat.id for cat in categories}
        self._id_to_name: Dict[int, str] = {cat.id: cat.name for cat in categories}
        self.examples: List[ExampleTuple] = examples or []
        self.use_examples: bool = use_examples

    def _build_examples_block(self) -> str:
        """Build the few-shot examples section of the prompt.

        Returns:
            A formatted multi-line string listing past examples, or an
            empty string if ``use_examples`` is ``False`` or no examples
            are available.
        """
        if not self.use_examples or not self.examples:
            return ""
        lines = ["PAST EXAMPLES (use these to guide your decisions):"]
        for ex in self.examples:
            counterparty, description, amount, side, category_id = ex
            category_name = self._id_to_name.get(category_id, "Unknown")
            lines.append(
                f'  counterparty="{counterparty}", description="{description}", '
                f'amount={amount}, type={side} -> "{category_name}"'
            )
        return "\n".join(lines)

    def categorize(self, transactions: List["Transaction"]) -> Dict[str, int]:
        """Categorise a list of transactions using the configured model.

        Transactions are processed in batches of :attr:`BATCH_SIZE` to
        keep individual prompts a manageable size.

        Args:
            transactions: The transactions to categorise.

        Returns:
            A dict mapping each transaction's ``reference`` to the
            assigned ``category_id``. Transactions the model failed to
            categorise (or categorised with an unrecognised category
            name) are omitted from the result.
        """
        results: Dict[str, int] = {}
        for i in range(0, len(transactions), self.BATCH_SIZE):
            batch = transactions[i:i + self.BATCH_SIZE]
            results.update(self._categorize_batch(batch))
        return results

    def _categorize_batch(self, transactions: List["Transaction"]) -> Dict[str, int]:
        """Categorise a single batch of transactions in one model call.

        Builds a prompt containing the valid category names, the
        few-shot examples block (if enabled), and the transactions to
        categorise, then sends it to the configured Ollama model.

        Args:
            transactions: The batch of transactions to categorise. Should
                contain at most :attr:`BATCH_SIZE` items.

        Returns:
            A dict mapping transaction ``reference`` to ``category_id``
            for every transaction in the batch the model successfully
            categorised.
        """
        category_names = [cat.name for cat in self.categories]
        tx_list = [
            {
                "reference": t.reference,
                "counterparty": t.counterparty_name or "",
                "description": t.description or "",
                "amount": str(t.amount),
                "type": t.side,
            }
            for t in transactions
        ]
        examples_block = self._build_examples_block()

        prompt = f"""You are a bookkeeping assistant. Categorize each transaction into EXACTLY one of these categories:
        {json.dumps(category_names)}
        
        {examples_block}
        
        TRANSACTIONS TO CATEGORIZE:
        {json.dumps(tx_list, indent=2)}
        
        RULES:
        - Output ONLY a JSON object, no explanation, no markdown
        - Every value must be copied verbatim from the category list above
        - Use the past examples as guidance for similar transactions
        
        Output format: {{"reference1": "CategoryName", "reference2": "CategoryName"}}"""

        response = ollama.chat(
            model=self.MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw: str = response["message"]["content"].strip()
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> Dict[str, int]:
        """Parse and validate the model's raw JSON response.

        Extracts the first ``{...}`` block from the response (in case the
        model wrapped it in extra text or markdown fences), parses it as
        JSON, and filters out any category names that don't match a
        known category.

        Args:
            raw: The raw text content returned by the model.

        Returns:
            A dict mapping transaction ``reference`` to ``category_id``.
            Returns an empty dict if the response isn't valid JSON, or
            entries whose category name isn't recognised are dropped.
        """
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        raw = match.group(0) if match else raw.strip()
        try:
            assignments: Dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        raw = raw.strip()
        try:
            assignments = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return {
            ref: self._category_map[name]
            for ref, name in assignments.items()
            if name in self._category_map
        }

    def is_ollama_available(self) -> bool:
        """Check whether the local Ollama service is reachable.

        Returns:
            ``True`` if a call to ``ollama.list()`` succeeds, ``False``
            if it raises any exception (e.g. the service isn't running).
        """
        try:
            ollama.list()
            return True
        except Exception:
            return False