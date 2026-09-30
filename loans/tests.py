from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Branch
from customers.models import Customer
from finance.models import CashEntry

from . import services
from .models import Loan, LoanProduct


class LoanFlowTests(TestCase):
    def setUp(self):
        self.b1 = Branch.objects.create(name="Kariakoo")
        self.b2 = Branch.objects.create(name="Mbezi")
        self.admin = User.objects.create_user("admin", password="pass1234", role="ADMIN", first_name="Admin")
        self.manager = User.objects.create_user("meneja", password="pass1234", role="MANAGER", branch=self.b1)
        self.officer = User.objects.create_user("afisa", password="pass1234", role="OFFICER", branch=self.b1)
        self.product = LoanProduct.objects.create(name="Siku 30", interest_rate=20, duration_days=30,
                                                  form_fee=10000, penalty_per_day=1000)
        self.c1 = Customer.objects.create(branch=self.b1, first_name="Hawa", last_name="Musa", gender="F", phone="0755000001")
        self.c2 = Customer.objects.create(branch=self.b2, first_name="Juma", last_name="Ali", gender="M", phone="0755000002")

    def _active_loan(self, customer=None, amount=200000):
        loan = services.create_loan(customer=customer or self.c1, product=self.product,
                                    principal=Decimal(amount), user=self.officer, form_fee_paid=True)
        services.approve_loan(loan.pk, self.manager)
        return services.disburse_loan(loan.pk, self.manager)

    def test_interest_and_full_flow(self):
        loan = self._active_loan()
        self.assertEqual(loan.total_payable, Decimal(240000))
        self.assertEqual(loan.due_date, timezone.localdate() + timedelta(days=30))
        self.assertEqual(CashEntry.objects.filter(entry_type="FORM_FEE").count(), 1)
        services.record_payment(loan.pk, amount=Decimal(100000), user=self.officer)
        loan.refresh_from_db()
        self.assertEqual(loan.balance, Decimal(140000))
        with self.assertRaises(services.LoanError):
            services.record_payment(loan.pk, amount=Decimal(150000), user=self.officer)
        services.record_payment(loan.pk, amount=Decimal(140000), user=self.officer)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.COMPLETED)

    def test_one_open_loan_per_customer(self):
        self._active_loan()
        with self.assertRaises(services.LoanError):
            services.create_loan(customer=self.c1, product=self.product, principal=Decimal(1000), user=self.officer)

    def test_product_change_does_not_affect_old_loans(self):
        loan = self._active_loan()
        self.product.interest_rate = 30
        self.product.save()
        loan.refresh_from_db()
        self.assertEqual(loan.total_payable, Decimal(240000))

    def test_overdue_and_auto_penalty_once_per_day(self):
        loan = self._active_loan()
        Loan.objects.filter(pk=loan.pk).update(due_date=timezone.localdate() - timedelta(days=3))
        self.assertEqual(services.apply_daily_penalties(), 1)
        self.assertEqual(services.apply_daily_penalties(), 0)
        loan = Loan.objects.with_totals().get(pk=loan.pk)
        self.assertTrue(loan.is_overdue)
        self.assertEqual(loan.balance_total, Decimal(241000))

    def test_branch_isolation(self):
        other = self._active_loan(customer=self.c2)
        self.client.login(username="afisa", password="pass1234")
        self.assertEqual(self.client.get(reverse("loan_detail", args=[other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("customer_detail", args=[self.c2.pk])).status_code, 404)

    def test_officer_cannot_approve(self):
        loan = services.create_loan(customer=self.c1, product=self.product, principal=Decimal(50000), user=self.officer)
        self.client.login(username="afisa", password="pass1234")
        self.client.post(reverse("loan_approve", args=[loan.pk]))
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.PENDING)
        self.assertEqual(self.client.get(reverse("product_list")).status_code, 302)

    def test_pay_via_view(self):
        loan = self._active_loan()
        self.client.login(username="afisa", password="pass1234")
        r = self.client.post(reverse("loan_pay", args=[loan.pk]), {"amount": "40000", "method": "MPESA", "reference": "QX1"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(loan.repayments.count(), 1)

    def test_all_pages_render(self):
        loan = self._active_loan()
        services.record_payment(loan.pk, amount=Decimal(20000), user=self.officer)
        CashEntry.objects.create(branch=self.b1, entry_type="EXPENSE", amount=5000, recorded_by=self.officer)
        pending = services.create_loan(customer=self.c2, product=self.product, principal=Decimal(50000), user=self.admin)
        urls = [
            reverse("dashboard"), reverse("customer_list"), reverse("customer_create"),
            reverse("customer_detail", args=[self.c1.pk]), reverse("customer_edit", args=[self.c1.pk]),
            reverse("loan_list"), reverse("loan_list") + "?hali=sugu", reverse("loan_list") + "?hali=inasubiri",
            reverse("loan_apply"), reverse("loan_detail", args=[loan.pk]), reverse("loan_detail", args=[pending.pk]),
            reverse("loan_statement", args=[loan.pk]), reverse("product_list"), reverse("product_create"),
            reverse("cash_list"), reverse("cash_create"), reverse("report_daily"), reverse("report_collections"),
            reverse("report_collections") + "?export=csv", reverse("report_disbursements"),
            reverse("report_overdue"), reverse("report_overdue") + "?export=csv", reverse("report_branches"),
            reverse("sms_log"), reverse("branch_list"), reverse("branch_create"), reverse("user_list"),
            reverse("user_create"), reverse("password_change"),
        ]
        for username in ("admin", "meneja", "afisa"):
            self.client.login(username=username, password="pass1234")
            for url in urls:
                r = self.client.get(url)
                allowed = (200, 302)
                if url == reverse("loan_detail", args=[pending.pk]) and username != "admin":
                    allowed = (404,)  # mkopo wa tawi jingine
                self.assertIn(r.status_code, allowed, f"{username} {url} -> {r.status_code}")
            self.client.logout()
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_cards_and_expected_collection(self):
        from core.stats import dashboard_cards
        loan = self._active_loan()  # 200,000 + 20% = 240,000, siku 30 kila siku -> 8,000 kwa siku
        Loan.objects.filter(pk=loan.pk).update(disbursed_at=timezone.now() - timedelta(days=5))
        services.record_payment(loan.pk, amount=Decimal(3000), user=self.officer)
        c = dashboard_cards(self.admin)
        self.assertEqual(c["makusanyo"]["makadirio"], Decimal(8000))
        self.assertEqual(c["makusanyo"]["leo"], Decimal(3000))
        self.assertEqual(c["makusanyo"]["hazijakusanywa"], Decimal(5000))
        self.assertEqual(c["makusanyo"]["asilimia"], 38)
        self.assertEqual(c["mikopo"]["wadaiwa"], Decimal(237000))
        self.assertEqual(c["mapato"]["fomu"], Decimal(10000))
        self.assertEqual(c["wateja"]["wanadaiwa"], 1)
        self.assertEqual(c["maombi"]["jumla"], 1)
        # Afisa wa tawi jingine haoni takwimu za tawi hili
        other = User.objects.create_user("mbezi", password="x", role="OFFICER", branch=self.b2)
        self.assertEqual(dashboard_cards(other)["mikopo"]["jumla"], Decimal(0))

    def test_branch_list_actions(self):
        self.client.login(username="admin", password="pass1234")
        r = self.client.post(reverse("branch_create"), {"name": "Mwenge", "phone": "0711000000", "is_active": "on"})
        self.assertEqual(r.status_code, 302)
        mwenge = Branch.objects.get(name="Mwenge")
        self.assertEqual(mwenge.created_by, self.admin)
        page = self.client.get(reverse("branch_list")).content.decode()
        for col in ("S/N", "Msajili", "Tarehe", "Actions"):
            self.assertIn(col, page)
        self.client.post(reverse("branch_toggle", args=[mwenge.pk]))
        mwenge.refresh_from_db()
        self.assertFalse(mwenge.is_active)
        # Tawi lililozimwa halionekani kwenye fomu ya mteja mpya
        self.assertNotIn(">Mwenge</option>", self.client.get(reverse("customer_create")).content.decode())
        # Tawi lenye wateja haliwezi kufutwa, tupu linafutika
        self.client.post(reverse("branch_delete", args=[self.b1.pk]))
        self.assertTrue(Branch.objects.filter(pk=self.b1.pk).exists())
        self.client.post(reverse("branch_delete", args=[mwenge.pk]))
        self.assertFalse(Branch.objects.filter(pk=mwenge.pk).exists())
