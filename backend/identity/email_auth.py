"""Opt-in email-verified account creation and password recovery.

Never activate users merely because a submitted email matches an existing CRM customer.
"""
import hashlib
import hmac
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import User


class Credentials(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=12,max_length=128,trim_whitespace=False,write_only=True)
    def validate_email(self, value):
        return value.strip().lower()
    def validate_password(self, value):
        validate_password(value)
        return value


class RecoveryEmail(serializers.Serializer):
    email=serializers.EmailField(max_length=254)


class TokenWithPassword(serializers.Serializer):
    uid=serializers.CharField(max_length=200)
    token=serializers.CharField(max_length=200)
    password=serializers.CharField(min_length=12,max_length=128,trim_whitespace=False,write_only=True)
    def validate_password(self, value):
        validate_password(value)
        return value


class TokenOnly(serializers.Serializer):
    uid=serializers.CharField(max_length=200)
    token=serializers.CharField(max_length=200)


def user_from_uid(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (ValueError,TypeError,User.DoesNotExist,OverflowError):
        return None


def mail_link(user, route, subject, description):
    uid=urlsafe_base64_encode(force_bytes(user.pk))
    token=default_token_generator.make_token(user)
    link=settings.PUBLIC_WEB_ORIGIN+"/?"+urlencode({
        "account_action":route,"uid":uid,"token":token,
    })
    delivered=send_mail(subject,description+"\n\n"+link+"\n\nСсылка действует 24 часа.",
         settings.DEFAULT_FROM_EMAIL,[user.email],fail_silently=False)
    if delivered!=1:
        raise RuntimeError("SMTP did not accept a single recipient.")


def rate_key(prefix,email):
    hash=hmac.new(settings.SECRET_KEY.encode(),email.encode(),hashlib.sha256).hexdigest()
    return "crm-auth:"+prefix+":"+hash


class PublicAuthStatus(APIView):
    permission_classes=[AllowAny]
    def get(self, request):
        return Response({"email_signup_enabled":settings.ENABLE_EMAIL_ONBOARDING,
                         "password_recovery_enabled":settings.ENABLE_EMAIL_ONBOARDING})


@method_decorator(csrf_protect,name="dispatch")
class EmailSignup(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope="auth"
    def post(self,request):
        if not settings.ENABLE_EMAIL_ONBOARDING:
            return Response({"code":"unavailable","message_ru":"Регистрация пока закрыта."},status=503)
        form=Credentials(data=request.data)
        form.is_valid(raise_exception=True)
        email=form.validated_data["email"]
        generic={"message_ru":"Если регистрация допустима, письмо для подтверждения будет отправлено."}
        if User.objects.filter(email__iexact=email).exists():
            return Response(generic,status=202)
        key=rate_key("signup",email)
        if not cache.add(key,"1",timeout=300):
            return Response(generic,status=202)
        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=email).exists():
                    return Response(generic,status=202)
                user=User.objects.create_user(email=email,password=form.validated_data["password"],is_active=False)
                mail_link(user,"verify","Подтвердите адрес электронной почты",
                          "Для активации учётной записи перейдите по ссылке:")
        except Exception:
            cache.delete(key)
            return Response({"code":"delivery_unavailable",
              "message_ru":"Не удалось отправить письмо. Попробуйте позднее."},status=503)
        return Response(generic,status=202)


@method_decorator(csrf_protect,name="dispatch")
class EmailVerify(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope="auth"
    def post(self,request):
        form=TokenOnly(data=request.data)
        form.is_valid(raise_exception=True)
        user=user_from_uid(form.validated_data["uid"])
        if not user or user.is_active or not default_token_generator.check_token(user,form.validated_data["token"]):
            return Response({"message_ru":"Ссылка недействительна или уже использована."},status=400)
        user.is_active=True
        user.save(update_fields=["is_active"])
        return Response({"verified":True})


@method_decorator(csrf_protect,name="dispatch")
class PasswordRecoveryRequest(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope="auth"
    def post(self,request):
        if not settings.ENABLE_EMAIL_ONBOARDING:
            return Response({"message_ru":"Восстановление пока закрыто."},status=503)
        form=RecoveryEmail(data=request.data)
        form.is_valid(raise_exception=True)
        email=form.validated_data["email"].strip().lower()
        generic={"message_ru":"Если учётная запись существует, письмо будет отправлено."}
        key=rate_key("recovery",email)
        if not cache.add(key,"1",timeout=300):
            return Response(generic,status=202)
        user=User.objects.filter(email__iexact=email,is_active=True).first()
        if user is not None:
            try:
                mail_link(user,"reset","Восстановление доступа к CRM",
                          "Чтобы установить новый пароль, перейдите по ссылке:")
            except Exception:
                # Never reveal existence of a user through SMTP availability.
                cache.delete(key)
        return Response(generic,status=202)


@method_decorator(csrf_protect,name="dispatch")
class PasswordRecoveryConfirm(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope="auth"
    def post(self,request):
        form=TokenWithPassword(data=request.data)
        form.is_valid(raise_exception=True)
        user=user_from_uid(form.validated_data["uid"])
        if not user or not user.is_active or not default_token_generator.check_token(user,form.validated_data["token"]):
            return Response({"message_ru":"Ссылка истекла или уже использована."},status=400)
        user.set_password(form.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"password_changed":True})
