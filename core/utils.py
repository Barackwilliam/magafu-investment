import csv
from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone


def role_required(*roles):
    """Admin anaruhusiwa kila mahali. Roles nyingine lazima zitajwe."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_admin or user.role in roles:
                return view(request, *args, **kwargs)
            messages.error(request, "Huna ruhusa ya kufanya hilo.")
            return redirect("dashboard")
        return wrapper
    return decorator


def branch_required(view):
    """Afisa au meneja bila tawi hawezi kusajili chochote: kila rekodi lazima iwe na tawi."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin and not request.user.branch_id:
            messages.error(request, "Akaunti yako haina tawi. Mwombe admin akuwekee tawi kwanza.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    return wrapper


admin_required = role_required()
manager_required = role_required("MANAGER")


def scope_by_branch(qs, user, field="branch"):
    """Admin anaona kila kitu, wengine wanaona tawi lao tu."""
    if user.is_admin:
        return qs
    if not user.branch_id:
        return qs.none()
    return qs.filter(**{f"{field}_id": user.branch_id})


def branch_filter(request, qs, field="branch"):
    """Kama scope_by_branch, pamoja na admin kuchagua tawi kwa ?tawi=ID."""
    qs = scope_by_branch(qs, request.user, field)
    tawi = request.GET.get("tawi", "")
    if request.user.is_admin and tawi.isdigit():
        qs = qs.filter(**{f"{field}_id": int(tawi)})
    return qs


def date_range(request, default_start=None):
    today = timezone.localdate()

    def parse(name, default):
        try:
            return date.fromisoformat(request.GET.get(name, ""))
        except ValueError:
            return default

    start = parse("kuanzia", default_start or today.replace(day=1))
    end = parse("mpaka", today)
    if start > end:
        start, end = end, start
    return start, end


def total(qs, field="amount"):
    return qs.aggregate(t=Sum(field))["t"] or 0


def paginate(request, qs, per_page=25):
    return Paginator(qs, per_page).get_page(request.GET.get("page"))


def csv_response(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")  # ili Excel isome herufi vizuri
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response
