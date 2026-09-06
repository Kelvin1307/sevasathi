"""SevaSathi conversational and voice-only interface.

Run with: streamlit run sevasathi.py
"""
from __future__ import annotations

import json

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
    div[data-testid="stButton"] button[kind="secondary"] { border-radius: 50%; width: 92px; height: 92px; padding: 0; font-size: 2.4rem; margin: 1rem auto; display: block; background: #d95d0d; color: white; border: 6px solid #ffd59e; box-shadow: 0 0 0 8px rgba(217,93,13,.15), 0 12px 30px rgba(120,45,5,.25); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_rag() -> SchemeRAG:
    return SchemeRAG()


def speak(text: str) -> None:
    try:
        from chat_coref.voice import synthesize_speech
        audio = synthesize_speech(text)
        if audio:
            st.audio(audio, format="audio/mp3", autoplay=True)
    except Exception as exc:
        st.error(f"Voice response unavailable: {exc}")


def render_result(result: dict) -> None:
    st.write(result.get("summary", ""))
    recommendations = result.get("recommendations", [])
    if not result.get("location_resolved"):
        st.subheader("Recommended schemes")
        for item in recommendations:
            st.markdown(f"- **{item.get('scheme_name', 'Scheme')}**: {item.get('why_it_matches', '')}")
        if recommendations:
            st.info("If you want to know your nearby channel partners and the best scheme for your location, enter your location address.")
        return

    item = result.get("best_recommendation") or (recommendations[0] if recommendations else None)
    if item:
        st.subheader(item.get("scheme_name", "Best recommended scheme"))
        st.markdown(
            f"<div class='scheme-card'><strong>{item.get('scheme_name', 'Scheme')}</strong>"
            f"<p>{item.get('why_it_matches', '')}</p>"
            f"<p><b>Eligibility:</b> {', '.join(item.get('eligibility', []))}</p>"
            f"<p><b>Benefits:</b> {', '.join(item.get('benefits', []))}</p>"
            f"<p><b>Documents required:</b> {', '.join(item.get('documents_required', []))}</p>"
            f"<p><b>Steps to apply:</b></p><ol>{''.join(f'<li>{step}</li>' for step in item.get('application_steps', []))}</ol>"
            f"<p><b>Official source:</b> {item.get('official_source', 'Verify with an authorized partner')}</p></div>",
            unsafe_allow_html=True,
        )
    partners = result.get("partners", [])
    if partners:
        st.subheader("Nearest eligible channel partners")
        for partner in partners:
            st.markdown(
                f"- **{partner.get('partner_name', 'Partner')}**: {partner.get('address', '')} "
                f"({partner.get('distance_km')} km, health score {partner.get('health_score')})"
            )


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

    voice_input = st.audio_input("", label_visibility="collapsed")
    if voice_input is None:
        return

    try:
        from chat_coref.voice import transcribe_audio
        spoken_text = transcribe_audio(voice_input.getvalue(), "voice-input.wav")
        coref = st.session_state.chat_coref
        from chat_coref.geo_router import contains_location_hint, extract_location_phrase, geocode_address
        location = st.session_state.voice_location
        if not location and contains_location_hint(spoken_text):
            coordinates = geocode_address(extract_location_phrase(spoken_text))
            if coordinates:
                location = {"address": spoken_text, "coordinates": coordinates}
                st.session_state.voice_location = location
        coref.update_from_message(spoken_text)
        result = rag.recommend(spoken_text, coref.summarize(), coref.history, location)
        st.session_state.voice_prompted = False
        response = result.get("summary", "I found eligible schemes for you.")
        if result.get("partners"):
            response += f" I found {len(result['partners'])} eligible channel partners near your location."
        elif not result.get("location_resolved"):
            response += " If you want nearby channel partners and the best scheme for your location, say your location address."
        speak(response)
        st.session_state.voice_stage = "request"
        coref.add_to_history("user", spoken_text)
        coref.add_to_history("assistant", json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        st.session_state.voice_prompted = False
        speak(f"I could not process that voice input. {exc}")


if "chat_coref" not in st.session_state:
    st.session_state.chat_coref = ChatCoref()
if "history" not in st.session_state:
    st.session_state.history = []

try:
    rag = get_rag()
except KnowledgeIndexError as exc:
    st.error(str(exc))
    st.stop()

if st.query_params.get("mode") == "voice":
    voice_page(rag)
    st.stop()

st.markdown(
    '<div class="hero"><h1>Find the right government scheme</h1><p>Tell me what you need. If you want nearby channels, enter your location afterward.</p></div>',
    unsafe_allow_html=True,
)

if st.button("🎙", key="voice_orb", help="Open voice-only conversation"):
    st.query_params["mode"] = "voice"
    st.rerun()

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and isinstance(message["content"], dict):
            render_result(message["content"])
        else:
            st.write(message["content"])

user_input = st.chat_input("Tell me about your situation...")
if user_input:
    coref = st.session_state.chat_coref
    coref.update_from_message(user_input)
    profile = coref.summarize()
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    from chat_coref.geo_router import contains_location_hint, extract_location_phrase, geocode_address
    location = st.session_state.get("location")
    if not location and contains_location_hint(user_input):
        coordinates = geocode_address(extract_location_phrase(user_input))
        if coordinates:
            location = {"address": user_input, "coordinates": coordinates}
            st.session_state.location = location
    with st.chat_message("assistant"):
        with st.spinner("Searching eligible schemes..."):
            result = rag.recommend(user_input, profile, coref.history, location)
        render_result(result)
        speak(result.get("summary", "Your scheme recommendations are ready."))
    st.session_state.history.append({"role": "assistant", "content": result})
    coref.add_to_history("user", user_input)

st.divider()
st.subheader("Nearby channel partners")
st.caption("Scheme recommendations do not require a location. Add one only if you want the best scheme and nearby authorized channels for that location.")
address = st.text_input("Location address", placeholder="Village, district, state", key="channel_address")
if st.button("Find nearby channels", key="use_location") and address.strip():
    from chat_coref.geo_router import geocode_address
    coordinates = geocode_address(address)
    if not coordinates:
        st.error("Address could not be resolved. Check GEOCODING_ENABLED=true and provide a complete address.")
    else:
        st.session_state.location = {"address": address, "coordinates": coordinates}
        last_user_message = next(
            (item["content"] for item in reversed(st.session_state.history) if item["role"] == "user"),
            "",
        )
        if last_user_message:
            profile = st.session_state.chat_coref.summarize()
            refreshed = rag.recommend(last_user_message, profile, st.session_state.chat_coref.history, st.session_state.location)
            for item in reversed(st.session_state.history):
                if item["role"] == "assistant" and isinstance(item["content"], dict):
                    item["content"] = refreshed
                    break
        st.success("Location saved. Nearby eligible channels are now available above.")
        st.rerun()
