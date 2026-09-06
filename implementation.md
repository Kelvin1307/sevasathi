# NyayaSetu AI Implementation Guide

## Goal

Build two Streamlit experiences over one shared scheme intelligence core:

- **SevaBot**: the existing guided eligibility wizard in `streamlit.py`.
- **SevaSathi**: a conversational search interface in `sevasathi.py`, with voice input and output.

The vector dataset is built offline. The running application must never ingest source files or rebuild embeddings. At runtime, it loads the previously generated vector artifact and applies deterministic eligibility filters before semantic retrieval.

## 1. Project Structure

```text
SIH/
├── streamlit.py                    # SevaBot guided wizard
├── sevasathi.py                    # SevaSathi conversational interface
├── scripts/
│   └── build_vectors.py            # Offline ingestion and vector build command
├── chat_coref/
│   ├── context.py                  # Conversation profile tracking
│   ├── eligibility.py              # Deterministic MoSJE rules
│   ├── finance.py                  # Moratorium and EMI calculations
│   ├── knowledge.py                # Runtime artifact loading and filtering only
│   ├── prompt.py                   # Grounded LLM prompts
│   ├── retriever.py                # Filtered retrieval and recommendations
│   └── voice.py                    # Groq STT and Edge TTS adapters
├── updated_data.csv
├── channel_partners.csv            # Verified branch/NPA/fund data for routing
├── gov_myscheme/
├── cache/
│   └── faiss_index/                # Generated artifact, not source code
├── requirements.txt
└── .env
```

## 2. Offline Vector Build

Create `scripts/build_vectors.py`. This is the only module allowed to read the CSV and `gov_myscheme/` source files, split documents, create embeddings, and write the vector artifact.

Run it explicitly after source-data changes:

```bash
python scripts/build_vectors.py
```

The command must:

1. Load `updated_data.csv`.
2. Load `.txt`, `.md`, `.json`, `.csv`, and PDF files from `gov_myscheme/`.
3. Normalize every document into a LangChain `Document`.
4. Add consistent metadata:
   - `source`
   - `file_name`
   - `scheme_name`
   - `state`
   - `social_category`
   - `gender`
   - `income_limit`
   - `loan_type`
   - `max_loan`
5. Split documents with a fixed chunk size and overlap.
6. Create embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
7. Save the FAISS index to `cache/faiss_index/`.
8. Save a manifest beside the index containing:
   - cache schema version
   - embedding model
   - chunk settings
   - source-file hashes
   - document and chunk counts
   - build timestamp

The builder should write to a temporary directory first and replace the old artifact only after the new index and manifest are complete. This prevents the application from seeing a partially written cache.

The build script may expose a `--force` option, but rebuilding must never happen implicitly from a Streamlit request.

## 3. Runtime Knowledge Module

Refactor `chat_coref/knowledge.py` so it is a runtime loader, not a pipeline owner.

It must provide functions similar to:

```python
def load_vectorstore(index_dir: str | Path = "cache/faiss_index"):
    """Load an existing FAISS artifact; never build one."""


def load_manifest(index_dir: str | Path = "cache/faiss_index") -> dict:
    """Read and validate the vector artifact manifest."""


def retrieve_documents(
    vectorstore,
    query: str,
    profile: dict,
    top_k: int = 8,
):
    """Apply deterministic metadata filters before semantic retrieval."""
```

`knowledge.py` must:

- fail clearly when the vector artifact does not exist;
- validate the manifest schema and embedding model;
- load FAISS with the existing embedding configuration;
- never call `build_documents`, `build_vectorstore`, or source-file loaders;
- never silently fall back to building vectors during application startup.

If the artifact is missing, the UI should show: `Knowledge index not found. Run python scripts/build_vectors.py first.`

The old pickle TF-IDF fallback should either be removed or treated as a separately generated offline artifact. It must not cause runtime ingestion or rebuilding.

## 4. Deterministic Eligibility Filtering

Create `chat_coref/eligibility.py`.

Implement the MoSJE rules before vector search and before the LLM call:

- Social category: SC where the scheme requires SC eligibility.
- Annual family income: up to ₹5,00,000.
- Micro Finance Scheme: maximum ₹1.40 lakh.
- Term Loan Scheme: maximum ₹50 lakh.
- Educational Loan Scheme: maximum ₹30 lakh.
- Mahila Samriddhi Yojana: female SC entrepreneurs, maximum ₹1.40 lakh.
- State-specific schemes must match the selected state or be marked as national.

The filter should return both documents and exclusion reasons so the UI can explain why a scheme was not shown.

Recommended interface:

```python
def eligible_scheme_metadata(profile: dict, scheme_metadata: dict) -> tuple[bool, str]:
    """Return eligibility and a human-readable reason."""
```

The current seven-step SevaBot flow should be aligned with the PDF by collecting:

1. Gender
2. Age or age category
3. State or Union Territory
4. Rural or urban residency
5. Social category
6. Annual family income
7. Loan purpose and project/course cost

Occupation can remain as additional profile context.

## 5. Retrieval and Recommendation

Update `chat_coref/retriever.py` so `SchemeRAG` only loads the generated artifact:

```python
class SchemeRAG:
    def __init__(self, index_dir="cache/faiss_index", top_k=8):
        self.vectorstore = load_vectorstore(index_dir)
        self.index_manifest = load_manifest(index_dir)
        self.top_k = top_k
```

Recommendation flow:

1. Normalize the user profile.
2. Apply deterministic eligibility rules.
3. Pass the eligible metadata filter to FAISS where supported.
4. Retrieve the highest-scoring chunks.
5. Construct context only from those chunks.
6. Ask the Groq LLM for grounded, structured recommendations.
7. Include eligibility, benefits, documents, application steps, official source, and confidence.
8. State clearly when final approval depends on an authorized channel partner.

Do not import or call document ingestion or vector-building functions from `retriever.py`.

## 6. Shared Finance Module

Create `chat_coref/finance.py` for the PDF formulas:

```text
I_m = P × (r / 100) × (m / 12)
P'  = P + I_m
EMI = [P' × r_m × (1 + r_m)^k] / [(1 + r_m)^k - 1]
```

Where `k = n - m` and `r_m = r / (12 × 100)`.

The module should validate that:

- principal is positive;
- interest rate is non-negative;
- tenure is greater than the moratorium;
- requested principal does not exceed the matched scheme limit.

Both Streamlit applications should use this module instead of duplicating calculations.

## 7. SevaSathi Voice Module

Create `chat_coref/voice.py` with provider selection driven by `.env`:

```env
VOICE_STT_PROVIDER=groq
VOICE_STT_MODEL=whisper-large-v3-turbo
VOICE_TTS_PROVIDER=edge-tts
VOICE_TTS_VOICE=en-US-JennyNeural
```

Responsibilities:

- accept microphone audio bytes from Streamlit;
- transcribe audio with Groq Whisper;
- synthesize assistant text with Edge TTS;
- return playable MP3 bytes to the UI;
- use temporary files only for the duration of the request;
- provide readable errors when credentials, providers, or audio are unavailable.

Add these dependencies to `requirements.txt`:

```text
groq
edge-tts
```

The Groq API key must remain in `.env` and must not be committed.

## 8. SevaSathi Streamlit Application

Create `sevasathi.py` and run it with:

```bash
streamlit run sevasathi.py
```

The application should provide:

- conversational text input;
- microphone input and transcript display;
- spoken assistant responses;
- quick-start categories for farmer, student, women support, housing, healthcare, employment, senior citizen, and disability;
- profile summary using `ChatCoref`;
- filtered scheme cards;
- EMI projection where sufficient values are available;
- official source links;
- conversation history.

The voice orb must open a voice-only mode. In that mode, microphone audio is transcribed internally and the response is synthesized as audio; do not show a transcript, text chat input, or text recommendation response.

Scheme recommendations must be returned even when no location is available. After the scheme result, SevaSathi should say: `If you want to know your nearby channel partners, enter your location address.` Channel-partner routing is optional and only runs after the address is resolved.

## 9. Geo-Spatial Channel Partner Routing

Create `chat_coref/geo_router.py` and populate `channel_partners.csv` only with verified partner data. Required columns are:

```text
partner_name,partner_type,address,state,latitude,longitude,npa_rate,fund_available,fund_allocated
```

The router must:

- geocode the beneficiary address;
- calculate Haversine distance;
- reject partners with `npa_rate >= 7.5`;
- reject partners with zero available funds;
- calculate the health score using NPA, fund availability, and distance decay;
- return ranked eligible partners.

Set `GEOCODING_ENABLED=true` only when the deployment is configured to use the geocoder. Without resolved coordinates, the system must ask for a more complete address and must not claim to have made a geo-spatial recommendation.

Use `st.session_state` for conversation history, location, voice stage, and the loaded `SchemeRAG` instance. Loading the RAG instance may happen once per session, but it must only load the existing vector artifact.

## 10. SevaBot Integration

Keep `streamlit.py` as the guided SevaBot interface. Move shared retrieval, eligibility, finance, and voice-independent logic into `chat_coref` so SevaBot and SevaSathi produce consistent results.

SevaBot should call:

```python
rag = SchemeRAG(index_dir="cache/faiss_index")
result = rag.recommend(user_message, user_profile)
```

It must not rebuild vectors when the app starts.

## 11. Requirements

The runtime requirements should include:

```text
streamlit
pandas
numpy
langchain
langchain-community
langchain-core
langchain-groq
faiss-cpu
sentence-transformers
pypdf
python-dotenv
groq
edge-tts
geopy
```

The vector-builder environment must also have the embedding dependencies installed. The generated `cache/faiss_index/` directory should be retained or regenerated through the explicit build command, depending on deployment strategy.

## 12. Operational Workflow

When source data changes:

```bash
python scripts/build_vectors.py
streamlit run streamlit.py
streamlit run sevasathi.py
```

When only application code changes, do not rebuild vectors. Restarting either Streamlit application should only load the existing artifact.

## 13. Acceptance Checklist

- [ ] `scripts/build_vectors.py` is the only vector-building entry point.
- [ ] `chat_coref/knowledge.py` never reads source data at runtime.
- [ ] Missing or invalid artifacts produce a clear startup message.
- [ ] FAISS metadata filters are applied before semantic retrieval.
- [ ] SevaBot and SevaSathi use the same eligibility rules.
- [ ] `sevasathi.py` supports text and voice input.
- [ ] Groq Whisper uses `whisper-large-v3-turbo`.
- [ ] Edge TTS uses `en-US-JennyNeural`.
- [ ] EMI calculations use the shared finance module.
- [ ] No API key is committed to the repository.
- [ ] Recommendations require a resolved beneficiary location.
- [ ] Partner routing applies NPA and fund exhaustion filters.

## 14. Implementation Order

1. Extract the offline ingestion and embedding code into `scripts/build_vectors.py`.
2. Generate and validate the versioned FAISS artifact.
3. Simplify `chat_coref/knowledge.py` into a runtime loader and filter adapter.
4. Add deterministic eligibility and finance services.
5. Update `SchemeRAG` to load the artifact directly.
6. Update `streamlit.py` to use the shared services.
7. Add `chat_coref/voice.py`.
8. Add `sevasathi.py` with conversational and voice workflows.
9. Run both Streamlit entry points against the generated artifact.
