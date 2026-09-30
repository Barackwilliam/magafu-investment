from django.contrib import admin

from .models import Loan, LoanProduct, Penalty, Repayment


class RepaymentInline(admin.TabularInline):
    model = Repayment
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "principal", "total_payable", "status", "due_date", "branch")
    list_filter = ("status", "branch")
    search_fields = ("customer__first_name", "customer__last_name", "customer__phone")
    inlines = [RepaymentInline]


admin.site.register(LoanProduct)
admin.site.register(Penalty)
admin.site.register(Repayment)
