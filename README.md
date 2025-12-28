# ForgeBreaker

A thinking tool for MTG Arena players who want to understand their decks, not just build them.

## Who This Is For

ForgeBreaker is for **deck brewers and budget-conscious players** who ask questions like:

- "What assumptions does my deck rely on?"
- "Which parts of my deck are fragile?"
- "What happens if this card or interaction underperforms?"
- "Why does this deck feel inconsistent?"

If you want to understand *why* a deck works (or doesn't), ForgeBreaker helps you explore that.

## What ForgeBreaker Does

**Surface Assumptions** — Every deck relies on implicit assumptions: mana curve expectations, key card dependencies, interaction timing. ForgeBreaker makes these visible and inspectable.

**Stress Test Ideas** — Intentionally stress specific assumptions to see what breaks first. Simulate underperformance, missing pieces, or variance scenarios.

**Explain Outcomes** — Every result comes with an explanation of what assumptions drove it and explicit acknowledgment of uncertainty.

**Collection-Aware Recommendations** — See which meta decks you're closest to completing and understand the wildcard investment required.

## What ForgeBreaker Is NOT

ForgeBreaker is deliberately limited in scope:

- **Not a meta aggregation platform** — We don't compete with Untapped, MTGGoldfish analytics, or similar services
- **Not a ladder optimizer** — We don't claim to tell you what deck will climb fastest
- **Not a winrate predictor** — Our ML-assisted recommendations have known limitations (see [Model Card](docs/MODEL_CARD.md))
- **Not a replacement for playtesting** — Understanding assumptions doesn't replace actually playing games

ForgeBreaker helps you think about your deck. It doesn't think for you.

## How It Works

```
Your Collection → ForgeBreaker
                      ↓
              Analyze Deck Assumptions
              (mana curve, key cards, interaction timing)
                      ↓
              Surface Fragility
              (what breaks under stress)
                      ↓
              Explain with Uncertainty
              ("Based on assumptions X, Y... results may vary if Z")
```

### Core Features

- **Import Collection** — Paste your Arena export to track owned cards
- **Browse Meta Decks** — See competitive decks from MTGGoldfish with completion percentages
- **Calculate Distance** — Understand wildcard costs to complete any deck
- **AI Deck Advisor** — Chat with Claude about your collection and deck ideas (with MCP tool calling)
- **Assumption Analysis** — See what your deck relies on (coming soon)
- **Stress Testing** — Simulate "what if" scenarios (coming soon)

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Frontend**: React 19 / TypeScript / Tailwind CSS
- **Database**: PostgreSQL (async via SQLAlchemy 2.0)
- **ML**: MLForge API for recommendation scoring (see [Model Card](docs/MODEL_CARD.md))
- **LLM**: Claude API with MCP tool calling

## Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/forgebreaker"
export ANTHROPIC_API_KEY="your-api-key"

# Run linting and tests
ruff check .
ruff format --check .
mypy forgebreaker
pytest

# Start dev server
uvicorn forgebreaker.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/collection/{user_id}` | GET | Get user's collection stats |
| `/collection/{user_id}/import` | POST | Import Arena collection |
| `/collection/{user_id}/stats` | GET | Collection statistics |
| `/decks/{format}` | GET | List meta decks for format |
| `/decks/{format}/{deck_name}` | GET | Get specific deck |
| `/distance/{user_id}/{format}/{deck_name}` | GET | Calculate deck distance |
| `/chat/` | POST | Chat with Claude |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://localhost:5432/forgebreaker` |
| `ANTHROPIC_API_KEY` | Claude API key | (required for chat) |
| `MLFORGE_URL` | MLForge API endpoint | `https://backend-production-b2b8.up.railway.app` |
| `DEBUG` | Enable debug mode | `false` |

## Deployment

Configured for Railway deployment. See `railway.toml` and `Procfile`.

## Project Structure

```
forgebreaker/
├── api/           # FastAPI routers
├── analysis/      # Deck distance/ranking/assumptions
├── db/            # Database operations
├── mcp/           # MCP tool definitions
├── models/        # Domain models
├── parsers/       # Arena export parsers
├── services/      # Deck building, synergies
└── scrapers/      # MTGGoldfish scraper

frontend/
├── src/
│   ├── api/       # API client
│   ├── components/# React components
│   └── hooks/     # React Query hooks
```

## License

MIT
