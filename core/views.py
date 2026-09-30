from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from finance.models import CashEntry
from loans.models import Loan, Repayment

from .forms import BranchForm
from .models import Branch
from .stats import dashboard_cards, year_chart
from .utils import admin_required, scope_by_branch, total

@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    loans = scope_by_branch(Loan.objects.all(), user)
    reps = scope_by_branch(Repayment.objects.all(), user, "loan__branch")
    cash = scope_by_branch(CashEntry.objects.all(), user)

    collected_today = total(reps.filter(paid_at__date=today))
    disbursed_today = total(loans.filter(disbursed_at__date=today), "principal")
    today_cash = cash.filter(date=today)
    inflow_today = total(today_cash.filter(entry_type__in=CashEntry.INFLOWS))
    expenses_today = total(today_cash.filter(entry_type=CashEntry.EntryType.EXPENSE))
    bank_today = total(today_cash.filter(entry_type=CashEntry.EntryType.TO_BANK))

    try:
        year = int(request.GET.get("mwaka", today.year))
    except ValueError:
        year = today.year
    chart = year_chart(user, year)
    chart_rows = [
        ("Wateja wapya", chart["wateja"], False),
        ("Mikopo iliyotolewa", chart["mikopo"], True),
        ("Makusanyo", chart["makusanyo"], True),
        ("Mauzo ya fomu", chart["fomu"], True),
    ]

    return render(request, "core/dashboard.html", {
        "today": today,
        "collected_today": collected_today,
        "disbursed_today": disbursed_today,
        "inflow_today": inflow_today,
        "expenses_today": expenses_today,
        "bank_today": bank_today,
        "net_today": collected_today + inflow_today - disbursed_today - expenses_today - bank_today,
        "c": dashboard_cards(user),
        "chart": chart,
        "chart_rows": [(label, data, sum(data), is_money) for label, data, is_money in chart_rows],
        "years": range(today.year, today.year - 4, -1),
        "due_soon": loans.active().with_totals().filter(due_date__range=(today, today + timedelta(days=7)))
                         .select_related("customer").order_by("due_date")[:8],
        "recent_payments": reps.select_related("loan__customer").order_by("-paid_at")[:8],
    })


@admin_required
def branch_list(request):
    branches = Branch.objects.select_related("created_by").annotate(
        customers_count=Count("customers", distinct=True),
        staff_count=Count("staff", distinct=True),
        loans_count=Count("loans", distinct=True),
    ).order_by("created_at")
    return render(request, "core/branch_list.html", {"branches": branches})


@admin_required
def branch_form(request, pk=None):
    instance = get_object_or_404(Branch, pk=pk) if pk else None
    form = BranchForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        branch = form.save(commit=False)
        if not instance:
            branch.created_by = request.user
        branch.save()
        messages.success(request, f"Tawi {branch} limehifadhiwa.")
        return redirect("branch_list")
    return render(request, "form.html", {
        "form": form, "back": reverse("branch_list"),
        "title": f"Hariri {instance}" if instance else "Ongeza tawi",
    })


@require_POST
@admin_required
def branch_toggle(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    branch.is_active = not branch.is_active
    branch.save(update_fields=["is_active"])
    state = "limewashwa" if branch.is_active else "limezimwa"
    messages.success(request, f"Tawi {branch} {state}.")
    return redirect("branch_list")


@require_POST
@admin_required
def branch_delete(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if branch.customers.exists() or branch.loans.exists() or branch.cash_entries.exists() or branch.staff.exists():
        messages.error(request, f"Tawi {branch} lina wateja, wafanyakazi au miamala, kwa hiyo haliwezi kufutwa. "
                                "Unaweza kulizima badala yake.")
    else:
        name = str(branch)
        branch.delete()
        messages.success(request, f"Tawi {name} limefutwa.")
    return redirect("branch_list")
