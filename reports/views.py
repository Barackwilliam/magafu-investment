from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from core.models import Branch
from core.utils import admin_required, branch_filter, csv_response, date_range, total
from customers.models import Customer
from finance.models import CashEntry
from loans.models import Loan, Repayment


def _branches(request):
    return Branch.objects.all() if request.user.is_admin else None


@login_required
def daily_report(request):
    try:
        day = date.fromisoformat(request.GET.get("tarehe", ""))
    except ValueError:
        day = timezone.localdate()

    loans = branch_filter(request, Loan.objects.select_related("customer"))
    reps = branch_filter(request, Repayment.objects.select_related("loan__customer", "received_by"), "loan__branch")
    cash = branch_filter(request, CashEntry.objects.select_related("customer"))

    disbursed = loans.filter(disbursed_at__date=day)
    payments = reps.filter(paid_at__date=day)
    entries = cash.filter(date=day)

    by_type = {t: total(entries.filter(entry_type=t)) for t in CashEntry.EntryType.values}
    by_method = [
        (label, total(payments.filter(method=value)))
        for value, label in Repayment.Method.choices
    ]
    collected = total(payments)
    disbursed_sum = total(disbursed, "principal")
    inflow = sum(by_type[t] for t in CashEntry.INFLOWS)
    net = inflow + collected - disbursed_sum - by_type["EXPENSE"] - by_type["TO_BANK"]

    return render(request, "reports/daily.html", {
        "day": day, "disbursed": disbursed, "payments": payments, "entries": entries,
        "collected": collected, "disbursed_sum": disbursed_sum,
        "by_type": by_type, "by_method": [m for m in by_method if m[1]],
        "type_labels": dict(CashEntry.EntryType.choices),
        "net": net, "branches": _branches(request),
        "new_customers": branch_filter(request, Customer.objects.all()).filter(created_at__date=day).count(),
    })


@login_required
def collections_report(request):
    start, end = date_range(request)
    qs = branch_filter(request, Repayment.objects.select_related("loan__customer", "loan__branch", "received_by"),
                       "loan__branch").filter(paid_at__date__range=(start, end))
    method = request.GET.get("njia", "")
    if method in Repayment.Method.values:
        qs = qs.filter(method=method)
    if request.GET.get("export") == "csv":
        return csv_response(
            f"makusanyo_{start}_{end}.csv",
            ["Tarehe", "Mkopo", "Mteja", "Simu", "Kiasi", "Njia", "Namba ya muamala", "Tawi", "Amepokea"],
            [[timezone.localtime(r.paid_at).strftime("%Y-%m-%d %H:%M"), r.loan.number, r.loan.customer.full_name,
              r.loan.customer.phone, f"{r.amount:.0f}", r.get_method_display(), r.reference,
              r.loan.branch.name, str(r.received_by or "")] for r in qs],
        )
    return render(request, "reports/collections.html", {
        "rows": qs[:500], "count": qs.count(), "sum": total(qs),
        "start": start, "end": end, "method": method, "methods": Repayment.Method.choices,
        "branches": _branches(request),
    })


@login_required
def disbursements_report(request):
    start, end = date_range(request)
    qs = (branch_filter(request, Loan.objects.with_totals().select_related("customer", "branch", "disbursed_by"))
          .filter(disbursed_at__date__range=(start, end)).order_by("-disbursed_at"))
    if request.GET.get("export") == "csv":
        return csv_response(
            f"mikopo_iliyotolewa_{start}_{end}.csv",
            ["Tarehe", "Mkopo", "Mteja", "Simu", "Mkopo", "Riba", "Jumla", "Amelipa", "Deni", "Hali", "Tawi"],
            [[timezone.localtime(l.disbursed_at).strftime("%Y-%m-%d"), l.number, l.customer.full_name,
              l.customer.phone, f"{l.principal:.0f}", f"{l.interest_amount:.0f}", f"{l.total_payable:.0f}",
              f"{l.paid_total:.0f}", f"{l.balance_total:.0f}", l.display_status_label, l.branch.name] for l in qs],
        )
    agg = qs.aggregate(p=Sum("principal"), i=Sum("interest_amount"), t=Sum("total_payable"))
    return render(request, "reports/disbursements.html", {
        "rows": qs[:500], "count": qs.count(), "agg": agg,
        "start": start, "end": end, "branches": _branches(request),
    })


@login_required
def overdue_report(request):
    qs = (branch_filter(request, Loan.objects.overdue().with_totals().select_related("customer", "branch"))
          .order_by("due_date"))
    if request.GET.get("export") == "csv":
        return csv_response(
            "madeni_sugu.csv",
            ["Mkopo", "Mteja", "Simu", "Mdhamini", "Simu ya mdhamini", "Mkopo", "Amelipa", "Deni",
             "Tarehe ya kumaliza", "Siku za kuchelewa", "Tawi"],
            [[l.number, l.customer.full_name, l.customer.phone, l.customer.guarantor_name,
              l.customer.guarantor_phone, f"{l.principal:.0f}", f"{l.paid_total:.0f}", f"{l.balance_total:.0f}",
              l.due_date.isoformat(), l.days_overdue, l.branch.name] for l in qs],
        )
    return render(request, "reports/overdue.html", {
        "rows": qs, "sum": qs.aggregate(t=Sum("balance_total"))["t"] or 0,
        "branches": _branches(request),
    })


@admin_required
def branches_report(request):
    start, end = date_range(request)
    rows = []
    for b in Branch.objects.all():
        cust = Customer.objects.filter(branch=b).aggregate(
            women=Count("id", filter=Q(gender="F")), men=Count("id", filter=Q(gender="M")), all=Count("id"))
        loans = Loan.objects.filter(branch=b)
        active = loans.active().with_totals()
        rows.append({
            "branch": b, **cust,
            "active": active.count(),
            "completed": loans.filter(status=Loan.Status.COMPLETED).count(),
            "outstanding": active.aggregate(t=Sum("balance_total"))["t"] or 0,
            "overdue": active.filter(due_date__lt=timezone.localdate()).aggregate(t=Sum("balance_total"))["t"] or 0,
            "disbursed": total(loans.filter(disbursed_at__date__range=(start, end)), "principal"),
            "collected": total(Repayment.objects.filter(loan__branch=b, paid_at__date__range=(start, end))),
        })
    totals = {k: sum(r[k] for r in rows) for k in
              ["women", "men", "all", "active", "completed", "outstanding", "overdue", "disbursed", "collected"]}
    return render(request, "reports/branches.html", {"rows": rows, "totals": totals, "start": start, "end": end})
