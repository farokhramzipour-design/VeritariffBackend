from typing import Tuple


def validate_required_fields(payload: dict) -> list[str]:
    errors = []
    if not payload.get("currency"):
        errors.append("currency required")
    if not payload.get("invoice_date"):
        errors.append("invoice_date required")
    line_items = payload.get("line_items") or []
    if not line_items:
        errors.append("at least one line item required")
    return errors


def reconcile_totals(payload: dict, tolerance: float = 0.01) -> Tuple[bool, str | None]:
    line_items = payload.get("line_items") or []
    if not line_items:
        return True, None

    line_total_sum = 0.0
    for item in line_items:
        line_total = item.get("line_total")
        if line_total is None:
            qty = item.get("quantity") or 0
            unit_price = item.get("unit_price") or 0
            line_total = qty * unit_price
        line_total_sum += float(line_total)

    subtotal = payload.get("subtotal")
    if subtotal is not None and abs(line_total_sum - float(subtotal)) > tolerance:
        return False, "subtotal does not match sum of line totals"

    total = payload.get("total")
    tax = payload.get("tax") or 0.0
    if total is not None and subtotal is not None:
        expected = float(subtotal) + float(tax)
        if abs(float(total) - expected) > tolerance:
            return False, "total does not match subtotal + tax"

    return True, None


def validate_quantities(payload: dict) -> list[str]:
    errors = []
    for idx, item in enumerate(payload.get("line_items") or []):
        qty = item.get("quantity")
        if qty is not None and qty < 0:
            errors.append(f"line_items[{idx}].quantity must be >= 0")
    return errors
