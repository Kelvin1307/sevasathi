from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

# Known Indian states for extraction
INDIAN_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal", "delhi", "jammu", "kashmir", "ladakh", "puducherry",
    "chandigarh", "andaman", "nicobar", "lakshadweep", "dadra", "daman", "diu",
]

# Occupation keywords
OCCUPATION_KEYWORDS = {
    "farmer": ["farmer", "agriculture", "kisan", "cultivation", "crop", "agricu"],
    "student": ["student", "school", "college", "university", "studying", "scholarship"],
    "labour": ["labour", "labor", "worker", "construction", "unorganized", "daily wage"],
    "self-employed": ["self-employed", "business", "entrepreneur", "shopkeeper", "vendor", "trader"],
    "unemployed": ["unemployed", "no job", "jobless", "looking for work", "seeking job"],
    "government employee": ["government employee", "sarkari", "govt employee", "public servant"],
    "senior citizen": ["senior citizen", "old age", "elderly", "retired", "pensioner"],
    "artisan": ["artisan", "craftsman", "weaver", "potter", "handicraft"],
    "fisher": ["fisher", "fisherman", "fishing"],
}

# Category keywords
CATEGORY_KEYWORDS = {
    "SC": ["sc", "scheduled caste", "dalit", "harijan"],
    "ST": ["st", "scheduled tribe", "tribal", "adivasi"],
    "OBC": ["obc", "other backward class", "backward class"],
    "minority": ["minority", "muslim", "christian", "sikh", "buddhist", "jain"],
    "general": ["general", "open category"],
    "EWS": ["ews", "economically weaker section"],
}

# Disability keywords
DISABILITY_KEYWORDS = ["disabled", "disability", "differently abled", "pwd", "handicapped", "divyang"]

# Gender keywords
GENDER_KEYWORDS = {
    "women": ["woman", "women", "female", "girl", "widow", "widowed", "mother", "wife", "daughter"],
    "men": ["man", "men", "male", "boy", "father", "husband", "son"],
    "transgender": ["transgender", "trans", "third gender"],
}

# Income keywords
INCOME_KEYWORDS = {
    "low income": ["low income", "poor", "bpl", "below poverty line", "economically weak", "ews", "pauper"],
    "middle income": ["middle income", "middle class"],
    "high income": ["high income", "rich", "affluent"],
}


@dataclass
class UserProfile:
    state: str = ""
    age: str = ""
    gender: str = ""
    category: str = ""
    income_group: str = ""
    occupation: str = ""
    disability: str = ""
    education: str = ""
    family_status: str = ""
    need: str = ""
    current_problem: str = ""
    extra_context: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, str]:
        data = {}
        for key, value in self.__dict__.items():
            if value not in ("", [], None):
                data[key] = value
        return data


class ChatCoref:
    """Maintains user profile and conversation context across turns."""

    def __init__(self):
        self.profile = UserProfile()
        self.history: List[Dict[str, str]] = []

    def update_from_message(self, message: str) -> None:
        """Extract and update user profile fields from a new message."""
        text = message.lower().strip()

        # State detection
        for state in INDIAN_STATES:
            if state in text:
                self.profile.state = state.title()
                break

        # Age detection (e.g. "I am 25 years old" or "age 30")
        age_match = re.search(r"\b(\d{1,3})\s*(?:years?\s*old|yr\s*old|year)\b", text)
        if age_match:
            self.profile.age = age_match.group(1)

        # Gender detection
        for gender, keywords in GENDER_KEYWORDS.items():
            if any(k in text for k in keywords):
                self.profile.gender = gender
                break

        # Category detection
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(k in text for k in keywords):
                self.profile.category = category
                break

        # Income detection
        for income_level, keywords in INCOME_KEYWORDS.items():
            if any(k in text for k in keywords):
                self.profile.income_group = income_level
                break

        # Occupation detection
        for occupation, keywords in OCCUPATION_KEYWORDS.items():
            if any(k in text for k in keywords):
                self.profile.occupation = occupation
                break

        # Disability detection
        if any(k in text for k in DISABILITY_KEYWORDS):
            self.profile.disability = "person with disability"

        # Education detection
        edu_patterns = {
            "10th pass": ["10th", "sslc", "matriculation"],
            "12th pass": ["12th", "hsc", "intermediate", "plus two"],
            "graduate": ["graduate", "bachelor", "b.a", "b.sc", "b.com", "b.tech", "btech", "ba", "bsc"],
            "post-graduate": ["post graduate", "master", "m.a", "m.sc", "m.com", "mtech", "mba"],
            "PhD": ["phd", "doctorate", "research scholar"],
        }
        for edu_level, patterns in edu_patterns.items():
            if any(p in text for p in patterns):
                self.profile.education = edu_level
                break

        # Family status detection
        family_patterns = {
            "widow": ["widow", "widowed"],
            "single parent": ["single parent", "single mother", "single father"],
            "married": ["married", "wife", "husband", "spouse"],
            "unmarried": ["unmarried", "single", "bachelor"],
            "orphan": ["orphan"],
        }
        for status, patterns in family_patterns.items():
            if any(p in text for p in patterns):
                self.profile.family_status = status
                break

        # Need/intent detection
        need_patterns = {
            "scholarship": ["scholarship", "education support", "study help", "tuition fee", "hostel fee"],
            "housing": ["house", "housing", "shelter", "home loan", "pucca house", "flat"],
            "healthcare": ["hospital", "health", "medical", "treatment", "medicine", "insurance", "ayushman"],
            "loan": ["loan", "credit", "finance", "mudra", "bank loan"],
            "employment": ["job", "employment", "work", "livelihood", "skill training", "vocational"],
            "pension": ["pension", "old age support", "retirement"],
            "food": ["food", "ration", "pds", "subsidized grain", "nutrition"],
            "agriculture": ["crop", "seed", "fertilizer", "irrigation", "subsidy", "kisan"],
        }
        for need, patterns in need_patterns.items():
            if any(p in text for p in patterns):
                self.profile.need = need
                break

        # Update current problem with message snippet
        if len(message) > 20:
            self.profile.current_problem = message[:300]

    def add_to_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def summarize(self) -> Dict[str, str]:
        return self.profile.to_dict()

    def reset(self) -> None:
        """Reset the profile and history."""
        self.profile = UserProfile()
        self.history = []
