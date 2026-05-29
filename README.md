# Breathe ESG — Emission Data Ingestion & Review Platform

Django REST API + React SPA for ingesting, normalizing, and reviewing corporate emission data from SAP (fuel/procurement), utility electricity bills, and corporate travel platforms.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Go to `http://localhost:3000`. API is at `http://localhost:8080/api/`.

## Pages

| Route | Description |
|-------|-------------|
| `/upload` | Select source type, upload CSV, see parse results |
| `/dashboard` | Filter records, approve/flag/lock, bulk approve |
| `/records/:id` | Full record detail, source data, audit trail |

## Source Types

- **SAP** — CSV with German/English headers, semicolon or comma delimited. Fuel and procurement materials with scope mapping.
- **Utility** — CSV from utility portal exports. Meter readings, billing periods, TOU tariffs, estimated/actual reads.
- **Travel** — CSV from Concur/Navan exports. Flights, hotels, car rentals, mileage. Airport code distance lookup.

## Sample Data

Seeds 46 records: 15 SAP, 15 Utility, 16 Travel. Run `python manage.py seed_data`.

## Docs

- `DECISIONS.md` — Every design decision with rationale
- `MODEL.md` — Data model with field-level notes
- `TRADEOFFS.md` — Three things deliberately not built
- `SOURCES.md` — Source format research and sample data justification

## Tech Stack

- **Backend:** Django 6.0 + DRF 3.17 + SQLite (dev) / PostgreSQL (prod)
- **Frontend:** Vite 8 + React 18 + Tailwind CSS
- **Deployment:** Render (see `render.yaml`)
