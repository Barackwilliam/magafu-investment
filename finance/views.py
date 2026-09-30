from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Branch
from core.utils import (Sheet, branch_filter, branch_required, date_range, excel_response, manager_required,
                        paginate, scope_by_branch, total, wants_excel)

from .forms import CashEntryForm
from .models import CashEntry


@login_required
def cash_list(request):
    start, end = date_range(request)
    qs = branch_filter(request, CashEntry.objects.select_related("branch", "customer", "recorded_by"))
    qs = qs.filter(date__range=(start, end))
    aina = request.GET.get("aina", "")
    if aina in CashEntry.EntryType.values:
        qs = qs.filter(entry_type=aina)
    inflow = total(qs.filter(entry_type__in=CashEntry.INFLOWS))
    outflow = total(qs.filter(entry_type__in=CashEntry.OUTFLOWS))
    if wants_excel(request):
        return excel_response(f"daftari_la_fedha_{start}_{end}.xlsx", Sheet(
            "Daftari la fedha",
            ["Tarehe", "Aina", "Maelezo", "Mteja", "Tawi", "Amerekodi", "Zilizoingia", "Zilizotoka"],
            [[e.date, e.get_entry_type_display(), e.description, str(e.customer or ""), e.branch.name,
              str(e.recorded_by or ""), e.amount if e.is_inflow else None, None if e.is_inflow else e.amount]
             for e in qs],
            totals=["Jumla", "", "", "", "", "", inflow, outflow], title="Daftari la fedha",
        ), subtitle=f"Kuanzia {start:%d/%m/%Y} mpaka {end:%d/%m/%Y}")
    return render(request, "finance/cash_list.html", {
        "page": paginate(request, qs),
        "start": start, "end": end, "aina": aina,
        "types": CashEntry.EntryType.choices,
        "inflow": inflow, "outflow": outflow, "net": inflow - outflow,
        "branches": Branch.objects.all() if request.user.is_admin else None,
    })


@branch_required
def cash_create(request):
    initial = {}
    if request.GET.get("aina") in CashEntry.EntryType.values:
        initial["entry_type"] = request.GET["aina"]
    form = CashEntryForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        if not request.user.is_admin:
            entry.branch = request.user.branch
        entry.recorded_by = request.user
        entry.save()
        messages.success(request, f"{entry.get_entry_type_display()} ya TSh {entry.amount:,.0f} imehifadhiwa.")
        return redirect("cash_list")
    return render(request, "form.html", {
        "form": form, "title": "Rekodi muamala wa fedha", "back": reverse("cash_list"),
    })


@manager_required
def cash_delete(request, pk):
    entry = get_object_or_404(scope_by_branch(CashEntry.objects, request.user), pk=pk)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Muamala umefutwa.")
    return redirect("cash_list")
