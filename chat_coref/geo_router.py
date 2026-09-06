from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PARTNER_FILE = BASE_DIR / "channel_partners.csv"
DEFAULT_NPA_MAX = 7.5
LOCATION_HINTS = {
    "delhi", "new delhi", "lucknow", "uttar pradesh", "bengaluru", "bangalore", "karnataka",
    "patna", "bihar", "mumbai", "maharashtra", "hyderabad", "telangana", "jaipur", "rajasthan",
    "kolkata", "west bengal", "chennai", "tamil nadu", "pune", "jharkhand", "ranchi",
}


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    radius = 6371.0
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def load_partners(path: str | Path = DEFAULT_PARTNER_FILE) -> list[dict[str, Any]]:
    partner_path = Path(path)
    if not partner_path.exists():
        return []
    with partner_path.open(newline="", encoding="utf-8-sig") as source:
        return [dict(row) for row in csv.DictReader(source)]


def geocode_address(address: str) -> tuple[float, float] | None:
    """Resolve an address with Nominatim when geocoding is enabled."""
    if not address.strip() or os.getenv("GEOCODING_ENABLED", "false").lower() != "true":
        return None
    try:
        from geopy.geocoders import Nominatim
        location = Nominatim(user_agent="nyayasetu-ai").geocode(address, timeout=8)
    except Exception:
        return None
    return (float(location.latitude), float(location.longitude)) if location else None


def contains_location_hint(text: str) -> bool:
    normalized = text.lower()
    return any(hint in normalized for hint in LOCATION_HINTS)


def extract_location_phrase(text: str) -> str:
    """Extract a geocoder-friendly location phrase from a natural-language request."""
    match = re.search(r"\b(?:in|from|near|at|address(?: is)?)\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def rank_partners(
    latitude: float,
    longitude: float,
    partners: list[dict[str, Any]],
    limit: int = 5,
    npa_max: float = DEFAULT_NPA_MAX,
    distance_decay: float = 0.02,
) -> list[dict[str, Any]]:
    ranked = []
    for partner in partners:
        try:
            npa = float(partner.get("npa_rate", 0))
            available = float(partner.get("fund_available", 0))
            allocated = float(partner.get("fund_allocated", 0))
            branch_lat = float(partner["latitude"])
            branch_lon = float(partner["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if npa >= npa_max or available <= 0 or allocated <= 0:
            continue
        distance = haversine_km(latitude, longitude, branch_lat, branch_lon)
        health = 0.5 * (1 - npa / npa_max) + 0.5 * (available / allocated)
        score = health * math.exp(-distance_decay * distance)
        ranked.append({**partner, "distance_km": round(distance, 2), "health_score": round(score, 4)})
    return sorted(ranked, key=lambda item: item["health_score"], reverse=True)[:limit]
