# -*- coding: utf-8 -*-

import json
import ollama

class AutoCategorizer:
    MODEL = "phi4-mini"
    BATCH_SIZE = 20

    def __init__(self, categories: list, examples: list = None):
        self.categories = categories
        self._category_map = {cat.name: cat.id for cat in categories}
        self._id_to_name = {cat.id: cat.name for cat in categories}  # needed to render examples
        self.examples = examples or []
    
    def _build_examples_block(self) -> str:
        if not self.examples:
            return ""
        lines = ["PAST EXAMPLES (use these to guide your decisions):"]
        for ex in self.examples:
            counterparty, description, amount, cdt_dbt, category_id = ex
            category_name = self._id_to_name.get(category_id, "Unknown")
            lines.append(
                f'  counterparty="{counterparty}", description="{description}", '
                f'amount={amount}, type={cdt_dbt} -> "{category_name}"'
            )
        return "\n".join(lines)

    def categorize(self, transactions: list) -> dict:
        """Returns {reference: category_id} for each transaction."""
        results = {}
        for i in range(0, len(transactions), self.BATCH_SIZE):
            batch = transactions[i:i + self.BATCH_SIZE]
            results.update(self._categorize_batch(batch))
        return results

    def _categorize_batch(self, transactions: list) -> dict:
        category_names = [cat.name for cat in self.categories]
        tx_list = [
            {
                "reference": t.reference,
                "counterparty": t.counterparty_name or "",
                "description": t.description or "",
                "amount": str(t.amount),
                "type": t.cdt_dbt,
            }
            for t in transactions
        ]

        examples_block = self._build_examples_block()
        print(examples_block)
        
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

        raw = response["message"]["content"].strip()
        print(raw)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
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
