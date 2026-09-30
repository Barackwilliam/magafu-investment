from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    ADMIN   -> anaona matawi yote, anasimamia settings na watumiaji
    MANAGER -> meneja wa tawi: anathibitisha na kutoa mikopo, anaweka faini
    OFFICER -> afisa mikopo: anasajili wateja, anaomba mikopo, anapokea marejesho
    """
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Meneja wa tawi"
        OFFICER = "OFFICER", "Afisa mikopo"

    role = models.CharField("Nafasi", max_length=10, choices=Role.choices, default=Role.OFFICER)
    branch = models.ForeignKey(
        "core.Branch", verbose_name="Tawi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="staff",
    )
    phone = models.CharField("Simu", max_length=20, blank=True)

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.is_admin or self.role == self.Role.MANAGER

    def __str__(self):
        return self.get_full_name() or self.username
