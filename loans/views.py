from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import Branch
from core.utils import (Sheet, admin_required, branch_filter, branch_required, excel_response,
                        manager_required, paginate, scope_by_branch, wants_excel)
from sms.services import send_reminder

from . import services
from .forms import (LoanApplicationForm, LoanProductForm, PenaltyForm, ReasonForm,
                    RepaymentForm)
from .models import Loan, LoanProduct

FILTERS = {
    "zote": ("Zote", None),
    "inasubiri": ("Zinasubiri", Q(status=Loan.Status.PENDING)),
    "imethibitishwa": ("Tayari kutolewa", Q(status=Loan.Status.APPROVED)),
    "hai": ("Zinadaiwa", Q(status=Loan.Status.ACTIVE)),
    "sugu": ("Nje ya mkataba", None),
    "zimeisha": ("Zimeisha", Q(status=Loan.Status.COMPLETED)),
    "zimekataliwa": ("Zimekataliwa/Zimefutwa",
                     Q(status__in=[Loan.Status.REJECTED, Loan.Status.WRITTEN_OFF])),
}


def _back(request, pk):
    """Rudi ukurasa uliotuma fomu (mf. ukurasa wa mteja), vinginevyo ukurasa wa mkopo."""
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("loan_detail", pk=pk)


def _loan_or_404(request, pk):
    qs = scope_by_branch(Loan.objects.with_totals().select_related("customer", "product", "branch"), request.user)
    return get_object_or_404(qs, pk=pk)


@login_required
def loan_list(request):
    services.apply_daily_penalties_once()
    qs = branch_filter(request, Loan.objects.with_totals().select_related("customer", "branch"))
    key = request.GET.get("hali", "hai")
    if key not in FILTERS:
        key = "hai"
    if key == "sugu":
        qs = qs.filter(status=Loan.Status.ACTIVE, due_date__lt=timezone.localdate()).order_by("due_date")
    elif FILTERS[key][1] is not None:
        qs = qs.filter(FILTERS[key][1])
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(customer__first_name__icontains=q) | Q(customer__last_name__icontains=q)
                       | Q(customer__phone__icontains=q))
    if wants_excel(request):
        return excel_response(f"mikopo_{key}_{timezone.localdate()}.xlsx", Sheet(
            FILTERS[key][0],
            ["Namba", "Mteja", "Simu", "Tawi", "Aina", "Mkopo", "Riba", "Jumla ya kulipa", "Faini", "Amelipa",
             "Deni", "Kutolewa", "Kumaliza", "Siku za kuchelewa", "Hali"],
            [[l.number, l.customer.full_name, l.customer.phone, l.branch.name, l.product.name, l.principal,
              l.interest_amount, l.total_payable, l.penalty_total, l.paid_total, l.balance_total,
              timezone.localtime(l.disbursed_at).date() if l.disbursed_at else None, l.due_date,
              l.days_overdue, l.display_status_label] for l in qs.select_related("product")],
            title=f"Mikopo: {FILTERS[key][0]}",
        ))
    return render(request, "loans/list.html", {
        "page": paginate(request, qs), "filters": {k: v[0] for k, v in FILTERS.items()},
        "current": key, "q": q,
        "branches": Branch.objects.all() if request.user.is_admin else None,
    })


@branch_required
def loan_apply(request):
    initial = {}
    if request.GET.get("mteja", "").isdigit():
        initial["customer"] = int(request.GET["mteja"])
    form = LoanApplicationForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            make = services.give_loan if settings.LOAN_ONE_STEP else services.create_loan
            loan = make(
                customer=d["customer"], product=d["product"], principal=d["principal"],
                user=request.user, notes=d["notes"], form_fee_paid=d["form_fee_paid"],
            )
        except services.LoanError as e:
            form.add_error(None, str(e))
        else:
            if settings.LOAN_ONE_STEP:
                messages.success(request, f"Mkopo {loan.number} umetolewa. Deni ni TSh {loan.total_payable:,.0f}, "
                                          f"kumaliza kabla ya {loan.due_date:%d/%m/%Y}. Rekodi malipo hapa akileta pesa.")
                return redirect(reverse("customer_detail", args=[loan.customer_id]) + "#lipa")
            messages.success(request, f"Ombi la mkopo {loan.number} limepokelewa. Linasubiri kuthibitishwa.")
            return redirect("loan_detail", pk=loan.pk)
    products = LoanProduct.objects.filter(is_active=True)
    return render(request, "loans/apply.html", {"form": form, "products": products})


@login_required
def loan_detail(request, pk):
    services.apply_daily_penalties_once()
    loan = _loan_or_404(request, pk)
    nav = {"PENDING": "inasubiri", "APPROVED": "imethibitishwa", "COMPLETED": "zimeisha",
           "ACTIVE": "sugu" if loan.is_overdue else "hai"}.get(loan.status, "zote")
    return render(request, "loans/detail.html", {
        "nav": "loans_" + nav,
        "loan": loan,
        "repayments": loan.repayments.select_related("received_by"),
        "penalties": loan.penalty_entries.all(),
        "sms_logs": loan.sms_logs.all()[:10],
        "pay_form": RepaymentForm(initial={"amount": min(loan.installment_amount, loan.balance)}),
        "penalty_form": PenaltyForm(initial={"amount": loan.product.penalty_per_day or None}),
        "reason_form": ReasonForm(),
    })


@require_POST
@manager_required
def loan_approve(request, pk):
    _loan_or_404(request, pk)
    try:
        services.approve_loan(pk, request.user)
        messages.success(request, "Mkopo umethibitishwa. Sasa unaweza kutolewa.")
    except services.LoanError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=pk)


@require_POST
@manager_required
def loan_reject(request, pk):
    _loan_or_404(request, pk)
    form = ReasonForm(request.POST)
    form.is_valid()
    try:
        services.reject_loan(pk, request.user, form.cleaned_data.get("reason", ""))
        messages.success(request, "Ombi la mkopo limekataliwa.")
    except services.LoanError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=pk)


@require_POST
@manager_required
def loan_disburse(request, pk):
    existing = _loan_or_404(request, pk)
    try:
        if settings.LOAN_ONE_STEP and existing.status == Loan.Status.PENDING:
            services.approve_loan(pk, request.user)
        loan = services.disburse_loan(pk, request.user)
        messages.success(request, f"Mkopo umetolewa. Mteja anatakiwa kumaliza kabla ya {loan.due_date:%d/%m/%Y}.")
    except services.LoanError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=pk)


@require_POST
@login_required
def loan_pay(request, pk):
    _loan_or_404(request, pk)
    form = RepaymentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Weka kiasi sahihi cha malipo.")
        return _back(request, pk)
    d = form.cleaned_data
    try:
        payment = services.record_payment(pk, amount=d["amount"], method=d["method"],
                                          reference=d["reference"], user=request.user)
        msg = f"Malipo ya TSh {payment.amount:,.0f} yamepokelewa."
        if payment.loan.status == Loan.Status.COMPLETED:
            msg += " Mteja amemaliza mkopo wote."
        messages.success(request, msg)
    except services.LoanError as e:
        messages.error(request, str(e))
    return _back(request, pk)


@require_POST
@manager_required
def loan_penalty(request, pk):
    _loan_or_404(request, pk)
    form = PenaltyForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Weka kiasi sahihi cha faini.")
        return redirect("loan_detail", pk=pk)
    try:
        services.add_penalty(pk, amount=form.cleaned_data["amount"],
                             reason=form.cleaned_data["reason"], user=request.user)
        messages.success(request, "Faini imewekwa.")
    except services.LoanError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=pk)


@require_POST
@admin_required
def loan_write_off(request, pk):
    _loan_or_404(request, pk)
    form = ReasonForm(request.POST)
    form.is_valid()
    try:
        services.write_off(pk, request.user, form.cleaned_data.get("reason", ""))
        messages.success(request, "Mkopo umefutwa kwenye madeni.")
    except services.LoanError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=pk)


@require_POST
@login_required
def loan_remind(request, pk):
    loan = _loan_or_404(request, pk)
    if loan.status != Loan.Status.ACTIVE:
        messages.error(request, "Kikumbusho kinatumwa kwa mkopo unaodaiwa tu.")
    else:
        log = send_reminder(loan, request.user)
        messages.success(request, f"Kikumbusho: {log.get_status_display()}.")
    return redirect("loan_detail", pk=pk)


@login_required
def loan_statement(request, pk):
    loan = _loan_or_404(request, pk)
    return render(request, "loans/statement.html", {
        "loan": loan,
        "repayments": loan.repayments.order_by("paid_at"),
        "penalties": loan.penalty_entries.order_by("date"),
        "now": timezone.localtime(),
    })


@admin_required
def product_list(request):
    return render(request, "loans/product_list.html", {"products": LoanProduct.objects.all()})


@admin_required
def product_form(request, pk=None):
    instance = get_object_or_404(LoanProduct, pk=pk) if pk else None
    form = LoanProductForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Aina ya mkopo imehifadhiwa. Mikopo ya zamani haiathiriki.")
        return redirect("product_list")
    return render(request, "form.html", {
        "form": form, "back": reverse("product_list"),
        "sections": {"name": "Masharti", "form_fee": "Ada na faini", "min_amount": "Kiwango cha mkopo"},
        "title": f"Hariri {instance.name}" if instance else "Ongeza aina ya mkopo",
    })
