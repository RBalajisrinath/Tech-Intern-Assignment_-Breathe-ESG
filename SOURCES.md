# Sources — Research and Sample Data

I spent a bunch of time researching what these data sources actually look like in the wild, not what the documentation says they should look like. Here's what I found and how it shaped the sample data.

---

## Source 1: SAP — Fuel and Procurement Data

### What I Researched

SAP has multiple ways to get data out. I looked at:

- **IDoc MATMAS05 (Material Master):** This is SAP's native format for material data exchange. It uses hierarchical segments — E1MARAM for the header (MATNR, MTART, MEINS), E1MAKTM for descriptions (SPRAS, MAKTX), E1MARM for units of measure. The data lives in 1000-character fixed-width SDATA fields inside EDID4 tables. To use IDocs, you need ALE configuration, partner profiles (WE20), distribution models (BD64), and RFC connections. It's robust but it's a whole project to set up.

- **IDoc INVOIC02 (Invoice):** For billing documents. Segments include E1EDK01 (header with currency, document number), E1EDP01 (line items with material, quantity, unit), E1EDKA1 (partner info). Common for procurement invoice scenarios.

- **BAPI / OData:** SAP's REST APIs via SAP Gateway. Requires service configuration and authentication. Becoming more common with S/4HANA Cloud but not universal yet.

- **Flat file / CSV:** Extracted via SE16 (table browser), SQVI (quick viewer), or custom Z-transactions. This is by far the most common integration path for external systems that don't have ALE or OData infrastructure. It's not glamorous but it works.

### What I Learned

1. **German column headers are the norm in EU installations.** You'll see MATNR, MENGE, MEINS, WERKS, BUDAT, DMBTR, WAERS, KOSTL. English headers exist but aren't universal. The parser handles both.

2. **Units are all over the place.** A material might be in liters (L), kilograms (KG), pieces (ST), or even the same material measured in different units at different plants.

3. **Plant codes are meaningless without a lookup table.** "1100" and "1200" are internal codes. You need the client to tell you what plant each code maps to.

4. **Material types determine Scope, but the mapping isn't straightforward.** ROH (raw materials) could be Scope 1 if it's diesel fuel or Scope 3 if it's paper rolls. HAWA (trading goods) is typically Scope 3. FERT (finished goods) is Scope 3. The parser uses a simple mapping table, but production would need a client-specific configuration.

5. **Semicolon delimiters.** German Windows defaults to semicolons in CSV exports. The parser auto-detects this.

### My Sample Data

The CSV `sap_fuel_export.csv` has 15 rows with:

- German column headers (MATNR, MAKTX, MTART, etc.) to match EU deployments
- Realistic materials: diesel (4500 L), gasoline (1200 L), heating oil (8000 L), natural gas (25000 kWh), lubricants (200 L), office supplies (150 units), IT hardware (10 units)
- Mixed scopes: ROH materials → Scope 1 (fuel), HAWA items → Scope 3 (procurement)
- Multiple plants: 1100 (HQ), 1200 (warehouse), 1300 (maintenance)
- Semicolon delimiter to test the auto-detection

### What Would Break in Production

- **Material type mapping is too simple.** ROH = Scope 1 assumes the raw material is fuel. Paper rolls are ROH but Scope 3. Production needs a client-provided mapping table.
- **Volume.** A real SAP export could be 50K+ rows. The current code processes them one at a time in a transaction. For 50K rows that would be slow and memory-heavy.
- **Encoding.** SAP exports can be ISO-8859-1 (Latin-1) for Western Europe. The parser assumes UTF-8. It would need encoding fallback.
- **Custom fields.** Clients add Z-fields (ZZEI_MATGRP, etc.) that the column mapper won't recognize. The admin would need a column mapping UI.
- **Deduplication.** The system re-parses the entire file each time. Production would need a way to detect and skip already-imported rows (hash of material number + document date).

---

## Source 2: Utility — Electricity Data

### What I Researched

- **Green Button (ESPI XML/CSV):** A standard from the Green Button Alliance. Uses `<UsageSummary>` with billing period, energy usage, charges, meter readings. Adopted by 100+ US utilities. The format is standardized but US-centric.

- **Utility portal CSV exports:** Most utility portals now have a "Download Data" button. Common columns: account number, service period, consumption, peak demand, meter readings, tariff/rate, charges. This is the most common path for enterprise facilities teams.

- **Smart meter platforms:** IAMMETER, Emporia Energy, and similar export CSV with timestamps and 15-minute interval data.

- **Utility bill OCR:** Services like utilitybillocr.com exist but accuracy varies wildly.

### What I Learned

1. **Billing periods almost never align with calendar months.** A bill might run January 15 to February 14. Carbon reporting is usually monthly or quarterly. You need to prorate consumption, which is a downstream calculation. The model stores the raw period.

2. **Time-of-use tariffs matter.** Industrial customers have peak/off-peak rates. Maximum demand in kW is as important as consumption in kWh for tariff calculations and sometimes for emission factor selection.

3. **Estimated vs. actual reads.** Utilities estimate when they can't access the meter. Estimated reads are less reliable and should be flagged for analyst review. The model captures this.

4. **Green Button is the closest thing to a standard,** but it's mainly US utilities. EU utilities use portal CSVs with different column names.

### My Sample Data

The CSV `utility_electricity_export.csv` has 15 rows with:

- 5 meters across real German utilities: E.ON SE, RWE AG, EnBW AG, Vattenfall AB
- 3 months per meter (January–March 2026)
- Staggered billing start dates (1st, 5th, 10th, 15th, 20th) — reflects real cycle diversity
- TOU tariffs: TOU-G3-IND (industrial), TOU-G2-COM (commercial), TOU-G1-SML (small)
- One estimated read on MTR-003 for February (flagged by the read_type field)
- Realistic consumption: 5,000–45,000 kWh/month with peak demand 22–185 kW

### What Would Break in Production

- **Column variation.** Every utility portal exports slightly different columns. Production would need configurable column mappings per utility per client.
- **Missing meter IDs.** Some exports don't include meter identifiers. Without meter_id you can't track trends or detect missing periods.
- **Composite bills.** Some utilities bill multiple meters on one CSV with subtotals. Parsing that needs hierarchical logic.
- **Negative consumption.** Solar installations export power. Consumption can be negative. The parser accepts negative values but the model doesn't distinguish import from export.
- **Multiple currencies.** EUR for EU, GBP for UK, USD for US. The model handles this via the currency field but doesn't convert to a common currency.

---

## Source 3: Corporate Travel — Flights, Hotels, Ground Transport

### What I Researched

- **Concur Expense API v4:** Base URL is `https://us.api.concursolutions.com/expensereports/v4/`. The key endpoint is `GET /users/{userId}/context/TRAVELER/reports/{reportId}/expenses` which returns expense items with ExpenseTypeName (Airline, Hotel, Car Rental, Mileage), TransactionDate, TransactionAmount, VendorDescription. The Trip Itinerary v4 API provides airport codes and class of service. Requires OAuth 2.0 and a paid CWS subscription (~$500/month). Rate limited to 120 requests per 5 minutes per user.

- **Concur CSV Export:** Every Concur admin can export reports to CSV via Reports → Export. No API subscription needed. The CSV includes expense type, vendor, date, amount, employee name, and (if configured) custom fields like trip purpose.

- **Navan API:** Similar structure to Concur. REST API with OAuth 2.0.

- **Corporate credit card data:** Amex, Visa, and Mastercard commercial card programs provide transaction-level data. Often used alongside travel platform data.

### What I Learned

1. **Distances are usually missing.** Concur CSVs have cost and vendor but rarely distance. If you have airport codes you can calculate great-circle distance. If you only have cost, you have to estimate distance from cost, which is much less accurate.

2. **Class of service matters a lot.** A business class flight emits roughly 3x the CO2 of economy for the same route. The model captures this so we can apply different emission factors.

3. **Employee attribution is important.** Travel emissions need to be attributed to the traveler (for internal carbon budgets) and the department (for cost allocation). The model tracks both employee_id on TravelRecord and cost_center on the parent EmissionRecord.

4. **API integration is expensive.** Concur's CWS subscription adds $500/month. Many organizations don't have it. CSV export is universally available and free.

5. **Hotel emissions depend on location.** A hotel in Norway (hydroelectric grid) has lower indirect emissions than one in Poland (coal grid). The model captures nights stayed but uses a flat factor. Geographic differentiation would need the hotel's address.

### My Sample Data

The CSV `travel_concur_export.csv` has 16 rows with:

- 5 employees with realistic names
- 6 flights: JFK→FRA (Lufthansa, business), SFO→LHR (British Airways, economy), CDG→DXB (Emirates, business), FRA→MUC, ZRH→AMS (economy), LHR→JFK (Virgin Atlantic, economy)
- 5 hotels: Marriott (3 nights), ibis (1 night), Hilton (4 nights), Radisson Blu (2 nights), Accor (2 nights)
- 2 car rentals: Sixt (3 days), Enterprise (5 days)
- 2 mileage claims at €0.50/km (standard EU rate)
- Airport codes without distances in some rows — the parser computes Haversine distance
- Mixed economy and business class

### What Would Break in Production

- **Missing airport codes.** If the CSV doesn't include origin/destination, we can't calculate distance. Fallback would be to estimate from cost (cost ÷ average price/km for that route type), which is rough.
- **Currency conversion.** Expenses come in USD, EUR, GBP, etc. The model stores the original currency but doesn't convert. Production needs daily exchange rate feeds.
- **Non-travel expenses in the feed.** Concur is also used for office supplies, software, and other purchases. These need to be filtered out or categorized differently.
- **Duplicate or deleted reports.** Expense reports can be deleted, updated, or re-submitted. The current model treats each upload as append-only. Production needs upsert logic based on report_id + expense_id.
- **Per-diem allowances.** Some organizations pay per-diem instead of reimbursing actual hotel and meal costs. Per-diem is harder to map to emission factors.
