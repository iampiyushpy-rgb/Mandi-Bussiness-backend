from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import AuditLog
from .serializers import AuditLogSerializer
from apps.accounts.permissions import IsAdmin

from django.db import transaction

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'app': 'Fruit Mandi ERP', 'version': '2.0.0-production'})

@api_view(['POST'])
@permission_classes([IsAdmin])
def reset_all_data(request):
    confirm_token = request.data.get('confirm') if hasattr(request, 'data') else None
    if confirm_token != 'CONFIRM_RESET_ALL_DATA':
        return Response(
            {'error': 'Destructive operation requires confirmation token "CONFIRM_RESET_ALL_DATA".'},
            status=400
        )

    with transaction.atomic():
        from apps.sales.models import SalesOrder, SalesOrderItem
        from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
        from apps.payments.models import CustomerLedger, SupplierLedger
        from apps.inventory.models import InventoryLot, InventoryTransaction
        from apps.customers.models import Customer
        from apps.suppliers.models import Supplier
        from apps.products.models import Product, ProductVariety

        SalesOrderItem.objects.all().delete()
        SalesOrder.objects.all().delete()

        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        SupplierTruckPayment.objects.all().delete()

        CustomerLedger.objects.all().delete()
        SupplierLedger.objects.all().delete()

        InventoryTransaction.objects.all().delete()
        InventoryLot.objects.all().delete()

        ProductVariety.objects.all().delete()
        Product.objects.all().delete()

        Customer.objects.all().delete()
        Supplier.objects.all().delete()

        AuditLog.objects.all().delete()

    return Response({'status': 'success', 'message': 'All website and database business records cleared.'})

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module__iexact=module)
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action__iexact=action)
        return qs
