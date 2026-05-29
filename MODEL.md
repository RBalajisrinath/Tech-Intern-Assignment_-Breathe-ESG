# Data Model

I kept going back and forth on how to structure this. Here's what I ended up with and why.

## The Big Picture

Everything is scoped to an Organization. No org can see another org's data. Simple FK on every table.

```
Organization ──┬── SourceUpload (one org, many uploads)
               ├── EmissionRecord (one org, many records)
               └── AuditLog (one org, many log entries)

SourceUpload ──┬── SapFuelRecord (one upload = many SAP rows)
               ├── UtilityRecord
               ├── TravelRecord
               └── EmissionRecord (one upload → many records)

EmissionRecord ──┬── SapFuelRecord (1:1, optional)
                 ├── UtilityRecord (1:1, optional)
                 ├── TravelRecord (1:1, optional)
                 └── AuditLog (many, polymorphic)

EmissionFactor (not tied to any org — global reference table)
```

## Why It's Split Like This

SAP data has material numbers, plant codes, cost centers. Utility data has meter IDs, tariff codes, meter readings. Travel data has airport codes, hotel nights, employee names. These have almost nothing in common. Throwing them into one wide table would give you 40 columns where 36 are null for any given row. So each source gets its own table with fields that actually make sense for that domain.

The `EmissionRecord` table is the canonical version — what matters for carbon accounting. The source tables (SapFuelRecord, UtilityRecord, TravelRecord) hold the original details — what matters for audit and reprocessing.

## Tables

### Organization

Just a name and a slug. The slug is what goes in URLs. Created automatically when a client signs up.

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | |
| name | CharField(255) | "Acme Corp" |
| slug | SlugField(unique) | "acme-corp" |
| created_at | DateTimeField(auto_now_add) | |

### SourceUpload

Every file or API pull that enters the system gets one of these. This is how you trace a row back to where it came from.

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | |
| organization | FK(Organization) | Scoped |
| source_type | Choice(SAP/UTILITY/TRAVEL) | |
| upload_type | Choice(FILE_UPLOAD/API_PULL/MANUAL) | Default FILE_UPLOAD for now |
| filename | CharField(500) | Original filename, like "sap_fuel_export.csv" |
| raw_file | FileField(null) | Stored so we can re-parse if the parser changes |
| status | Choice(UPLOADED/PARSING/PARSED/FAILED) | |
| row_count | IntegerField | Total rows in file |
| parsed_count | IntegerField | How many made it through the parser |
| error_count | IntegerField | How many failed |
| error_log | JSONField | Array of {row, error} objects. I picked JSON over a separate table because these errors are ephemeral — shown once on the upload result screen, not queried later. |
| uploaded_by | CharField(255) | Who did it |
| uploaded_at | DateTimeField(auto_now_add) | When |

### EmissionRecord

This is the main table. Every emission record lives here regardless of whether it came from SAP, a utility bill, or a travel expense. Analysts review and approve these.

| Field | Type | Notes |
|-------|------|-------|
| organization | FK(Organization) | Tenant isolation |
| source_upload | FK(SourceUpload, nullable) | Links back to the original file |
| source_type | CharField | SAP/UTILITY/TRAVEL — denormalized so we don't have to join to filter |
| scope | IntegerField(1/2/3) | Scope 1 = direct (fuel burned on site), Scope 2 = purchased electricity, Scope 3 = value chain (flights, hotels, etc.) |
| category | CharField | FUEL/ELECTRICITY/FLIGHT/HOTEL/CAR_RENTAL/MILEAGE |
| subcategory | CharField | Free text: "ROH" for raw materials, tariff code for electricity, economy class for flights |
| status | Choice(PENDING/REVIEWED/APPROVED/FLAGGED/LOCKED) | Workflow state |
| raw_description | TextField | Original description from source |
| raw_quantity | Decimal(16,4) | The quantity exactly as it arrived |
| raw_unit | CharField(20) | The unit exactly as it arrived (L, kg, ST, kWh, km) |
| raw_date_from | Date | Start of the reporting period |
| raw_date_to | Date(null) | End. Null for single-day events like fuel delivery |
| canonical_quantity | Decimal(16,4) | Normalized to our standard unit |
| canonical_unit | CharField(20) | L, kg, kWh, km, nights, units |
| co2e_kg | Decimal(16,4, null) | Not calculated yet. Field is ready for when we build the CO2 engine |
| source_record_id | CharField | The ID of this record in the source system (e.g. SAP material number) |
| is_edited | Boolean | Was this manually edited after parsing? |
| edited_by/at/reason | | Who, when, why |
| flagged_by/at/reason | | Flag audit trail |
| approved_by/at | | Approval audit trail |
| locked_by/at | | Lock audit trail |
| notes | TextField | Analyst's free-text notes |

The status flow looks like this:

```
PENDING → REVIEWED → APPROVED → LOCKED
  ↓                        ↑
  └──→ FLAGGED →──────────┘
```

LOCKED means the record is frozen. No edits, no status changes. That's the audit-ready state.

### SapFuelRecord

Stores the original SAP row. One-to-one with EmissionRecord.

| Field | Notes |
|-------|-------|
| material_number | MATNR from SAP |
| material_description | MAKTX — what the material is called |
| material_type | MTART — ROH (raw material/fuel), HAWA (trading goods), FERT (finished) |
| quantity, unit | As it came out of SAP |
| plant_code | WERKS — plant identifier. Means nothing without the client's lookup table |
| document_type | BSTYP — document category |
| document_date, posting_date | BLDAT, BUDAT |
| amount, currency | DMBTR, WAERS — cost if available |
| cost_center | KOSTL — who to bill internally |

### UtilityRecord

| Field | Notes |
|-------|-------|
| meter_id | Utility's identifier for this meter |
| utility_name | E.ON SE, RWE AG, EnBW, Vattenfall — whoever supplies the power |
| billing_start, billing_end | The billing period. Often doesn't align to calendar months |
| consumption_kwh | Total kWh for the period |
| peak_demand_kw | Highest demand spike. Matters for time-of-use tariffs |
| tariff_code | TOU-G3-IND (industrial), TOU-G2-COM (commercial), etc. |
| meter_start_read, meter_end_read | Beginning and ending meter readings |
| read_type | ACTUAL (someone read the meter) or ESTIMATED (utility guessed) |
| charge_amount, currency | What the utility charged |

### TravelRecord

| Field | Notes |
|-------|-------|
| expense_type | FLIGHT/HOTEL/CAR_RENTAL/MILEAGE |
| vendor | Airline, hotel chain, rental agency |
| origin_code, destination_code | IATA airport codes like JFK, LHR, FRA |
| distance_km | Either in the CSV or computed from airport codes via Haversine |
| class_of_service | ECONOMY/BUSINESS/FIRST — business class emits ~3x economy |
| hotel_nights | Number of nights stayed |
| amount, currency | Transaction amount |
| employee_id, employee_name | Who traveled |

### AuditLog

Immutable, append-only. Every time someone approves a record, flags a record, edits a record, or a seed script runs, it gets logged here.

| Field | Notes |
|-------|-------|
| organization | FK — scoped |
| record_type | Like "EmissionRecord" |
| record_id | The ID of whatever was changed |
| action | APPROVE, FLAG, LOCK, EDIT, SEED, etc. |
| old_values, new_values | JSON snapshots of what changed |
| performed_by | User identifier |
| performed_at | Auto-set |

### EmissionFactor

Static reference table. Not tied to any org. Used for CO2 calculation when we build that feature.

| Field | Notes |
|-------|-------|
| category | FUEL/ELECTRICITY/FLIGHT/HOTEL/CAR_RENTAL/MILEAGE |
| subcategory | Diesel, Grid Average, Economy class |
| unit | L, kWh, km, nights |
| factor_kg_co2e_per_unit | The actual emission factor |
| source | EPA eGRID, DEFRA, etc. |
| effective_from, effective_to | When this factor is valid. Updated yearly |

## Indexes

Three compound indexes on EmissionRecord:

- (organization, status) — the dashboard filter
- (organization, source_type) — breakdown by source
- (organization, scope) — Scope 1/2/3 reporting

## Multi-Tenancy Note

Right now the API takes `?organization=1` as a query parameter. That's obviously not production-ready. In production, every API request would be scoped by `request.user.organization` extracted from a JWT. But for an MVP that demonstrates the data model and workflow, the query parameter approach works fine.
