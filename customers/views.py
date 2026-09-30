from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Branch
from core.utils import (Sheet, branch_filter, branch_required, excel_response, paginate,
                        scope_by_branch, wants_excel)
from loans.models import Loan, Repayment

from .forms import CustomerForm
from .models import Customer


@login_required
def customer_list(request):
    qs = branch_filter(request, Customer.objects.select_related("branch"))
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(middle_name__icontains=q)
            | Q(last_name__icontains=q) | Q(phone__icontains=q)
        )
    gender = request.GET.get("jinsia")
    if gender in ("F", "M"):
        qs = qs.filter(gender=gender)
    qs = qs.annotate(
        loans_count=Count("loans"),
        active_count=Count("loans", filter=Q(loans__status=Loan.Status.ACTIVE)),
        active_loan_id=Max("loans__id", filter=Q(loans__status=Loan.Status.ACTIVE)),
    ).order_by("-created_at")
    if wants_excel(request):
        from django.utils import timezone
        return excel_response(f"wateja_{timezone.localdate()}.xlsx", Sheet(
            "Wateja",
            ["Jina", "Simu", "Jinsia", "NIDA", "Makazi", "Kazi", "Tawi", "Mdhamini", "Simu ya mdhamini",
             "Uhusiano", "Mikopo", "Anadaiwa sasa", "Alisajiliwa"],
            [[c.full_name, c.phone, c.get_gender_display(), c.national_id, c.address, c.occupation, c.branch.name,
              c.guarantor_name, c.guarantor_phone, c.guarantor_relation, c.loans_count,
              "Ndiyo" if c.active_count else "Hapana", timezone.localtime(c.created_at).date()] for c in qs],
            title="Orodha ya wateja",
        ))
    return render(request, "customers/list.html", {
        "page": paginate(request, qs),
        "q": q,
        "branches": Branch.objects.all() if request.user.is_admin else None,
    })


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(scope_by_branch(Customer.objects.select_related("branch"), request.user), pk=pk)
    loans = customer.loans.with_totals().select_related("product")
    open_loan = loans.filter(status__in=Loan.OPEN_STATUSES).first()
    repayments = (Repayment.objects.filter(loan__customer=customer)
                  .select_related("loan", "received_by").order_by("-paid_at")[:50])
    return render(request, "customers/detail.html", {
        "customer": customer, "loans": loans, "open_loan": open_loan, "repayments": repayments,
        "methods": Repayment.Method.choices,
    })


@branch_required
def customer_form(request, pk=None):
    instance = None
    if pk:
        instance = get_object_or_404(scope_by_branch(Customer.objects, request.user), pk=pk)
    form = CustomerForm(request.POST or None, instance=instance, user=request.user)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        if not request.user.is_admin:
            customer.branch = request.user.branch
        if not instance:
            customer.registered_by = request.user
        customer.save()
        messages.success(request, f"Mteja {customer} amehifadhiwa.")
        return redirect("customer_detail", pk=customer.pk)
    return render(request, "form.html", {
        "form": form,
        "title": f"Hariri {instance}" if instance else "Sajili mteja mpya",
        "back": reverse("customer_detail", args=[pk]) if pk else reverse("customer_list"),
        "submit": "Hifadhi mteja",
        "sections": {"first_name": "Taarifa binafsi", "address": "Makazi na kazi",
                     "guarantor_name": "Mdhamini", "is_active": "Hali"},
    })
