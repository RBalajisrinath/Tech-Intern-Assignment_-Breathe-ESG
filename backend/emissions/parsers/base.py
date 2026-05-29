import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime


class BaseParser:
    source_type = None
    scope = None
    category = None

    def __init__(self, file_content, source_upload):
        self.file_content = file_content
        self.source_upload = source_upload
        self.errors = []
        self.parsed_rows = []

    def safe_strip(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def parse_decimal(self, value):
        if value is None:
            return None
        cleaned = str(value).strip().replace(",", ".")
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def parse_date(self, value, formats=None):
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        if formats is None:
            formats = ["%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                pass
        return None

    def get_reader(self):
        content = self.file_content
        sample = content[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            return csv.DictReader(io.StringIO(content), delimiter=dialect.delimiter)
        except csv.Error:
            return csv.DictReader(io.StringIO(content))

    def parse(self):
        raise NotImplementedError
