from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from core.models import Branch
from core.utils import Sheet, admin_required, branch_filter, date_range, excel_response, total, wants_excel
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

    if wants_excel(request):
        labels = dict(CashEntry.EntryType.choices)
        summary = [["Marejesho ya mikopo", collected]] + [[labels[t], by_type[t]] for t in CashEntry.INFLOWS] + [
            ["Mikopo iliyotolewa", -disbursed_sum], [labels["EXPENSE"], -by_type["EXPENSE"]],
            [labels["TO_BANK"], -by_type["TO_BANK"]]]
        return excel_response(f"ripoti_ya_siku_{day}.xlsx", [
            Sheet("Muhtasari", ["Kipengele", "Kiasi"], summary, totals=["Salio la mkononi", net],
                  title="Muhtasari wa fedha za siku"),
            Sheet("Marejesho", ["Muda", "Mkopo", "Mteja", "Njia", "Namba ya muamala", "Amepokea", "Kiasi"],
                  [[r.paid_at, r.loan.number, r.loan.customer.full_name, r.get_method_display(), r.reference,
                    str(r.received_by or ""), r.amount] for r in payments],
                  totals=["Jumla", "", "", "", "", "", collected], title="Marejesho"),
            Sheet("Mikopo iliyotolewa", ["Mkopo", "Mteja", "Kiasi", "Jumla ya kulipa", "Kumaliza"],
                  [[l.number, l.customer.full_name, l.principal, l.total_payable, l.due_date] for l in disbursed],
                  totals=["Jumla", "", disbursed_sum], title="Mikopo iliyotolewa"),
            Sheet("Miamala mingine", ["Aina", "Maelezo", "Mteja", "Kiasi"],
                  [[e.get_entry_type_display(), e.description, str(e.customer or ""),
                    e.amount if e.is_inflow else -e.amount] for e in entries], title="Miamala mingine"),
        ], subtitle=f"Tarehe {day:%d/%m/%Y}")
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
    if wants_excel(request):
        return excel_response(f"makusanyo_{start}_{end}.xlsx", Sheet(
            "Makusanyo",
            ["Tarehe", "Mkopo", "Mteja", "Simu", "Kiasi", "Njia", "Namba ya muamala", "Tawi", "Amepokea"],
            [[r.paid_at, r.loan.number, r.loan.customer.full_name, r.loan.customer.phone, r.amount,
              r.get_method_display(), r.reference, r.loan.branch.name, str(r.received_by or "")] for r in qs],
            totals=["Jumla", "", "", "", total(qs)], title="Makusanyo (marejesho ya mikopo)",
        ), subtitle=f"Kuanzia {start:%d/%m/%Y} mpaka {end:%d/%m/%Y}")
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
    agg = qs.aggregate(p=Sum("principal"), i=Sum("interest_amount"), t=Sum("total_payable"))
    if wants_excel(request):
        return excel_response(f"mikopo_iliyotolewa_{start}_{end}.xlsx", Sheet(
            "Mikopo iliyotolewa",
            ["Tarehe", "Namba", "Mteja", "Simu", "Mkopo", "Riba", "Jumla ya kulipa", "Amelipa", "Deni", "Kumaliza", "Hali", "Tawi"],
            [[timezone.localtime(l.disbursed_at).date(), l.number, l.customer.full_name, l.customer.phone,
              l.principal, l.interest_amount, l.total_payable, l.paid_total, l.balance_total, l.due_date,
              l.display_status_label, l.branch.name] for l in qs],
            totals=["Jumla", "", "", "", agg["p"] or 0, agg["i"] or 0, agg["t"] or 0], title="Mikopo iliyotolewa",
        ), subtitle=f"Kuanzia {start:%d/%m/%Y} mpaka {end:%d/%m/%Y}")
    return render(request, "reports/disbursements.html", {
        "rows": qs[:500], "count": qs.count(), "agg": agg,
        "start": start, "end": end, "branches": _branches(request),
    })


@login_required
def overdue_report(request):
    qs = (branch_filter(request, Loan.objects.overdue().with_totals().select_related("customer", "branch"))
          .order_by("due_date"))
    if wants_excel(request):
        return excel_response(f"madeni_sugu_{timezone.localdate()}.xlsx", Sheet(
            "Madeni sugu",
            ["Namba", "Mteja", "Simu", "Mdhamini", "Simu ya mdhamini", "Mkopo", "Amelipa", "Deni",
             "Tarehe ya kumaliza", "Siku za kuchelewa", "Tawi"],
            [[l.number, l.customer.full_name, l.customer.phone, l.customer.guarantor_name,
              l.customer.guarantor_phone, l.principal, l.paid_total, l.balance_total,
              l.due_date, l.days_overdue, l.branch.name] for l in qs],
            totals=["Jumla", "", "", "", "", "", "", qs.aggregate(t=Sum("balance_total"))["t"] or 0],
            title="Madeni sugu (nje ya mkataba)",
        ))
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
    keys = ["women", "men", "all", "active", "completed", "disbursed", "collected", "outstanding", "overdue"]
    if wants_excel(request):
        return excel_response(f"ripoti_ya_matawi_{start}_{end}.xlsx", Sheet(
            "Matawi",
            ["Tawi", "Wanawake", "Wanaume", "Wateja", "Wanadaiwa", "Wamemaliza", "Imetolewa", "Makusanyo",
             "Madeni", "Madeni sugu"],
            [[r["branch"].name] + [r[k] for k in keys] for r in rows],
            totals=["Jumla"] + [totals[k] for k in keys], title="Ripoti ya matawi",
        ), subtitle=f"Kuanzia {start:%d/%m/%Y} mpaka {end:%d/%m/%Y}")
    return render(request, "reports/branches.html", {"rows": rows, "totals": totals, "start": start, "end": end})
