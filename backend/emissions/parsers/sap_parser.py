from datetime import date
from decimal import Decimal
from .base import BaseParser


class SAPParser(BaseParser):
    source_type = "SAP"
    scope = 1
    category = "FUEL"

    COLUMN_MAP = {
        "MATNR": "matnr", "Material Number": "matnr",
        "MAKTX": "maktx", "Material Description": "maktx",
        "Material Description (F)": "maktx",
        "MTART": "mtart", "Material Type": "mtart",
        "MENGE": "menge", "Quantity": "menge",
        "MEINS": "meins", "Base Unit": "meins", "Unit": "meins",
        "WERKS": "werks", "Plant": "werks", "Plant Code": "werks",
        "BSTYP": "bstyp", "Document Type": "bstyp",
        "BUDAT": "budat", "Posting Date": "budat",
        "BLDAT": "bldat", "Document Date": "bldat",
        "DMBTR": "dmbtr", "Amount": "dmbtr", "Amount (LC)": "dmbtr",
        "WAERS": "waers", "Currency": "waers",
        "KOSTL": "kostl", "Cost Center": "kostl",
    }

    SCOPE_MAP = {"ROH": 1, "HAWA": 3, "FERT": 1, "DIEN": 3, "ZFG": 1}

    def _map_row(self, row):
        mapped = {}
        for k, v in row.items():
            key = k.strip()
            if key in self.COLUMN_MAP:
                mapped[self.COLUMN_MAP[key]] = self.safe_strip(v)
            elif key.upper() in self.COLUMN_MAP:
                mapped[self.COLUMN_MAP[key.upper()]] = self.safe_strip(v)
        return mapped

    def parse(self):
        reader = self.get_reader()
        for row_num, row in enumerate(reader, start=2):
            try:
                r = self._map_row(row)

                qty = self.parse_decimal(r.get("menge", "0")) or Decimal("0")
                unit = r.get("meins", "ST")
                mtant = r.get("mtart", "")
                doc_date = self.parse_date(r.get("bldat", ""))
                posting_date = self.parse_date(r.get("budat", "")) or doc_date
                if doc_date is None:
                    doc_date = date.today()

                scope = self.SCOPE_MAP.get(mtant, 1)

                canonical_qty = qty
                canonical_unit = unit
                u = unit.upper()
                if u in ("L", "LTR"):
                    canonical_unit = "L"
                elif u in ("KG", "KGM"):
                    canonical_unit = "kg"
                elif u in ("ST", "PC", "EA", ""):
                    canonical_unit = "units"

                self.parsed_rows.append({
                    "material_number": r.get("matnr", ""),
                    "material_description": r.get("maktx", ""),
                    "material_type": mtant,
                    "quantity": qty,
                    "unit": unit,
                    "plant_code": r.get("werks", ""),
                    "document_type": r.get("bstyp", ""),
                    "document_date": doc_date,
                    "posting_date": posting_date,
                    "amount": self.parse_decimal(r.get("dmbtr", "")),
                    "currency": r.get("waers", "EUR") or "EUR",
                    "cost_center": r.get("kostl", ""),
                    "scope": scope,
                    "category": "FUEL",
                    "canonical_quantity": canonical_qty,
                    "canonical_unit": canonical_unit,
                    "raw_description": f"{r.get('matnr', '')} - {r.get('maktx', '')}" if r.get('maktx') else r.get('matnr', ''),
                    "raw_date_from": doc_date,
                })
            except Exception as e:
                self.errors.append({"row": row_num, "error": str(e)})
        return self.parsed_rows, self.errors
