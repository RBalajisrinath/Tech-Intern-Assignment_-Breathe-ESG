from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmissionFactor(models.Model):
    CATEGORY_CHOICES = [
        ("FUEL", "Fuel (Scope 1)"),
        ("ELECTRICITY", "Electricity (Scope 2)"),
        ("FLIGHT", "Flight (Scope 3)"),
        ("HOTEL", "Hotel (Scope 3)"),
        ("CAR_RENTAL", "Car Rental (Scope 3)"),
        ("MILEAGE", "Mileage (Scope 3)"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20)
    factor_kg_co2e_per_unit = models.DecimalField(max_digits=14, decimal_places=6)
    source = models.CharField(max_length=100, blank=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["category", "subcategory"]

    def __str__(self):
        return f"{self.get_category_display()} / {self.subcategory}: {self.factor_kg_co2e_per_unit} kgCO2e/{self.unit}"


class SourceUpload(models.Model):
    SOURCE_CHOICES = [
        ("SAP", "SAP - Fuel & Procurement"),
        ("UTILITY", "Utility - Electricity"),
        ("TRAVEL", "Corporate Travel"),
    ]
    STATUS_CHOICES = [
        ("UPLOADED", "Uploaded"),
        ("PARSING", "Parsing"),
        ("PARSED", "Parsed"),
        ("FAILED", "Failed"),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="uploads")
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    upload_type = models.CharField(
        max_length=20,
        choices=[("FILE_UPLOAD", "File Upload"), ("API_PULL", "API Pull"), ("MANUAL", "Manual")],
        default="FILE_UPLOAD",
    )
    filename = models.CharField(max_length=500, blank=True)
    raw_file = models.FileField(upload_to="uploads/", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="UPLOADED")
    row_count = models.IntegerField(default=0)
    parsed_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)
    uploaded_by = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.filename} - {self.status}"


class EmissionRecord(models.Model):
    SCOPE_CHOICES = [
        (1, "Scope 1 - Direct"),
        (2, "Scope 2 - Indirect (Electricity)"),
        (3, "Scope 3 - Value Chain"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("REVIEWED", "Reviewed"),
        ("APPROVED", "Approved"),
        ("FLAGGED", "Flagged"),
        ("LOCKED", "Locked for Audit"),
    ]
    CATEGORY_CHOICES = [
        ("FUEL", "Fuel"),
        ("ELECTRICITY", "Electricity"),
        ("FLIGHT", "Flight"),
        ("HOTEL", "Hotel"),
        ("CAR_RENTAL", "Car Rental"),
        ("MILEAGE", "Mileage"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="records")
    source_upload = models.ForeignKey(
        SourceUpload, on_delete=models.SET_NULL, null=True, related_name="records"
    )
    source_type = models.CharField(max_length=10, choices=SourceUpload.SOURCE_CHOICES)
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    raw_description = models.TextField(blank=True)
    raw_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    raw_unit = models.CharField(max_length=20)
    raw_date_from = models.DateField()
    raw_date_to = models.DateField(null=True, blank=True)

    canonical_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    canonical_unit = models.CharField(max_length=20)
    co2e_kg = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)

    source_record_id = models.CharField(max_length=255, blank=True)

    is_edited = models.BooleanField(default=False)
    edited_by = models.CharField(max_length=255, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    edit_reason = models.TextField(blank=True)

    flagged_by = models.CharField(max_length=255, blank=True)
    flagged_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.TextField(blank=True)

    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    locked_by = models.CharField(max_length=255, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "source_type"]),
            models.Index(fields=["organization", "scope"]),
        ]

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.raw_description} - {self.status}"


class SapFuelRecord(models.Model):
    upload = models.ForeignKey(SourceUpload, on_delete=models.CASCADE, related_name="sap_records")
    material_number = models.CharField(max_length=50)
    material_description = models.TextField(blank=True)
    material_type = models.CharField(max_length=10, blank=True)
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=10)
    plant_code = models.CharField(max_length=20, blank=True)
    document_type = models.CharField(max_length=10, blank=True)
    document_date = models.DateField()
    posting_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    cost_center = models.CharField(max_length=20, blank=True)
    emission_record = models.OneToOneField(
        EmissionRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="sap_detail"
    )

    def __str__(self):
        return f"{self.material_number} - {self.material_description[:50]}"


class UtilityRecord(models.Model):
    upload = models.ForeignKey(SourceUpload, on_delete=models.CASCADE, related_name="utility_records")
    meter_id = models.CharField(max_length=50)
    utility_name = models.CharField(max_length=100, blank=True)
    billing_start = models.DateField()
    billing_end = models.DateField()
    consumption_kwh = models.DecimalField(max_digits=16, decimal_places=4)
    peak_demand_kw = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    tariff_code = models.CharField(max_length=50, blank=True)
    meter_start_read = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    meter_end_read = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    read_type = models.CharField(
        max_length=10, choices=[("ACTUAL", "Actual"), ("ESTIMATED", "Estimated")], default="ACTUAL"
    )
    charge_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    emission_record = models.OneToOneField(
        EmissionRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="utility_detail"
    )

    def __str__(self):
        return f"Meter {self.meter_id}: {self.billing_start} - {self.billing_end}"


class TravelRecord(models.Model):
    EXPENSE_CHOICES = [
        ("FLIGHT", "Flight"),
        ("HOTEL", "Hotel"),
        ("CAR_RENTAL", "Car Rental"),
        ("MILEAGE", "Mileage"),
        ("OTHER", "Other"),
    ]
    CLASS_CHOICES = [
        ("ECONOMY", "Economy"),
        ("BUSINESS", "Business"),
        ("FIRST", "First"),
    ]
    upload = models.ForeignKey(SourceUpload, on_delete=models.CASCADE, related_name="travel_records")
    expense_type = models.CharField(max_length=20, choices=EXPENSE_CHOICES)
    vendor = models.CharField(max_length=200, blank=True)
    trip_purpose = models.TextField(blank=True)
    departure_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    origin_code = models.CharField(max_length=10, blank=True)
    destination_code = models.CharField(max_length=10, blank=True)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    class_of_service = models.CharField(
        max_length=10, choices=CLASS_CHOICES, default="ECONOMY"
    )
    hotel_nights = models.IntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    employee_id = models.CharField(max_length=50, blank=True)
    employee_name = models.CharField(max_length=200, blank=True)
    emission_record = models.OneToOneField(
        EmissionRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="travel_detail"
    )

    def __str__(self):
        return f"{self.get_expense_type_display()} - {self.vendor}: {self.departure_date}"


class AuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_logs")
    record_type = models.CharField(max_length=50)
    record_id = models.IntegerField()
    action = models.CharField(max_length=20)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    performed_by = models.CharField(max_length=255, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.action} on {self.record_type}#{self.record_id} by {self.performed_by}"
