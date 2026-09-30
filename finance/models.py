from django.conf import settings
from django.db import models
from django.utils import timezone


class CashEntry(models.Model):
    """
    Daftari la fedha la tawi (nje ya mikopo na marejesho yenyewe):
    matumizi, pesa zilizoongezwa, pesa kwenda benki, ada za fomu n.k.
    """
    class EntryType(models.TextChoices):
        CAPITAL_IN = "CAPITAL_IN", "Pesa zilizoongezwa"
        FORM_FEE = "FORM_FEE", "Ada ya fomu"
        VISIT_FEE = "VISIT_FEE", "Ada ya kutembelea"
        OTHER_INCOME = "OTHER_INCOME", "Mapato mengine"
        EXPENSE = "EXPENSE", "Matumizi"
        TO_BANK = "TO_BANK", "Pesa kwenda benki"

    INFLOWS = ["CAPITAL_IN", "FORM_FEE", "VISIT_FEE", "OTHER_INCOME"]
    OUTFLOWS = ["EXPENSE", "TO_BANK"]

    branch = models.ForeignKey("core.Branch", verbose_name="Tawi", on_delete=models.PROTECT,
                               related_name="cash_entries")
    entry_type = models.CharField("Aina", max_length=15, choices=EntryType.choices)
    amount = models.DecimalField("Kiasi", max_digits=14, decimal_places=2)
    description = models.TextField("Maelezo", blank=True)
    customer = models.ForeignKey("customers.Customer", verbose_name="Mteja", null=True, blank=True,
                                 on_delete=models.SET_NULL)
    date = models.DateField("Tarehe", default=timezone.localdate)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Muamala wa fedha"
        verbose_name_plural = "Daftari la fedha"
        indexes = [models.Index(fields=["branch", "date", "entry_type"])]

    @property
    def is_inflow(self):
        return self.entry_type in self.INFLOWS
