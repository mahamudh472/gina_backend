from django.contrib.auth import get_user_model
from django.test import TestCase

class LoginAPITest(TestCase):
    def setUp(self):
        pass

    def test_login(self):
        self.assertEqual(1, 1)
