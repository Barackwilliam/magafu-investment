from django import forms
from django.db import models
from django.contrib.auth.forms import AuthenticationForm

from core.models import Branch

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Jina la mtumiaji")
    password = forms.CharField(label="Nenosiri", widget=forms.PasswordInput)
    error_messages = {
        "invalid_login": "Jina la mtumiaji au nenosiri si sahihi.",
        "inactive": "Akaunti hii imezimwa. Wasiliana na admin.",
    }


class UserForm(forms.ModelForm):
    password1 = forms.CharField(label="Nenosiri", widget=forms.PasswordInput, required=False, min_length=6)
    password2 = forms.CharField(label="Rudia nenosiri", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "phone", "role", "branch", "is_active"]
        labels = {"first_name": "Jina la kwanza", "last_name": "Jina la mwisho",
                  "username": "Jina la mtumiaji (la kuingilia)", "is_active": "Akaunti iko hai"}

    def __init__(self, *args, acting_user=None, **kwargs):
        self.acting_user = acting_user
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["username"].help_text = ""
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        self.fields["branch"].empty_label = "Matawi yote (kwa admin)"
        if self.instance.pk:
            self.fields["password1"].help_text = "Acha wazi kama hutaki kubadilisha nenosiri."
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p1 != p2:
            self.add_error("password2", "Nenosiri hazifanani.")
        role, active = data.get("role"), data.get("is_active")
        if role != User.Role.ADMIN and not data.get("branch"):
            self.add_error("branch", "Meneja na afisa lazima wawe na tawi.")
        user = self.instance
        if user.pk and user.is_admin and not user.is_superuser and (role != User.Role.ADMIN or not active):
            if self.acting_user and user.pk == self.acting_user.pk:
                self.add_error(None, "Huwezi kujiondolea nafasi ya admin au kuzima akaunti yako mwenyewe.")
            elif not User.objects.filter(is_active=True).exclude(pk=user.pk).filter(
                    models.Q(role=User.Role.ADMIN) | models.Q(is_superuser=True)).exists():
                self.add_error(None, "Lazima abaki angalau admin mmoja anayefanya kazi.")
        if user.pk and self.acting_user and user.pk == self.acting_user.pk and active is False:
            self.add_error("is_active", "Huwezi kuzima akaunti yako mwenyewe.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
