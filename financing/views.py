from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from common.permissions import IsMerchantLenderOrCompliance
from common.models import UserProfile, AccessLog
from common.audit import log_access
from .models import FinancingRequest, FinancingIndex
from merchants.models import MerchantIndex
from django.db import transaction




class FinancingListView(APIView):
    # Different roles for different actions: the three roles may LIST,
    # but only a merchant may CREATE a financing request.
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated(), IsMerchantLenderOrCompliance()]

    def get_visible_indexes(self, request):
        base = FinancingIndex.objects.select_related(
            'financing_request',
            'financing_request__merchant',
            'financing_request__merchant__index',
        )

        try:
            role = request.user.profile.role
        except UserProfile.DoesNotExist:
            return base

        # A merchant sees only requests belonging to their own merchant.
        # If their profile has no merchant linked, this safely returns nothing.
        if role == UserProfile.Role.MERCHANT:
            return base.filter(
                financing_request__merchant=request.user.profile.merchant
            )

        # Lenders and compliance review across all merchants.
        return base

    def get(self, request):
        items = []
        for idx in self.get_visible_indexes(request):
            fr = idx.financing_request
            items.append({
                'id': idx.id,
                'merchant': fr.merchant.index.id if hasattr(fr.merchant, 'index') else None,
                'amount': str(fr.amount),
                'currency': fr.currency,
                'purpose': fr.purpose,
                'status': fr.status,
            })
            # We log only the index ids that were returned, never the contents.
        log_access(
            request,
            action=AccessLog.Action.LIST_FINANCING,
            record_ids=[item['id'] for item in items],
            resource_type='financing_request',
        )

        return Response(items)

    def post(self, request):
        data = request.data
        merchant_id = data.get('merchant')
        try:
            merchant_idx = MerchantIndex.objects.get(pk=int(merchant_id))
            merchant = merchant_idx.merchant
        except Exception:
            return Response({'detail': 'Invalid merchant'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile_merchant_id = request.user.profile.merchant_id if request.user.is_authenticated else None
        except UserProfile.DoesNotExist:
            profile_merchant_id = None

        if profile_merchant_id is not None and profile_merchant_id != merchant.pk:
            return Response(
                {'detail': 'You may only submit financing requests for your own merchant account.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        
        from .serializers import FinancingRequestSerializer
        serializer = FinancingRequestSerializer(data={
            'merchant': merchant.pk,
            'amount': data.get('amount'),
            'currency': data.get('currency', 'USD'),
            'purpose': data.get('purpose', ''),
            'payback_date': data.get('payback_date'),
        })
        serializer.is_valid(raise_exception=True)
        from django.db import transaction
        with transaction.atomic():
            fr = serializer.save()
            idx = FinancingIndex.objects.create(financing_request=fr)
            log_access(
            request,
            action=AccessLog.Action.CREATE_FINANCING,
            record_ids=[idx.id],
            resource_type='financing_request',
        )
            
            return Response({'id': idx.id}, status=status.HTTP_201_CREATED)

