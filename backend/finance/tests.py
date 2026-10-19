from django.test import TestCase
from django.db import IntegrityError, transaction
from identity.models import Organization, Branch
from .models import Invoice, Cashbox

class CashboxContracts(TestCase):
    def test_duplicate_cashbox_in_same_branch_rejected(self):
        org = Organization.objects.create(name="Service")
        branch = Branch.objects.create(organization=org, name="Main", code="main")
        Cashbox.objects.create(organization=org, branch=branch, name="Cash")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cashbox.objects.create(organization=org, branch=branch, name="Cash")
