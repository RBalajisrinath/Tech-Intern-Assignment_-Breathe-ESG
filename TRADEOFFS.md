# Tradeoffs — Three Things I Didn't Build

Every project has stuff you deliberately leave out. Here are three big ones and why they're not in this version.

## 1. PDF Bill Ingestion

**The idea:** You upload a PDF utility bill and the system extracts meter readings, consumption, charges, and dates automatically.

**Why it's not here:** PDF parsing is a rabbithole with no bottom. Utilities format their bills completely differently — E.ON's German PDF has different tables, fonts, and layouts than RWE's. When a utility rebrands or updates their billing software, the parser breaks and someone has to retrain a model or update a template. Building something that works across 50+ utilities at 90%+ accuracy is a 3-6 month project involving ML training, template configuration, and someone whose job it is to maintain it.

CSV exports from utility portals already exist and are structured. Enterprise clients have portal access — that's how their facilities teams pull data today. For the remaining 15% of utilities that only provide paper bills, a manual data entry form in the UI is more pragmatic than a PDF pipeline.

**What I'd tell the PM:** "PDF ingestion is 4-6 weeks of work with ongoing maintenance. CSV covers 85% of utility data today. I'd build a manual entry form for the rest and revisit PDF only if a specific client needs it. If they do, I'd evaluate a service like Azure Form Recognizer rather than building our own OCR."

---

## 2. Live API Connectors

**The idea:** Direct integrations with SAP (BAPI/OData), Concur (Expense API v4), and Navan (REST API) that pull data on a schedule without anyone uploading files.

**Why it's not here:** Each API integration requires:

- OAuth 2.0 setup, client registration, API keys, service accounts
- Rate limit handling (Concur: 120 requests per 5 minutes per user)
- Error handling for network failures, API version changes, schema drift
- Scheduled job infrastructure (Celery + Redis or similar)
- Credential storage and rotation

That's a lot of infrastructure for something we haven't validated yet. File uploads let us test the data model and the review workflow end-to-end before we invest in API plumbing. API connectors are the obvious phase 2 — and I designed the parser architecture so that a new connector just replaces the "Source → Parser" step without changing anything downstream.

**The pipeline looks like this:**

```
Source → Parser → Normalized dicts → EmissionRecords + SourceRecords
```

An API connector only replaces the first two boxes. The rest stays the same.

---

## 3. Automated CO2 Calculation Engine

**The idea:** The system automatically multiplies canonical_quantity × emission_factor for every record and fills in the co2e_kg field.

**Why it's not here:** CO2 calculation looks like simple multiplication but it's not. Here's why:

- **Electricity:** Market-based vs. location-based factors. Both are valid. They give different numbers.
- **Flights:** You need a radiative forcing index multiplier. Short-haul and long-haul have different factors. Business class emits about 3x economy.
- **Hotels:** Factors depend on the country (grid mix for electricity), star rating, and even occupancy rate.
- **Emission factors change every year.** EPA eGRID updates annually. DEFRA updates annually. Different clients use different databases.
- **Some clients have proprietary factors** they've developed internally.

Building this correctly requires someone who actually knows carbon accounting, not just someone who can write the multiplication. I built the model to support it — the EmissionFactor table has date-ranged factors, and EmissionRecord has a co2e_kg field waiting to be filled. But the actual calculation logic and factor selection should be a product decision validated by someone who knows the domain.

**What I built instead:** The EmissionFactor table with sample factors from EPA eGRID and DEFRA, and the co2e_kg field on every record. When we know what factors the client actually uses, the calculation function looks like:

```python
def calculate_co2(record):
    factor = EmissionFactor.objects.get(
        category=record.category,
        effective_from__lte=record.raw_date_from,
        effective_to__gte=record.raw_date_from,
    )
    return record.canonical_quantity * factor.factor_kg_co2e_per_unit
```

It's ready. Just needs someone to say "yes, use these factors."
