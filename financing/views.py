from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import FinancingRequest, FinancingIndex
from merchants.models import MerchantIndex



class FinancingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = []
        for idx in FinancingIndex.objects.select_related('financing_request').all():
            fr = idx.financing_request
            items.append({
                'id': idx.id,
                'merchant': fr.merchant.index.id if hasattr(fr.merchant, 'index') else None,
                'amount': str(fr.amount),
                'currency': fr.currency,
                'purpose': fr.purpose,
                'status': fr.status,
            })
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
