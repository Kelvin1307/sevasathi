"""SevaSathi conversational and voice-only interface.

Run with: streamlit run sevasathi.py
"""
from __future__ import annotations

import json
import re

import streamlit as st
from dotenv import load_dotenv

from chat_coref.context import ChatCoref
from chat_coref.knowledge import KnowledgeIndexError
from chat_coref.retriever import SchemeRAG

load_dotenv()

st.set_page_config(page_title="SevaSathi", page_icon="🌾", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #fffaf2, #f9e5bf); }
    .hero { padding: 1.5rem 1.8rem; border-radius: 18px; color: white; background: linear-gradient(120deg, #8f2e08, #ed6b12); margin-bottom: 1rem; }
    .scheme-card { padding: 1rem 1.2rem; border: 1px solid #efb66e; border-left: 5px solid #d95d0d; border-radius: 12px; background: rgba(255,255,255,.82); margin-bottom: .8rem; }
    .score-track { height: 8px; background: #f3d9bd; border-radius: 99px; overflow: hidden; margin: .45rem 0 .9rem; }
    .score-fill { height: 100%; background: linear-gradient(90deg, #f5961e, #8f2e08); border-radius: 99px; }
    .profile-card { padding: .7rem .8rem; border: 1px solid #efb66e; border-radius: 10px; background: rgba(255,255,255,.72); }
    .profile-row { display: flex; justify-content: space-between; gap: .5rem; padding: .25rem 0; font-size: .82rem; border-bottom: 1px solid rgba(180,100,20,.1); }
    .profile-row:last-child { border-bottom: 0; }
    .profile-key { color: #9a7040; }
    .profile-val { color: #3b1b04; font-weight: 600; text-align: right; }
    div[data-testid="stButton"] button[kind="secondary"] { border-radius: 50%; width: 92px; height: 92px; padding: 0; font-size: 2.4rem; margin: 1rem auto; display: block; background: #d95d0d; color: white; border: 6px solid #ffd59e; box-shadow: 0 0 0 8px rgba(217,93,13,.15), 0 12px 30px rgba(120,45,5,.25); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_rag(cache_version: str = "20260906-groq-reasoning-v2") -> SchemeRAG:
    return SchemeRAG()


def speak(text: str) -> None:
    try:
        from chat_coref.voice import synthesize_speech
        audio = synthesize_speech(text)
        if audio:
            st.audio(audio, format="audio/mp3", autoplay=True)
    except Exception as exc:
        st.error(f"Voice response unavailable: {exc}")


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
    text = message.strip().lower()
    if field == "gender":
        if "transgender" in text or "third gender" in text:
            return "transgender"
        if any(word in text for word in ("female", "woman", "women", "girl")):
            return "female"
        if any(word in text for word in ("male", "man", "men", "boy")):
            return "male"
    elif field == "age":
        explicit_age = re.search(
            r"(?:\b(?:i am|i'm|age is|aged)\s*)(\d{1,3})\b|\b(\d{1,3})\s*(?:years?\s*old|yrs?\.?\s*old)\b",
            text,
        )
        standalone_age = re.fullmatch(r"\s*(\d{1,3})\s*", text)
        match = explicit_age or standalone_age
        age_value = next((group for group in match.groups() if group), None) if match else None
        if age_value and 1 <= int(age_value) <= 110:
            return f"{age_value} years old"
        for keyword, value in {"youth": "17 years old", "young": "25 years old", "adult": "45 years old", "senior": "65 years old", "elderly": "65 years old"}.items():
            if keyword in text:
                return value
    elif field == "state":
        states = ("Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal")
        for state in states:
            if state.lower() in text:
                return state
    elif field == "occupation":
        values = {"farmer": ("farmer", "agriculture", "kisan"), "student": ("student", "school", "college", "studying"), "self-employed": ("self-employed", "business", "entrepreneur", "shopkeeper", "startup owner", "startup founder", "founder"), "unemployed": ("unemployed", "jobless", "job seeker"), "labour": ("labour", "labor", "worker", "daily wage"), "homemaker": ("homemaker", "housewife", "retired", "pensioner")}
        for value, keywords in values.items():
            if any(keyword in text for keyword in keywords):
                return value
    elif field == "category":
        values = {"General": ("general", "open category"), "EWS": ("ews", "economically weaker"), "OBC": ("obc", "backward class"), "SC": ("scheduled caste", "dalit"), "ST": ("scheduled tribe", "tribal"), "Minority": ("minority", "muslim", "sikh", "christian")}
        for value, keywords in values.items():
            if value in {"SC", "ST", "OBC", "EWS"} and re.search(rf"\b{value.lower()}\b", text):
                return value
            if any(keyword in text for keyword in keywords):
                return value
    elif field == "income":
        if any(keyword in text for keyword in ("below", "bpl", "less than 1", "under 1", "low income")):
            return "low income BPL below 1 lakh"
        if any(keyword in text for keyword in ("1 to 2.5", "1-2.5", "less than 2.5", "under 2.5", "below 2.5", "2.5 lpa", "2.5 lakh", "one to two", "middle income")):
            return "1 to 2.5 lakhs income"
        if any(keyword in text for keyword in ("2.5 to 6", "2.5-6", "two to six")):
            return "2.5 to 6 lakhs middle income"
        if any(keyword in text for keyword in ("above", "over 6", "more than 6", "high income")):
            return "above 6 lakhs income"
    elif field == "need":
        values = {"scholarship": ("education", "scholarship", "tuition", "study"), "housing": ("housing", "house", "shelter", "home"), "healthcare": ("health", "medical", "hospital", "medicine", "insurance"), "agriculture": ("farm", "farming", "crop", "fertilizer", "kisan"), "pension": ("pension", "senior", "old age", "retirement"), "loan": ("loan", "credit", "business", "finance", "startup"), "employment": ("job", "employment", "work", "skill", "livelihood")}
        for value, keywords in values.items():
            if any(keyword in text for keyword in keywords):
                return value
    return ""


def _sync_answer_to_profile(field: str, value: str) -> None:
    profile_field = {"income": "income_group"}.get(field, field)
    setattr(st.session_state.chat_coref.profile, profile_field, value)


def _extract_answers(message: str) -> dict[str, str]:
    """Extract every eligibility field present in one natural-language turn."""
    return {
        field: value
        for field, _, _ in QUESTION_FLOW
        if (value := _answer_value(field, message))
    }


def append_assistant_message(content: str) -> None:
    st.session_state.history.append({"role": "assistant", "content": content})
    st.session_state.chat_coref.add_to_history("assistant", content)


def render_result(result: dict, key_prefix: str = "main") -> None:
    st.write(result.get("summary", ""))
    recommendations = result.get("recommendations", [])
    if not recommendations:
        st.warning("No exact matching schemes found. Try updating your profile in a new conversation.")
        return

    st.subheader("Recommended schemes")
    for index, item in enumerate(recommendations[:3], start=1):
        scheme_name = item.get("scheme_name", f"Scheme {index}")
        score = float(item.get("match_score", 0) or 0)
        score_pct = int(score * 100) if score <= 1 else int(score)
        confidence = item.get("confidence", "Medium")
        source = str(item.get("official_source", ""))
        docs = item.get("documents_required", []) or ["Aadhaar Card", "Bank Account Passbook", "Income / Caste Certificate"]
        steps = item.get("application_steps", []) or ["Visit the official scheme portal or nearest CSC", "Register and upload the required documents", "Submit the application and save the acknowledgement number"]
        st.markdown(
            f"<div class='scheme-card'><h3>{index}. {scheme_name}</h3>"
            f"<p><b>{confidence} match</b> · {score_pct}% relevance</p>"
            f"<div class='score-track'><div class='score-fill' style='width:{max(0, min(score_pct, 100))}%'></div></div>"
            f"<p>{item.get('why_it_matches', '')}</p></div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Details and application steps: {scheme_name}", expanded=index == 1):
            st.markdown("**Eligibility**")
            for value in item.get("eligibility", []):
                st.markdown(f"- {value}")
            st.markdown("**Benefits**")
            for value in item.get("benefits", []):
                st.markdown(f"- {value}")
            st.markdown("**Documents required**")
            for value in docs:
                st.markdown(f"- {value}")
            st.markdown("**Application steps**")
            for step_index, value in enumerate(steps, start=1):
                st.markdown(f"{step_index}. {value}")
            if source:
                apply_url = source if source.startswith("http") else f"https://www.google.com/search?q={source.replace(' ', '+')}"
                st.link_button("Apply on official portal", apply_url, key=f"sevasathi_apply_{key_prefix}_{index}_{scheme_name[:20]}")

    if not result.get("location_resolved"):
        st.info("If you want nearby channel partners, use device location or enter your complete address in the sidebar.")
    partners = result.get("partners", [])
    if partners:
        partner = partners[0]
        st.subheader("Nearest eligible channel partner")
        st.markdown(
            f"- **{partner.get('partner_name', 'Partner')}**: {partner.get('address', '')} "
            f"({partner.get('distance_km')} km)"
        )


def start_msg() -> None:
    """Start a text conversation once per Streamlit session."""
    if st.session_state.history:
        return
    append_assistant_message("Hello, I am SevaSathi. I will ask seven short questions, one at a time, before finding suitable schemes.")
    _, question, hint = current_question()
    append_assistant_message(f"**{question}**\n\n{hint}")


def _is_recommendation_request(message: str) -> bool:
    keywords = (
        "recommend again", "new schemes", "different schemes", "re-evaluate",
        "recalculate", "update scheme", "recommend schemes", "scheme list",
    )
    normalized = message.lower()
    return any(keyword in normalized for keyword in keywords)


def msg_handle(user_input: str, rag: SchemeRAG) -> str | dict:
    """Handle one user turn and persist both messages before the next turn."""
    coref = st.session_state.chat_coref
    st.session_state.history.append({"role": "user", "content": user_input})
    coref.add_to_history("user", user_input)

    if not st.session_state.quiz_completed:
        extracted_answers = _extract_answers(user_input)
        if not extracted_answers:
            response = "I could not identify that answer. Please provide a clear response for this question."
            append_assistant_message(response)
            return response

        for field, value in extracted_answers.items():
            st.session_state.quiz_answers[field] = value
            _sync_answer_to_profile(field, value)

        missing_fields = [
            field for field, _, _ in QUESTION_FLOW
            if not st.session_state.quiz_answers.get(field)
        ]
        st.session_state.quiz_step = next(
            (index + 1 for index, (field, _, _) in enumerate(QUESTION_FLOW) if field in missing_fields),
            len(QUESTION_FLOW) + 1,
        )
        if missing_fields:
            _, question, hint = current_question()
            response = f"**{question}**\n\n{hint}"
        else:
            st.session_state.quiz_completed = True
            response = "Thanks. I have all seven details. I am now checking the scheme database for your eligibility."
        append_assistant_message(response)
        return response

    coref.update_from_message(user_input)

    from chat_coref.geo_router import contains_location_hint, extract_location_phrase, geocode_address

    location = st.session_state.get("location")
    if not location and contains_location_hint(user_input):
        coordinates = geocode_address(extract_location_phrase(user_input))
        if coordinates:
            location = {"address": user_input, "coordinates": coordinates}
            st.session_state.location = location

    if _is_recommendation_request(user_input):
        response = rag.recommend(user_input, coref.summarize(), coref.history, location)
    else:
        response = rag.chat_answer(user_input, coref.summarize(), coref.history)

    st.session_state.history.append({"role": "assistant", "content": response})
    history_content = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else response
    coref.add_to_history("assistant", history_content)
    return response


def end_msg() -> None:
    """End the current conversation and clear its state."""
    st.session_state.history = []
    st.session_state.chat_coref.reset()
    st.session_state.pop("location", None)
    st.session_state.location_request_active = False


def _refresh_location_result(rag: SchemeRAG) -> bool:
    """Re-run the latest recommendation after a location becomes available."""
    last_user_message = next(
        (item["content"] for item in reversed(st.session_state.history) if item["role"] == "user"),
        "",
    )
    if not last_user_message:
        return False

    refreshed = rag.recommend(
        last_user_message,
        st.session_state.chat_coref.summarize(),
        st.session_state.chat_coref.history,
        st.session_state.location,
    )
    st.session_state.recommendation_results = refreshed
    for item in reversed(st.session_state.history):
        if item["role"] == "assistant" and isinstance(item["content"], dict):
            item["content"] = refreshed
            break
    return True


def _save_location(location: dict, rag: SchemeRAG) -> None:
    st.session_state.location = location
    st.session_state.location_request_active = False
    _refresh_location_result(rag)


def request_device_location(rag: SchemeRAG) -> None:
    """Request browser location and keep the address fallback available."""
    if not st.session_state.get("location_request_active") or st.session_state.get("location"):
        return
    try:
        from streamlit_geolocation import streamlit_geolocation
    except ImportError:
        st.session_state.location_request_active = False
        st.warning("Device location is unavailable in this installation. Enter your address below instead.")
        return

    browser_location = streamlit_geolocation()
    latitude = browser_location.get("latitude") if browser_location else None
    longitude = browser_location.get("longitude") if browser_location else None
    if latitude is None or longitude is None:
        st.info("Allow location access in your browser. If it is unavailable, enter your address below.")
        return

    _save_location(
        {
            "address": "Current device location",
            "coordinates": (float(latitude), float(longitude)),
            "source": "browser",
        },
        rag,
    )
    st.success("Your device location was used for nearby channel recommendations.")
    st.rerun()


def voice_page(rag: SchemeRAG) -> None:
    """Voice-only interaction page: audio in, audio out, no transcript or text chat."""
    if st.button("←", key="leave_voice", help="Return to text conversation"):
        st.query_params.clear()
        st.rerun()

    st.markdown("<div class='hero'><h1>SevaSathi Voice</h1><p>Speak naturally. I will listen and answer aloud.</p></div>", unsafe_allow_html=True)
    if "voice_stage" not in st.session_state:
        st.session_state.voice_stage = "request"
    if "voice_location" not in st.session_state:
        st.session_state.voice_location = None
    if "voice_prompted" not in st.session_state:
        st.session_state.voice_prompted = False

    if not st.session_state.voice_prompted:
        prompt = "Please tell me what scheme or financial support you need. I can recommend schemes now. If you want nearby channel partners, you can say your location afterward."
        speak(prompt)
        st.session_state.voice_prompted = True

    voice_input = st.audio_input("Voice input", label_visibility="collapsed")
    if voice_input is None:
        return

    try:
        from chat_coref.voice import transcribe_audio
        spoken_text = transcribe_audio(voice_input.getvalue(), "voice-input.wav")
        result = msg_handle(spoken_text, rag)
        st.session_state.voice_prompted = False
        if st.session_state.quiz_completed and st.session_state.recommendation_results is None:
            answers = st.session_state.quiz_answers
            summary_query = (
                f"I am {answers['age']} and {answers['gender']} from {answers['state']}. "
                f"Category: {answers['category']}, Occupation: {answers['occupation']}, "
                f"Income: {answers['income']}. Seeking: {answers['need']}."
            )
            st.session_state.recommendation_results = rag.recommend(
                summary_query,
                st.session_state.chat_coref.summarize(),
                st.session_state.chat_coref.history,
                st.session_state.get("location"),
            )
        if isinstance(result, dict):
            response = result.get("summary", "I found eligible schemes for you.")
        elif st.session_state.recommendation_results:
            response = st.session_state.recommendation_results.get("summary", result)
        else:
            response = result
        speak(response)
        st.session_state.voice_stage = "request"
    except Exception as exc:
        st.session_state.voice_prompted = False
        speak(f"I could not process that voice input. {exc}")


if "chat_coref" not in st.session_state:
    st.session_state.chat_coref = ChatCoref()
if "history" not in st.session_state:
    st.session_state.history = []
if "quiz_step" not in st.session_state:
    st.session_state.quiz_step = 1
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {field: "" for field, _, _ in QUESTION_FLOW}
if "quiz_completed" not in st.session_state:
    st.session_state.quiz_completed = False
if "recommendation_results" not in st.session_state:
    st.session_state.recommendation_results = None
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False
if "location_request_active" not in st.session_state:
    st.session_state.location_request_active = False

try:
    rag = get_rag()
except KnowledgeIndexError as exc:
    st.error(str(exc))
    st.stop()

if st.query_params.get("mode") == "voice":
    voice_page(rag)
    st.stop()

with st.sidebar:
    st.markdown("<div style='text-align:center; padding:.5rem 0 1rem;'><div style='font-size:2.8rem;'>🌾</div><div style='font-size:1.55rem; font-weight:800; color:#c35b00;'>SevaSathi</div><div style='font-size:.8rem; color:#9a7040;'>Conversational Government Scheme Assistant</div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("#### Conversation progress")
    for step_number, (field, _, _) in enumerate(QUESTION_FLOW, start=1):
        answer = st.session_state.quiz_answers.get(field, "")
        marker = "✅" if answer else "◉" if step_number == st.session_state.quiz_step and not st.session_state.quiz_completed else "○"
        state_label = "Complete" if answer else "Current" if marker == "◉" else "Pending"
        st.markdown(f"<div class='profile-row'><span class='profile-key'>{marker} {step_number}. {field.title()}</span><span class='profile-val'>{state_label}</span></div>", unsafe_allow_html=True)
    st.progress(sum(bool(st.session_state.quiz_answers.get(field)) for field, _, _ in QUESTION_FLOW) / len(QUESTION_FLOW))

    st.markdown("#### Eligibility profile")
    profile = st.session_state.chat_coref.summarize()
    if profile:
        rows = "".join(f"<div class='profile-row'><span class='profile-key'>{key.replace('_', ' ').title()}</span><span class='profile-val'>{value}</span></div>" for key, value in profile.items())
        st.markdown(f"<div class='profile-card'>{rows}</div>", unsafe_allow_html=True)
    else:
        st.caption("Your saved answers will appear here.")

    st.markdown("---")
    st.session_state.voice_enabled = st.toggle("🎙 Voice chat", value=st.session_state.voice_enabled, help="Enable microphone answers in the conversation.")
    if st.button("🔄 New conversation", use_container_width=True):
        end_msg()
        st.session_state.quiz_step = 1
        st.session_state.quiz_answers = {field: "" for field, _, _ in QUESTION_FLOW}
        st.session_state.quiz_completed = False
        st.session_state.recommendation_results = None
        st.session_state.voice_enabled = False
        st.rerun()

    st.markdown("---")
    st.markdown("#### Nearby channel partners")
    if st.button("Use my current location", use_container_width=True, key="sevasathi_device_location"):
        st.session_state.location_request_active = True
        st.rerun()
    request_device_location(rag)
    address = st.text_input("Complete address", placeholder="Village, district, state", key="sevasathi_channel_address")
    if st.button("Find nearby channels", use_container_width=True, key="sevasathi_use_location") and address.strip():
        from chat_coref.geo_router import geocode_address
        coordinates = geocode_address(address)
        if not coordinates:
            st.error("Address could not be resolved. Check geocoding settings and provide a complete address.")
        else:
            _save_location({"address": address, "coordinates": coordinates, "source": "address"}, rag)
            st.success("Location saved.")
            st.rerun()

    st.markdown("---")
    st.caption("Recommendations are grounded in the local scheme knowledge index. Final approval depends on the authorized partner.")

start_msg()

st.markdown(
    '<div class="hero"><h1>Find the right government scheme</h1><p>Tell me what you need. If you want nearby channels, enter your location afterward.</p></div>',
    unsafe_allow_html=True,
)

def render_history() -> None:
    for message_index, message in enumerate(st.session_state.history):
        if isinstance(message["content"], dict):
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


render_history()

if not st.session_state.quiz_completed:
    user_input = st.chat_input("Answer the current question...")
    if st.session_state.voice_enabled:
        voice_input = st.audio_input("Or answer by voice", label_visibility="visible")
        if voice_input is not None:
            try:
                from chat_coref.voice import transcribe_audio
                user_input = transcribe_audio(voice_input.getvalue(), "sevasathi-eligibility-answer.wav")
            except Exception as exc:
                st.error(f"Voice input unavailable: {exc}")
    if user_input:
        msg_handle(user_input, rag)
        st.rerun()
    st.stop()

if st.session_state.recommendation_results is None:
    answers = st.session_state.quiz_answers
    summary_query = (
        f"I am {answers['age']} and {answers['gender']} from {answers['state']}. "
        f"Category: {answers['category']}, Occupation: {answers['occupation']}, "
        f"Income: {answers['income']}. Seeking: {answers['need']}."
    )
    with st.spinner("Analyzing your completed eligibility profile..."):
        st.session_state.recommendation_results = rag.recommend(
            summary_query,
            st.session_state.chat_coref.summarize(),
            st.session_state.chat_coref.history,
            st.session_state.get("location"),
        )
    st.session_state.chat_coref.add_to_history(
        "assistant", json.dumps(st.session_state.recommendation_results, ensure_ascii=False)
    )
    st.rerun()

render_result(st.session_state.recommendation_results, key_prefix="current")
st.subheader("Continue your conversation")
st.caption("Ask about eligibility, benefits, documents, application steps, or request updated schemes.")
follow_up = st.chat_input("Ask a follow-up question...")
if st.session_state.voice_enabled:
    voice_follow_up = st.audio_input("Or ask by voice", label_visibility="visible")
    if voice_follow_up is not None:
        try:
            from chat_coref.voice import transcribe_audio
            follow_up = transcribe_audio(voice_follow_up.getvalue(), "sevasathi-follow-up.wav")
        except Exception as exc:
            st.error(f"Voice input unavailable: {exc}")
if follow_up:
    msg_handle(follow_up, rag)
    st.rerun()

st.stop()

voice_col, reset_col = st.columns([1, 1])
with voice_col:
    if st.button("🎙", key="voice_orb", help="Open voice-only conversation"):
        st.query_params["mode"] = "voice"
        st.rerun()
with reset_col:
    if st.button("New conversation", key="new_conversation"):
        end_msg()
        st.rerun()

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and isinstance(message["content"], dict):
            render_result(message["content"])
        else:
            st.write(message["content"])

user_input = st.chat_input("Tell me about your situation...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("Thinking..."):
        response = msg_handle(user_input, rag)
    with st.chat_message("assistant"):
        if isinstance(response, dict):
            render_result(response)
            speak(response.get("summary", "Your scheme recommendations are ready."))
        else:
            st.markdown(response)
            speak(response)
    st.rerun()

st.divider()
st.subheader("Nearby channel partners")
st.caption("Scheme recommendations do not require a location. Add one only if you want the best scheme and nearby authorized channels for that location.")
if st.button("Use my current location", key="use_device_location"):
    st.session_state.location_request_active = True
    st.rerun()
request_device_location(rag)

address = st.text_input("Location address", placeholder="Village, district, state", key="channel_address")
if st.button("Find nearby channels", key="use_location") and address.strip():
    from chat_coref.geo_router import geocode_address
    coordinates = geocode_address(address)
    if not coordinates:
        st.error("Address could not be resolved. Check GEOCODING_ENABLED=true and provide a complete address.")
    else:
        _save_location({"address": address, "coordinates": coordinates, "source": "address"}, rag)
        st.success("Location saved. Nearby eligible channels are now available above.")
        st.rerun()
