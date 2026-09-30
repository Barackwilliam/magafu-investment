from django.conf import settings


def company(request):
    return {"COMPANY_NAME": settings.COMPANY_NAME, "COMPANY_PHONE": settings.COMPANY_PHONE}
