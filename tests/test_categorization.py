"""
SpendSense — Milestone 2 Tests: Deterministic Categorization.

Covers:
1. Every locked rule and pattern (R_TRANSFER, R_REFUND, R_INCOME, R_DINING,
   R_GROCERIES, R_SUBSCRIPTION, R_TRANSPORT)
2. Overlapping patterns and priority precedence (e.g., 'uber eats' vs 'uber',
   'transfer' vs 'dining')
3. Transaction-type restrictions (DEBIT-only, CREDIT-only, and ANY)
4. Case-insensitive and whitespace-tolerant matching
5. Documented fallbacks for unmatched DEBIT and CREDIT
6. Input validation (invalid types, non-string inputs)
7. Non-mutation of original descriptions and independent categorization
"""

import pytest

from categorization import (
    CATEGORIZATION_RULES,
    FALLBACK_CREDIT,
    FALLBACK_DEBIT,
    categorize_transaction,
    normalize_description,
)


# ============================================================================
# Section 1: Normalization Tests
# ============================================================================

def test_normalize_description_trimming_and_lowercase():
    """Test description text is trimmed and converted to lowercase."""
    assert normalize_description("  DMART STORE 018  ") == "dmart store 018"
    assert normalize_description("Uber Eats") == "uber eats"
    assert normalize_description("\tSWIGGY\n") == "swiggy"


def test_normalize_description_invalid_input():
    """Test non-string inputs raise ValueError."""
    for bad_input in [None, 123, ["description"]]:
        with pytest.raises(ValueError):
            normalize_description(bad_input)


# ============================================================================
# Section 2: Individual Rule Tests
# ============================================================================

@pytest.mark.parametrize(
    "pattern,tx_type,expected_cat,expected_rule_id",
    [
        # Priority 1: R_TRANSFER (applies to ANY)
        ("internal xfer to savings", "DEBIT", "Transfer", "R_TRANSFER"),
        ("monthly transfer from parent", "CREDIT", "Transfer", "R_TRANSFER"),
        ("wire xfer", "DEBIT", "Transfer", "R_TRANSFER"),
        # Priority 2: R_REFUND (applies to CREDIT)
        ("amazon refund processed", "CREDIT", "Refund", "R_REFUND"),
        ("fee reversal", "CREDIT", "Refund", "R_REFUND"),
        # Priority 3: R_INCOME (applies to CREDIT)
        ("monthly salary", "CREDIT", "Income", "R_INCOME"),
        ("company payroll", "CREDIT", "Income", "R_INCOME"),
        ("paycheck deposit", "CREDIT", "Income", "R_INCOME"),
        # Priority 10: R_DINING (applies to DEBIT)
        ("uber eats food order", "DEBIT", "Dining", "R_DINING"),
        ("swiggy bangalore", "DEBIT", "Dining", "R_DINING"),
        ("zomato gold", "DEBIT", "Dining", "R_DINING"),
        # Priority 20: R_GROCERIES (applies to DEBIT)
        ("dmart supercenter", "DEBIT", "Groceries", "R_GROCERIES"),
        ("bigbasket delivery", "DEBIT", "Groceries", "R_GROCERIES"),
        ("wholefoods market", "DEBIT", "Groceries", "R_GROCERIES"),
        # Priority 30: R_SUBSCRIPTION (applies to DEBIT)
        ("netflix monthly", "DEBIT", "Subscriptions", "R_SUBSCRIPTION"),
        ("spotify premium", "DEBIT", "Subscriptions", "R_SUBSCRIPTION"),
        ("prime video channel", "DEBIT", "Subscriptions", "R_SUBSCRIPTION"),
        # Priority 40: R_TRANSPORT (applies to DEBIT)
        ("uber trip ride", "DEBIT", "Transport", "R_TRANSPORT"),
        ("ola cabs", "DEBIT", "Transport", "R_TRANSPORT"),
        ("shell petrol pump", "DEBIT", "Transport", "R_TRANSPORT"),
        ("city fuel station", "DEBIT", "Transport", "R_TRANSPORT"),
    ],
)
def test_all_locked_rules_match_expected_category_and_rule_id(
    pattern, tx_type, expected_cat, expected_rule_id
):
    """Test every pattern in the locked rules assigns the exact category and rule_id."""
    cat, rule_id = categorize_transaction(pattern, tx_type)
    assert cat == expected_cat
    assert rule_id == expected_rule_id


# ============================================================================
# Section 3: Overlapping Pattern Priority Tests
# ============================================================================

def test_overlapping_priority_uber_eats_over_uber():
    """
    Priority 10 (R_DINING: 'uber eats') must win over Priority 40 (R_TRANSPORT: 'uber').
    """
    description = "Uber Eats Order #9988"
    cat, rule_id = categorize_transaction(description, "DEBIT")
    assert cat == "Dining"
    assert rule_id == "R_DINING"


def test_overlapping_priority_transfer_over_dining():
    """
    Priority 1 (R_TRANSFER: 'transfer') must win over Priority 10 (R_DINING: 'swiggy').
    """
    description = "Transfer for Swiggy payment"
    cat, rule_id = categorize_transaction(description, "DEBIT")
    assert cat == "Transfer"
    assert rule_id == "R_TRANSFER"


def test_overlapping_priority_transfer_over_transport():
    """
    Priority 1 (R_TRANSFER: 'xfer') must win over Priority 40 (R_TRANSPORT: 'ola').
    """
    description = "Internal xfer ola ride"
    cat, rule_id = categorize_transaction(description, "DEBIT")
    assert cat == "Transfer"
    assert rule_id == "R_TRANSFER"


# ============================================================================
# Section 4: Transaction-Type Restrictions
# ============================================================================

def test_refund_requires_credit():
    """A DEBIT containing 'refund' must NOT match R_REFUND (CREDIT only)."""
    cat, rule_id = categorize_transaction("merchant refund charge", "DEBIT")
    assert cat == "Uncategorized"
    assert rule_id == "R_UNKNOWN_DEBIT"


def test_income_requires_credit():
    """A DEBIT containing 'salary' must NOT match R_INCOME (CREDIT only)."""
    cat, rule_id = categorize_transaction("salary payment adjustment", "DEBIT")
    assert cat == "Uncategorized"
    assert rule_id == "R_UNKNOWN_DEBIT"


def test_dining_requires_debit():
    """A CREDIT containing 'swiggy' must NOT match R_DINING (DEBIT only)."""
    cat, rule_id = categorize_transaction("swiggy cash credit", "CREDIT")
    assert cat == "Other Credit"
    assert rule_id == "R_UNKNOWN_CREDIT"


def test_groceries_requires_debit():
    """A CREDIT containing 'dmart' must NOT match R_GROCERIES (DEBIT only)."""
    cat, rule_id = categorize_transaction("dmart store deposit", "CREDIT")
    assert cat == "Other Credit"
    assert rule_id == "R_UNKNOWN_CREDIT"


def test_transport_requires_debit():
    """A CREDIT containing 'uber' must NOT match R_TRANSPORT (DEBIT only)."""
    cat, rule_id = categorize_transaction("uber promotional credit", "CREDIT")
    assert cat == "Other Credit"
    assert rule_id == "R_UNKNOWN_CREDIT"


def test_subscriptions_requires_debit():
    """A CREDIT containing 'netflix' must NOT match R_SUBSCRIPTION (DEBIT only)."""
    cat, rule_id = categorize_transaction("netflix credit balance", "CREDIT")
    assert cat == "Other Credit"
    assert rule_id == "R_UNKNOWN_CREDIT"


def test_transfer_applies_to_any():
    """R_TRANSFER matches both DEBIT and CREDIT."""
    cat_debit, rule_debit = categorize_transaction("bank transfer", "DEBIT")
    cat_credit, rule_credit = categorize_transaction("bank transfer", "CREDIT")
    assert cat_debit == "Transfer" and rule_debit == "R_TRANSFER"
    assert cat_credit == "Transfer" and rule_credit == "R_TRANSFER"


# ============================================================================
# Section 5: Case and Whitespace Tolerance
# ============================================================================

def test_case_insensitive_matching():
    """Matching must be case-insensitive."""
    assert categorize_transaction("dMaRt StOrE", "DEBIT") == ("Groceries", "R_GROCERIES")
    assert categorize_transaction("NETFLIX", "DEBIT") == ("Subscriptions", "R_SUBSCRIPTION")
    assert categorize_transaction("UBER EATS", "DEBIT") == ("Dining", "R_DINING")
    assert categorize_transaction("SALARY", "CREDIT") == ("Income", "R_INCOME")


def test_type_case_and_whitespace_normalization():
    """Transaction type accepts mixed case and surrounding whitespace."""
    assert categorize_transaction("swiggy", " debit ") == ("Dining", "R_DINING")
    assert categorize_transaction("salary", " Credit ") == ("Income", "R_INCOME")


# ============================================================================
# Section 6: Fallback Handling
# ============================================================================

def test_unmatched_debit_fallback():
    """Unmatched DEBIT transaction falls back to ('Uncategorized', 'R_UNKNOWN_DEBIT')."""
    cat, rule_id = categorize_transaction("Custom Bookstore 404", "DEBIT")
    assert (cat, rule_id) == FALLBACK_DEBIT
    assert cat == "Uncategorized"
    assert rule_id == "R_UNKNOWN_DEBIT"


def test_unmatched_credit_fallback():
    """Unmatched CREDIT transaction falls back to ('Other Credit', 'R_UNKNOWN_CREDIT')."""
    cat, rule_id = categorize_transaction("Unidentified Deposit", "CREDIT")
    assert (cat, rule_id) == FALLBACK_CREDIT
    assert cat == "Other Credit"
    assert rule_id == "R_UNKNOWN_CREDIT"


# ============================================================================
# Section 7: Input Validation
# ============================================================================

def test_invalid_transaction_type_raises_value_error():
    """Invalid transaction types raise ValueError."""
    for invalid_type in ["UNKNOWN", "TRANSFER", "", "   ", 123]:
        with pytest.raises(ValueError):
            categorize_transaction("some description", invalid_type)


def test_invalid_description_type_raises_value_error():
    """Non-string description raises ValueError."""
    for invalid_desc in [None, 123, []]:
        with pytest.raises(ValueError):
            categorize_transaction(invalid_desc, "DEBIT")


# ============================================================================
# Section 8: Immutability and Independence
# ============================================================================

def test_original_description_is_not_mutated():
    """Categorization must not mutate or alter the original description object."""
    original = "  DMART Store 018  "
    original_copy = original[:]
    cat, rule_id = categorize_transaction(original, "DEBIT")
    assert cat == "Groceries"
    assert original == original_copy
    assert original == "  DMART Store 018  "


def test_multiple_independent_transactions():
    """Multiple transactions must be categorized independently without state leakage."""
    transactions = [
        ("uber eats", "DEBIT", "Dining", "R_DINING"),
        ("uber cab", "DEBIT", "Transport", "R_TRANSPORT"),
        ("monthly salary", "CREDIT", "Income", "R_INCOME"),
        ("dmart supercenter", "DEBIT", "Groceries", "R_GROCERIES"),
        ("unknown expense", "DEBIT", "Uncategorized", "R_UNKNOWN_DEBIT"),
        ("unknown gift", "CREDIT", "Other Credit", "R_UNKNOWN_CREDIT"),
    ]
    for desc, tx_type, expected_cat, expected_rule in transactions:
        res_cat, res_rule = categorize_transaction(desc, tx_type)
        assert res_cat == expected_cat
        assert res_rule == expected_rule
