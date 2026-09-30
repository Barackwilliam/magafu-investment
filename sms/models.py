from django.conf import settings
from django.db import models


class SmsLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Inasubiri"
        SENT = "SENT", "Imetumwa"
        FAILED = "FAILED", "Imeshindwa"
        SKIPPED = "SKIPPED", "SMS zimezimwa"

    class Kind(models.TextChoices):
        RECEIPT = "RECEIPT", "Risiti ya malipo"
        REMINDER = "REMINDER", "Kikumbusho"
        DISBURSED = "DISBURSED", "Mkopo umetolewa"
        GENERAL = "GENERAL", "Nyingine"

    phone = models.CharField(max_length=20)
    message = models.TextField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.GENERAL)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    response = models.TextField(blank=True)
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL)
    loan = models.ForeignKey("loans.Loan", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="sms_logs")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS"
        verbose_name_plural = "SMS"
