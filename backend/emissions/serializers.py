from rest_framework import serializers
from .models import *


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class EmissionRecordListSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            "id", "organization", "source_type", "source_type_display",
            "scope", "scope_display", "category", "category_display",
            "subcategory", "status", "status_display",
            "raw_description", "raw_quantity", "raw_unit",
            "raw_date_from", "raw_date_to",
            "canonical_quantity", "canonical_unit", "co2e_kg",
            "is_edited", "flagged_by", "flag_reason",
            "approved_by", "notes",
            "created_at", "updated_at",
        ]


class EmissionRecordDetailSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    sap_detail = serializers.SerializerMethodField()
    utility_detail = serializers.SerializerMethodField()
    travel_detail = serializers.SerializerMethodField()
    audit_logs = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = "__all__"

    def get_sap_detail(self, obj):
        if hasattr(obj, "sap_detail") and obj.sap_detail:
            from .serializers import SapFuelRecordSerializer
            return SapFuelRecordSerializer(obj.sap_detail).data
        return None

    def get_utility_detail(self, obj):
        if hasattr(obj, "utility_detail") and obj.utility_detail:
            return UtilityRecordSerializer(obj.utility_detail).data
        return None

    def get_travel_detail(self, obj):
        if hasattr(obj, "travel_detail") and obj.travel_detail:
            return TravelRecordSerializer(obj.travel_detail).data
        return None

    def get_audit_logs(self, obj):
        logs = AuditLog.objects.filter(
            record_type="EmissionRecord", record_id=obj.id
        )[:20]
        return AuditLogSerializer(logs, many=True).data


class EmissionRecordActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "flag", "review", "lock", "unlock"])
    reason = serializers.CharField(required=False, allow_blank=True)
    performed_by = serializers.CharField(default="analyst")


class SapFuelRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SapFuelRecord
        fields = "__all__"


class UtilityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityRecord
        fields = "__all__"


class TravelRecordSerializer(serializers.ModelSerializer):
    expense_type_display = serializers.CharField(source="get_expense_type_display", read_only=True)
    class_of_service_display = serializers.CharField(source="get_class_of_service_display", read_only=True)

    class Meta:
        model = TravelRecord
        fields = "__all__"


class SourceUploadSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    records_approved = serializers.SerializerMethodField()
    records_flagged = serializers.SerializerMethodField()

    class Meta:
        model = SourceUpload
        fields = [
            "id", "organization", "source_type", "upload_type",
            "filename", "raw_file", "status",
            "row_count", "parsed_count", "error_count", "error_log",
            "uploaded_by", "uploaded_at",
            "records_count", "records_approved", "records_flagged",
        ]
        read_only_fields = ["status", "row_count", "parsed_count", "error_count", "error_log", "uploaded_at"]

    def get_records_count(self, obj):
        return obj.records.count()

    def get_records_approved(self, obj):
        return obj.records.filter(status="APPROVED").count()

    def get_records_flagged(self, obj):
        return obj.records.filter(status="FLAGGED").count()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"
