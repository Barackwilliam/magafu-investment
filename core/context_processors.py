from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone


def company(request):
    return {"COMPANY_NAME": settings.COMPANY_NAME, "COMPANY_PHONE": settings.COMPANY_PHONE,
            "ONE_STEP": settings.LOAN_ONE_STEP}


# url_name -> ufunguo wa menyu. Kwa kurasa zenye ?hali= au ?aina=, ufunguo unatoka kwenye query.
NAV_KEYS = {
    "dashboard": "home", "search": "search",
    "customer_list": "customers", "customer_detail": "customers", "customer_edit": "customers",
    "customer_create": "customer_new",
    "loan_apply": "loan_apply", "loan_detail": "loans_hai", "loan_statement": "loans_hai",
    "cash_list": "cash", "cash_create": "cash_new",
    "report_daily": "r_daily", "report_collections": "r_collections",
    "report_disbursements": "r_disbursements", "report_overdue": "r_overdue",
    "report_branches": "r_branches", "sms_log": "sms",
    "branch_list": "branches", "branch_create": "branches", "branch_edit": "branches",
    "user_list": "users", "user_create": "users", "user_edit": "users",
    "product_list": "products", "product_create": "products", "product_edit": "products",
    "password_change": "password",
}


def navigation(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    match = request.resolver_match
    name = match.url_name if match else ""
    key = NAV_KEYS.get(name, "")
    if name == "loan_list":
        key = "loans_" + request.GET.get("hali", "hai")
    elif name == "cash_create":
        aina = request.GET.get("aina", "")
        key = {"EXPENSE": "cash_expense", "CAPITAL_IN": "cash_capital", "TO_BANK": "cash_bank"}.get(aina, "cash_new")

    from core.utils import scope_by_branch
    from loans.models import Loan
    counts = scope_by_branch(Loan.objects.all(), user).aggregate(
        pending=Count("id", filter=Q(status=Loan.Status.PENDING)),
        approved=Count("id", filter=Q(status=Loan.Status.APPROVED)),
        overdue=Count("id", filter=Q(status=Loan.Status.ACTIVE, due_date__lt=timezone.localdate())),
    )
    initials = "".join(p[0] for p in (user.get_full_name() or user.username).split()[:2]).upper() or "M"
    return {"nav": key, "nav_counts": counts, "user_initials": initials}
