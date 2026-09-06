from __future__ import annotations

from typing import Any

MO_SJE_INCOME_LIMIT = 500000
SCHEME_LIMITS = {
    "micro": 140000,
    "micro finance": 140000,
    "mahila": 140000,
    "term": 5000000,
    "education": 3000000,
}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def eligible_scheme_metadata(profile: dict[str, Any], metadata: dict[str, Any]) -> tuple[bool, str]:
    category = str(profile.get("category", profile.get("social_category", ""))).lower()
    required_category = str(metadata.get("social_category", "any")).lower()
    if required_category == "sc" and category not in {"sc", "scheduled caste"}:
        return False, "This scheme requires SC category eligibility."

    income = _number(profile.get("income") or profile.get("annual_income") or profile.get("income_amount"))
    if income is not None and income > MO_SJE_INCOME_LIMIT:
        return False, "Annual family income is above the MoSJE limit of Rs 5 lakh."

    gender = str(profile.get("gender", "")).lower()
    required_gender = str(metadata.get("gender", "any")).lower()
    if required_gender == "women" and gender not in {"women", "female", "woman"}:
        return False, "This scheme is reserved for women applicants."

    requested = _number(profile.get("project_cost") or profile.get("loan_amount") or profile.get("course_cost"))
    limit = _number(metadata.get("max_loan"))
    if requested is not None and limit is not None and requested > limit:
        return False, "The requested amount exceeds this scheme's maximum loan limit."

    return True, "Eligible for metadata-based matching; final approval is by the authorized partner."


def filter_metadata(profile: dict[str, Any], metadata_list: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    eligible = []
    excluded = []
    for metadata in metadata_list:
        allowed, reason = eligible_scheme_metadata(profile, metadata)
        if allowed:
            eligible.append(metadata)
        else:
            excluded.append(f"{metadata.get('scheme_name', 'Scheme')}: {reason}")
    return eligible, excluded
