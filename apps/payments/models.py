from django.db import models
from apps.core.models import AuditModel
from apps.customers.models import Customer
from apps.suppliers.models import Supplier

class CustomerLedger(AuditModel):
    TRANSACTION_TYPES = (
        ('SALES_INVOICE', 'Sales Invoice'),
        ('PAYMENT_RECEIVED', 'Payment Received'),
        ('SALES_RETURN', 'Sales Return Credit'),
        ('OPENING_BALANCE', 'Opening Balance'),
        ('ADJUSTMENT', 'Ledger Adjustment'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Increases customer receivable
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Decreases customer receivable
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['transaction_date', 'id']

    def __str__(self):
        return f"{self.customer.customer_name} - {self.transaction_type}: ₹{self.debit or self.credit}"

class SupplierLedger(AuditModel):
    TRANSACTION_TYPES = (
        ('PURCHASE_BILL', 'Purchase Bill'),
        ('PAYMENT_MADE', 'Payment Made'),
        ('PURCHASE_RETURN', 'Purchase Return Debit'),
        ('OPENING_BALANCE', 'Opening Balance'),
        ('ADJUSTMENT', 'Ledger Adjustment'),
    )

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Decreases supplier payable
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Increases supplier payable
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['transaction_date', 'id']

    def __str__(self):
        return f"{self.supplier.supplier_name} - {self.transaction_type}: ₹{self.debit or self.credit}"


class Payment(AuditModel):
    PARTY_TYPES = (
        ('CUSTOMER', 'Customer Receipt'),
        ('SUPPLIER', 'Supplier Payment / Expense'),
    )
    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('BANK', 'Bank Transfer'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    )

    payment_no = models.CharField(max_length=50, unique=True)
    party_type = models.CharField(max_length=20, choices=PARTY_TYPES, default='CUSTOMER')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='CASH')
    transaction_reference = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-payment_date', '-id']

    def __str__(self):
        party = self.customer.customer_name if self.customer else (self.supplier.supplier_name if self.supplier else 'General')
        return f"{self.payment_no} - {self.party_type} ({party}): ₹{self.amount}"

