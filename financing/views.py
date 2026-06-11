from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.permissions import IsMerchant, IsLender, IsCompliance
from common.models import UserProfile
from common.models import AccessLog
from common.audit import log_access
from .models import FinancingRequest, FinancingIndex
from merchants.models import MerchantIndex




class FinancingListView(APIView):
    # Different roles for different actions: the three roles may LIST,
    # but only a merchant may CREATE a financing request.
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsMerchant()]
        return [IsAuthenticated(), (IsMerchant | IsLender | IsCompliance)()]

    def get_visible_indexes(self, request):
        base = FinancingIndex.objects.select_related(
            'financing_request',
            'financing_request__merchant',
            'financing_request__merchant__index',
        )

        # A merchant sees only requests belonging to their own merchant.
        # If their profile has no merchant linked, this safely returns nothing.
        if request.user.profile.role == UserProfile.Role.MERCHANT:
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

        fr = FinancingRequest.objects.create(
            merchant=merchant,
            amount=data.get('amount', 0),
            currency=data.get('currency', 'USD'),
            purpose=data.get('purpose', ''),
        )
        idx = FinancingIndex.objects.create(financing_request=fr)
        return Response({'id': idx.id}, status=status.HTTP_201_CREATED)
