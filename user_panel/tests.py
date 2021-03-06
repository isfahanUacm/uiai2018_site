from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from user_panel import models, views, validators


class APITests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        models.Settings(key='test_key', value='test_value').save()
        models.Settings(key='version_client_python', value='94').save()
        self.test_user1 = models.User.objects.create_user(
            email='pkazemi3@gmail.com',
            password='pkazemi1376safe',
            first_name='پرهام',
            last_name='کاظمی',
            phone='09130001122',
            institute='University of Isfahan',
            english_full_name='Parham Kazemi'
        )
        self.test_user2 = models.User.objects.create_user(
            email='pkazemi76@yahoo.com',
            password='pkazemi1376',
            first_name='کاربر',
            last_name='تست',
            english_full_name='Test User',
            phone='09139998877',
            institute='University of Isfahan',
        )

    def test_settings(self):
        request = self.factory.get(reverse('get_settings'))
        response = views.get_settings(request)
        self.assertIn('test_key', response.data)

    def test_signup(self):
        data = {
            "email": "pkazemi3@gmail.com",
            "password": "pass1234",
            "first_name": "پرهام",
            "last_name": "کاظمی",
            "phone": "09131002030",
            "institute": "University of Isfahan",
            "english_full_name": "Parham Kazemi"
        }
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 400, 'Repeated email checking failed')
        data['email'] = 'a@a.com'
        del data['phone']
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 400, 'Missing fields checking failed')
        data.update({'phone': '09131002030', 'password': '1234'})
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 400, 'Weak password allowed')
        data.update({'english_full_name': 'پرهام کاظمی'})
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 400, 'Non-English name allowed')
        data.update({'english_full_name': 'Parham Kazemi', 'first_name': 'Parham'})
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 400, 'Non-Persian name allowed')
        data.update({'first_name': 'پرهام', 'password': 'securePass1234'})
        request = self.factory.post(reverse('sign_up'), data)
        response = views.sign_up(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(models.User.objects.filter(email='a@a.com').count(), 1, 'User object not created')

    def test_edit_and_get_user_info(self):
        data = self.test_user1.get_dict()
        data['phone'] = '09130001122'
        request = self.factory.post(reverse('edit_user_info'), data)
        force_authenticate(request, self.test_user1)
        response = views.edit_user_info(request)
        self.assertEqual(response.status_code, 200)
        request = self.factory.get(reverse('get_user_info'))
        force_authenticate(request, self.test_user1)
        response = views.get_user_info(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual('09130001122', response.data['phone'])

    def test_create_team(self):
        request = self.factory.post(reverse('create_team'), data={'name': 'TableFlipperZ'})
        force_authenticate(request, self.test_user1)
        response = views.create_team(request)
        self.assertEqual(response.status_code, 201)
        request = self.factory.get(reverse('get_team_info'))
        force_authenticate(request, self.test_user1)
        response = views.get_team_info(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'TableFlipperZ')
        self.assertIn(self.test_user1.email, response.data['members'])
        request = self.factory.post(reverse('send_team_invitation'), data={'email': self.test_user2.email})
        force_authenticate(request, self.test_user1)
        response = views.send_team_invitation(request)
        self.assertEqual(response.status_code, 201)
        invitation = self.test_user2.received_invitations.first()
        self.assertEqual(invitation.get_status_display(), 'در انتظار')
        request = self.factory.post(reverse('accept_team_invitation'), data={'id': invitation.pk})
        force_authenticate(request, self.test_user2)
        response = views.accept_team_invitation(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.test_user1, self.test_user1.team.get_member1())
        self.assertEqual(self.test_user2, self.test_user1.team.get_member2())

    def test_version_checking(self):
        request = self.factory.get(reverse('get_version'), data={'name': 'client_python'})
        response = views.get_version(request)
        self.assertEqual(response.data['version'], '94')


class UtilTests(TestCase):

    def _test_validator_valid(self, validator, test_cases):
        for test in test_cases:
            try:
                validator(test)
            except ValidationError:
                self.fail('Validation for {} and string {} failed'.format(validator, test))

    def _test_validator_invalid(self, validator, test_cases):
        for test in test_cases:
            self.assertRaises(ValidationError, validator, test)

    def test_team_name_regex_valid(self):
        test_cases = ['TableFlipperZ', 'RandomTeam123', 'team_name', 'Flip123_- ']
        self._test_validator_valid(validators.team_name_validator, test_cases)

    def test_team_name_regex_invalid(self):
        test_cases = ['نام تیم', 'نباید', 'فارسی', 'باشد123_', 'teamیname', 'team@name', 'team:name']
        self._test_validator_invalid(validators.team_name_validator, test_cases)

    def test_english_name_regex_valid(self):
        test_cases = ['Parham Kazemi', 'Parham', 'Kazemi', 'parham kazemi']
        self._test_validator_valid(validators.english_string_validator, test_cases)

    def test_english_name_regex_invalid(self):
        test_cases = ['پرهام کاظمی', 'Parham کاظمی', 'Parham_Kazemi', 'Parham123']
        self._test_validator_invalid(validators.english_string_validator, test_cases)

    def test_phone_regex_valid(self):
        test_cases = ['09131112233', '09101234567', '09381112233']
        self._test_validator_valid(validators.phone_number_validator, test_cases)

    def test_phone_regex_invalid(self):
        test_cases = ['091311122334', '00989130001122', '9130001122', '+989131112233', '130001122', 'telephone']
        self._test_validator_invalid(validators.phone_number_validator, test_cases)

    def test_persian_names_valid(self):
        test_cases = ['پرهام', 'پرهام کاظمی', 'پرهام کاظمی اصل', 'ك ي', 'ئ ؤ نیم‌فاصله']
        self._test_validator_valid(validators.persian_name_validator, test_cases)

    def test_persian_names_invalid(self):
        test_cases = ['Parham', 'Parham Kazemi', 'پرهام Kazemi', 'پرهام۱۲۳', 'پرهام123']
        self._test_validator_invalid(validators.persian_name_validator, test_cases)
