"""Orchestrates the full pipeline described in the spec:

gross_income -> ATP -> AM-bidrag -> personlig indkomst -> allowances ->
skattepligtig indkomst -> state tax -> municipal tax -> church tax ->
net income

`calculate_annual_tax()` and `calculate_monthly_withholding()` are kept
separate (per spec) but share every lower-level function in this package
— only the constants they're called with differ (annual constants vs
constants divided by 12 for the monthly estimate).

V1.1 additions (see docs/old_streamlit_feature_audit.md): tips are added
to the taxable base before ATP/AM-bidrag/allowances/tax run (never added
after tax); an optional extra_deduction reduces skattepligtig indkomst
(the municipal/church tax base) rather than duplicating the automatic
personfradrag; holiday pay is computed as a fully separate income stream
via app.calculations.holiday_pay and never folded into ordinary net
salary automatically; total_with_holiday sums the two already-computed
streams without double-counting AM-bidrag or allowances.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.calculations import allowances, am_bidrag, atp, municipal_tax, salary, tax
from app.calculations.frikort import compute_frikort_withholding
from app.calculations.holiday_pay import compute_holiday_pay
from app.calculations.withholding import compute_tax_card_withholding
from app.data_loader import get_municipality, load_tax_rules
from app.models.salary_input import SalaryInput, TaxCardMode, TaxCardType
from app.models.tax_result import CalculationBasis, TaxResult, TotalWithHolidayResult

MONTHS_PER_YEAR = Decimal(12)


def round_dkk(amount: Decimal) -> Decimal:
    """Round to the nearest whole DKK, half-up — matches how Danish
    payslips present line items. See docs/research_2026.md item 12."""
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _scaled_tax_rules(tax_rules: dict, period: str) -> dict:
    """Annual constants used as-is; monthly constants are the annual
    figures divided by 12, per docs/research_2026.md item 11 (this
    mirrors how SKAT derives its own monthly trækprocent tables from
    annual figures rather than maintaining a separate monthly rule set)."""
    if period == "annual":
        return tax_rules

    divisor = MONTHS_PER_YEAR
    scaled = {
        "am_bidrag": tax_rules["am_bidrag"],
        "personal_allowance": {
            **tax_rules["personal_allowance"],
            "annual": Decimal(str(tax_rules["personal_allowance"]["annual"])) / divisor,
        },
        "state_tax_brackets": {
            "bundskat": tax_rules["state_tax_brackets"]["bundskat"],
            "mellemskat": {
                **tax_rules["state_tax_brackets"]["mellemskat"],
                "threshold": Decimal(str(tax_rules["state_tax_brackets"]["mellemskat"]["threshold"])) / divisor,
            },
            "topskat": {
                **tax_rules["state_tax_brackets"]["topskat"],
                "threshold": Decimal(str(tax_rules["state_tax_brackets"]["topskat"]["threshold"])) / divisor,
            },
            "ekstra_topskat": {
                **tax_rules["state_tax_brackets"]["ekstra_topskat"],
                "threshold": Decimal(str(tax_rules["state_tax_brackets"]["ekstra_topskat"]["threshold"])) / divisor,
            },
        },
        "employment_allowance": {
            **tax_rules["employment_allowance"],
            "max_annual": Decimal(str(tax_rules["employment_allowance"]["max_annual"])) / divisor,
        },
        "job_allowance": {
            **tax_rules["job_allowance"],
            "floor_annual": Decimal(str(tax_rules["job_allowance"]["floor_annual"])) / divisor,
            "max_annual": Decimal(str(tax_rules["job_allowance"]["max_annual"])) / divisor,
        },
        "holiday_pay": tax_rules["holiday_pay"],
    }
    return scaled


def _period_amount(monthly_amount: Decimal, period: str) -> Decimal:
    return monthly_amount * MONTHS_PER_YEAR if period == "annual" else monthly_amount


def _compute_total_with_holiday(
    gross_income: Decimal, total_tax: Decimal, net_income: Decimal, holiday
) -> TotalWithHolidayResult:
    return TotalWithHolidayResult(
        gross=round_dkk(gross_income + holiday.gross),
        tax=round_dkk(total_tax + holiday.am_bidrag + holiday.income_tax),
        net=round_dkk(net_income + holiday.net),
    )


def _standard_estimate(
    base_gross_income: Decimal,
    tips: Decimal,
    extra_deduction: Decimal,
    municipality: dict,
    is_church_member: bool,
    hours_worked: Decimal,
    income_type,
    period: str,
    tax_rules: dict,
    tax_year: int,
    tax_card_mode: TaxCardMode,
    age: int | None = None,
) -> TaxResult:
    rules = _scaled_tax_rules(tax_rules, period)

    am_rate = Decimal(str(rules["am_bidrag"]["rate"]))
    personal_allowance = Decimal(str(rules["personal_allowance"]["annual"]))
    am_exempt = am_bidrag.is_exempt_by_age(age)

    gross_income = base_gross_income + tips

    atp_contribution = atp.get_atp_employee_contribution(
        hours_worked, pay_frequency="monthly", year=tax_year
    )
    if period == "annual":
        atp_contribution *= MONTHS_PER_YEAR

    am_base = am_bidrag.compute_am_bidrag_base(gross_income, atp_contribution)
    am_amount = am_bidrag.compute_am_bidrag(am_base, am_rate, exempt=am_exempt)

    personlig_indkomst = tax.compute_personlig_indkomst(am_base, am_amount)

    employment_allowance_amount = allowances.compute_employment_allowance(
        am_base,
        Decimal(str(rules["employment_allowance"]["rate"])),
        Decimal(str(rules["employment_allowance"]["max_annual"])),
    )
    job_allowance_amount = allowances.compute_job_allowance(
        am_base,
        Decimal(str(rules["job_allowance"]["rate"])),
        Decimal(str(rules["job_allowance"]["floor_annual"])),
        Decimal(str(rules["job_allowance"]["max_annual"])),
    )

    state_tax = tax.compute_state_tax(
        personlig_indkomst, personal_allowance, rules["state_tax_brackets"]
    )

    skattepligtig_indkomst = municipal_tax.compute_skattepligtig_indkomst(
        personlig_indkomst, employment_allowance_amount, job_allowance_amount
    ) - extra_deduction

    municipal_rate = Decimal(str(municipality["municipal_tax_rate"]))
    church_rate = Decimal(str(municipality["church_tax_rate"]))

    municipal_amount = municipal_tax.compute_municipal_tax(
        skattepligtig_indkomst, personal_allowance, municipal_rate
    )
    church_amount = municipal_tax.compute_church_tax(
        skattepligtig_indkomst, personal_allowance, church_rate, is_church_member
    )

    total_tax = (
        atp_contribution
        + am_amount
        + state_tax.total
        + municipal_amount
        + church_amount
    )
    net_income = gross_income - total_tax
    effective_rate = (total_tax / gross_income) if gross_income else Decimal(0)

    assumptions = [
        "Estimated net salary based on 2026 Danish tax rules and the information provided.",
        "Standard estimate: does not reproduce an individual's exact SKAT-issued tax-card withholding.",
    ]
    if tips:
        assumptions.append(
            "Tips are treated as ordinary taxable A-income and included in the ATP/AM-bidrag/tax base "
            "(assumes tips are paid through payroll, not cash tips reported independently)."
        )
    if extra_deduction:
        assumptions.append(
            "The additional deduction you entered reduces skattepligtig indkomst (municipal/church tax "
            "base), the same base the employment and job allowances reduce — see docs/research_2026.md item 13c."
        )
    if am_exempt:
        assumptions.append(
            "AM-bidrag (8%) was not applied because you entered an age of 17 or under. This uses a "
            "simplified age check (age today, not date of birth) — see docs/research_2026.md item 14 "
            "for the exact 2026 rule and its limitation."
        )

    holiday = compute_holiday_pay(
        income_type=income_type,
        holiday_eligible_gross=gross_income,
        am_rate=Decimal(0) if am_exempt else am_rate,
        municipal_rate=municipal_rate,
        church_rate=church_rate,
        is_church_member=is_church_member,
        personlig_indkomst=personlig_indkomst,
        state_tax_brackets=rules["state_tax_brackets"],
        tax_card_mode=tax_card_mode,
        tax_card_percentage=None,
        holiday_pay_rules=rules["holiday_pay"],
    )
    holiday_rounded = holiday.__class__(
        rate_used=holiday.rate_used,
        rate_label=holiday.rate_label,
        gross=round_dkk(holiday.gross),
        am_bidrag=round_dkk(holiday.am_bidrag),
        income_tax=round_dkk(holiday.income_tax),
        net=round_dkk(holiday.net),
        marginal_rate_applied=holiday.marginal_rate_applied,
    )
    total_with_holiday = _compute_total_with_holiday(
        gross_income, total_tax, net_income, holiday_rounded
    )

    return TaxResult(
        period=period,
        calculation_basis=CalculationBasis.STANDARD_ESTIMATE,
        gross_income=round_dkk(gross_income),
        atp_employee_contribution=round_dkk(atp_contribution),
        am_bidrag_base=round_dkk(am_base),
        am_bidrag=round_dkk(am_amount),
        employment_allowance=round_dkk(employment_allowance_amount),
        job_allowance=round_dkk(job_allowance_amount),
        taxable_income=round_dkk(personlig_indkomst),
        bundskat=round_dkk(state_tax.bundskat),
        mellemskat=round_dkk(state_tax.mellemskat),
        topskat=round_dkk(state_tax.topskat),
        ekstra_topskat=round_dkk(state_tax.ekstra_topskat),
        state_tax_total=round_dkk(state_tax.total),
        municipal_tax=round_dkk(municipal_amount),
        church_tax=round_dkk(church_amount),
        is_church_member=is_church_member,
        net_income=round_dkk(net_income),
        effective_tax_rate=effective_rate,
        municipality_name=municipality["name"],
        tax_year=tax_year,
        assumptions=assumptions,
        base_gross_income=round_dkk(base_gross_income),
        tips=round_dkk(tips),
        extra_deduction_applied=round_dkk(extra_deduction),
        holiday_pay=holiday_rounded,
        total_with_holiday=total_with_holiday,
        age_am_bidrag_exempt=am_exempt,
    )


def _tax_card_estimate(
    salary_input: SalaryInput,
    base_gross_income: Decimal,
    tips: Decimal,
    hours_worked: Decimal,
    period: str,
    tax_rules: dict,
    tax_year: int,
) -> TaxResult:
    rules = _scaled_tax_rules(tax_rules, period)
    am_rate = Decimal(str(rules["am_bidrag"]["rate"]))
    am_exempt = am_bidrag.is_exempt_by_age(salary_input.age)

    gross_income = base_gross_income + tips

    atp_contribution = atp.get_atp_employee_contribution(
        hours_worked, pay_frequency="monthly", year=tax_year
    )
    if period == "annual":
        atp_contribution *= MONTHS_PER_YEAR

    am_base = am_bidrag.compute_am_bidrag_base(gross_income, atp_contribution)
    am_amount = am_bidrag.compute_am_bidrag(am_base, am_rate, exempt=am_exempt)

    monthly_deduction = salary_input.tax_card_monthly_deduction or Decimal(0)
    if period == "annual":
        monthly_deduction *= MONTHS_PER_YEAR

    result = compute_tax_card_withholding(
        gross_income=gross_income,
        atp_employee_contribution=atp_contribution,
        am_bidrag=am_amount,
        tax_card_percentage=salary_input.tax_card_percentage,
        tax_card_type=salary_input.tax_card_type,
        tax_card_monthly_deduction=monthly_deduction,
    )

    total_tax = atp_contribution + am_amount + result.withheld_tax
    net_income = gross_income - total_tax
    effective_rate = (total_tax / gross_income) if gross_income else Decimal(0)

    zero = Decimal(0)
    assumptions = [
        "Withholding estimated from the tax-card percentage and deduction you provided.",
        "This reflects your supplied tax card figures, not a recalculation of them — "
        "confirm those figures against your own forskudsopgørelse/skattekort.",
    ]
    if tips:
        assumptions.append(
            "Tips are included in the withholding base (added before ATP/AM-bidrag are subtracted)."
        )
    if am_exempt:
        assumptions.append(
            "AM-bidrag (8%) was not applied because you entered an age of 17 or under. This uses a "
            "simplified age check (age today, not date of birth) — see docs/research_2026.md item 14 "
            "for the exact 2026 rule and its limitation."
        )

    holiday = compute_holiday_pay(
        income_type=salary_input.income_type,
        holiday_eligible_gross=gross_income,
        am_rate=Decimal(0) if am_exempt else am_rate,
        municipal_rate=Decimal(0),
        church_rate=Decimal(0),
        is_church_member=salary_input.is_church_member,
        personlig_indkomst=Decimal(0),
        state_tax_brackets=rules["state_tax_brackets"],
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_percentage=salary_input.tax_card_percentage,
        holiday_pay_rules=rules["holiday_pay"],
    )
    holiday_rounded = holiday.__class__(
        rate_used=holiday.rate_used,
        rate_label=holiday.rate_label,
        gross=round_dkk(holiday.gross),
        am_bidrag=round_dkk(holiday.am_bidrag),
        income_tax=round_dkk(holiday.income_tax),
        net=round_dkk(holiday.net),
        marginal_rate_applied=holiday.marginal_rate_applied,
    )
    total_with_holiday = _compute_total_with_holiday(
        gross_income, total_tax, net_income, holiday_rounded
    )

    return TaxResult(
        period=period,
        calculation_basis=CalculationBasis.TAX_CARD,
        gross_income=round_dkk(gross_income),
        atp_employee_contribution=round_dkk(atp_contribution),
        am_bidrag_base=round_dkk(am_base),
        am_bidrag=round_dkk(am_amount),
        employment_allowance=zero,
        job_allowance=zero,
        taxable_income=round_dkk(result.withholding_base),
        bundskat=zero,
        mellemskat=zero,
        topskat=zero,
        ekstra_topskat=zero,
        state_tax_total=round_dkk(result.withheld_tax),
        municipal_tax=zero,
        church_tax=zero,
        is_church_member=salary_input.is_church_member,
        net_income=round_dkk(net_income),
        effective_tax_rate=effective_rate,
        municipality_name=salary_input.municipality_name,
        tax_year=tax_year,
        assumptions=assumptions,
        base_gross_income=round_dkk(base_gross_income),
        tips=round_dkk(tips),
        extra_deduction_applied=zero,
        holiday_pay=holiday_rounded,
        total_with_holiday=total_with_holiday,
        age_am_bidrag_exempt=am_exempt,
    )


def _frikort_estimate(
    salary_input: SalaryInput,
    base_gross_income: Decimal,
    tips: Decimal,
    hours_worked: Decimal,
    period: str,
    tax_rules: dict,
    tax_year: int,
) -> TaxResult:
    rules = _scaled_tax_rules(tax_rules, period)
    am_rate = Decimal(str(rules["am_bidrag"]["rate"]))
    am_exempt = am_bidrag.is_exempt_by_age(salary_input.age)

    gross_income = base_gross_income + tips

    atp_contribution = atp.get_atp_employee_contribution(
        hours_worked, pay_frequency="monthly", year=tax_year
    )
    if period == "annual":
        atp_contribution *= MONTHS_PER_YEAR

    am_base = am_bidrag.compute_am_bidrag_base(gross_income, atp_contribution)
    am_amount = am_bidrag.compute_am_bidrag(am_base, am_rate, exempt=am_exempt)

    remaining_frikort_amount = salary_input.remaining_frikort_amount or Decimal(0)
    if period == "annual":
        remaining_frikort_amount *= MONTHS_PER_YEAR

    # compute_frikort_withholding raises FrikortBalanceExceededError (a
    # ValueError subclass) when gross_income exceeds the remaining
    # balance — the caller (API layer) surfaces that as a clear 400, not
    # a silent fallback to another tax-card type. See app/calculations/frikort.py.
    result = compute_frikort_withholding(
        gross_income=gross_income,
        atp_employee_contribution=atp_contribution,
        am_bidrag=am_amount,
        remaining_frikort_amount=remaining_frikort_amount,
    )

    total_tax = atp_contribution + am_amount + result.withheld_tax
    net_income = gross_income - total_tax
    effective_rate = (total_tax / gross_income) if gross_income else Decimal(0)

    zero = Decimal(0)
    assumptions = [
        "Frikort: this income is within your stated remaining Frikort balance, so no state, "
        "municipal or church income tax is withheld on it. AM-bidrag and ATP still apply as normal.",
        "This is the well-verified Frikort case only — if this income exceeded your remaining "
        "balance, the app would stop and ask you to use Bikort instead, rather than guessing.",
    ]
    if tips:
        assumptions.append(
            "Tips are included in the Frikort balance check and in the AM-bidrag base."
        )
    if am_exempt:
        assumptions.append(
            "AM-bidrag (8%) was not applied because you entered an age of 17 or under. This uses a "
            "simplified age check (age today, not date of birth) — see docs/research_2026.md item 14 "
            "for the exact 2026 rule and its limitation."
        )

    holiday = compute_holiday_pay(
        income_type=salary_input.income_type,
        holiday_eligible_gross=gross_income,
        am_rate=Decimal(0) if am_exempt else am_rate,
        municipal_rate=Decimal(0),
        church_rate=Decimal(0),
        is_church_member=salary_input.is_church_member,
        personlig_indkomst=Decimal(0),
        state_tax_brackets=rules["state_tax_brackets"],
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_percentage=Decimal(0),
        holiday_pay_rules=rules["holiday_pay"],
    )
    holiday_rounded = holiday.__class__(
        rate_used=holiday.rate_used,
        rate_label=holiday.rate_label,
        gross=round_dkk(holiday.gross),
        am_bidrag=round_dkk(holiday.am_bidrag),
        income_tax=round_dkk(holiday.income_tax),
        net=round_dkk(holiday.net),
        marginal_rate_applied=holiday.marginal_rate_applied,
    )
    total_with_holiday = _compute_total_with_holiday(
        gross_income, total_tax, net_income, holiday_rounded
    )

    return TaxResult(
        period=period,
        calculation_basis=CalculationBasis.FRIKORT,
        gross_income=round_dkk(gross_income),
        atp_employee_contribution=round_dkk(atp_contribution),
        am_bidrag_base=round_dkk(am_base),
        am_bidrag=round_dkk(am_amount),
        employment_allowance=zero,
        job_allowance=zero,
        taxable_income=round_dkk(result.withholding_base),
        bundskat=zero,
        mellemskat=zero,
        topskat=zero,
        ekstra_topskat=zero,
        state_tax_total=round_dkk(result.withheld_tax),
        municipal_tax=zero,
        church_tax=zero,
        is_church_member=salary_input.is_church_member,
        net_income=round_dkk(net_income),
        effective_tax_rate=effective_rate,
        municipality_name=salary_input.municipality_name,
        tax_year=tax_year,
        assumptions=assumptions,
        base_gross_income=round_dkk(base_gross_income),
        tips=round_dkk(tips),
        extra_deduction_applied=zero,
        holiday_pay=holiday_rounded,
        total_with_holiday=total_with_holiday,
        age_am_bidrag_exempt=am_exempt,
        remaining_frikort_amount=round_dkk(remaining_frikort_amount),
    )


def _run(salary_input: SalaryInput, period: str, tax_year: int = 2026) -> TaxResult:
    municipality = get_municipality(salary_input.municipality_name, tax_year)
    if municipality is None:
        raise ValueError(f"Unknown municipality: {salary_input.municipality_name}")

    tax_rules = load_tax_rules(tax_year)

    monthly_base_gross = salary.compute_monthly_gross_income(salary_input)
    hours_worked = salary.decimal_hours_worked(salary_input)

    base_gross_income = _period_amount(monthly_base_gross, period)
    tips = _period_amount(salary_input.tips or Decimal(0), period)
    extra_deduction = _period_amount(salary_input.extra_deduction or Decimal(0), period)

    if salary_input.tax_card_mode is TaxCardMode.MY_TAX_CARD:
        if salary_input.tax_card_type is TaxCardType.FRIKORT:
            return _frikort_estimate(
                salary_input, base_gross_income, tips, hours_worked, period, tax_rules, tax_year
            )
        return _tax_card_estimate(
            salary_input, base_gross_income, tips, hours_worked, period, tax_rules, tax_year
        )

    return _standard_estimate(
        base_gross_income,
        tips,
        extra_deduction,
        municipality,
        salary_input.is_church_member,
        hours_worked,
        salary_input.income_type,
        period,
        tax_rules,
        tax_year,
        salary_input.tax_card_mode,
        salary_input.age,
    )


def calculate_annual_tax(salary_input: SalaryInput, tax_year: int = 2026) -> TaxResult:
    """Full-year estimate, using the true annual constants (no /12 scaling)."""
    return _run(salary_input, period="annual", tax_year=tax_year)


def calculate_monthly_withholding(salary_input: SalaryInput, tax_year: int = 2026) -> TaxResult:
    """Monthly payslip estimate: same pipeline, constants scaled to a
    monthly basis. This is the figure the V1 UI shows first."""
    return _run(salary_input, period="monthly", tax_year=tax_year)
