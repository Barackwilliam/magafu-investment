import math
from decimal import ROUND_UP, Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

MONEY = dict(max_digits=14, decimal_places=2)


class LoanProduct(models.Model):
    """Aina ya mkopo. Admin anabadilisha riba, muda, faini na ada hapa bila kugusa code."""
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Kila siku"
        WEEKLY = "WEEKLY", "Kila wiki"
        MONTHLY = "MONTHLY", "Kila mwezi"
        ONCE = "ONCE", "Mara moja mwisho wa muda"

    name = models.CharField("Jina", max_length=100, unique=True)
    interest_rate = models.DecimalField("Riba (%)", max_digits=5, decimal_places=2)
    duration_days = models.PositiveIntegerField("Muda (siku)", default=30)
    repayment_frequency = models.CharField("Marejesho", max_length=10, choices=Frequency.choices,
                                           default=Frequency.DAILY)
    form_fee = models.DecimalField("Ada ya fomu", default=0, **MONEY)
    penalty_per_day = models.DecimalField("Faini kwa kila siku ya kuchelewa", default=0, **MONEY,
                                          help_text="0 = hakuna faini ya moja kwa moja")
    min_amount = models.DecimalField("Kiwango cha chini", default=0, **MONEY)
    max_amount = models.DecimalField("Kiwango cha juu", default=0, **MONEY, help_text="0 = hakuna kikomo")
    is_active = models.BooleanField("Inatumika", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Aina ya mkopo"
        verbose_name_plural = "Aina za mikopo"

    def __str__(self):
        return f"{self.name} ({self.interest_rate:g}%, siku {self.duration_days})"


class LoanQuerySet(models.QuerySet):
    def with_totals(self):
        """Inaongeza paid_total, penalty_total na balance_total kwa query moja (bila N+1)."""
        out = DecimalField(**MONEY)
        paid = (Repayment.objects.filter(loan=OuterRef("pk")).values("loan")
                .annotate(t=Sum("amount")).values("t"))
        pen = (Penalty.objects.filter(loan=OuterRef("pk")).values("loan")
               .annotate(t=Sum("amount")).values("t"))
        return self.annotate(
            paid_total=Coalesce(Subquery(paid, output_field=out), Value(Decimal(0)), output_field=out),
            penalty_total=Coalesce(Subquery(pen, output_field=out), Value(Decimal(0)), output_field=out),
        ).annotate(
            balance_total=F("total_payable") + F("penalty_total") - F("paid_total"),
        )

    def active(self):
        return self.filter(status=Loan.Status.ACTIVE)

    def overdue(self):
        return self.filter(status=Loan.Status.ACTIVE, due_date__lt=timezone.localdate())


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Inasubiri kuthibitishwa"
        APPROVED = "APPROVED", "Imethibitishwa"
        ACTIVE = "ACTIVE", "Anadaiwa"
        COMPLETED = "COMPLETED", "Amemaliza"
        REJECTED = "REJECTED", "Imekataliwa"
        WRITTEN_OFF = "WRITTEN_OFF", "Imefutwa"

    OPEN_STATUSES = [Status.PENDING, Status.APPROVED, Status.ACTIVE]

    customer = models.ForeignKey("customers.Customer", verbose_name="Mteja",
                                 on_delete=models.PROTECT, related_name="loans")
    branch = models.ForeignKey("core.Branch", on_delete=models.PROTECT, related_name="loans")
    product = models.ForeignKey(LoanProduct, verbose_name="Aina ya mkopo", on_delete=models.PROTECT)

    # Nakala ya masharti siku ya maombi: kubadilisha product hakuathiri mikopo ya zamani
    principal = models.DecimalField("Kiasi cha mkopo", **MONEY)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    interest_amount = models.DecimalField(**MONEY)
    total_payable = models.DecimalField(**MONEY)
    duration_days = models.PositiveIntegerField()
    repayment_frequency = models.CharField(max_length=10, choices=LoanProduct.Frequency.choices)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="created_loans")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="approved_loans")
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="disbursed_loans")
    disbursed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField("Maelezo", blank=True)

    objects = LoanQuerySet.as_manager()

    class Meta:
        ordering = ["-applied_at"]
        verbose_name = "Mkopo"
        verbose_name_plural = "Mikopo"
        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["disbursed_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            p = self.product
            self.interest_rate = p.interest_rate
            self.duration_days = p.duration_days
            self.repayment_frequency = p.repayment_frequency
            self.interest_amount = (self.principal * self.interest_rate / 100).quantize(Decimal("1"))
            self.total_payable = self.principal + self.interest_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} {self.customer}"

    @property
    def number(self):
        return f"MG{self.pk:05d}" if self.pk else "MG-----"

    # Hesabu: tunatumia thamani za with_totals() zikiwepo, vinginevyo tunahesabu
    @property
    def amount_paid(self):
        v = getattr(self, "paid_total", None)
        return v if v is not None else (self.repayments.aggregate(t=Sum("amount"))["t"] or Decimal(0))

    @property
    def penalties(self):
        v = getattr(self, "penalty_total", None)
        return v if v is not None else (self.penalty_entries.aggregate(t=Sum("amount"))["t"] or Decimal(0))

    @property
    def balance(self):
        return self.total_payable + self.penalties - self.amount_paid

    @property
    def is_overdue(self):
        return (self.status == self.Status.ACTIVE and self.due_date is not None
                and self.due_date < timezone.localdate())

    @property
    def days_overdue(self):
        return (timezone.localdate() - self.due_date).days if self.is_overdue else 0

    @property
    def days_left(self):
        return max(0, (self.due_date - timezone.localdate()).days) if self.due_date else 0

    @property
    def display_status(self):
        return "OVERDUE" if self.is_overdue else self.status

    @property
    def display_status_label(self):
        return "Nje ya mkataba" if self.is_overdue else self.get_status_display()

    # Ratiba ya marejesho
    PERIOD_DAYS = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}

    @property
    def installments(self):
        per = self.PERIOD_DAYS.get(self.repayment_frequency)
        return max(1, math.ceil(self.duration_days / per)) if per else 1

    @property
    def installment_amount(self):
        return (self.total_payable / self.installments).quantize(Decimal("1"), rounding=ROUND_UP)

    @property
    def expected_paid_to_date(self):
        """Kiasi ambacho mteja alipaswa kuwa amelipa hadi leo kwa ratiba."""
        if self.status != self.Status.ACTIVE or not self.disbursed_at:
            return Decimal(0)
        elapsed = (timezone.localdate() - timezone.localtime(self.disbursed_at).date()).days
        per = self.PERIOD_DAYS.get(self.repayment_frequency, self.duration_days)
        periods = min(elapsed // per, self.installments)
        return min(self.total_payable, self.installment_amount * periods)

    @property
    def arrears(self):
        return max(Decimal(0), self.expected_paid_to_date - self.amount_paid)

    @property
    def progress(self):
        due = self.total_payable + self.penalties
        return int(min(100, (self.amount_paid / due) * 100)) if due else 0


class Repayment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Taslimu"
        MPESA = "MPESA", "M-Pesa"
        MIXX = "MIXX", "Mixx by Yas (Tigo Pesa)"
        AIRTEL = "AIRTEL", "Airtel Money"
        HALOPESA = "HALOPESA", "HaloPesa"
        BANK = "BANK", "Benki"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="repayments")
    amount = models.DecimalField("Kiasi", **MONEY)
    method = models.CharField("Njia ya malipo", max_length=10, choices=Method.choices, default=Method.CASH)
    reference = models.CharField("Namba ya muamala", max_length=60, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    paid_at = models.DateTimeField(default=timezone.now)
    note = models.CharField("Maelezo", max_length=200, blank=True)

    class Meta:
        ordering = ["-paid_at"]
        verbose_name = "Rejesho"
        verbose_name_plural = "Marejesho"
        indexes = [models.Index(fields=["paid_at"])]


class Penalty(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="penalty_entries")
    amount = models.DecimalField("Kiasi", **MONEY)
    reason = models.CharField("Sababu", max_length=200, default="Kuchelewa kulipa")
    date = models.DateField(default=timezone.localdate)
    is_auto = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Faini"
        verbose_name_plural = "Faini"
        constraints = [
            # Faini ya moja kwa moja inawekwa mara moja tu kwa siku
            models.UniqueConstraint(fields=["loan", "date"], condition=Q(is_auto=True),
                                    name="one_auto_penalty_per_day"),
        ]
