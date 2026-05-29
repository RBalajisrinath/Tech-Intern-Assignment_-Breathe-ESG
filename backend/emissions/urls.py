from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet)
router.register(r"uploads", SourceUploadViewSet)
router.register(r"records", EmissionRecordViewSet)
router.register(r"sap-records", SapFuelRecordViewSet)
router.register(r"utility-records", UtilityRecordViewSet)
router.register(r"travel-records", TravelRecordViewSet)
router.register(r"audit-logs", AuditLogViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
