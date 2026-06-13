"""Views for the merchants app.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from .models import Merchant, MerchantIndex
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers



@method_decorator(csrf_exempt, name='dispatch')
class SessionLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    @extend_schema(
        request=inline_serializer(
            name='SessionLogin',
            fields={'username': serializers.CharField(), 'password': serializers.CharField()},
        ),
        responses={200: inline_serializer(
            name='SessionLoginResponse', 
            fields={'username': serializers.CharField(), 'is_staff': serializers.BooleanField()},
        )},
    )

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({'username': user.username, 'is_staff': user.is_staff})



class MerchantCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        business_name = data.get('name') or data.get('business_name')
        email = data.get('contact_email') or data.get('email')
        if not email:
            return Response(
                {'email': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        merchant, _ = Merchant.objects.get_or_create(
            email=email,
            defaults={
                'business_name': business_name or '',
                'owner_name': data.get('owner_name', ''),
                'phone': data.get('phone', ''),
                'country': data.get('country', ''),
            },
        )
        idx, _ = MerchantIndex.objects.get_or_create(merchant=merchant)
        return Response({'id': idx.id}, status=status.HTTP_201_CREATED)


class MerchantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            idx = MerchantIndex.objects.get(pk=pk)
        except MerchantIndex.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        m = idx.merchant
        return Response({
            'id': idx.id,
            'name': m.business_name,
            'registration_number': '',
            'contact_email': m.email,
        })

class ApiTokenLoginView(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        # Hand the submitted credentials to DRF's validator
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        # Raises a 400 with an error if username/password are wrong
        serializer.is_valid(raise_exception=True)

        # The validated user is whoever just proved their identity.=
        user = serializer.validated_data["user"]

        # get_or_create reuses the same token across logins instead of
        # minting a new one each time the token stays valid until we
        # delete it, which is how we revoke access.
        token, _ = Token.objects.get_or_create(user=user)

        # Return the token and just enough identity for the client to use.
        try:
            role = user.profile.role
        except Exception:
            role = ''
        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
            "is_staff": user.is_staff,
            "role": role,
    })