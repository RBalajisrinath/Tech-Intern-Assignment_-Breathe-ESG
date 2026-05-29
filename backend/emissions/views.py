from datetime import datetime

from django.db import transaction
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import *
from .serializers import *
from .parsers import SAPParser, UtilityParser, TravelParser


PARSER_MAP = {
    "SAP": SAPParser,
    "UTILITY": UtilityParser,
    "TRAVEL": TravelParser,
}


class EmissionRecordPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class SourceUploadViewSet(viewsets.ModelViewSet):
    queryset = SourceUpload.objects.all()
    serializer_class = SourceUploadSerializer

    @action(detail=False, methods=["post"], parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_file(self, request):
        source_type = request.data.get("source_type")
        org_id = request.data.get("organization")
        file = request.FILES.get("file")

        if not all([source_type, org_id, file]):
            return Response(
                {"error": "source_type, organization, and file are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        upload = SourceUpload.objects.create(
            organization=org,
            source_type=source_type,
            filename=file.name,
            raw_file=file,
            status="PARSING",
            uploaded_by=request.data.get("uploaded_by", "api"),
        )

        try:
            content = file.read().decode("utf-8-sig")
            parser_class = PARSER_MAP.get(source_type)
            if not parser_class:
                upload.status = "FAILED"
                upload.error_log = [{"error": f"Unknown source type: {source_type}"}]
                upload.save()
                return Response(
                    {"error": f"Unknown source type: {source_type}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            parser = parser_class(content, upload)
            parsed_rows, errors = parser.parse()

            upload.row_count = len(parsed_rows) + len(errors)
            upload.error_count = len(errors)
            upload.error_log = errors[:100]

            created_count = 0
            with transaction.atomic():
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
                        raw_date_from=row_data.get("raw_date_from", datetime.now().date()),
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
                            document_date=row_data.get("document_date", datetime.now().date()),
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
                            billing_start=row_data.get("billing_start", datetime.now().date()),
                            billing_end=row_data.get("billing_end", datetime.now().date()),
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
                            departure_date=row_data.get("departure_date", datetime.now().date()),
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

                    created_count += 1

            upload.parsed_count = created_count
            upload.status = "PARSED"
            upload.save()

            serializer = self.get_serializer(upload)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            upload.status = "FAILED"
            upload.error_log = upload.error_log + [{"error": str(e)}]
            upload.save()
            return Response(
                {"error": str(e), "upload_id": upload.id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = EmissionRecord.objects.select_related(
        "source_upload", "sap_detail", "utility_detail", "travel_detail"
    )
    serializer_class = EmissionRecordListSerializer
    pagination_class = EmissionRecordPagination
    filterset_fields = ["organization", "source_type", "scope", "category", "status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EmissionRecordDetailSerializer
        if self.action in ("approve", "flag", "review", "lock", "unlock"):
            return EmissionRecordActionSerializer
        return EmissionRecordListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        if params.get("organization"):
            qs = qs.filter(organization_id=params["organization"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("source_type"):
            qs = qs.filter(source_type=params["source_type"])
        if params.get("scope"):
            qs = qs.filter(scope=params["scope"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("search"):
            qs = qs.filter(raw_description__icontains=params["search"])

        return qs

    def _record_action(self, request, action_name, new_status):
        try:
            record = self.get_object()
        except Exception:
            return Response({"error": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EmissionRecordActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        performed_by = serializer.validated_data.get("performed_by", "analyst")
        reason = serializer.validated_data.get("reason", "")
        now = datetime.now()
        old_status = record.status

        if new_status == "FLAGGED":
            record.flagged_by = performed_by
            record.flagged_at = now
            record.flag_reason = reason
        elif new_status == "REVIEWED":
            record.reviewed_by = performed_by
            record.reviewed_at = now
        elif new_status == "APPROVED":
            record.approved_by = performed_by
            record.approved_at = now
        elif new_status == "LOCKED":
            record.locked_by = performed_by
            record.locked_at = now

        record.status = new_status
        record.save()

        AuditLog.objects.create(
            organization=record.organization,
            record_type="EmissionRecord",
            record_id=record.id,
            action=action_name.upper(),
            old_values={"status": old_status},
            new_values={"status": new_status, "reason": reason},
            performed_by=performed_by,
        )

        return Response(EmissionRecordDetailSerializer(record).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._record_action(request, "approve", "APPROVED")

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        return self._record_action(request, "flag", "FLAGGED")

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        return self._record_action(request, "review", "REVIEWED")

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        return self._record_action(request, "lock", "LOCKED")

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        record = self.get_object()
        record.status = "APPROVED"
        record.locked_by = ""
        record.locked_at = None
        record.save()
        return Response(EmissionRecordDetailSerializer(record).data)

    @action(detail=False, methods=["post"])
    def bulk_approve(self, request):
        ids = request.data.get("ids", [])
        performed_by = request.data.get("performed_by", "analyst")
        now = datetime.now()
        updated = EmissionRecord.objects.filter(id__in=ids, status__in=["PENDING", "REVIEWED", "FLAGGED"]).update(
            status="APPROVED", approved_by=performed_by, approved_at=now
        )
        return Response({"updated": updated})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = EmissionRecord.objects.all()
        if request.query_params.get("organization"):
            qs = qs.filter(organization_id=request.query_params["organization"])
        return Response({
            "total": qs.count(),
            "pending": qs.filter(status="PENDING").count(),
            "reviewed": qs.filter(status="REVIEWED").count(),
            "approved": qs.filter(status="APPROVED").count(),
            "flagged": qs.filter(status="FLAGGED").count(),
            "locked": qs.filter(status="LOCKED").count(),
            "scope_1": qs.filter(scope=1).count(),
            "scope_2": qs.filter(scope=2).count(),
            "scope_3": qs.filter(scope=3).count(),
        })


class SapFuelRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SapFuelRecord.objects.all()
    serializer_class = SapFuelRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("upload"):
            qs = qs.filter(upload_id=self.request.query_params["upload"])
        return qs


class UtilityRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UtilityRecord.objects.all()
    serializer_class = UtilityRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("upload"):
            qs = qs.filter(upload_id=self.request.query_params["upload"])
        return qs


class TravelRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TravelRecord.objects.all()
    serializer_class = TravelRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("upload"):
            qs = qs.filter(upload_id=self.request.query_params["upload"])
        return qs


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("organization"):
            qs = qs.filter(organization_id=p["organization"])
        if p.get("record_type"):
            qs = qs.filter(record_type=p["record_type"])
        if p.get("record_id"):
            qs = qs.filter(record_id=p["record_id"])
        return qs
