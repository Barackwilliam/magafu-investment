from django import forms

from customers.models import Customer

from .models import Loan, LoanProduct, Repayment


class LoanProductForm(forms.ModelForm):
    class Meta:
        model = LoanProduct
        fields = ["name", "interest_rate", "duration_days", "repayment_frequency", "form_fee",
                  "penalty_per_day", "min_amount", "max_amount", "is_active"]

    def clean(self):
        data = super().clean()
        rate, days = data.get("interest_rate"), data.get("duration_days")
        low, high = data.get("min_amount"), data.get("max_amount")
        if rate is not None and not 0 <= rate <= 100:
            self.add_error("interest_rate", "Riba iwe kati ya 0 na 100.")
        if days is not None and days < 1:
            self.add_error("duration_days", "Muda lazima uwe angalau siku 1.")
        for name in ("form_fee", "penalty_per_day", "min_amount", "max_amount"):
            if data.get(name) is not None and data[name] < 0:
                self.add_error(name, "Kiasi hakiwezi kuwa hasi.")
        if low and high and high < low:
            self.add_error("max_amount", "Kiwango cha juu hakiwezi kuwa chini ya kiwango cha chini.")
        return data


class LoanApplicationForm(forms.Form):
    customer = forms.ModelChoiceField(label="Mteja", queryset=Customer.objects.none(), empty_label="Chagua mteja…")
    product = forms.ModelChoiceField(label="Aina ya mkopo", queryset=LoanProduct.objects.filter(is_active=True),
                                     empty_label="Chagua aina ya mkopo…")
    principal = forms.DecimalField(label="Kiasi cha mkopo (TSh)", max_digits=14, decimal_places=0, min_value=1)
    form_fee_paid = forms.BooleanField(label="Mteja amelipa ada ya fomu sasa", required=False, initial=True)
    notes = forms.CharField(label="Maelezo", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Customer.objects.filter(is_active=True).order_by("first_name", "last_name")
        if user and not user.is_admin:
            qs = qs.filter(branch=user.branch)
        self.fields["customer"].queryset = qs

    def clean(self):
        data = super().clean()
        product, amount, customer = data.get("product"), data.get("principal"), data.get("customer")
        if product and amount:
            if product.min_amount and amount < product.min_amount:
                self.add_error("principal", f"Kiwango cha chini ni TSh {product.min_amount:,.0f}.")
            if product.max_amount and amount > product.max_amount:
                self.add_error("principal", f"Kiwango cha juu ni TSh {product.max_amount:,.0f}.")
        if customer and Loan.objects.filter(customer=customer, status__in=Loan.OPEN_STATUSES).exists():
            self.add_error("customer", "Mteja huyu tayari ana mkopo ambao haujaisha.")
        return data


class RepaymentForm(forms.Form):
    amount = forms.DecimalField(label="Kiasi (TSh)", max_digits=14, decimal_places=0, min_value=1)
    method = forms.ChoiceField(label="Njia ya malipo", choices=Repayment.Method.choices)
    reference = forms.CharField(label="Namba ya muamala", required=False)


class PenaltyForm(forms.Form):
    amount = forms.DecimalField(label="Kiasi cha faini (TSh)", max_digits=14, decimal_places=0, min_value=1)
    reason = forms.CharField(label="Sababu", required=False)


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Sababu", required=False)
