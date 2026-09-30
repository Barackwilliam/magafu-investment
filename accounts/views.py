from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from core.utils import admin_required

from .forms import LoginForm, UserForm
from .models import User


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "form.html"
    success_url = reverse_lazy("dashboard")
    extra_context = {"title": "Badilisha nenosiri", "submit": "Badilisha nenosiri"}

    def form_valid(self, form):
        messages.success(self.request, "Nenosiri limebadilishwa.")
        return super().form_valid(form)


@admin_required
def user_list(request):
    users = User.objects.select_related("branch").order_by("-is_active", "first_name")
    return render(request, "accounts/user_list.html", {"users": users})


@admin_required
def user_form(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else None
    form = UserForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Mtumiaji {user} amehifadhiwa.")
        return redirect("user_list")
    return render(request, "form.html", {
        "form": form,
        "title": f"Hariri {instance}" if instance else "Ongeza mtumiaji",
        "back": reverse("user_list"),
    })
