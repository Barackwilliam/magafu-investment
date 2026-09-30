"""
Takwimu za dashboard (kama cards za mfumo wa zamani: jumla, leo, mwezi huu, mwaka huu).
Kila card inahesabiwa kwa aggregate moja yenye filters, si query nyingi.
"""
from decimal import Decimal

from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from customers.models import Customer
from finance.models import CashEntry
from loans.models import Loan, Penalty, Repayment
from sms.models import SmsLog

from .models import Branch
from .utils import scope_by_branch

ZERO = Decimal(0)


def _periods(field, today):
    """Filters za leo / mwezi huu / mwaka huu kwa field ya tarehe au datetime."""
    date_field = field if field == "date" else f"{field}__date"
    return {
        "leo": Q(**{date_field: today}),
        "mwezi": Q(**{f"{date_field}__gte": today.replace(day=1)}),
        "mwaka": Q(**{f"{date_field}__gte": today.replace(month=1, day=1)}),
    }


def _sum_by_period(qs, field, value, today, prefix=""):
    p = _periods(field, today)
    agg = qs.aggregate(
        jumla=Sum(value),
        **{f"{prefix}{k}": Sum(value, filter=q) for k, q in p.items()},
    )
    return {k: v or ZERO for k, v in agg.items()}


def _count_by_period(qs, field, today):
    p = _periods(field, today)
    return qs.aggregate(jumla=Count("id"), **{k: Count("id", filter=q) for k, q in p.items()})


def expected_today(active_loans, today):
    """Makadirio ya makusanyo ya leo kwa ratiba ya kila mkopo unaodaiwa."""
    total = ZERO
    for loan in active_loans:
        if not loan.disbursed_at or loan.balance_total <= 0:
            continue
        elapsed = (today - timezone.localtime(loan.disbursed_at).date()).days
        if elapsed <= 0:
            continue
        freq, inst = loan.repayment_frequency, loan.installment_amount
        if freq == "DAILY":
            due = inst
        elif freq == "WEEKLY":
            due = inst if elapsed % 7 == 0 else ZERO
        elif freq == "MONTHLY":
            due = inst if elapsed % 30 == 0 else ZERO
        else:
            due = loan.balance_total if loan.due_date == today else ZERO
        total += min(due, loan.balance_total)
    return total


def dashboard_cards(user):
    today = timezone.localdate()
    loans = scope_by_branch(Loan.objects.all(), user)
    reps = scope_by_branch(Repayment.objects.all(), user, "loan__branch")
    cash = scope_by_branch(CashEntry.objects.all(), user)
    customers = scope_by_branch(Customer.objects.all(), user)
    penalties = scope_by_branch(Penalty.objects.all(), user, "loan__branch")
    sms = scope_by_branch(SmsLog.objects.all(), user, "customer__branch")

    # Maombi ya mikopo
    maombi = _count_by_period(loans, "applied_at", today)
    maombi.update(loans.aggregate(
        yanasubiri=Count("id", filter=Q(status=Loan.Status.PENDING)),
        yamekataliwa=Count("id", filter=Q(status=Loan.Status.REJECTED)),
        yamekubaliwa=Count("id", filter=Q(status__in=[Loan.Status.APPROVED, Loan.Status.ACTIVE,
                                                        Loan.Status.COMPLETED, Loan.Status.WRITTEN_OFF])),
    ))

    # Wateja
    has_active = Loan.objects.filter(customer=OuterRef("pk"), status=Loan.Status.ACTIVE)
    has_done = Loan.objects.filter(customer=OuterRef("pk"), status=Loan.Status.COMPLETED)
    wateja = _count_by_period(customers, "created_at", today)
    cust = customers.annotate(a=Exists(has_active), d=Exists(has_done))
    wateja["wanadaiwa"] = cust.filter(a=True).count()
    wateja["waliomaliza"] = cust.filter(d=True, a=False).count()

    # Mikopo iliyotolewa
    disbursed = loans.exclude(disbursed_at=None)
    mikopo = _sum_by_period(disbursed, "disbursed_at", "principal", today)
    active = loans.active().with_totals()
    mikopo["wadaiwa"] = active.aggregate(t=Sum("balance_total"))["t"] or ZERO
    overdue = active.filter(due_date__lt=today)
    mikopo["sugu"] = overdue.aggregate(t=Sum("balance_total"))["t"] or ZERO
    mikopo["sugu_idadi"] = overdue.count()
    mikopo["hai_idadi"] = active.count()
    mikopo["waliomaliza"] = loans.filter(status=Loan.Status.COMPLETED).aggregate(t=Sum("total_payable"))["t"] or ZERO

    # Makusanyo
    makusanyo = _sum_by_period(reps, "paid_at", "amount", today)
    active_rows = active.only("id", "disbursed_at", "due_date", "repayment_frequency",
                              "duration_days", "total_payable", "status")
    makadirio = expected_today(active_rows, today)
    makusanyo["makadirio"] = makadirio
    makusanyo["hazijakusanywa"] = max(ZERO, makadirio - makusanyo["leo"])
    makusanyo["asilimia"] = round(makusanyo["leo"] / makadirio * 100) if makadirio else None

    # Mapato: ada za fomu, faini, kutembelea, mapato mengine
    income = cash.filter(entry_type__in=["FORM_FEE", "VISIT_FEE", "OTHER_INCOME"])
    by_type = income.aggregate(
        fomu=Sum("amount", filter=Q(entry_type="FORM_FEE")),
        fomu_leo=Sum("amount", filter=Q(entry_type="FORM_FEE", date=today)),
        tembelea=Sum("amount", filter=Q(entry_type="VISIT_FEE")),
        mengine=Sum("amount", filter=Q(entry_type="OTHER_INCOME")),
    )
    mapato = {k: v or ZERO for k, v in by_type.items()}
    mapato["faini"] = penalties.aggregate(t=Sum("amount"))["t"] or ZERO
    mapato["jumla"] = mapato["fomu"] + mapato["tembelea"] + mapato["mengine"] + mapato["faini"]

    benki = _sum_by_period(cash.filter(entry_type="TO_BANK"), "date", "amount", today)

    sms_stats = _count_by_period(sms, "created_at", today)
    sms_stats["zimeshindwa"] = sms.filter(status=SmsLog.Status.FAILED).count()

    branches = Branch.objects.all() if user.is_admin else Branch.objects.filter(pk=user.branch_id)
    matawi = branches.aggregate(
        jumla=Count("id", distinct=True),
        hai=Count("id", filter=Q(is_active=True), distinct=True),
        wafanyakazi=Count("staff", filter=Q(staff__is_active=True), distinct=True),
    )

    return {
        "maombi": maombi, "wateja": wateja, "mikopo": mikopo, "makusanyo": makusanyo,
        "mapato": mapato, "benki": benki, "sms": sms_stats, "matawi": matawi,
    }


def year_chart(user, year):
    """Kwa kila mwezi: wateja wapya, mikopo iliyotolewa, makusanyo, mauzo ya fomu."""
    def monthly(qs, field, value=None):
        rows = (qs.filter(**{f"{field}__year": year}).annotate(m=TruncMonth(field)).values("m")
                .annotate(t=Sum(value) if value else Count("id")))
        data = [0] * 12
        for r in rows:
            if r["m"]:
                data[r["m"].month - 1] = float(r["t"] or 0)
        return data

    loans = scope_by_branch(Loan.objects.all(), user)
    today = timezone.localdate()
    return {
        "year": year,
        "months_passed": 12 if year < today.year else (today.month if year == today.year else 0),
        "labels": ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ago", "Sep", "Okt", "Nov", "Des"],
        "wateja": monthly(scope_by_branch(Customer.objects.all(), user), "created_at"),
        "mikopo": monthly(loans, "disbursed_at", "principal"),
        "makusanyo": monthly(scope_by_branch(Repayment.objects.all(), user, "loan__branch"), "paid_at", "amount"),
        "fomu": monthly(scope_by_branch(CashEntry.objects.filter(entry_type="FORM_FEE"), user), "date", "amount"),
    }
