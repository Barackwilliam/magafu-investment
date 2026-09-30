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
        customers = Customer.objects.all()
        if user and not user.is_admin:
            del self.fields["branch"]
        else:
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
            customers = customers.filter(branch=user.branch)
        self.fields["customer"].queryset = customers
        self.fields["customer"].required = False
        self.fields["customer"].help_text = "Kwa ada ya fomu au kutembelea tu."

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Kiasi lazima kiwe zaidi ya sifuri.")
        return amount

    def clean_date(self):
        d = self.cleaned_data["date"]
        if d > timezone.localdate():
            raise forms.ValidationError("Huwezi kurekodi muamala wa tarehe ijayo.")
        return d
