"""Holiday pay (feriepenge) — a separate income stream from ordinary
salary, never folded into monthly net salary automatically.

Two flavours, chosen by income mode (see docs/research_2026.md item 13a):
- Hourly Wage mode -> feriegodtgørelse, 12.5% of gross (base + tips).
- Fixed Salary mode -> ferietillæg, 1% of gross (base + tips), since a
  funktionær instead gets paid holiday leave itself.

Both are AM-bidrag-liable A-indkomst taxed "at the employee's current
withholding rate" rather than a fresh bracket calculation — the ordinary
salary in the same period has already consumed the personal allowance and
the lower brackets, so re-running the full bracket logic on holiday pay
would double-count that allowance. Standard-estimate mode therefore uses
the person's current MARGINAL combined rate; tax-card mode applies the
supplied percentage directly, with no second fradrag. ATP is not charged
on holiday pay (documented assumption — ATP accrues on hours worked, not
on a holiday payout).
"""
from __future__ import annotations

from decimal import Decimal

from app.models.salary_input import IncomeType, TaxCardMode
from app.models.tax_result import HolidayPayResult


def determine_marginal_state_rate(personlig_indkomst: Decimal, brackets: dict) -> Decimal:
    """Sum of every state-tax bracket rate the person's ordinary personlig
    indkomst already reaches — i.e. the rate the NEXT krone of income is
    taxed at, since the personal allowance and lower brackets are already
    used up by the ordinary salary in the same period."""
    rate = Decimal(str(brackets["bundskat"]["rate"]))
    if personlig_indkomst > Decimal(str(brackets["mellemskat"]["threshold"])):
        rate += Decimal(str(brackets["mellemskat"]["rate"]))
    if personlig_indkomst > Decimal(str(brackets["topskat"]["threshold"])):
        rate += Decimal(str(brackets["topskat"]["rate"]))
    if personlig_indkomst > Decimal(str(brackets["ekstra_topskat"]["threshold"])):
        rate += Decimal(str(brackets["ekstra_topskat"]["rate"]))
    return rate


def compute_holiday_pay(
    income_type: IncomeType,
    holiday_eligible_gross: Decimal,
    am_rate: Decimal,
    municipal_rate: Decimal,
    church_rate: Decimal,
    is_church_member: bool,
    personlig_indkomst: Decimal,
    state_tax_brackets: dict,
    tax_card_mode: TaxCardMode,
    tax_card_percentage: Decimal | None,
    holiday_pay_rules: dict,
) -> HolidayPayResult:
    if income_type is IncomeType.HOURLY_WAGE:
        rate = Decimal(str(holiday_pay_rules["feriegodtgorelse_rate"]))
        label = "feriegodtgørelse (12.5%)"
    else:
        rate = Decimal(str(holiday_pay_rules["ferietillaeg_rate"]))
        label = "ferietillæg (1%)"

    gross = holiday_eligible_gross * rate
    am_amount = gross * am_rate
    am_base = gross - am_amount

    if tax_card_mode is TaxCardMode.MY_TAX_CARD:
        marginal_rate = tax_card_percentage or Decimal(0)
    else:
        marginal_rate = (
            municipal_rate
            + (church_rate if is_church_member else Decimal(0))
            + determine_marginal_state_rate(personlig_indkomst, state_tax_brackets)
        )

    income_tax = am_base * marginal_rate
    net = gross - am_amount - income_tax

    return HolidayPayResult(
        rate_used=rate,
        rate_label=label,
        gross=gross,
        am_bidrag=am_amount,
        income_tax=income_tax,
        net=net,
        marginal_rate_applied=marginal_rate,
    )
