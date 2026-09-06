from __future__ import annotations


def calculate_emi(principal: float, annual_rate: float, tenure_months: int, moratorium_months: int = 0) -> dict[str, float | int]:
    if principal <= 0:
        raise ValueError("Principal must be positive.")
    if annual_rate < 0:
        raise ValueError("Interest rate cannot be negative.")
    if tenure_months <= moratorium_months:
        raise ValueError("Tenure must be greater than the moratorium period.")

    accrued_interest = principal * (annual_rate / 100) * (moratorium_months / 12)
    adjusted_principal = principal + accrued_interest
    repayment_months = tenure_months - moratorium_months
    monthly_rate = annual_rate / (12 * 100)
    if monthly_rate == 0:
        emi = adjusted_principal / repayment_months
    else:
        factor = (1 + monthly_rate) ** repayment_months
        emi = adjusted_principal * monthly_rate * factor / (factor - 1)
    return {
        "accrued_interest": round(accrued_interest, 2),
        "adjusted_principal": round(adjusted_principal, 2),
        "emi": round(emi, 2),
        "repayment_months": repayment_months,
    }
