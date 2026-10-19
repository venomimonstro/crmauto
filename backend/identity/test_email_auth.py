from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from identity.models import User

SETTINGS={
    "ENABLE_EMAIL_ONBOARDING":True,
    "PUBLIC_WEB_ORIGIN":"http://localhost:5173",
    "EMAIL_BACKEND":"django.core.mail.backends.locmem.EmailBackend",
    "DEFAULT_FROM_EMAIL":"noreply@invalid.test",
}

@override_settings(**SETTINGS)
class EmailAccountTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        cache.clear()

    def post(self,path,body):
        return self.client.post("/api/v1/"+path,body,format="json")

    def test_verified_signup_is_required_before_login(self):
        data={"email":"signup1@invalid.test","password":"ThisPasswordIsLong3377!"}
        response=self.post("auth/signup-email",data)
        self.assertEqual(response.status_code,202,response.content)
        user=User.objects.get(email=data["email"])
        self.assertFalse(user.is_active)
        self.assertIsNone(authenticate(username=data["email"],password=data["password"]))
        self.assertEqual(len(mail.outbox),1)
        uid=urlsafe_base64_encode(force_bytes(user.pk))
        token=default_token_generator.make_token(user)
        self.assertEqual(self.post("auth/email/verify",{
            "uid":uid,"token":token,"password":"NotTheCorrectPassword399!"}).status_code,400)
        confirmation=self.post("auth/email/verify",{"uid":uid,"token":token,
            "password":data["password"]})
        self.assertEqual(confirmation.status_code,200,confirmation.content)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(authenticate(username=data["email"],password=data["password"]))
        self.assertEqual(self.post("auth/email/verify",{"uid":uid,"token":token,"password":data["password"]}).status_code,400)

    def test_password_recovery_token_cannot_be_reused(self):
        user=User.objects.create_user("recovery@invalid.test","PreviousLongPassword3377!")
        response=self.post("auth/password/recovery",{"email":user.email})
        self.assertEqual(response.status_code,202,response.content)
        uid=urlsafe_base64_encode(force_bytes(user.pk))
        token=default_token_generator.make_token(user)
        body={"uid":uid,"token":token,"password":"NewAndStrongPassword3388!"}
        changed=self.post("auth/password/confirm",body)
        self.assertEqual(changed.status_code,200,changed.content)
        self.assertIsNone(authenticate(username=user.email,password="PreviousLongPassword3377!"))
        self.assertIsNotNone(authenticate(username=user.email,password="NewAndStrongPassword3388!"))
        self.assertEqual(self.post("auth/password/confirm",body).status_code,400)

    def test_existing_address_does_not_disclose_account(self):
        User.objects.create_user("exists@invalid.test","SafeLongPassword77666!")
        result=self.post("auth/signup-email",{
            "email":"exists@invalid.test","password":"OtherLongPassword3377!"})
        self.assertEqual(result.status_code,202,result.content)
        self.assertEqual(User.objects.count(),1)


    def test_abandoned_inactive_signup_can_be_restarted_safely(self):
        first={"email":"abandoned@invalid.test","password":"InitialStrongPassword9988!"}
        self.assertEqual(self.post("auth/signup-email",first).status_code,202)
        user=User.objects.get(email=first["email"])
        previous=default_token_generator.make_token(user)
        cache.clear()  # Simulate a retry after the throttling window.
        retry={"email":first["email"],"password":"UpdatedStrongPassword9977!"}
        self.assertEqual(self.post("auth/signup-email",retry).status_code,202)
        user.refresh_from_db()
        uid=urlsafe_base64_encode(force_bytes(user.pk))
        self.assertFalse(default_token_generator.check_token(user,previous))
        latest=default_token_generator.make_token(user)
        self.assertEqual(self.post("auth/email/verify",{
            "uid":uid,"token":latest,"password":first["password"]}).status_code,400)
        self.assertEqual(self.post("auth/email/verify",{
            "uid":uid,"token":latest,"password":retry["password"]}).status_code,200)

    @override_settings(ENABLE_EMAIL_ONBOARDING=False)
    def test_disabled_signup_does_not_create_accounts(self):
        response=self.post("auth/signup-email",{
            "email":"disabled@invalid.test","password":"OtherLongPassword3377!"})
        self.assertEqual(response.status_code,503)
        self.assertEqual(User.objects.count(),0)
