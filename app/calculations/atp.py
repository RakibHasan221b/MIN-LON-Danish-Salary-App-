"""ATP employee contribution — a fixed DKK table keyed by hours worked and
pay frequency, NOT a percentage of salary. See docs/research_2026.md
item 7 for the verified 2026 source values.
"""
from __future__ import annotations

from decimal import Decimal

from app.data_loader import load_atp_rules


def get_atp_employee_contribution(
    hours_worked: Decimal, pay_frequency: str = "monthly", year: int = 2026
) -> Decimal:
    """Look up the employee's ATP contribution for the given hours worked
    in the period, at the given pay frequency ('monthly' | 'biweekly' |
    'weekly')."""
    atp_data = load_atp_rules(year)
    try:
        frequency_data = atp_data["pay_frequencies"][pay_frequency]
    except KeyError as exc:
        raise ValueError(
            f"Unknown pay_frequency '{pay_frequency}'. "
            f"Available: {list(atp_data['pay_frequencies'])}"
        ) from exc

    # Brackets are matched purely by their lower bound, checked from the
    # highest threshold down: this correctly handles fractional hours
    # (e.g. 39h30m) that fall strictly between two whole-hour brackets,
    # which a naive [min, max] range check would miss at the boundary.
    # `max_hours` in the data file is descriptive only, not used for
    # matching.
    brackets_by_min_desc = sorted(
        frequency_data["brackets"],
        key=lambda b: Decimal(str(b["min_hours"])),
        reverse=True,
    )
    for bracket in brackets_by_min_desc:
        min_hours = Decimal(str(bracket["min_hours"]))
        if hours_worked >= min_hours:
            return Decimal(str(bracket["employee_contribution"]))

    # Should be unreachable since the lowest bracket has min_hours == 0,
    # but fail loudly rather than silently returning 0 if the data file
    # is ever malformed.
    raise ValueError(
        f"No ATP bracket matched {hours_worked} hours at frequency '{pay_frequency}'"
    )
