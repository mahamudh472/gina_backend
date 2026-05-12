from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

def handle_logout(request):
    refresh_token = request.data.get('refresh_token')
    if not refresh_token:
        return Response(
            {"error": "Refresh token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    token = RefreshToken(refresh_token)
    token.blacklist()
