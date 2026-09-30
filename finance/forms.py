from django import forms

from core.models import Branch
from django.utils import timezone

from customers.models import Customer

from .models import CashEntry


class CashEntryForm(forms.ModelForm):
    class Meta:
        model = CashEntry
        fields = ["entry_type", "date", "amount", "branch", "customer", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        customers = Customer.objects.filter(is_active=True).select_related("branch").order_by("first_name", "last_name")
        if user and not user.is_admin:
            del self.fields["branch"]
            customers = customers.filter(branch=user.branch)
        else:
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        self.fields["customer"].queryset = customers
        self.fields["customer"].required = False
        self.fields["entry_type"].choices = [("", "Chagua aina ya muamala…")] + list(CashEntry.EntryType.choices)
        self.fields["amount"].widget.attrs["inputmode"] = "numeric"
        self.fields["customer"].empty_label = "Hakuna (si ya mteja)"
        if "branch" in self.fields:
            self.fields["branch"].empty_label = "Chagua tawi…"
        self.fields["customer"].help_text = "Kwa ada ya fomu au kutembelea tu."

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Kiasi lazima kiwe zaidi ya sifuri.")
        return amount

    def clean(self):
        data = super().clean()
        customer, branch = data.get("customer"), data.get("branch")
        if customer and branch and customer.branch_id != branch.pk:
            self.add_error("customer", "Mteja huyu ni wa tawi jingine.")
        return data

    def clean_date(self):
        d = self.cleaned_data["date"]
        if d > timezone.localdate():
            raise forms.ValidationError("Huwezi kurekodi muamala wa tarehe ijayo.")
        return d
