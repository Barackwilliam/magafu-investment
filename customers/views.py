from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Branch
from core.utils import branch_filter, paginate, scope_by_branch
from loans.models import Loan

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
    ).order_by("-created_at")
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
    return render(request, "customers/detail.html", {
        "customer": customer, "loans": loans, "open_loan": open_loan,
    })


@login_required
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
    })
