# Decisions

These are the fork-in-the-road moments where I had to pick one path and reject another. I tried to note what I'd ask the PM at each one, because some of these are product calls I shouldn't make alone.

## 1. SAP: CSV Upload, Not IDoc

I picked flat file CSV uploads.

IDocs (MATMAS05, INVOIC02) are the "proper" SAP way to do this. They have segments like E1MARAM with fixed-width SDATA fields, and they flow through ALE with partner profiles and RFC destinations. It's robust but it requires an SAP basis team to configure, and most companies I've talked to don't have that set up for external systems.

The reality is that most SAP-to-anything integrations start with someone running SE16 or SQVI and dumping a CSV to a network drive. It's not elegant, but it works on day one without touching the SAP config. The parser auto-detects semicolons vs commas and maps German or English column headers.

**What I'm handling:** Material master data — material number, description, type, quantity, unit, plant, dates, cost, cost center. Fuel materials get Scope 1, procurement items get Scope 3.

**What I'm ignoring:** IDoc hierarchical structures, BOMs, serial numbers, batch management, quality data, serial numbers. If the client needs those, we'd build IDoc parsing in phase 2.

**Ask the PM:** "Does the client already export SAP data to CSV somewhere? Do they use German or English column headers? Do they have ALE middleware we could plug into instead?"

---

## 2. Utility: CSV Portal Export, Not PDF

I picked CSV file uploads from utility portals.

PDF parsing is a nightmare. Every utility formats their bill differently. E.ON's German bill looks nothing like RWE's, and both change their layout every few years. A PDF parser that works at 90%+ accuracy across 50 utilities is a 3-6 month ML project. CSV exports from utility portals are structured, consistent, and available for every enterprise client (they have portal logins).

Green Button XML is the closest thing to a standard, but it's US-centric. EU utilities don't use it. CSV is universal.

**What I'm handling:** Electricity data with meter IDs, billing periods, consumption, peak demand, tariff codes, meter readings, and charges. Actual and estimated reads.

**What I'm ignoring:** PDF invoices, paper bills, natural gas (same model would work with different columns), water, Green Button XML. If a client has a utility that only provides PDF, we'd build a manual entry form rather than a PDF parser.

**Ask the PM:** "Which utilities does this client use in the EU vs US? Do they have portal access? Any utilities that still mail paper bills?"

---

## 3. Travel: File Upload, Not Live API

I picked file uploads from Concur or Navan CSV exports.

Concur's API requires a "Client Web Services" subscription that costs about $500/month. On top of that, you need OAuth 2.0 registration, and you're rate-limited to 120 requests per 5 minutes. The API is paginated and requires multiple round-trips per expense report. A CSV export (Reports → Export → CSV) is free, immediate, and requires zero IT setup.

Navan's API is similar. Same story.

**What I'm handling:** Flights, hotels, car rentals, mileage claims. Each with type, vendor, dates, cost, employee attribution, airport codes, and class of service.

**What I'm ignoring:** Per-diem allowances, meal expenses, parking/tolls, office supplies that show up in Concur, software subscriptions. IATA lookup covers ~40 major airports — a production system would need the full OurAirports database.

**Ask the PM:** "Concur or Navan? Do they have the paid CWS subscription? Can they get a CSV export from their travel admin?"

---

## 4. Unit Normalization: Keep Both Raw and Canonical

I store the original value AND a normalized version on every record. This means I never throw away what SAP actually said.

Why this matters: If SAP says "500 L" and I convert it to "398.6 kg" using a diesel density factor, an auditor needs to see 500 L, not 398.6 kg. If the emission factor changes next year, I can recalculate from the raw value instead of trying to reverse my own conversion.

The canonical mapping for this MVP:
- L / LTR → L (diesel, gasoline, heating oil)
- KG / KGM → kg (lubricants, propane)
- ST / PC / EA → units (office supplies, hardware)
- kWh → kWh (electricity)
- km → km (flights, car rentals)
- nights → nights (hotels)

**Ask the PM:** "Do we have a standard list of canonical units the client uses, or should I use the GHG Protocol defaults?"

---

## 5. Status Workflow: PENDING → REVIEWED → APPROVED → LOCKED

Four states with a flag side-path.

PENDING means nobody has looked at it. REVIEWED means someone looked and it seems fine. APPROVED means it's been signed off. LOCKED means it's frozen for audit — no edits, no status changes.

FLAGGED is for when something looks suspicious (estimated meter read, unusually high consumption, missing airport code). Flagged records can still be approved if the analyst decides it's fine, but the flag stays in the audit trail.

---

## 6. Airport Distance: Haversine with a Built-In Lookup Table

Travel CSV exports often give you airport codes (JFK, LHR, FRA) but no distances. So I compute the great-circle distance using the Haversine formula.

The airport lookup table is hardcoded in the parser with about 40 major airports. Yes, that's a hack. A production system would use OurAirports (40K+ airports) or a geocoding service. But for an MVP that handles the most common business travel routes, 40 airports covers JFK-LHR, SFO-FRA, CDG-DXB, and all the other common pairs.

---

## 7. CO2 Calculation: Deferred

I'm not calculating CO2e in this version. The model supports it — canonical_quantity × emission_factor = co2e_kg — but I'm not running that calculation.

Why: CO2 calculation is a product decision, not an engineering one. Electricity can use market-based or location-based factors (different numbers, both valid). Flights need a radiative forcing index multiplier. Factors change every year and differ by country. I don't know which factors this client uses, and picking the wrong ones would produce wrong numbers that someone might report.

The seed data includes sample factors from EPA eGRID (electricity) and DEFRA (fuels, flights) to show the mechanism works. When we know what factors the client actually uses, we flip the switch.

**Ask the PM:** "Which emission factor database does the client use — EPA eGRID, DEFRA, GHG Protocol, or their own? Market-based or location-based for electricity? Do they need RFI multipliers for flights?"

---

## 8. Separate Source Tables, Not One Wide Table

I could have put all source data into one table with a type column and a JSON blob. I didn't.

SAP data has material numbers, plant codes, document types. Utility data has meter IDs, tariff codes, meter readings. Travel data has airport codes, hotel nights, cabin class. These don't overlap. A single wide table would be 90% nulls. A JSON blob would make "find all SAP records from plant 1100" impossible without parsing JSON at query time.

The cost is that adding a new source type means new table + migration + serializer + viewset. That's more code but cleaner data.

---

## 9. Error Log in JSONField, Not a Separate Table

Parser errors go into a JSONField on SourceUpload. They're generated during parsing and shown once in the upload result UI. They don't need to be queried, indexed, or joined. A separate ErrorLog table would add a join for what's essentially a transient message. If someone later wants "show me all parsing errors from last month," that's when we migrate to a proper table.

---

## What I'd Ask the PM If I Could

1. **Volume and frequency:** How many rows per source per month? Daily or monthly uploads?
2. **User roles:** Who uploads, who reviews, who approves, who locks? Need SSO?
3. **Emission factors:** Which database — EPA eGRID, DEFRA, GHG Protocol, or client custom? Market-based or location-based for electricity?
4. **Notifications:** Should the review team know when new data lands? Should approvers get pinged?
5. **Connector priority:** Which should we build first — live SAP API, Concur API, or PDF bill ingestion?
6. **Auditor access:** Do auditors get a read-only view, or the same dashboard with no edit buttons?
7. **Data retention:** How long do we keep raw files? What's the deletion policy for test or erroneous uploads?
8. **Multi-region:** Does the client operate in the EU ETS, UK ETS, California? Each has different reporting rules.
