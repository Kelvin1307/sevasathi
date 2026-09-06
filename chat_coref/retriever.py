from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from chat_coref.knowledge import DEFAULT_INDEX_DIR, load_manifest, load_vectorstore, retrieve_documents
from chat_coref.geo_router import geocode_address, load_partners, rank_partners
from chat_coref.prompt import SYSTEM_PROMPT, CHAT_FOLLOWUP_PROMPT

load_dotenv()


class SchemeRAG:
    """
    Retrieval-Augmented Generation pipeline for government scheme recommendations & conversational Q&A.
    Uses vectorstore + Groq-hosted model.
    """

    def __init__(
        self,
        index_dir: str = str(DEFAULT_INDEX_DIR),
        model: str = "openai/gpt-oss-20b",
        top_k: int = 8,
    ):
        self.vectorstore = load_vectorstore(index_dir)
        self.index_manifest = load_manifest(index_dir)
        self.top_k = top_k
        self.partners = load_partners()

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing. Add it to your .env file.")

        print(f"[RAG] Loading Groq model: {model}")
        self.llm = ChatGroq(model_name=model, groq_api_key=groq_api_key, temperature=0.2)
        print("[RAG] Ready.")

    def format_user_profile(self, profile: Dict[str, Any]) -> str:
        if not profile:
            return "No user profile available yet."
        return "\n".join(f"{key}: {value}" for key, value in profile.items())

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response even if wrapped in markdown code fences."""
        cleaned = text.strip()

        # Remove ```json ... ``` or ``` ... ``` fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        # Find the first '{' to start JSON parsing
        brace_idx = cleaned.find("{")
        if brace_idx != -1:
            cleaned = cleaned[brace_idx:]

        return json.loads(cleaned)

    def recommend(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        chat_history: list | None = None,
        location: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Retrieve relevant documents and generate a ranked scheme recommendation JSON."""
        location = location or {}
        coordinates = location.get("coordinates")
        if not coordinates and location.get("address"):
            coordinates = geocode_address(str(location["address"]))
        profile_keywords = " ".join(str(v) for v in user_profile.values())
        enriched_query = f"{user_message} {profile_keywords}".strip()

        relevant_docs = retrieve_documents(self.vectorstore, enriched_query, user_profile, self.top_k)
        context = "\n\n".join(doc.page_content for doc in relevant_docs[:8])
        user_info = self.format_user_profile(user_profile)

        history_text = ""
        if chat_history:
            recent = chat_history[-4:]
            history_text = "\n".join(
                f"{m['role'].capitalize()}: {m['content'][:300]}" for m in recent if isinstance(m.get('content'), str)
            )

        prompt = PromptTemplate.from_template(
            """{system_prompt}

User query:
{user_query}

User profile:
{user_profile}

{history_section}

Retrieved scheme knowledge:
{context}
"""
        )

        filled_prompt = prompt.format(
            system_prompt=SYSTEM_PROMPT,
            user_query=user_message,
            user_profile=user_info,
            history_section=f"Recent conversation:\n{history_text}" if history_text else "",
            context=context,
        )

        response = self.llm.invoke(filled_prompt)
        content = response.content if hasattr(response, "content") else str(response)

        try:
            result = self.parse_json_response(content)
        except Exception as e:
            print(f"[RAG] JSON parse error: {e}")
            result = {
                "summary": "Retrieved recommendations based on your profile.",
                "recommendations": [],
                "_raw": content,
            }
        result["status"] = "complete"
        result["location_resolved"] = bool(coordinates)
        result["best_recommendation"] = (result.get("recommendations") or [None])[0]
        result["partners"] = rank_partners(coordinates[0], coordinates[1], self.partners) if coordinates else []
        result["location"] = (
            {"address": location.get("address", ""), "latitude": coordinates[0], "longitude": coordinates[1]}
            if coordinates
            else None
        )
        result["nearby_channels_message"] = (
            "If you want to know your nearby channel partners, enter your location address."
            if not coordinates
            else ""
        )
        return result

    def chat_answer(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        chat_history: list | None = None,
    ) -> str:
        """Answer a follow-up user question in natural Markdown without regenerating scheme JSON."""
        relevant_docs = retrieve_documents(self.vectorstore, user_message, user_profile, self.top_k)
        context = "\n\n".join(doc.page_content for doc in relevant_docs[:6])
        user_info = self.format_user_profile(user_profile)

        prompt = PromptTemplate.from_template(CHAT_FOLLOWUP_PROMPT)
        filled_prompt = prompt.format(
            user_profile=user_info,
            user_query=user_message,
            context=context,
        )

        response = self.llm.invoke(filled_prompt)
        return response.content if hasattr(response, "content") else str(response)
