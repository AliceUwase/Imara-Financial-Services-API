from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser
from rest_framework.test import APIRequestFactory

from common.models import UserProfile, AccessLog
from common.permissions import (
    IsMerchant, IsLender, IsCompliance, IsSupport,
    IsMerchantLenderOrCompliance,
)
from common.audit import get_role, get_client_ip


def _make_user(username, role):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.create(user=user, role=role)
    return user


def _req(user):
    req = APIRequestFactory().get('/')
    req.user = user
    return req


class TestPermissionClasses(TestCase):
    """
    Unit tests for every permission class — called directly, no HTTP round-trip.
    Proves the role gates behave correctly for every role including edge cases
    (anonymous user, user with no profile).
    """

    def test_is_merchant_allows_merchant(self):
        self.assertTrue(IsMerchant().has_permission(_req(_make_user('m1', 'merchant')), None))

    def test_is_merchant_blocks_lender(self):
        self.assertFalse(IsMerchant().has_permission(_req(_make_user('m2', 'lender')), None))

    def test_is_merchant_blocks_compliance(self):
        self.assertFalse(IsMerchant().has_permission(_req(_make_user('m3', 'compliance')), None))

    def test_is_merchant_blocks_anonymous(self):
        req = APIRequestFactory().get('/')
        req.user = AnonymousUser()
        self.assertFalse(IsMerchant().has_permission(req, None))

    def test_is_merchant_blocks_user_without_profile(self):
        user = User.objects.create_user(username='noprofile', password='pass')
        self.assertFalse(IsMerchant().has_permission(_req(user), None))

    def test_is_lender_allows_lender(self):
        self.assertTrue(IsLender().has_permission(_req(_make_user('l1', 'lender')), None))

    def test_is_lender_blocks_merchant(self):
        self.assertFalse(IsLender().has_permission(_req(_make_user('l2', 'merchant')), None))

    def test_is_compliance_allows_compliance(self):
        self.assertTrue(IsCompliance().has_permission(_req(_make_user('c1', 'compliance')), None))

    def test_is_support_allows_support(self):
        self.assertTrue(IsSupport().has_permission(_req(_make_user('s1', 'support')), None))

    def test_merchant_lender_compliance_blocks_support(self):
        self.assertFalse(
            IsMerchantLenderOrCompliance().has_permission(
                _req(_make_user('mlc1', 'support')), None
            )
        )

    def test_merchant_lender_compliance_blocks_anonymous(self):
        req = APIRequestFactory().get('/')
        req.user = AnonymousUser()
        self.assertFalse(IsMerchantLenderOrCompliance().has_permission(req, None))

    def test_merchant_lender_compliance_allows_all_three_roles(self):
        for role in ('merchant', 'lender', 'compliance'):
            user = _make_user(f'mlc_{role}', role)
            with self.subTest(role=role):
                self.assertTrue(
                    IsMerchantLenderOrCompliance().has_permission(_req(user), None)
                )


class TestGetRole(TestCase):
    """Unit tests for the get_role() audit helper."""

    def test_returns_role_for_authenticated_user(self):
        user = _make_user('gr1', 'lender')
        self.assertEqual(get_role(user), 'lender')

    def test_returns_empty_string_for_user_without_profile(self):
        user = User.objects.create_user(username='gr2', password='pass')
        self.assertEqual(get_role(user), '')

    def test_returns_empty_string_for_anonymous_user(self):
        self.assertEqual(get_role(AnonymousUser()), '')


class TestGetClientIp(TestCase):
    """Unit tests for the get_client_ip() audit helper."""

    def test_returns_remote_addr_when_no_proxy_header(self):
        req = APIRequestFactory().get('/', REMOTE_ADDR='1.2.3.4')
        self.assertEqual(get_client_ip(req), '1.2.3.4')

    def test_prefers_first_entry_in_x_forwarded_for(self):
        req = APIRequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='9.9.9.9, 1.2.3.4',
            REMOTE_ADDR='1.2.3.4',
        )
        self.assertEqual(get_client_ip(req), '9.9.9.9')

    def test_strips_whitespace_from_forwarded_ip(self):
        req = APIRequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='  5.5.5.5  , 1.2.3.4',
        )
        self.assertEqual(get_client_ip(req), '5.5.5.5')
