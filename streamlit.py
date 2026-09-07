"""
SevaBot – Interactive Government Scheme Finder & Recommendation Assistant
Run with: streamlit run streamlit.py
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Any

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SevaBot – Government Scheme Finder",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS & Styling ───────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans:wght@400;600;700&display=swap');

    /* ── Root palette ── */
    :root {
        --saffron-deep:   #c35b00;
        --saffron-mid:    #e07020;
        --saffron-light:  #f9a84d;
        --saffron-pale:   #fff3e0;
        --saffron-glow:   rgba(224, 112, 32, 0.12);
        --white:          #ffffff;
        --glass:          rgba(255,255,255,0.85);
        --border:         rgba(180,100,20,0.18);
        --text-primary:   #1a0e00;
        --text-secondary: #5a3a10;
        --text-muted:     #9a7040;
        --success:        #15803d;
        --info:           #1d4ed8;
        --warning:        #b45309;
        --shadow-sm:      0 2px 8px rgba(150,80,10,0.08);
        --shadow-md:      0 8px 30px rgba(150,80,10,0.12);
        --shadow-lg:      0 18px 50px rgba(150,80,10,0.16);
        --radius-sm:      8px;
        --radius-md:      16px;
        --radius-lg:      24px;
    }

    /* ── App background ── */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {
        font-family: 'Inter', 'Noto Sans', sans-serif;
        background: linear-gradient(135deg, #fffbf5 0%, #fff0d6 40%, #fde3b0 100%);
        min-height: 100vh;
        color: var(--text-primary);
    }

    /* ── Main container ── */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1150px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fff8ef 0%, #feecd0 60%, #fdd59a 100%);
        border-right: 1px solid var(--border);
        box-shadow: 4px 0 20px rgba(150,80,10,0.06);
    }
    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }

    /* ── Hero header ── */
    .seva-hero {
        background: linear-gradient(135deg, #b04500 0%, #e06010 45%, #f5961e 100%);
        border-radius: var(--radius-lg);
        padding: 1.8rem 2.2rem;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    .seva-hero::before {
        content: "🤖";
        position: absolute;
        right: 2rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 4.5rem;
        opacity: 0.2;
    }
    .seva-hero h1 {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .seva-hero p {
        font-size: 1.05rem;
        opacity: 0.92;
        margin: 0.4rem 0 0;
    }

    /* ── Quiz Card Container ── */
    .quiz-card {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 2rem 2.2rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-md);
        backdrop-filter: blur(10px);
    }
    .quiz-step-badge {
        display: inline-block;
        background: var(--saffron-pale);
        color: var(--saffron-deep);
        border: 1px solid var(--saffron-light);
        padding: 0.35rem 0.9rem;
        border-radius: 99px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }
    .quiz-question {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--saffron-deep);
        margin-bottom: 0.5rem;
    }
    .quiz-subtitle {
        font-size: 0.95rem;
        color: var(--text-muted);
        margin-bottom: 1.4rem;
    }

    /* ── Scheme cards ── */
    .scheme-card {
        background: linear-gradient(160deg, rgba(255,255,255,0.92) 0%, rgba(255,243,220,0.95) 100%);
        border: 1px solid var(--border);
        border-left: 5px solid var(--saffron-mid);
        border-radius: var(--radius-md);
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-md);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .scheme-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }
    .scheme-card h3 {
        color: var(--saffron-deep);
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0 0 0.6rem;
    }
    .scheme-card .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 99px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-high   { background: #d1fae5; color: #065f46; }
    .badge-medium { background: #fef3c7; color: #92400e; }
    .badge-low    { background: #fee2e2; color: #991b1b; }
    .badge-score  { background: var(--saffron-pale); color: var(--saffron-deep); border: 1px solid var(--saffron-light); }
    .score-track { height: 8px; background: #f3d9bd; border-radius: 99px; overflow: hidden; margin: 0.45rem 0 0.9rem; }
    .score-fill { height: 100%; background: linear-gradient(90deg, #f5961e, #b04500); border-radius: 99px; }
    .chat-intro { color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 1rem; }

    .scheme-detail-row {
        display: flex;
        gap: 0.4rem;
        align-items: flex-start;
        margin: 0.4rem 0;
        font-size: 0.92rem;
        color: var(--text-secondary);
    }
    .scheme-detail-icon { font-size: 1rem; flex-shrink: 0; }
    .scheme-detail-label { font-weight: 600; color: var(--text-primary); }

    /* ── Profile Pill Summary ── */
    .profile-pill-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0 1.5rem;
    }
    .profile-pill {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid var(--border);
        border-radius: 99px;
        padding: 0.35rem 0.85rem;
        font-size: 0.85rem;
        color: var(--saffron-deep);
        font-weight: 600;
        box-shadow: var(--shadow-sm);
    }

    /* ── Profile Sidebar Card ── */
    .profile-card {
        background: rgba(255,255,255,0.75);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.9rem 1rem;
        margin-bottom: 0.8rem;
    }
    .profile-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.83rem;
        padding: 0.3rem 0;
        border-bottom: 1px solid rgba(180,100,20,0.08);
    }
    .profile-row:last-child { border-bottom: none; }
    .profile-key { color: var(--text-muted); font-weight: 500; }
    .profile-val { color: var(--text-primary); font-weight: 600; }

    /* ── Section titles ── */
    .section-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--saffron-deep);
        margin: 1.2rem 0 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--saffron-mid) 0%, var(--saffron-deep) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        transition: opacity 0.2s, transform 0.2s !important;
    }
    .stButton > button:hover {
        opacity: 0.92 !important;
        transform: translateY(-1px) !important;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: var(--glass) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        backdrop-filter: blur(8px);
        padding: 0.9rem 1.1rem !important;
        margin-bottom: 0.6rem !important;
        box-shadow: var(--shadow-sm) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Lazy-load core dependencies ────────────────────────────────────────────────
def get_coref():
    if "chat_coref" not in st.session_state:
        from chat_coref.context import ChatCoref
        st.session_state.chat_coref = ChatCoref()
    return st.session_state.chat_coref


def get_rag():
    if "rag" not in st.session_state:
        from chat_coref.knowledge import KnowledgeIndexError
        from chat_coref.retriever import SchemeRAG
        with st.spinner("⏳ Initializing SevaBot Scheme Intelligence Base..."):
            try:
                st.session_state.rag = SchemeRAG()
            except KnowledgeIndexError as exc:
                st.error(str(exc))
                st.stop()
    return st.session_state.rag


# ── Session State Initialization ──────────────────────────────────────────────
if "quiz_step" not in st.session_state:
    st.session_state.quiz_step = 1  # 1 to 7

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {
        "gender": "",
        "age": "",
        "state": "",
        "occupation": "",
        "category": "",
        "income": "",
        "need": "",
    }

if "quiz_completed" not in st.session_state:
    st.session_state.quiz_completed = False

if "recommendation_results" not in st.session_state:
    st.session_state.recommendation_results = None

if "history" not in st.session_state:
    st.session_state.history = []
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False


# ── Indian States List ────────────────────────────────────────────────────────
INDIAN_STATES_LIST = [
    "All India / Central",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

QUESTION_FLOW = [
    ("gender", "What is your gender?", "For example: female, male, or transgender."),
    ("age", "How old are you?", "You can enter your age or an age group such as senior citizen."),
    ("state", "Which state or Union Territory do you live in?", "Please provide the full state name."),
    ("occupation", "What is your occupation or current status?", "For example: farmer, student, self-employed, or unemployed."),
    ("category", "What is your social category?", "For example: General, EWS, OBC, SC, ST, or Minority."),
    ("income", "What is your annual family income range?", "For example: below 1 lakh, 1 to 2.5 lakhs, or above 6 lakhs."),
    ("need", "What kind of support do you need?", "For example: education, housing, healthcare, farming, pension, loan, or employment."),
]


def current_question() -> tuple[str, str, str]:
    return QUESTION_FLOW[st.session_state.quiz_step - 1]


def _answer_value(field: str, message: str) -> str:
    """Normalize one conversational answer without calling the recommender."""
    text = message.strip()
    lowered = text.lower()
    if field == "gender":
        if any(word in lowered for word in ("transgender", "third gender")):
            return "transgender"
        if any(word in lowered for word in ("female", "woman", "women", "girl")):
            return "female"
        if any(word in lowered for word in ("male", "man", "men", "boy")):
            return "male"
    elif field == "age":
        import re
        match = re.search(r"\b(\d{1,3})\b", lowered)
        if match and 1 <= int(match.group(1)) <= 110:
            return f"{match.group(1)} years old"
        age_groups = {
            "youth": "17 years old", "minor": "17 years old", "young": "25 years old",
            "adult": "45 years old", "senior": "65 years old", "elderly": "65 years old",
        }
        for keyword, value in age_groups.items():
            if keyword in lowered:
                return value
    elif field == "state":
        for state in INDIAN_STATES_LIST:
            if state != "All India / Central" and state.lower() in lowered:
                return state
    elif field == "occupation":
        occupation_values = {
            "farmer": ("farmer", "agriculture", "kisan", "cultivation"),
            "student": ("student", "school", "college", "studying"),
            "self-employed": ("self-employed", "business", "entrepreneur", "shopkeeper", "vendor"),
            "unemployed": ("unemployed", "jobless", "looking for work", "job seeker"),
            "labour": ("labour", "labor", "worker", "daily wage", "construction"),
            "homemaker": ("homemaker", "housewife", "pensioner", "retired"),
        }
        for value, keywords in occupation_values.items():
            if any(keyword in lowered for keyword in keywords):
                return value
    elif field == "category":
        categories = {"general": ("general", "open"), "EWS": ("ews", "economically weaker"), "OBC": ("obc", "backward"), "SC": ("sc", "scheduled caste", "dalit"), "ST": ("st", "scheduled tribe", "tribal"), "Minority": ("minority", "muslim", "sikh", "christian")}
        for value, keywords in categories.items():
            if any(keyword in lowered for keyword in keywords):
                return value
    elif field == "income":
        if any(keyword in lowered for keyword in ("below", "bpl", "less than 1", "under 1", "low income")):
            return "low income BPL below 1 lakh"
        if any(keyword in lowered for keyword in ("1 to 2.5", "1-2.5", "one to two", "middle income")):
            return "1 to 2.5 lakhs income"
        if any(keyword in lowered for keyword in ("2.5 to 6", "2.5-6", "two to six")):
            return "2.5 to 6 lakhs middle income"
        if any(keyword in lowered for keyword in ("above", "over 6", "more than 6", "high income")):
            return "above 6 lakhs income"
    elif field == "need":
        needs = {
            "scholarship": ("education", "scholarship", "tuition", "study"),
            "housing": ("housing", "house", "shelter", "home"),
            "healthcare": ("health", "medical", "hospital", "medicine", "insurance"),
            "agriculture": ("farm", "farming", "crop", "fertilizer", "kisan"),
            "pension": ("pension", "senior", "old age", "retirement"),
            "loan": ("loan", "credit", "business", "finance"),
            "employment": ("job", "employment", "work", "skill", "livelihood"),
        }
        for value, keywords in needs.items():
            if any(keyword in lowered for keyword in keywords):
                return value
    return ""


def _sync_answer_to_profile(field: str, value: str) -> None:
    coref = get_coref()
    profile_field = {"income": "income_group"}.get(field, field)
    if hasattr(coref.profile, profile_field):
        setattr(coref.profile, profile_field, value)


def append_assistant_message(content: str) -> None:
    st.session_state.history.append({"role": "assistant", "content": content})
    get_coref().add_to_history("assistant", content)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 0.5rem 0 1rem;">
            <div style="font-size:3rem;">🌾</div>
            <div style="font-size:1.6rem; font-weight:800; color:#c35b00;">SevaBot</div>
            <div style="font-size:0.82rem; color:#9a7040; margin-top:0.2rem;">
                Government Scheme Recommendation Assistant
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("#### Your progress")
    for step_number, (field, _, _) in enumerate(QUESTION_FLOW, start=1):
        answer = st.session_state.quiz_answers.get(field, "")
        if answer:
            marker = "✅"
            state_label = "Complete"
        elif step_number == st.session_state.quiz_step and not st.session_state.quiz_completed:
            marker = "◉"
            state_label = "Current"
        else:
            marker = "○"
            state_label = "Pending"
        st.markdown(
            f"<div class='profile-row'><span class='profile-key'>{marker} {step_number}. {field.title()}</span>"
            f"<span class='profile-val'>{state_label}</span></div>",
            unsafe_allow_html=True,
        )
    st.progress(sum(bool(st.session_state.quiz_answers.get(field)) for field, _, _ in QUESTION_FLOW) / 7)

    coref = get_coref()
    profile = coref.summarize()

    st.markdown("#### 🪪 Your Eligibility Profile")
    if profile:
        rows_html = ""
        for k, v in profile.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            rows_html += f"""
            <div class="profile-row">
                <span class="profile-key">{k.replace('_',' ').title()}</span>
                <span class="profile-val">{v}</span>
            </div>"""
        st.markdown(f'<div class="profile-card">{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("Answer the questions to build your profile.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Restart Eligibility Questionnaire", use_container_width=True):
        st.session_state.quiz_step = 1
        st.session_state.quiz_answers = {
            "gender": "",
            "age": "",
            "state": "",
            "occupation": "",
            "category": "",
            "income": "",
            "need": "",
        }
        st.session_state.quiz_completed = False
        st.session_state.recommendation_results = None
        st.session_state.history = []
        st.session_state.conversation_started = False
        st.session_state.voice_enabled = False
        coref.reset()
        st.rerun()

    st.markdown("---")
    st.session_state.voice_enabled = st.toggle(
        "🎙 Voice chat",
        value=st.session_state.voice_enabled,
        help="Enable microphone input for the conversation.",
    )
    if st.session_state.voice_enabled:
        st.caption("Voice input is enabled. You can still type instead.")

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size:0.78rem; color:#9a7040; text-align:center; line-height:1.5;">
            ☁️ Powered by SevaBot Scheme RAG<br>
            🤖 AI Recommendations & Retrieval<br>
            📚 Knowledge Source: myScheme.gov.in
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Hero Header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="seva-hero">
        <h1>🌾 SevaBot</h1>
        <p>Interactive Government Scheme Finder — answer a few simple questions to find schemes tailored for you.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Result Renderer Function ───────────────────────────────────────────────────
def render_scheme_results(result: dict, key_prefix: str = "main") -> None:
    """Render scheme recommendation cards with expanders for eligibility, benefits, and steps."""
    summary = result.get("summary", "")
    if summary:
        st.info(f"📋 **Summary of Scheme Eligibility:** {summary}")

    recommendations = result.get("recommendations", [])
    if not recommendations:
        st.warning("No exact matching schemes found. Try restarting the quiz with broader options.")
        return

    st.markdown(
        f'<p class="section-title">🏆 Top {len(recommendations)} Schemes Recommended For You</p>',
        unsafe_allow_html=True,
    )

    for i, item in enumerate(recommendations[:7], start=1):
        scheme_name = item.get("scheme_name", f"Scheme #{i}")
        match_score = item.get("match_score", 0)
        confidence = item.get("confidence", "Medium")
        why = item.get("why_it_matches", "")
        eligibility = item.get("eligibility", [])
        benefits = item.get("benefits", [])
        docs_req = item.get("documents_required", [])
        steps = item.get("application_steps", [])
        source = item.get("official_source", "")

        # Fallback for documents if empty or marked not specified
        if not docs_req or any("not specified" in str(d).lower() for d in docs_req):
            docs_req = ["Aadhaar Card", "Bank Account Passbook", "Income / Caste Certificate", "Domicile / Identity Proof"]

        # Fallback for application steps if empty or marked not specified
        if not steps or any("not specified" in str(s).lower() for s in steps):
            steps = [
                "Visit the official scheme portal or nearest Common Service Centre (CSC)",
                "Register using your Aadhaar-linked mobile number",
                "Fill out the application form and upload mandatory documents",
                "Submit form and save the Application Reference Number for tracking"
            ]

        conf_lower = str(confidence).lower()
        badge_cls = "badge-high" if conf_lower == "high" else "badge-medium" if conf_lower == "medium" else "badge-low"
        score_pct = int(float(match_score) * 100) if float(match_score) <= 1 else int(match_score)

        st.markdown(
            f"""
            <div class="scheme-card">
                <h3>{i}. {scheme_name}</h3>
                <div style="margin-bottom:0.6rem;">
                    <span class="badge {badge_cls}">✅ {confidence} Match</span>
                    <span class="badge badge-score">Relevance Score: {score_pct}%</span>
                </div>
                <div class="score-track"><div class="score-fill" style="width:{max(0, min(score_pct, 100))}%"></div></div>
                <div class="scheme-detail-row">
                    <span class="scheme-detail-icon">💡</span>
                    <span><span class="scheme-detail-label">Why it matches: </span>{why}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"📄 Full Scheme Details & How to Apply — {scheme_name}", expanded=(i == 1)):
            cols_detail = st.columns(2)
            with cols_detail[0]:
                if eligibility:
                    st.markdown("**✅ Eligibility Criteria**")
                    for e in eligibility:
                        st.markdown(f"- {e}")
                if benefits:
                    st.markdown("**🎁 Scheme Benefits**")
                    for b in benefits:
                        st.markdown(f"- {b}")
            with cols_detail[1]:
                if docs_req:
                    st.markdown("**📋 Documents Required**")
                    for d in docs_req:
                        st.markdown(f"- {d}")
                if steps:
                    st.markdown("**🚶 Application Steps**")
                    for s_idx, s in enumerate(steps, 1):
                        st.markdown(f"{s_idx}. {s}")
            if source:
                clean_url = source if str(source).startswith("http") else f"https://www.google.com/search?q={str(source).replace(' ', '+')}"
                link_text = source if str(source).startswith("http") else f"Official {source} Portal"
                st.markdown(f"🔗 **Official Website / Ministry:** [{link_text}]({clean_url})")
                st.link_button("Apply on official portal", clean_url, key=f"apply_{key_prefix}_{i}")


# ── Conversational Eligibility Flow ───────────────────────────────────────────
def render_chat_history() -> None:
    for message in st.session_state.history:
        with st.chat_message(message["role"], avatar="🧑" if message["role"] == "user" else "🌾"):
            st.markdown(message["content"])


def add_user_turn(message: str) -> None:
    st.session_state.history.append({"role": "user", "content": message})
    get_coref().add_to_history("user", message)


def ask_next_question() -> None:
    field, question, hint = current_question()
    append_assistant_message(f"**{question}**\n\n{hint}")


def process_eligibility_answer(message: str) -> None:
    field, _, _ = current_question()
    value = _answer_value(field, message)
    if not value:
        append_assistant_message("I could not identify that answer. Please provide a clear response for this question.")
        return

    st.session_state.quiz_answers[field] = value
    _sync_answer_to_profile(field, value)
    st.session_state.quiz_step += 1
    if st.session_state.quiz_step > len(QUESTION_FLOW):
        st.session_state.quiz_completed = True
        append_assistant_message("Thanks. I have all seven details. I am now checking the scheme database for your eligibility.")
    else:
        ask_next_question()


if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

if not st.session_state.conversation_started:
    st.session_state.conversation_started = True
    append_assistant_message("Hello, I am SevaBot. I will ask seven short questions, one at a time, before finding suitable schemes.")
    ask_next_question()

if not st.session_state.quiz_completed:
    st.markdown('<p class="chat-intro">Answer naturally in the chat. Your progress and saved details stay visible in the sidebar.</p>', unsafe_allow_html=True)
    render_chat_history()
    user_chat = st.chat_input("Type your answer...")
    if st.session_state.voice_enabled:
        voice_input = st.audio_input("Or answer by voice", label_visibility="visible")
        if voice_input is not None:
            try:
                from chat_coref.voice import transcribe_audio
                user_chat = transcribe_audio(voice_input.getvalue(), "eligibility-answer.wav")
            except Exception as exc:
                st.error(f"Voice input unavailable: {exc}")
    if user_chat:
        add_user_turn(user_chat)
        process_eligibility_answer(user_chat)
        st.rerun()
    st.stop()


# ── Completed profile and results ─────────────────────────────────────────────
if st.session_state.quiz_completed and st.session_state.recommendation_results is None:
    ans = st.session_state.quiz_answers
    coref = get_coref()
    summary_query = (
        f"I am {ans.get('age', '')} and {ans.get('gender', '')} from {ans.get('state', '')}. "
        f"Category: {ans.get('category', '')}, Occupation: {ans.get('occupation', '')}, "
        f"Income: {ans.get('income', '')}. Seeking: {ans.get('need', '')}."
    )
    with st.spinner("Analyzing your completed eligibility profile..."):
        rag = get_rag()
        st.session_state.recommendation_results = rag.recommend(
            user_message=summary_query,
            user_profile=coref.summarize(),
            chat_history=coref.history,
        )
    result_text = json.dumps(st.session_state.recommendation_results, ensure_ascii=False)
    coref.add_to_history("assistant", result_text)
    st.session_state.history.append({"role": "assistant", "content": st.session_state.recommendation_results.get("summary", "Your recommendations are ready.")})

render_chat_history()
render_scheme_results(st.session_state.recommendation_results, key_prefix="initial_results")

st.markdown('<p class="section-title">💬 Continue your conversation</p>', unsafe_allow_html=True)
st.caption("Ask about eligibility, documents, benefits, application steps, or request a fresh scheme list.")
user_chat = st.chat_input("Ask a follow-up question...")
if st.session_state.voice_enabled:
    voice_followup = st.audio_input("Or ask by voice", label_visibility="visible")
    if voice_followup is not None:
        try:
            from chat_coref.voice import transcribe_audio
            user_chat = transcribe_audio(voice_followup.getvalue(), "follow-up-question.wav")
        except Exception as exc:
            st.error(f"Voice input unavailable: {exc}")
if user_chat:
    rag = get_rag()
    coref = get_coref()
    add_user_turn(user_chat)
    re_recommend_keywords = (
        "regive", "re-give", "recalculate", "new schemes", "update schemes",
        "recommend again", "re-evaluate", "altered details", "change profile",
        "different schemes", "refresh schemes", "re-recommend",
    )
    if any(keyword in user_chat.lower() for keyword in re_recommend_keywords):
        response = rag.recommend(user_chat, coref.summarize(), coref.history)
        st.session_state.recommendation_results = response
        response_text = response.get("summary", "I updated your recommendations.")
    else:
        response_text = rag.chat_answer(user_chat, coref.summarize(), coref.history)
    append_assistant_message(response_text)
    st.rerun()

st.stop()


# ── Legacy card flow retained below for reference ─────────────────────────────
# The active application exits above. The original controls remain below so the
# previous implementation can be compared or removed in a later cleanup.
# ── Interactive 7-Step Questionnaire Flow ──────────────────────────────────────
if not st.session_state.quiz_completed:
    current_step = st.session_state.quiz_step
    st.progress(current_step / 7, text=f"Questionnaire Progress: Step {current_step} of 7")

    # STEP 1: Gender
    if current_step == 1:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 1 of 7</span>
                <div class="quiz-question">What is your Gender?</div>
                <div class="quiz-subtitle">Certain government schemes are specifically crafted for women, girls, or transgender empowerment.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("👩 Female", key="g_female", use_container_width=True):
                st.session_state.quiz_answers["gender"] = "female"
                st.session_state.quiz_step = 2
                st.rerun()
        with col2:
            if st.button("👨 Male", key="g_male", use_container_width=True):
                st.session_state.quiz_answers["gender"] = "male"
                st.session_state.quiz_step = 2
                st.rerun()
        with col3:
            if st.button("⚧️ Transgender / Other", key="g_trans", use_container_width=True):
                st.session_state.quiz_answers["gender"] = "transgender"
                st.session_state.quiz_step = 2
                st.rerun()

    # STEP 2: Age Group
    elif current_step == 2:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 2 of 7</span>
                <div class="quiz-question">What is your Age Group?</div>
                <div class="quiz-subtitle">Select your age category or enter your exact age below.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("👶 Youth (< 18 years)", key="age_1", use_container_width=True):
                st.session_state.quiz_answers["age"] = "17 years old"
                st.session_state.quiz_step = 3
                st.rerun()
        with col2:
            if st.button("🧑 Young Adult (18-35 years)", key="age_2", use_container_width=True):
                st.session_state.quiz_answers["age"] = "25 years old"
                st.session_state.quiz_step = 3
                st.rerun()
        with col3:
            if st.button("🧔 Adult (36-59 years)", key="age_3", use_container_width=True):
                st.session_state.quiz_answers["age"] = "45 years old"
                st.session_state.quiz_step = 3
                st.rerun()
        with col4:
            if st.button("👴 Senior Citizen (60+ years)", key="age_4", use_container_width=True):
                st.session_state.quiz_answers["age"] = "65 years old"
                st.session_state.quiz_step = 3
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        custom_age = st.number_input("Or enter exact age:", min_value=1, max_value=110, value=25, key="num_age")
        col_b, col_n = st.columns([1, 4])
        with col_b:
            if st.button("⬅️ Back", key="back_2"):
                st.session_state.quiz_step = 1
                st.rerun()
        with col_n:
            if st.button("Continue with Exact Age ➡️", key="next_age"):
                st.session_state.quiz_answers["age"] = f"{custom_age} years old"
                st.session_state.quiz_step = 3
                st.rerun()

    # STEP 3: State / UT
    elif current_step == 3:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 3 of 7</span>
                <div class="quiz-question">Which State / Union Territory do you reside in?</div>
                <div class="quiz-subtitle">This helps include both State-specific and Central government schemes.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        selected_state = st.selectbox("Select your State:", INDIAN_STATES_LIST, index=0)

        col_b, col_n = st.columns([1, 4])
        with col_b:
            if st.button("⬅️ Back", key="back_3"):
                st.session_state.quiz_step = 2
                st.rerun()
        with col_n:
            if st.button("Next Question ➡️", key="next_state"):
                st.session_state.quiz_answers["state"] = selected_state
                st.session_state.quiz_step = 4
                st.rerun()

    # STEP 4: Occupation / Primary Status
    elif current_step == 4:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 4 of 7</span>
                <div class="quiz-question">What is your Occupation or Current Status?</div>
                <div class="quiz-subtitle">Choose the option that best describes your primary work or status.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👨‍🌾 Farmer / Agriculture", key="occ_farmer", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "farmer"
                st.session_state.quiz_step = 5
                st.rerun()
            if st.button("💼 Business / Self-Employed", key="occ_business", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "self-employed"
                st.session_state.quiz_step = 5
                st.rerun()
        with c2:
            if st.button("🎓 Student", key="occ_student", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "student"
                st.session_state.quiz_step = 5
                st.rerun()
            if st.button("🔍 Unemployed / Job Seeker", key="occ_unemp", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "unemployed"
                st.session_state.quiz_step = 5
                st.rerun()
        with c3:
            if st.button("👷 Worker / Daily Wage Labour", key="occ_worker", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "labour"
                st.session_state.quiz_step = 5
                st.rerun()
            if st.button("👵 Housewife / Pensioner", key="occ_other", use_container_width=True):
                st.session_state.quiz_answers["occupation"] = "homemaker"
                st.session_state.quiz_step = 5
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Back", key="back_4"):
            st.session_state.quiz_step = 3
            st.rerun()

    # STEP 5: Social Category
    elif current_step == 5:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 5 of 7</span>
                <div class="quiz-question">What is your Social Category?</div>
                <div class="quiz-subtitle">Many welfare subsidies and scholarships are reserved for specific social categories.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("General", key="cat_gen", use_container_width=True):
                st.session_state.quiz_answers["category"] = "General"
                st.session_state.quiz_step = 6
                st.rerun()
            if st.button("EWS (Economically Weaker)", key="cat_ews", use_container_width=True):
                st.session_state.quiz_answers["category"] = "EWS"
                st.session_state.quiz_step = 6
                st.rerun()
        with c2:
            if st.button("OBC (Other Backward Class)", key="cat_obc", use_container_width=True):
                st.session_state.quiz_answers["category"] = "OBC"
                st.session_state.quiz_step = 6
                st.rerun()
            if st.button("Minority (Muslim, Sikh, etc.)", key="cat_min", use_container_width=True):
                st.session_state.quiz_answers["category"] = "Minority"
                st.session_state.quiz_step = 6
                st.rerun()
        with c3:
            if st.button("SC (Scheduled Caste)", key="cat_sc", use_container_width=True):
                st.session_state.quiz_answers["category"] = "SC"
                st.session_state.quiz_step = 6
                st.rerun()
            if st.button("ST (Scheduled Tribe)", key="cat_st", use_container_width=True):
                st.session_state.quiz_answers["category"] = "ST"
                st.session_state.quiz_step = 6
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Back", key="back_5"):
            st.session_state.quiz_step = 4
            st.rerun()

    # STEP 6: Annual Income Level
    elif current_step == 6:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 6 of 7</span>
                <div class="quiz-question">What is your Annual Family Income?</div>
                <div class="quiz-subtitle">Select your income range to filter for income-eligible benefits and BPL schemes.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🏷️ Below ₹1 Lakh / BPL (Low Income)", key="inc_1", use_container_width=True):
                st.session_state.quiz_answers["income"] = "low income BPL below 1 lakh"
                st.session_state.quiz_step = 7
                st.rerun()
            if st.button("🏷️ ₹1 Lakh – ₹2.5 Lakhs", key="inc_2", use_container_width=True):
                st.session_state.quiz_answers["income"] = "1 to 2.5 lakhs income"
                st.session_state.quiz_step = 7
                st.rerun()
        with c2:
            if st.button("🏷️ ₹2.5 Lakhs – ₹6 Lakhs", key="inc_3", use_container_width=True):
                st.session_state.quiz_answers["income"] = "2.5 to 6 lakhs middle income"
                st.session_state.quiz_step = 7
                st.rerun()
            if st.button("🏷️ Above ₹6 Lakhs", key="inc_4", use_container_width=True):
                st.session_state.quiz_answers["income"] = "above 6 lakhs income"
                st.session_state.quiz_step = 7
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Back", key="back_6"):
            st.session_state.quiz_step = 5
            st.rerun()

    # STEP 7: Primary Assistance Needed
    elif current_step == 7:
        st.markdown(
            """
            <div class="quiz-card">
                <span class="quiz-step-badge">Question 7 of 7</span>
                <div class="quiz-question">What Primary Assistance or Scheme Benefit are you seeking?</div>
                <div class="quiz-subtitle">Choose the main area where you need financial or government support.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎓 Education & Scholarship", key="need_edu", use_container_width=True):
                st.session_state.quiz_answers["need"] = "scholarship education tuition hostel fee support"
                st.session_state.quiz_completed = True
                st.rerun()
            if st.button("🏠 Housing & Pucca House", key="need_house", use_container_width=True):
                st.session_state.quiz_answers["need"] = "housing house loan pucca house shelter grant"
                st.session_state.quiz_completed = True
                st.rerun()
            if st.button("👴 Pension & Senior Care", key="need_pen", use_container_width=True):
                st.session_state.quiz_answers["need"] = "pension old age widow disability monthly support"
                st.session_state.quiz_completed = True
                st.rerun()
        with c2:
            if st.button("🌾 Farming & Crop Support", key="need_farm", use_container_width=True):
                st.session_state.quiz_answers["need"] = "crop subsidy fertilizer irrigation kisan income support"
                st.session_state.quiz_completed = True
                st.rerun()
            if st.button("🏥 Medical & Health Insurance", key="need_health", use_container_width=True):
                st.session_state.quiz_answers["need"] = "health insurance medical treatment hospital card ayushman"
                st.session_state.quiz_completed = True
                st.rerun()
        with c3:
            if st.button("💰 Business Loan & Credit", key="need_loan", use_container_width=True):
                st.session_state.quiz_answers["need"] = "business loan mudra credit capital self employment"
                st.session_state.quiz_completed = True
                st.rerun()
            if st.button("🛠️ Skill Training & Employment", key="need_job", use_container_width=True):
                st.session_state.quiz_answers["need"] = "job placement skill training livelihood employment"
                st.session_state.quiz_completed = True
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Back", key="back_7"):
            st.session_state.quiz_step = 6
            st.rerun()


# ── Quiz Completed & Results Section ───────────────────────────────────────────
else:
    ans = st.session_state.quiz_answers
    coref = get_coref()

    # Sync context profile from answers if not done yet
    summary_query = f"I am a {ans.get('age', '')} {ans.get('gender', '')} from {ans.get('state', '')}. Category: {ans.get('category', '')}, Occupation: {ans.get('occupation', '')}, Income: {ans.get('income', '')}. Seeking: {ans.get('need', '')}."
    coref.update_from_message(summary_query)

    # Directly inject quiz answers into profile to guarantee accuracy —
    # NLP extraction from the synthetic sentence can miss or misread values.
    import re as _re
    if ans.get("state"):
        coref.profile.state = ans["state"]
    if ans.get("gender"):
        coref.profile.gender = ans["gender"]
    if ans.get("occupation"):
        coref.profile.occupation = ans["occupation"]
    if ans.get("category"):
        coref.profile.category = ans["category"]
    if ans.get("income"):
        coref.profile.income_group = ans["income"]
    if ans.get("need"):
        coref.profile.need = ans["need"]
    if ans.get("age"):
        _m = _re.search(r"(\d+)", ans["age"])
        if _m:
            coref.profile.age = _m.group(1)

    # Display profile pill summary
    p_pills = ""
    for k, v in ans.items():
        if v:
            p_pills += f'<div class="profile-pill"><strong>{k.title()}:</strong> {v}</div>'
    st.markdown(f'<div class="profile-pill-container">{p_pills}</div>', unsafe_allow_html=True)

    # Fetch RAG recommendations if not cached
    if st.session_state.recommendation_results is None:
        rag = get_rag()
        with st.spinner("🔍 Analyzing scheme database for your profile..."):
            results = rag.recommend(
                user_message=summary_query,
                user_profile=coref.summarize(),
                chat_history=coref.history,
            )
            st.session_state.recommendation_results = results


    # Render Scheme Results Cards
    render_scheme_results(st.session_state.recommendation_results, key_prefix="initial_results")

    st.markdown("---")
    st.markdown('<p class="section-title">💬 Have Follow-up Questions for SevaBot?</p>', unsafe_allow_html=True)
    st.caption("Ask anything about these schemes, eligibility documents, or application procedures.")

    # Render prior chat history if any
    for msg_idx, msg in enumerate(st.session_state.history):
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            with st.chat_message("user", avatar="🧑"):
                st.write(content)
        else:
            with st.chat_message("assistant", avatar="🌾"):
                if isinstance(content, str) and content.strip().startswith("{") and content.strip().endswith("}"):
                    try:
                        res_json = json.loads(content)
                        render_scheme_results(res_json, key_prefix=f"history_{msg_idx}")
                    except Exception:
                        st.markdown(content)
                else:
                    st.markdown(content)

    # Follow-up Chat Input
    user_chat = st.chat_input("Ask a follow-up question to SevaBot...")

    if "pending_chat" in st.session_state and st.session_state.pending_chat:
        user_chat = st.session_state.pending_chat
        st.session_state.pending_chat = None

    if user_chat:
        rag = get_rag()
        coref.update_from_message(user_chat)

        with st.chat_message("user", avatar="🧑"):
            st.write(user_chat)

        st.session_state.history.append({"role": "user", "content": user_chat})

        # Check if user explicitly asked to recalculate or re-give schemes
        re_recommend_keywords = [
            "regive", "re-give", "recalculate", "new schemes", "update schemes",
            "recommend again", "re-evaluate", "altered details", "change profile",
            "different schemes", "refresh schemes", "re-recommend"
        ]
        is_re_recommend = any(kw in user_chat.lower() for kw in re_recommend_keywords)

        with st.chat_message("assistant", avatar="🌾"):
            with st.spinner("🤖 SevaBot is analyzing your request..."):
                if is_re_recommend:
                    follow_res = rag.recommend(
                        user_message=user_chat,
                        user_profile=coref.summarize(),
                        chat_history=st.session_state.history,
                    )
                    st.session_state.recommendation_results = follow_res
                    render_scheme_results(follow_res, key_prefix=f"followup_{len(st.session_state.history)}")
                    st.session_state.history.append({"role": "assistant", "content": json.dumps(follow_res, ensure_ascii=False)})
                    coref.add_to_history("assistant", follow_res.get("summary", ""))
                else:
                    text_answer = rag.chat_answer(
                        user_message=user_chat,
                        user_profile=coref.summarize(),
                        chat_history=st.session_state.history,
                    )
                    st.markdown(text_answer)
                    st.session_state.history.append({"role": "assistant", "content": text_answer})
                    coref.add_to_history("assistant", text_answer[:200])

        st.rerun()
