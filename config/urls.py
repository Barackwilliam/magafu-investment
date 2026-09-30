from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# Admin ya pili (kwa mteja) kwenye /mfumo-ndani/, yenye kila kitu kama /admin/
client_admin = admin.AdminSite(name="mfumo_ndani")
for _model, _model_admin in admin.site._registry.items():
    client_admin.register(_model, type(_model_admin))

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("mfumo-ndani/", client_admin.urls),
    path("", include("core.urls")),
    path("akaunti/", include("accounts.urls")),
    path("wateja/", include("customers.urls")),
    path("mikopo/", include("loans.urls")),
    path("fedha/", include("finance.urls")),
    path("ripoti/", include("reports.urls")),
    path("sms/", include("sms.urls")),
]

admin.site.site_header = f"{settings.COMPANY_NAME} (developer)"
