from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from common.models import UserProfile
from merchants.models import Merchant, MerchantIndex


class TestMerchantCreate(TestCase):
    """
    Layer 2 — integration: POST /api/merchants/ hits the real DB.
    Tests the full request/response cycle including idempotency.
    """

    def setUp(self):
        self.client = APIClient()
        self.valid_payload = {
            'business_name': 'Test Corp',
            'owner_name': 'Alice',
            'email': 'alice@testcorp.com',
            'phone': '+250780000001',
            'country': 'RW',
        }

    def test_creates_merchant_and_returns_integer_id(self):
        response = self.client.post('/api/merchants/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)
        self.assertIsInstance(response.data['id'], int)

    def test_same_email_twice_is_idempotent(self):
        r1 = self.client.post('/api/merchants/', self.valid_payload, format='json')
        r2 = self.client.post('/api/merchants/', self.valid_payload, format='json')
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.data['id'], r2.data['id'])
        self.assertEqual(Merchant.objects.count(), 1)

    def test_missing_email_returns_400(self):
        payload = {**self.valid_payload}
        del payload['email']
        response = self.client.post('/api/merchants/', payload, format='json')
        self.assertEqual(response.status_code, 400)


class TestTokenLogin(TestCase):
    """
    Layer 2 — integration: POST /api/auth/token/ through the real auth stack.
    Proves the token endpoint returns the role alongside the token,
    and rejects bad credentials cleanly.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='merchant1', password='correctpass')
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.MERCHANT)

    def test_valid_credentials_return_token_and_role(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'merchant1',
            'password': 'correctpass',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['role'], 'merchant')
        self.assertEqual(response.data['username'], 'merchant1')

    def test_same_user_gets_same_token_on_repeat_login(self):
        r1 = self.client.post('/api/auth/token/', {
            'username': 'merchant1', 'password': 'correctpass',
        }, format='json')
        r2 = self.client.post('/api/auth/token/', {
            'username': 'merchant1', 'password': 'correctpass',
        }, format='json')
        self.assertEqual(r1.data['token'], r2.data['token'])

    def test_wrong_password_returns_400(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'merchant1',
            'password': 'wrongpass',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_user_returns_400(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'ghost',
            'password': 'anything',
        }, format='json')
        self.assertEqual(response.status_code, 400)


class TestMerchantDetail(TestCase):
    """
    Layer 2 — integration: GET /api/merchants/{id}/.
    """

    def setUp(self):
        self.client = APIClient()
        merchant = Merchant.objects.create(
            business_name='Detail Corp',
            owner_name='Bob',
            email='bob@detail.com',
            phone='+250780000002',
            country='RW',
        )
        self.idx = MerchantIndex.objects.create(merchant=merchant)

    def test_returns_expected_fields(self):
        response = self.client.get(f'/api/merchants/{self.idx.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.idx.id)
        self.assertIn('name', response.data)
        self.assertIn('contact_email', response.data)

    def test_nonexistent_id_returns_404(self):
        response = self.client.get('/api/merchants/99999/')
        self.assertEqual(response.status_code, 404)


class TestSessionLogin(TestCase):
    """
    Layer 2 — integration + security: POST /api/session/login/.
    Public endpoint — proves it accepts valid credentials and rejects bad ones
    without leaking information about which field was wrong.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='sessionuser', password='goodpass')
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.MERCHANT)

    def test_valid_credentials_return_200_and_username(self):
        response = self.client.post('/api-auth/login/', {
            'username': 'sessionuser',
            'password': 'goodpass',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'sessionuser')

    def test_wrong_password_returns_400(self):
        response = self.client.post('/api-auth/login/', {
            'username': 'sessionuser',
            'password': 'wrongpass',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_user_returns_400(self):
        response = self.client.post('/api-auth/login/', {
            'username': 'nobody',
            'password': 'anything',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_missing_password_returns_400(self):
        response = self.client.post('/api-auth/login/', {
            'username': 'sessionuser',
        }, format='json')
        self.assertEqual(response.status_code, 400)


class TestHealthEndpoint(TestCase):
    """
    Layer 2 — integration: GET /api/health/.
    No authentication required. Proves the health check is wired and returns
    the expected payload — the signal Docker and load balancers rely on.
    """

    def setUp(self):
        self.client = APIClient()

    def test_health_returns_200(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_returns_ok_status(self):
        response = self.client.get('/api/health/')
        body = response.json()
        self.assertIn('status', body)
        self.assertEqual(body['status'], 'ok')
