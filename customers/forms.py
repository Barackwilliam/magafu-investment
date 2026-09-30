from django import forms

from core.models import Branch

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "first_name", "middle_name", "last_name", "gender", "phone", "national_id",
            "address", "occupation", "branch",
            "guarantor_name", "guarantor_phone", "guarantor_relation", "is_active",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_admin:
            # Afisa/meneja anasajili kwenye tawi lake tu
            del self.fields["branch"]
        else:
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        if not self.instance.pk:
            del self.fields["is_active"]
        self.fields["phone"].widget.attrs["placeholder"] = "07XXXXXXXX"

    def clean(self):
        data = super().clean()
        branch = data.get("branch")
        if (self.instance.pk and branch and branch.pk != self.instance.branch_id
                and self.instance.loans.filter(status__in=["PENDING", "APPROVED", "ACTIVE"]).exists()):
            self.add_error("branch", "Mteja ana mkopo ambao haujaisha, kwa hiyo hawezi kuhamishwa tawi sasa.")
        return data

    def clean_phone(self):
        return normalize_tz_phone(self.cleaned_data["phone"])

    def clean_guarantor_phone(self):
        phone = self.cleaned_data.get("guarantor_phone", "")
        return normalize_tz_phone(phone) if phone else ""


def normalize_tz_phone(value):
    phone = "".join(ch for ch in value if ch.isdigit())
    if phone.startswith("255"):
        phone = "0" + phone[3:]
    elif len(phone) == 9:
        phone = "0" + phone
    if len(phone) != 10 or not phone.startswith("0"):
        raise forms.ValidationError("Weka namba sahihi, mfano 0712345678.")
    return phone
