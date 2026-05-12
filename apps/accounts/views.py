from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import GenericAPIView
from .serializers import (
    CustomTokenObtainPairSerializer, 
    ResetPasswordConfirmSerializer,
    RegisterSerializer,
    UserSerializer, 
    VerifyEmailSerializer,
    ChangePasswordSerializer
)
from .services import handle_logout
from rest_framework import status
from .utils import send_otp_email, check_otp, use_otp
from .models import User

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        if self.serializer_class:
            serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            otp_send = send_otp_email(user)
            if otp_send:
                return Response({ "message": "Otp sent to your email"})
            return Response({"error": "Otp sent failed"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(GenericAPIView):
    serializer_class = VerifyEmailSerializer

    def post(self, request):
        try:
            if self.serializer_class:
                serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            email = serializer.validated_data.get('email')
            user= User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            if user.is_active:
                return Response({"message": f"Email {email} is already verified"}, status=status.HTTP_200_OK)

            input_otp = serializer.validated_data.get('otp')
            otp_use = use_otp(user, input_otp)
            if otp_use:
                user.is_active = True
                user.save()
                return Response({"message": f"Email {email} successfully verified"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "OTP is expired or already used"}, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "error": "Failed to verify email.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
class PasswordResetConfirmView(GenericAPIView):
    serializer_class = ResetPasswordConfirmSerializer

    def post(self, request):
        try:
            if self.serializer_class:
                serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.validated_data.get('email')
            input_otp = serializer.validated_data.get('otp')
            new_password = serializer.validated_data.get('new_password')

            user= User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            otp_use = use_otp(user, input_otp)
            if otp_use:
                user.set_password(new_password)
                user.save()
                return Response({"message": f"Password for {email} successfully reset"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "OTP is expired or already used"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": "Failed to reset password.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SendOTPView(GenericAPIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        otp_send = send_otp_email(user)
        if otp_send:
            return Response({"message": "OTP sent to your email"}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to send OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CheckOTPView(GenericAPIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if check_otp(user, otp):
            return Response({"message": "OTP is valid"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "OTP is invalid or expired"}, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if self.serializer_class:
            serializer = self.serializer_class(user)

        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateProfileView(GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        if self.serializer_class:
            serializer = self.serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if self.serializer_class:
            serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            if not user.check_password(serializer.validated_data.get('old_password')):
                return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data.get('new_password'))
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            handle_logout(request)
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
