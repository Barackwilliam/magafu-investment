from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.utils import manager_required, paginate, scope_by_branch
from loans.models import Loan

from .models import SmsLog
from .services import send_reminder


@login_required
def sms_log(request):
    qs = scope_by_branch(SmsLog.objects.select_related("customer"), request.user, "customer__branch")
    status = request.GET.get("status", "")
    if status in SmsLog.Status.values:
        qs = qs.filter(status=status)
    return render(request, "sms/log.html", {
        "page": paginate(request, qs), "status": status, "statuses": SmsLog.Status.choices,
    })


@manager_required
def remind_overdue(request):
    """Tuma kikumbusho kwa wote walio nje ya mkataba."""
    if request.method != "POST":
        return redirect("report_overdue")
    loans = scope_by_branch(Loan.objects.overdue(), request.user).select_related("customer")
    count = 0
    for loan in loans:
        send_reminder(loan, request.user)
        count += 1
    messages.success(request, f"Vikumbusho {count} vimeshughulikiwa. Angalia kumbukumbu za SMS.")
    return redirect("sms_log")
