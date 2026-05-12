from .models import User, OTP
from django.conf import settings
from django.core.mail import send_mail
from datetime import timedelta
from django.utils import timezone
import random
from typing import Optional

def check_email_service():
    try:
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            return True
        return False
    except:
        return False

def send_otp_email(user: User):
    if not check_email_service():
        return False

    otp = str(random.randint(1000, 9999))

    OTP.objects.create(
        user=user,
        code=otp,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    print(f"Sending OTP {otp} to email {user.email}")

    try:
        send_mail(
            'Verify your email',
            f'Your OTP for email verification is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False

def check_otp(user, otp):
    obj: Optional[OTP] = OTP.objects.filter(user=user, code=otp).first()
    if obj:
        return obj.is_valid()
    return False

def use_otp(user, otp):
    obj: Optional[OTP] = OTP.objects.filter(user=user, code=otp).first()
    if obj:
        if obj.is_valid():
            obj.is_used = True
            obj.save()
            return True
    return False
