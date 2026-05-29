from django.contrib import admin
from .models import *

admin.site.register(Organization)
admin.site.register(SourceUpload)
admin.site.register(EmissionFactor)
admin.site.register(EmissionRecord)
admin.site.register(SapFuelRecord)
admin.site.register(UtilityRecord)
admin.site.register(TravelRecord)
admin.site.register(AuditLog)
