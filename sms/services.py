"""
Kutuma SMS kupitia Beem Africa (https://beem.africa).
Weka SMS_ENABLED=True pamoja na BEEM_API_KEY na BEEM_SECRET_KEY kwenye environment.
Zikiwa zimezimwa, SMS zinarekodiwa tu bila kutumwa (nzuri kwa kujaribu).
"""
import re

import requests
from django.conf import settings

from .models import SmsLog

BEEM_URL = "https://apisms.beem.africa/v1/send"


def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0"):
        digits = "255" + digits[1:]
    elif len(digits) == 9:
        digits = "255" + digits
    return digits


def send_sms(phone, message, *, kind=SmsLog.Kind.GENERAL, customer=None, loan=None, user=None):
    log = SmsLog.objects.create(
        phone=normalize_phone(phone), message=message, kind=kind,
        customer=customer, loan=loan, sent_by=user,
    )
    if not settings.SMS_ENABLED:
        log.status = SmsLog.Status.SKIPPED
        log.response = "SMS_ENABLED=False"
        log.save(update_fields=["status", "response"])
        return log

    payload = {
        "source_addr": settings.SMS_SENDER_ID,
        "encoding": 0,
        "schedule_time": "",
        "message": message,
        "recipients": [{"recipient_id": 1, "dest_addr": log.phone}],
    }
    try:
        r = requests.post(BEEM_URL, json=payload, timeout=15,
                          auth=(settings.BEEM_API_KEY, settings.BEEM_SECRET_KEY))
        log.status = SmsLog.Status.SENT if r.ok else SmsLog.Status.FAILED
        log.response = r.text[:1000]
    except requests.RequestException as exc:
        log.status = SmsLog.Status.FAILED
        log.response = str(exc)[:1000]
    log.save(update_fields=["status", "response"])
    return log


def reminder_text(loan):
    return (
        f"Habari {loan.customer.first_name}, deni lako la mkopo {loan.number} ni "
        f"TSh {loan.balance:,.0f}. Tarehe ya kumaliza ni {loan.due_date:%d/%m/%Y}. "
        f"Tafadhali lipa kwa wakati. {settings.COMPANY_NAME}"
    )


def receipt_text(payment):
    loan = payment.loan
    return (
        f"Tumepokea TSh {payment.amount:,.0f} kwa mkopo {loan.number}. "
        f"Deni lililobaki ni TSh {loan.balance:,.0f}. Asante, {settings.COMPANY_NAME}"
    )


def disbursed_text(loan):
    return (
        f"Hongera {loan.customer.first_name}, umepokea mkopo wa TSh {loan.principal:,.0f}. "
        f"Jumla ya kulipa ni TSh {loan.total_payable:,.0f} kabla ya {loan.due_date:%d/%m/%Y}. "
        f"{settings.COMPANY_NAME}"
    )


def send_reminder(loan, user=None):
    return send_sms(loan.customer.phone, reminder_text(loan), kind=SmsLog.Kind.REMINDER,
                    customer=loan.customer, loan=loan, user=user)
