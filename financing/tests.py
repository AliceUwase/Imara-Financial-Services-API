from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from unittest.mock import patch
from django.db import IntegrityError


from common.models import AccessLog, UserProfile
from merchants.models import Merchant, MerchantIndex
from .models import FinancingRequest


def make_merchant_user(username, email):
    """Create a User + UserProfile(MERCHANT) + Merchant + MerchantIndex."""
    user = User.objects.create_user(username=username, password="testpass123")
    merchant = Merchant.objects.create(
        business_name=f"{username} Corp",
        owner_name=username,
        email=email,
        phone="+250780000001",
        country="RW",
    )
    MerchantIndex.objects.create(merchant=merchant)
    UserProfile.objects.create(user=user, role=UserProfile.Role.MERCHANT, merchant=merchant)
    token, _ = Token.objects.get_or_create(user=user)
    return user, merchant, token


class TestFinancingValidation(TestCase):
    """
    BUG 1: FinancingListView.post() bypasses FinancingRequestSerializer.
    All five cases below should return 400; before the fix they return 201
    and persist corrupt data.
    """

    def setUp(self):
        self.client = APIClient()
        self.user, self.merchant, self.token = make_merchant_user(
            "alice", "alice@example.com"
        )
        self.idx = MerchantIndex.objects.get(merchant=self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.valid_payload = {
            "merchant": self.idx.id,
            "amount": "5000.00",
            "currency": "USD",
            "purpose": "Purchase new equipment for the warehouse",
        }

    def _post(self, overrides):
        payload = {**self.valid_payload, **overrides}
        return self.client.post("/api/financing/requests/", payload, format="json")

    def test_negative_amount_rejected(self):
        response = self._post({"amount": "-500"})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

    def test_zero_amount_rejected(self):
        response = self._post({"amount": "0"})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

    def test_amount_over_ceiling_rejected(self):
        response = self._post({"amount": "1000001"})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

    def test_invalid_currency_rejected(self):
        response = self._post({"currency": "FAKE"})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

    def test_short_purpose_rejected(self):
        response = self._post({"purpose": "Too short"})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

class TestMerchantOwnership(TestCase):
    """
    BUG 2: IsMerchant() only checks role, not record ownership.
    Any merchant can POST a financing request using another merchant's ID.
    """

    def setUp(self):
        self.client = APIClient()
        _, self.merchant_a, self.token_a = make_merchant_user(
            "merchant_a", "a@example.com"
        )
        _, self.merchant_b, self.token_b = make_merchant_user(
            "merchant_b", "b@example.com"
        )
        self.idx_a = MerchantIndex.objects.get(merchant=self.merchant_a)
        self.idx_b = MerchantIndex.objects.get(merchant=self.merchant_b)

    def _post_as_a_for(self, merchant_idx_id):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        return self.client.post(
            "/api/financing/requests/",
            {
                "merchant": merchant_idx_id,
                "amount": "5000.00",
                "currency": "USD",
                "purpose": "Purchase new equipment for the warehouse",
            },
            format="json",
        )

    def test_merchant_cannot_submit_for_another_merchant(self):
        """Authenticated as merchant_a, targeting merchant_b's ID → must be 403."""
        response = self._post_as_a_for(self.idx_b.id)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 0)

    def test_merchant_can_submit_for_own_merchant(self):
        """Authenticated as merchant_a, targeting merchant_a's own ID → must be 201."""
        response = self._post_as_a_for(self.idx_a.id)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(FinancingRequest.objects.count(), 1)

class TestFinancingAtomicity(TestCase):
    """
    BUG 3: FinancingRequest and FinancingIndex are created without transaction.atomic().
    If FinancingIndex creation fails, the FinancingRequest is already committed —
    an orphan that is invisible to the API but corrupts the ledger.
    """

    def setUp(self):
        self.client = APIClient()
        self.user, self.merchant, self.token = make_merchant_user(
            "carol", "carol@example.com"
        )
        self.idx = MerchantIndex.objects.get(merchant=self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.valid_payload = {
            "merchant": self.idx.id,
            "amount": "5000.00",
            "currency": "USD",
            "purpose": "Purchase new equipment for the warehouse",
        }

    def test_no_orphaned_request_when_index_creation_fails(self):
        """FinancingRequest must be rolled back if FinancingIndex creation fails."""
        with patch(
            "financing.views.FinancingIndex.objects.create",
            side_effect=IntegrityError("simulated constraint failure"),
        ):
            try:
                self.client.post(
                    "/api/financing/requests/", self.valid_payload, format="json"
                )
            except IntegrityError:
                pass
        self.assertEqual(FinancingRequest.objects.count(), 0)

class TestFinancingAuditLog(TestCase):
    """
    BUG 4: FinancingListView.post() has no log_access() call.
    Financing creation leaves no AccessLog entry, a compliance blind spot.
    GET is logged correctly; POST is not.
    """

    def setUp(self):
        self.client = APIClient()
        self.user, self.merchant, self.token = make_merchant_user(
            "dave", "dave@example.com"
        )
        self.idx = MerchantIndex.objects.get(merchant=self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.valid_payload = {
            "merchant": self.idx.id,
            "amount": "5000.00",
            "currency": "USD",
            "purpose": "Purchase new equipment for the warehouse",
        }

    def test_financing_creation_is_audit_logged(self):
        """A successful POST must create an AccessLog entry with action='create_financing'."""
        self.client.post("/api/financing/requests/", self.valid_payload, format="json")
        self.assertEqual(
            AccessLog.objects.filter(action="create_financing").count(),
            1,
        )

    def test_audit_log_records_correct_user(self):
        """The AccessLog entry must capture the authenticated user."""
        self.client.post("/api/financing/requests/", self.valid_payload, format="json")
        log = AccessLog.objects.filter(action="create_financing").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.username, self.user.username)
