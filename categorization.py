"""
SpendSense — Transaction Categorization Module.

This module implements Milestone 2: Deterministic Categorization.
Rules are evaluated in explicit priority order (first match wins).
Each rule matches a normalized substring and is constrained by transaction type (DEBIT, CREDIT, or ANY).

Required fallback rules:
- Unmatched DEBIT -> ('Uncategorized', 'R_UNKNOWN_DEBIT')
- Unmatched CREDIT -> ('Other Credit', 'R_UNKNOWN_CREDIT')
"""

from typing import Any

# Locked categorization rules from SpendSense_Final_Architecture_LOCKED_v1_2.md Section 6
CATEGORIZATION_RULES: tuple[dict[str, Any], ...] = (
    {
        "priority": 1,
        "rule_id": "R_TRANSFER",
        "patterns": ("internal xfer", "transfer", "xfer"),
        "applies_to": "ANY",
        "category": "Transfer",
    },
    {
        "priority": 2,
        "rule_id": "R_REFUND",
        "patterns": ("refund", "reversal"),
        "applies_to": "CREDIT",
        "category": "Refund",
    },
    {
        "priority": 3,
        "rule_id": "R_INCOME",
        "patterns": ("salary", "payroll", "paycheck"),
        "applies_to": "CREDIT",
        "category": "Income",
    },
    {
        "priority": 10,
        "rule_id": "R_DINING",
        "patterns": ("uber eats", "swiggy", "zomato"),
        "applies_to": "DEBIT",
        "category": "Dining",
    },
    {
        "priority": 20,
        "rule_id": "R_GROCERIES",
        "patterns": ("dmart", "bigbasket", "wholefoods"),
        "applies_to": "DEBIT",
        "category": "Groceries",
    },
    {
        "priority": 30,
        "rule_id": "R_SUBSCRIPTION",
        "patterns": ("netflix", "spotify", "prime video"),
        "applies_to": "DEBIT",
        "category": "Subscriptions",
    },
    {
        "priority": 40,
        "rule_id": "R_TRANSPORT",
        "patterns": ("uber", "ola", "shell", "fuel"),
        "applies_to": "DEBIT",
        "category": "Transport",
    },
)

# Documented fallback categories and rule IDs
FALLBACK_DEBIT: tuple[str, str] = ("Uncategorized", "R_UNKNOWN_DEBIT")
FALLBACK_CREDIT: tuple[str, str] = ("Other Credit", "R_UNKNOWN_CREDIT")


def normalize_description(description: str) -> str:
    """
    Return the normalized matching text.

    Trims surrounding whitespace and converts to lowercase.
    Preserves original description elsewhere for reporting.
    """
    if not isinstance(description, str):
        raise ValueError("description must be a string")
    return description.strip().lower()


def categorize_transaction(description: str, transaction_type: str) -> tuple[str, str]:
    """
    Categorize a transaction based on description and transaction type.

    Applies deterministic, ordered rules where the first applicable match wins.
    Returns (category, rule_id).

    Raises:
    - ValueError if description is not a string or transaction_type is not 'DEBIT' or 'CREDIT'.
    """
    if not isinstance(description, str):
        raise ValueError("description must be a string")
    if not isinstance(transaction_type, str):
        raise ValueError("transaction_type must be a string")

    norm_type = transaction_type.strip().upper()
    if norm_type not in ("DEBIT", "CREDIT"):
        raise ValueError(f"Invalid transaction type: '{transaction_type}'. Must be 'DEBIT' or 'CREDIT'.")

    norm_desc = normalize_description(description)

    # Evaluate rules in documented priority order
    for rule in CATEGORIZATION_RULES:
        applies_to = rule["applies_to"]
        if applies_to == "ANY" or applies_to == norm_type:
            for pattern in rule["patterns"]:
                if pattern in norm_desc:
                    return (rule["category"], rule["rule_id"])

    # Fallback when no rule matches
    if norm_type == "DEBIT":
        return FALLBACK_DEBIT
    return FALLBACK_CREDIT
