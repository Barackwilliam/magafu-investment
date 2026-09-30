from django.conf import settings
from django.db import models


class Branch(models.Model):
    """Tawi la kampuni."""
    name = models.CharField("Jina la tawi", max_length=120, unique=True)
    location = models.CharField("Mahali", max_length=200, blank=True)
    phone = models.CharField("Simu", max_length=20, blank=True)
    is_active = models.BooleanField("Linafanya kazi", default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Msajili", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="registered_branches")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tawi"
        verbose_name_plural = "Matawi"

    def __str__(self):
        return self.name
