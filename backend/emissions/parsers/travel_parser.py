import math
from decimal import Decimal
from .base import BaseParser

AIRPORTS = {
    "JFK": (40.6413, -73.7781), "LHR": (51.47, -0.4543),
    "CDG": (49.0097, 2.5479), "FRA": (50.0379, 8.5622),
    "DXB": (25.2532, 55.3657), "SFO": (37.6213, -122.379),
    "LAX": (33.9416, -118.4085), "ORD": (41.9742, -87.9073),
    "AMS": (52.3105, 4.7683), "SIN": (1.3592, 103.9894),
    "HKG": (22.308, 113.9185), "NRT": (35.772, 140.3929),
    "DEL": (28.5562, 77.1), "BOM": (19.0896, 72.8656),
    "SYD": (-33.9399, 151.1753), "ICN": (37.4602, 126.4407),
    "MUC": (48.3538, 11.7861), "ZRH": (47.4582, 8.5551),
    "YYZ": (43.6777, -79.6248), "SEA": (47.4502, -122.3088),
    "BKK": (13.6811, 100.7466), "FCO": (41.8003, 12.2389),
    "MAD": (40.4936, -3.5668), "BCN": (41.2971, 2.0785),
    "CPH": (55.6181, 12.6561), "ARN": (59.6519, 17.9186),
    "OSL": (60.2028, 11.0839), "HEL": (60.3172, 24.9633),
    "WAW": (52.1657, 20.9671), "PRG": (50.1008, 14.26),
    "VIE": (48.1197, 16.5638), "BRU": (50.9014, 4.4844),
    "DUB": (53.4264, -6.2499), "LIS": (38.7742, -9.1342),
    "ATH": (37.9364, 23.9475), "IST": (41.2753, 28.7519),
    "NBO": (-1.3192, 36.9275), "JNB": (-26.1392, 28.246),
    "GIG": (-22.8092, -43.2486), "EZE": (-34.8222, -58.5358),
    "HND": (35.5494, 139.7798), "PVG": (31.1443, 121.8083),
    "PEK": (40.0799, 116.6031), "KUL": (2.7456, 101.7099),
    "MNL": (14.5097, 121.0194),
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def lookup_distance(origin, destination):
    if not origin or not destination:
        return None
    o = origin.upper().strip()
    d = destination.upper().strip()
    if o in AIRPORTS and d in AIRPORTS:
        lat1, lon1 = AIRPORTS[o]
        lat2, lon2 = AIRPORTS[d]
        return round(haversine(lat1, lon1, lat2, lon2), 2)
    return None


class TravelParser(BaseParser):
    source_type = "TRAVEL"

    TYPE_MAP = {
        "FLIGHT": ("FLIGHT", 3), "AIR": ("FLIGHT", 3), "AIRLINE": ("FLIGHT", 3),
        "HOTEL": ("HOTEL", 3), "LODGING": ("HOTEL", 3),
        "CAR_RENTAL": ("CAR_RENTAL", 3), "CAR": ("CAR_RENTAL", 3), "RENTAL": ("CAR_RENTAL", 3),
        "MILEAGE": ("MILEAGE", 3), "MILES": ("MILEAGE", 3),
    }

    COLUMN_MAP = {
        "Expense Type": "expense_type", "expense_type": "expense_type", "Category": "expense_type",
        "Vendor": "vendor", "vendor": "vendor", "Merchant": "vendor",
        "Trip Purpose": "trip_purpose", "Purpose": "trip_purpose",
        "Departure Date": "departure_date", "departure_date": "departure_date", "Start Date": "departure_date",
        "Return Date": "return_date", "return_date": "return_date", "End Date": "return_date",
        "Origin": "origin_code", "origin_code": "origin_code", "From": "origin_code",
        "Destination": "destination_code", "destination_code": "destination_code", "To": "destination_code",
        "Distance (km)": "distance_km", "distance_km": "distance_km",
        "Class": "class_of_service", "class_of_service": "class_of_service", "Cabin": "class_of_service",
        "Hotel Nights": "hotel_nights", "nights": "hotel_nights",
        "Amount": "amount", "amount": "amount", "Total": "amount",
        "Currency": "currency", "currency": "currency",
        "Employee ID": "employee_id", "employee_id": "employee_id",
        "Employee Name": "employee_name", "employee_name": "employee_name", "Name": "employee_name",
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

                raw_type = r.get("expense_type", "").upper()
                cat_info = self.TYPE_MAP.get(raw_type, ("OTHER", 3))
                category = cat_info[0]
                scope = cat_info[1]

                depart = self.parse_date(r.get("departure_date", ""))
                if not depart:
                    self.errors.append({"row": row_num, "error": "Missing departure date"})
                    continue

                ret = self.parse_date(r.get("return_date", ""))
                dist = self.parse_decimal(r.get("distance_km", ""))
                if dist is None and category in ("FLIGHT", "MILEAGE") and r.get("origin_code") and r.get("destination_code"):
                    dist = lookup_distance(r.get("origin_code"), r.get("destination_code")) or Decimal("0")

                cls_raw = r.get("class_of_service", "")
                if cls_raw.upper() in ("FIRST", "F"):
                    cls = "FIRST"
                elif cls_raw.upper() in ("BUSINESS", "BUS", "B"):
                    cls = "BUSINESS"
                else:
                    cls = "ECONOMY"

                nights_raw = r.get("hotel_nights", "")
                nights = int(nights_raw) if nights_raw and nights_raw.isdigit() else None

                if category == "HOTEL":
                    canonical_qty = Decimal(nights or 1)
                    canonical_unit = "nights"
                else:
                    canonical_qty = dist or Decimal("0")
                    canonical_unit = "km"

                description = f"{category} - {r.get('vendor', '')}" if r.get('vendor') else category

                self.parsed_rows.append({
                    "expense_type": category,
                    "vendor": r.get("vendor", ""),
                    "trip_purpose": r.get("trip_purpose", ""),
                    "departure_date": depart,
                    "return_date": ret,
                    "origin_code": r.get("origin_code", ""),
                    "destination_code": r.get("destination_code", ""),
                    "distance_km": dist,
                    "class_of_service": cls,
                    "hotel_nights": nights,
                    "amount": self.parse_decimal(r.get("amount", "")),
                    "currency": r.get("currency", "EUR") or "EUR",
                    "employee_id": r.get("employee_id", ""),
                    "employee_name": r.get("employee_name", ""),
                    "scope": scope,
                    "category": category,
                    "canonical_quantity": canonical_qty,
                    "canonical_unit": canonical_unit,
                    "raw_description": description,
                    "raw_date_from": depart,
                    "raw_date_to": ret,
                })
            except Exception as e:
                self.errors.append({"row": row_num, "error": str(e)})
        return self.parsed_rows, self.errors
