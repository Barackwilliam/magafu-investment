from django import forms
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["username"].help_text = ""
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
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
        if data.get("role") != User.Role.ADMIN and not data.get("branch"):
            self.add_error("branch", "Meneja na afisa lazima wawe na tawi.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
