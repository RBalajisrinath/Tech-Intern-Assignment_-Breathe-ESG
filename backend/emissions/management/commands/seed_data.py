import os
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from emissions.models import *
from emissions.parsers import SAPParser, UtilityParser, TravelParser


SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "media", "sample_data")


def seed_sample_data(source_type):
    mapping = {
        "SAP": ("sap_fuel_export.csv", SAPParser),
        "UTILITY": ("utility_electricity_export.csv", UtilityParser),
        "TRAVEL": ("travel_concur_export.csv", TravelParser),
    }
    filename, parser_class = mapping[source_type]
    filepath = os.path.join(SAMPLE_DIR, filename)

    if not os.path.exists(filepath):
        print(f"  Sample file not found: {filepath}")
        return

    org, _ = Organization.objects.get_or_create(name="Acme Corp", slug="acme-corp")

    upload = SourceUpload.objects.create(
        organization=org,
        source_type=source_type,
        filename=filename,
        status="PARSING",
        uploaded_by="seed",
    )

    with open(filepath, "rb") as f:
        content = f.read().decode("utf-8-sig")

    parser = parser_class(content, upload)
    parsed_rows, errors = parser.parse()

    upload.row_count = len(parsed_rows) + len(errors)
    upload.error_count = len(errors)
    upload.error_log = errors[:100]

    created = 0
    for row_data in parsed_rows:
        emission = EmissionRecord.objects.create(
            organization=org,
            source_upload=upload,
            source_type=source_type,
            scope=row_data.get("scope", 1),
            category=row_data.get("category", "FUEL"),
            subcategory=row_data.get("material_type", row_data.get("tariff_code", "")),
            status="PENDING",
            raw_description=row_data.get("raw_description", ""),
            raw_quantity=row_data.get("quantity", row_data.get("consumption_kwh", row_data.get("canonical_quantity", 0))),
            raw_unit=row_data.get("unit", row_data.get("canonical_unit", "")),
            raw_date_from=row_data.get("raw_date_from", date.today()),
            raw_date_to=row_data.get("raw_date_to", None),
            canonical_quantity=row_data.get("canonical_quantity", 0),
            canonical_unit=row_data.get("canonical_unit", ""),
        )

        if source_type == "SAP":
            SapFuelRecord.objects.create(
                upload=upload, emission_record=emission,
                material_number=row_data.get("material_number", ""),
                material_description=row_data.get("material_description", ""),
                material_type=row_data.get("material_type", ""),
                quantity=row_data.get("quantity", 0),
                unit=row_data.get("unit", ""),
                plant_code=row_data.get("plant_code", ""),
                document_type=row_data.get("document_type", ""),
                document_date=row_data.get("document_date", date.today()),
                posting_date=row_data.get("posting_date", None),
                amount=row_data.get("amount", None),
                currency=row_data.get("currency", "EUR"),
                cost_center=row_data.get("cost_center", ""),
            )
        elif source_type == "UTILITY":
            UtilityRecord.objects.create(
                upload=upload, emission_record=emission,
                meter_id=row_data.get("meter_id", ""),
                utility_name=row_data.get("utility_name", ""),
                billing_start=row_data.get("billing_start", date.today()),
                billing_end=row_data.get("billing_end", date.today()),
                consumption_kwh=row_data.get("consumption_kwh", 0),
                peak_demand_kw=row_data.get("peak_demand_kw", None),
                tariff_code=row_data.get("tariff_code", ""),
                meter_start_read=row_data.get("meter_start_read", None),
                meter_end_read=row_data.get("meter_end_read", None),
                read_type=row_data.get("read_type", "ACTUAL"),
                charge_amount=row_data.get("charge_amount", None),
                currency=row_data.get("currency", "EUR"),
            )
        elif source_type == "TRAVEL":
            TravelRecord.objects.create(
                upload=upload, emission_record=emission,
                expense_type=row_data.get("expense_type", "OTHER"),
                vendor=row_data.get("vendor", ""),
                trip_purpose=row_data.get("trip_purpose", ""),
                departure_date=row_data.get("departure_date", date.today()),
                return_date=row_data.get("return_date", None),
                origin_code=row_data.get("origin_code", ""),
                destination_code=row_data.get("destination_code", ""),
                distance_km=row_data.get("distance_km", None),
                class_of_service=row_data.get("class_of_service", "ECONOMY"),
                hotel_nights=row_data.get("hotel_nights", None),
                amount=row_data.get("amount", None),
                currency=row_data.get("currency", "EUR"),
                employee_id=row_data.get("employee_id", ""),
                employee_name=row_data.get("employee_name", ""),
            )
        created += 1

    upload.parsed_count = created
    upload.status = "PARSED"
    upload.save()

    AuditLog.objects.create(
        organization=org,
        record_type="SourceUpload",
        record_id=upload.id,
        action="SEEDED",
        old_values={},
        new_values={"source_type": source_type, "rows": created, "errors": len(errors)},
        performed_by="seed",
    )

    print(f"  Seeded {created} records from {filename} ({'no errors' if not errors else f'{len(errors)} errors'})")


class Command(BaseCommand):
    help = "Seed the database with sample data for SAP, Utility, and Travel sources"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data...\n")

        org, _ = Organization.objects.get_or_create(name="Acme Corp", slug="acme-corp")
        self.stdout.write(f"  Organization: {org.name}")

        EmissionFactor.objects.get_or_create(
            category="ELECTRICITY", subcategory="Grid Average",
            defaults={"unit": "kWh", "factor_kg_co2e_per_unit": Decimal("0.92"),
                       "source": "EPA eGRID 2024", "effective_from": date(2024, 1, 1)}
        )
        EmissionFactor.objects.get_or_create(
            category="FUEL", subcategory="Diesel",
            defaults={"unit": "L", "factor_kg_co2e_per_unit": Decimal("2.68"),
                       "source": "DEFRA 2024", "effective_from": date(2024, 1, 1)}
        )
        EmissionFactor.objects.get_or_create(
            category="FLIGHT", subcategory="Economy",
            defaults={"unit": "km", "factor_kg_co2e_per_unit": Decimal("0.233"),
                       "source": "DEFRA 2024", "effective_from": date(2024, 1, 1)}
        )
        EmissionFactor.objects.get_or_create(
            category="FLIGHT", subcategory="Business",
            defaults={"unit": "km", "factor_kg_co2e_per_unit": Decimal("0.699"),
                       "source": "DEFRA 2024", "effective_from": date(2024, 1, 1)}
        )

        self.stdout.write("")
        for src in ["SAP", "UTILITY", "TRAVEL"]:
            seed_sample_data(src)

        self.stdout.write("\nDone! Sample data seeded.")
        self.stdout.write(f"  Organization ID: {org.id}")
