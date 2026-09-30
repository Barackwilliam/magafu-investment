from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
    path("akaunti/", include("accounts.urls")),
    path("wateja/", include("customers.urls")),
    path("mikopo/", include("loans.urls")),
    path("fedha/", include("finance.urls")),
    path("ripoti/", include("reports.urls")),
    path("sms/", include("sms.urls")),
]

admin.site.site_header = f"{settings.COMPANY_NAME} (developer)"
