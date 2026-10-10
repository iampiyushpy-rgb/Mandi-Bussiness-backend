from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Category, Unit, Product, ProductVariety
from .serializers import (
    CategorySerializer, UnitSerializer,
    ProductSerializer, ProductVarietySerializer
)
from apps.accounts.permissions import CanManageInventory

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('-id')
    serializer_class = CategorySerializer
    permission_classes = [CanManageInventory]

class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all().order_by('-id')
    serializer_class = UnitSerializer
    permission_classes = [CanManageInventory]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'default_unit').prefetch_related('varieties').order_by('-id')
    serializer_class = ProductSerializer
    permission_classes = [CanManageInventory]

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        has_lots = hasattr(product, 'inventory_lots') and product.inventory_lots.exists()
        if has_lots:
            product.is_active = False
            product.save()
            return Response(
                {'detail': 'Product is associated with existing inventory lots. Marked INACTIVE instead of deleting.'},
                status=status.HTTP_200_OK
            )
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        category_id = data.get('category')
        if not category_id or not Category.objects.filter(id=category_id).exists():
            cat = Category.objects.first()
            if not cat:
                cat = Category.objects.create(name='Fresh Fruits')
            data['category'] = cat.id

        if not data.get('product_code') or Product.objects.filter(product_code=data.get('product_code')).exists():
            count = Product.objects.count() + 1
            code = f"PROD-{count:04d}"
            while Product.objects.filter(product_code=code).exists():
                count += 1
                code = f"PROD-{count:04d}"
            data['product_code'] = code

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ProductVarietyViewSet(viewsets.ModelViewSet):
    queryset = ProductVariety.objects.all().select_related('product', 'product__category').order_by('-id')
    serializer_class = ProductVarietySerializer
    permission_classes = [CanManageInventory]

    def destroy(self, request, *args, **kwargs):
        variety = self.get_object()
        has_lots = hasattr(variety, 'inventory_lots') and variety.inventory_lots.exists()
        if has_lots:
            variety.is_active = False
            variety.save()
            return Response(
                {'detail': 'Variety is associated with existing inventory lots. Marked INACTIVE instead of deleting.'},
                status=status.HTTP_200_OK
            )
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        product_id = data.get('product')
        if not product_id or not Product.objects.filter(id=product_id).exists():
            prod = Product.objects.first()
            if not prod:
                cat = Category.objects.first() or Category.objects.create(name='Fresh Fruits')
                prod = Product.objects.create(category=cat, name='General Fruit', product_code='PROD-GEN-01')
            data['product'] = prod.id

        existing = ProductVariety.objects.filter(product_id=data['product'], variety_name__iexact=data.get('variety_name', '')).first()
        if existing:
            return Response(ProductVarietySerializer(existing).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
