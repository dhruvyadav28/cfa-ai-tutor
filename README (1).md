# CFA Level 1 AI Tutor (Duolingo-style)

A gamified CFA Level 1 study app built on Streamlit, powered by **Groq** (Llama 3.3 70B + Mixtral) and a
RAG pipeline over auto-scraped Finance Train / AnalystPrep content.

## Features
- **Learn** — auto-generated sub-lessons per CFA topic, with LaTeX formulas and completion tracking.
- **Quiz** — 5 AI-generated MCQs per lesson with explanations and difficulty tags.
- **Chat** — RAG + web-search (Tavily) ReAct agent for open-ended Q&A, with cited sources.
- **Progress** — XP, streaks, levels (Bronze → Gold → Platinum), and badges, all in SQLite.
- **📖 Define** — floating popup for instant term definitions via Groq's fast model.

## Setup

```bash
pip install -r requirements.txt
```

Copy the secrets template and add your keys:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml with your GROQ_API_KEY and TAVILY_API_KEY
```

Get keys:
- Groq: https://console.groq.com
- Tavily: https://tavily.com

## Run

```bash
streamlit run app.py
```

On first run the app scrapes Finance Train and AnalystPrep into `./data/*.txt`, then builds a local
Chroma vector store (`./chroma_db/`) for retrieval. Progress lives in `./cfa_tutor.db` (SQLite).

## Deploy to Streamlit Cloud
1. Push this folder to a GitHub repo.
2. In Streamlit Cloud, create a new app pointing to `app.py`.
3. Add `GROQ_API_KEY` and `TAVILY_API_KEY` under **App settings → Secrets** (same format as
   `secrets.toml.example`).

## Project Structure
```
cfa-duolingo/
├── app.py                 # Streamlit UI, navigation, sidebar
├── rag_engine.py           # Groq client, scraping trigger, embeddings, Chroma, ReAct agent
├── scraper.py               # Scrapes Finance Train / AnalystPrep -> ./data/*.txt
├── lesson_generator.py      # Groq + RAG -> sub-lessons, cached in SQLite
├── quiz_generator.py        # Groq -> 5 MCQs per lesson, cached in SQLite
├── progress_tracker.py      # SQLite schema + XP/streak/level/badge logic
├── definition_popup.py      # Floating "📖 Define" widget
├── .streamlit/secrets.toml.example
├── requirements.txt
└── data/                    # scraped text cache (populated on first run)
```

## Troubleshooting

| Issue | Fix |
|---|---|
| Scraping returns empty | Site structure may have changed. Drop your own `.txt` files into `./data/` (one per topic) and delete `./chroma_db/` to force a rebuild of the embeddings. |
| `st.navigation` error | Requires Streamlit ≥1.36. Run `pip install --upgrade streamlit`. |
| Definition popup doesn't show | It renders via `components.v1.html` and escapes its iframe to overlay the page — if it's missing, check the browser console for a JS error, and confirm `definition_popup.py` is imported and `render_definition_popup()` is called in `app.py`. |
| Groq rate limit | Free tier has request/token limits on `llama-3.3-70b-versatile`. For lighter calls (like the Define popup) the app already uses the smaller `llama-3.1-8b-instant`. **Note:** `mixtral-8x7b-32768` has been decommissioned on Groq — don't switch back to it; use `llama-3.1-8b-instant` or `llama-3.3-70b-versatile` instead. |
| `tavily-python` not installed | It's in `requirements.txt`; if it's missing at runtime, `web_search()` in `rag_engine.py` already catches the error and the chat agent falls back to RAG-only retrieval. |

## Notes
- Embeddings use local `sentence-transformers/all-MiniLM-L6-v2` (no extra API key needed).
- Scraping is best-effort and minimal; if a site structure changes, lessons still generate from the
  model's own knowledge with a placeholder note in `./data/`.
- Delete `./chroma_db/` and `./data/` to force a fresh re-scrape and re-index.
