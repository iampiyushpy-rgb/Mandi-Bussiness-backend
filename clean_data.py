import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Role, UserProfile
from apps.products.models import Category, Unit, Product, ProductVariety
from apps.suppliers.models import Supplier
from apps.customers.models import Customer
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from apps.sales.models import SalesOrder, SalesOrderItem
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.payments.models import CustomerLedger, SupplierLedger, Payment

print("=== CLEANING BUSINESS DATA ===")

# Delete transactional and operational data
Payment.objects.all().delete()
print("Cleared Payments")
SupplierTruckPayment.objects.all().delete()
print("Cleared SupplierTruckPayment")

SalesOrderItem.objects.all().delete()
SalesOrder.objects.all().delete()
print("Cleared SalesOrder and Items")

PurchaseOrderItem.objects.all().delete()
PurchaseOrder.objects.all().delete()
print("Cleared PurchaseOrder and Items")

CustomerLedger.objects.all().delete()
SupplierLedger.objects.all().delete()
print("Cleared Ledgers")

InventoryLot.objects.all().delete()
InventoryTransaction.objects.all().delete()
print("Cleared Inventory Lots and Transactions")

ProductVariety.objects.all().delete()
Product.objects.all().delete()
print("Cleared Products and Varieties")

Customer.objects.all().delete()
print("Cleared Customers")

Supplier.objects.all().delete()
print("Cleared Suppliers")

from apps.core.models import AuditLog
AuditLog.objects.all().delete()
print("Cleared Audit Logs")

print("\n=== SETTING UP CLEAN MASTER ESSENTIALS ===")
# Ensure master categories & units exist so new entries have valid foreign keys
cat1, _ = Category.objects.get_or_create(name='Fresh Fruits')
cat2, _ = Category.objects.get_or_create(name='Dry Fruits & Nuts')
print(f"Categories ready: {cat1.name}, {cat2.name}")

u1, _ = Unit.objects.get_or_create(unit_name='Kilogram', defaults={'symbol': 'KG'})
u2, _ = Unit.objects.get_or_create(unit_name='Box', defaults={'symbol': 'BX'})
print(f"Units ready: {u1.unit_name}, {u2.unit_name}")

# Ensure admin user is active
admin_user, created = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True, 'first_name': 'Aziz', 'last_name': 'Admin'})
admin_pwd = os.getenv('ADMIN_PASSWORD')
if admin_pwd:
    admin_user.set_password(admin_pwd)
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.is_active = True
admin_user.save()

super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin', 'description': 'System Administrator'})
UserProfile.objects.get_or_create(user=admin_user, defaults={'role': super_role, 'phone': '9876543210'})
print(f"Admin user verified (active: {admin_user.is_active})")

print("\n=== VERIFYING FINAL COUNTS ===")
from django.apps import apps
for m in apps.get_models():
    if not m._meta.app_label.startswith('django') and m._meta.app_label not in ('auth', 'contenttypes', 'sessions', 'admin'):
        print(f"{m._meta.label}: {m.objects.count()}")
