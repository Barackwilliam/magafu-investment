"""
Kila operesheni ya pesa inapita hapa, si moja kwa moja kwenye views.
Hii inazuia makosa kama malipo mawili kuingia kwa wakati mmoja.
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from finance.models import CashEntry
from sms.models import SmsLog
from sms.services import disbursed_text, receipt_text, send_sms

from .models import Loan, Penalty, Repayment


class LoanError(Exception):
    pass


@transaction.atomic
def create_loan(*, customer, product, principal, user, notes="", form_fee_paid=False):
    customer = type(customer).objects.select_for_update().get(pk=customer.pk)
    if Loan.objects.filter(customer=customer, status__in=Loan.OPEN_STATUSES).exists():
        raise LoanError("Mteja huyu tayari ana mkopo ambao haujaisha.")
    loan = Loan.objects.create(
        customer=customer, branch=customer.branch, product=product,
        principal=principal, created_by=user, notes=notes,
    )
    if form_fee_paid and product.form_fee > 0:
        CashEntry.objects.create(
            branch=customer.branch, entry_type=CashEntry.EntryType.FORM_FEE,
            amount=product.form_fee, customer=customer, recorded_by=user,
            description=f"Ada ya fomu, mkopo {loan.number}",
        )
    return loan


def _locked(loan_id):
    return Loan.objects.select_for_update().get(pk=loan_id)


@transaction.atomic
def approve_loan(loan_id, user):
    loan = _locked(loan_id)
    if loan.status != Loan.Status.PENDING:
        raise LoanError("Mkopo huu hauko kwenye hali ya kusubiri.")
    loan.status = Loan.Status.APPROVED
    loan.approved_by = user
    loan.approved_at = timezone.now()
    loan.save(update_fields=["status", "approved_by", "approved_at"])
    return loan


@transaction.atomic
def reject_loan(loan_id, user, reason=""):
    loan = _locked(loan_id)
    if loan.status not in (Loan.Status.PENDING, Loan.Status.APPROVED):
        raise LoanError("Mkopo ambao tayari umetolewa hauwezi kukataliwa.")
    loan.status = Loan.Status.REJECTED
    loan.closed_at = timezone.now()
    if reason:
        loan.notes = (loan.notes + f"\nSababu ya kukataliwa: {reason}").strip()
    loan.save(update_fields=["status", "closed_at", "notes"])
    return loan


def disburse_loan(loan_id, user):
    with transaction.atomic():
        loan = _locked(loan_id)
        if loan.status != Loan.Status.APPROVED:
            raise LoanError("Mkopo lazima uthibitishwe kwanza.")
        loan.status = Loan.Status.ACTIVE
        loan.disbursed_by = user
        loan.disbursed_at = timezone.now()
        loan.due_date = timezone.localdate() + timedelta(days=loan.duration_days)
        loan.save(update_fields=["status", "disbursed_by", "disbursed_at", "due_date"])
    send_sms(loan.customer.phone, disbursed_text(loan), kind=SmsLog.Kind.DISBURSED,
             customer=loan.customer, loan=loan, user=user)
    return loan


def record_payment(loan_id, *, amount, user, method=Repayment.Method.CASH, reference="", note=""):
    with transaction.atomic():
        loan = _locked(loan_id)
        if loan.status != Loan.Status.ACTIVE:
            raise LoanError("Mkopo huu haupokei malipo.")
        if amount <= 0:
            raise LoanError("Kiasi lazima kiwe zaidi ya sifuri.")
        balance = loan.balance
        if amount > balance:
            raise LoanError(f"Kiasi kimezidi deni lililobaki (TSh {balance:,.0f}).")
        payment = Repayment.objects.create(
            loan=loan, amount=amount, method=method,
            reference=reference, note=note, received_by=user,
        )
        if balance - amount <= 0:
            loan.status = Loan.Status.COMPLETED
            loan.closed_at = timezone.now()
            loan.save(update_fields=["status", "closed_at"])
    if settings.SMS_ON_PAYMENT:
        send_sms(loan.customer.phone, receipt_text(payment), kind=SmsLog.Kind.RECEIPT,
                 customer=loan.customer, loan=loan, user=user)
    return payment


@transaction.atomic
def add_penalty(loan_id, *, amount, reason, user):
    loan = _locked(loan_id)
    if loan.status != Loan.Status.ACTIVE:
        raise LoanError("Faini inawekwa kwenye mkopo unaodaiwa tu.")
    if amount <= 0:
        raise LoanError("Kiasi cha faini lazima kiwe zaidi ya sifuri.")
    return Penalty.objects.create(loan=loan, amount=amount, reason=reason or "Kuchelewa kulipa", created_by=user)


@transaction.atomic
def write_off(loan_id, user, reason=""):
    loan = _locked(loan_id)
    if loan.status != Loan.Status.ACTIVE:
        raise LoanError("Mkopo unaodaiwa tu ndio unaweza kufutwa.")
    loan.status = Loan.Status.WRITTEN_OFF
    loan.closed_at = timezone.now()
    loan.notes = (loan.notes + f"\nUmefutwa na {user}: {reason}").strip()
    loan.save(update_fields=["status", "closed_at", "notes"])
    return loan


def apply_daily_penalties_once():
    """
    Faini za siku bila kutegemea cron: ombi la kwanza la siku linaziweka.
    Salama kuitwa mara nyingi, kwa sababu faini ya moja kwa moja ni moja tu kwa siku.
    """
    key = f"penalties:{timezone.localdate().isoformat()}"
    if cache.add(key, True, timeout=60 * 60 * 26):
        return apply_daily_penalties()
    return 0


def apply_daily_penalties():
    """Inaweka faini ya kila siku kwa mikopo iliyo nje ya mkataba (mara moja tu kwa siku)."""
    today = timezone.localdate()
    count = 0
    for loan in Loan.objects.overdue().select_related("product"):
        rate = loan.product.penalty_per_day
        if rate > 0:
            _, created = Penalty.objects.get_or_create(
                loan=loan, date=today, is_auto=True,
                defaults={"amount": rate, "reason": "Faini ya kuchelewa (moja kwa moja)"},
            )
            count += created
    return count
