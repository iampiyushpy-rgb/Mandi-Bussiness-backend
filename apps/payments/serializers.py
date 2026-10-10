from rest_framework import serializers
from .models import CustomerLedger, SupplierLedger, Payment

class CustomerLedgerSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)

    class Meta:
        model = CustomerLedger
        fields = '__all__'


class SupplierLedgerSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)

    class Meta:
        model = SupplierLedger
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
        extra_kwargs = {
            'payment_no': {'required': False}
        }

