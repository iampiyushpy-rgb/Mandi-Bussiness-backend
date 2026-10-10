import datetime
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CustomerLedger, SupplierLedger, Payment
from .serializers import CustomerLedgerSerializer, SupplierLedgerSerializer, PaymentSerializer
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.accounts.permissions import CanManagePayments

class CustomerLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerLedger.objects.all().select_related('customer').order_by('-transaction_date', '-id')
    serializer_class = CustomerLedgerSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        qs = super().get_queryset()
        cust_id = self.request.query_params.get('customer')
        if cust_id:
            qs = qs.filter(customer_id=cust_id)
        return qs


class SupplierLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierLedger.objects.all().select_related('supplier').order_by('-transaction_date', '-id')
    serializer_class = SupplierLedgerSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        qs = super().get_queryset()
        supp_id = self.request.query_params.get('supplier')
        if supp_id:
            qs = qs.filter(supplier_id=supp_id)
        return qs


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('customer', 'supplier').order_by('-payment_date', '-id')
    serializer_class = PaymentSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        qs = super().get_queryset()
        cust_id = self.request.query_params.get('customer')
        if cust_id:
            qs = qs.filter(customer_id=cust_id)
        supp_id = self.request.query_params.get('supplier')
        if supp_id:
            qs = qs.filter(supplier_id=supp_id)
        party_type = self.request.query_params.get('party_type')
        if party_type:
            qs = qs.filter(party_type__iexact=party_type)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        with transaction.atomic():
            if not data.get('payment_no'):
                today_str = datetime.date.today().strftime('%Y%m%d')
                count = Payment.objects.count() + 1
                data['payment_no'] = f"PAY-{today_str}-{count:04d}"

            # Customer resolution
            cust_id = data.get('customer')
            cust_name = str(data.get('customer_name') or '').strip()
            cust_obj = None
            if cust_id and str(cust_id).isdigit():
                cust_obj = Customer.objects.filter(id=int(cust_id)).first()
            elif cust_name:
                cust_obj = Customer.objects.filter(customer_name__iexact=cust_name).first()

            if cust_obj:
                data['customer'] = cust_obj.id

            # Supplier resolution
            supp_id = data.get('supplier')
            supp_name = str(data.get('supplier_name') or '').strip()
            supp_obj = None
            if supp_id and str(supp_id).isdigit():
                supp_obj = Supplier.objects.filter(id=int(supp_id)).first()
            elif supp_name:
                supp_obj = Supplier.objects.filter(supplier_name__iexact=supp_name).first()

            if supp_obj:
                data['supplier'] = supp_obj.id

            # Fallback payment date
            if not data.get('payment_date'):
                data['payment_date'] = datetime.date.today()

            # Normalize method / reference / notes
            if data.get('payment_mode') and not data.get('payment_method'):
                data['payment_method'] = data['payment_mode']
            if data.get('reference_number') and not data.get('transaction_reference'):
                data['transaction_reference'] = data['reference_number']
            if data.get('description') and not data.get('notes'):
                data['notes'] = data['description']

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            payment = serializer.save()

            amt = Decimal(str(payment.amount or 0))

            # Sync ledger and party balances
            if cust_obj and amt > 0:
                cust_obj.current_balance = max(Decimal('0'), cust_obj.current_balance - amt)
                cust_obj.save()

                CustomerLedger.objects.create(
                    customer=cust_obj,
                    transaction_date=payment.payment_date,
                    transaction_type='PAYMENT_RECEIVED',
                    reference_type='PAYMENT',
                    reference_id=payment.payment_no,
                    debit=Decimal('0'),
                    credit=amt,
                    balance=cust_obj.current_balance,
                    description=payment.notes or f"Payment received from {cust_obj.customer_name}"
                )

            elif supp_obj and amt > 0:
                supp_obj.current_balance = max(Decimal('0'), supp_obj.current_balance - amt)
                supp_obj.save()

                SupplierLedger.objects.create(
                    supplier=supp_obj,
                    transaction_date=payment.payment_date,
                    transaction_type='PAYMENT_MADE',
                    reference_type='PAYMENT',
                    reference_id=payment.payment_no,
                    debit=amt,
                    credit=Decimal('0'),
                    balance=supp_obj.current_balance,
                    description=payment.notes or f"Payment made to {supp_obj.supplier_name}"
                )

            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        payment = self.get_object()
        with transaction.atomic():
            # Delete corresponding ledger records
            CustomerLedger.objects.filter(reference_id=payment.payment_no).delete()
            SupplierLedger.objects.filter(reference_id=payment.payment_no).delete()
            payment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

