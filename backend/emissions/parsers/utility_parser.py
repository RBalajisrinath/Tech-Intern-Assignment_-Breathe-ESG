from decimal import Decimal
from .base import BaseParser


class UtilityParser(BaseParser):
    source_type = "UTILITY"
    scope = 2
    category = "ELECTRICITY"

    COLUMN_MAP = {
        "Meter ID": "meter_id", "Meter": "meter_id", "meter_id": "meter_id",
        "Utility": "utility_name", "Utility Name": "utility_name", "utility_name": "utility_name",
        "Billing Start": "billing_start", "billing_start": "billing_start",
        "Service Period Start": "billing_start",
        "Billing End": "billing_end", "billing_end": "billing_end",
        "Service Period End": "billing_end",
        "Consumption (kWh)": "consumption_kwh", "consumption_kwh": "consumption_kwh",
        "Usage (kWh)": "consumption_kwh", "kWh": "consumption_kwh",
        "Peak Demand (kW)": "peak_demand_kw", "peak_demand_kw": "peak_demand_kw",
        "Tariff": "tariff_code", "tariff_code": "tariff_code", "Rate": "tariff_code",
        "Meter Start": "meter_start_read", "meter_start_read": "meter_start_read",
        "Meter End": "meter_end_read", "meter_end_read": "meter_end_read",
        "Read Type": "read_type", "read_type": "read_type",
        "Total Charge": "charge_amount", "charge_amount": "charge_amount",
        "Amount": "charge_amount",
        "Currency": "currency", "currency": "currency",
    }

    def _map_row(self, row):
        mapped = {}
        for k, v in row.items():
            k = k.strip()
            if k in self.COLUMN_MAP:
                mapped[self.COLUMN_MAP[k]] = self.safe_strip(v)
        return mapped

    def parse(self):
        reader = self.get_reader()
        for row_num, row in enumerate(reader, start=2):
            try:
                r = self._map_row(row)

                bill_start = self.parse_date(r.get("billing_start", ""))
                bill_end = self.parse_date(r.get("billing_end", ""))

                if not bill_start or not bill_end:
                    self.errors.append({"row": row_num, "error": f"Invalid dates: {r.get('billing_start')} / {r.get('billing_end')}"})
                    continue

                kwh = self.parse_decimal(r.get("consumption_kwh", "0")) or Decimal("0")
                peak = self.parse_decimal(r.get("peak_demand_kw", ""))

                rt = r.get("read_type", "ACTUAL")
                read_type = "ESTIMATED" if rt.upper() in ("ESTIMATED", "EST", "E") else "ACTUAL"

                description = f"Meter {r.get('meter_id', '')}"
                if r.get("utility_name"):
                    description += f" - {r.get('utility_name')}"

                self.parsed_rows.append({
                    "meter_id": r.get("meter_id", ""),
                    "utility_name": r.get("utility_name", ""),
                    "billing_start": bill_start,
                    "billing_end": bill_end,
                    "consumption_kwh": kwh,
                    "peak_demand_kw": peak,
                    "tariff_code": r.get("tariff_code", ""),
                    "meter_start_read": self.parse_decimal(r.get("meter_start_read", "")),
                    "meter_end_read": self.parse_decimal(r.get("meter_end_read", "")),
                    "read_type": read_type,
                    "charge_amount": self.parse_decimal(r.get("charge_amount", "")),
                    "currency": r.get("currency", "EUR") or "EUR",
                    "scope": 2,
                    "category": "ELECTRICITY",
                    "canonical_quantity": kwh,
                    "canonical_unit": "kWh",
                    "raw_description": description,
                    "raw_date_from": bill_start,
                    "raw_date_to": bill_end,
                })
            except Exception as e:
                self.errors.append({"row": row_num, "error": str(e)})
        return self.parsed_rows, self.errors
