from django.conf import settings
from django.db import models


class Customer(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Mwanamke"
        MALE = "M", "Mwanaume"

    branch = models.ForeignKey("core.Branch", verbose_name="Tawi", on_delete=models.PROTECT, related_name="customers")
    first_name = models.CharField("Jina la kwanza", max_length=60)
    middle_name = models.CharField("Jina la kati", max_length=60, blank=True)
    last_name = models.CharField("Jina la mwisho", max_length=60)
    gender = models.CharField("Jinsia", max_length=1, choices=Gender.choices)
    phone = models.CharField("Simu", max_length=20, unique=True,
                             error_messages={"unique": "Kuna mteja mwingine mwenye namba hii."})
    national_id = models.CharField("Namba ya NIDA", max_length=30, blank=True)
    address = models.CharField("Makazi", max_length=200, blank=True)
    occupation = models.CharField("Kazi au biashara", max_length=120, blank=True)

    guarantor_name = models.CharField("Jina la mdhamini", max_length=120, blank=True)
    guarantor_phone = models.CharField("Simu ya mdhamini", max_length=20, blank=True)
    guarantor_relation = models.CharField("Uhusiano na mdhamini", max_length=60, blank=True)

    is_active = models.BooleanField("Yuko hai", default=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="registered_customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mteja"
        verbose_name_plural = "Wateja"
        indexes = [models.Index(fields=["branch", "created_at"])]

    @property
    def full_name(self):
        return " ".join(p for p in [self.first_name, self.middle_name, self.last_name] if p)

    def __str__(self):
        return self.full_name
