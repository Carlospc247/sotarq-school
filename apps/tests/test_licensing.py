from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponseForbidden
from django.urls import ResolverMatch
from apps.core.middleware import LicenseMiddleware
from apps.customers.models import Client
from apps.plans.models import Plan, Module
from apps.licenses.models import License
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

class LicenseMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = LicenseMiddleware(lambda r: None)
        
        # Setup Plan and Modules
        self.module_finance = Module.objects.create(name="Finance", code="finance")
        self.module_academic = Module.objects.create(name="Academic", code="academic")
        
        self.plan_basic = Plan.objects.create(name="Basic", code="basic")
        self.plan_basic.modules.add(self.module_academic)
        
        self.plan_pro = Plan.objects.create(name="Pro", code="pro")
        self.plan_pro.modules.add(self.module_academic)
        self.plan_pro.modules.add(self.module_finance)

        # Mock Tenant and License
        self.tenant = Client.objects.create(name="School 1", schema_name="school1")
        self.license = License.objects.create(
            client=self.tenant, 
            plan=self.plan_basic, 
            status='active',
            start_date=timezone.now()
        )
        
    def test_access_allowed_with_module(self):
        request = self.factory.get('/academic/some-view/')
        request.tenant = self.tenant
        request.user = AnonymousUser()
        
        # Mock resolver match to 'academic' app
        request.resolver_match = ResolverMatch(func=lambda: None, args=(), kwargs={}, app_name='academic')
        
        response = self.middleware.process_view(request, None, None, None)
        self.assertIsNone(response, "Should allow access to academic as it is in the plan")

    def test_access_denied_missing_module(self):
        request = self.factory.get('/finance/some-view/')
        request.tenant = self.tenant # Tenant has Basic plan (Academic only)
        request.user = AnonymousUser()
        
        # Mock resolver match to 'finance' app
        request.resolver_match = ResolverMatch(func=lambda: None, args=(), kwargs={}, app_name='finance')
        
        response = self.middleware.process_view(request, None, None, None)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn("does not include the 'finance' module", response.content.decode())

    def test_access_denied_expired_license(self):
        # Expire license
        self.license.status = 'expired'
        self.license.save()
        
        request = self.factory.get('/academic/some-view/')
        request.tenant = self.tenant
        request.user = AnonymousUser()
        request.resolver_match = ResolverMatch(func=lambda: None, args=(), kwargs={}, app_name='academic')
        
        response = self.middleware.process_view(request, None, None, None)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn("inactive or expired", response.content.decode())

    def test_public_schema_skipped(self):
        request = self.factory.get('/')
        request.tenant = Client(schema_name='public')
        request.resolver_match = ResolverMatch(func=lambda: None, args=(), kwargs={}, app_name='finance')
        
        response = self.middleware.process_view(request, None, None, None)
        self.assertIsNone(response, "Should skip checks for public schema")
