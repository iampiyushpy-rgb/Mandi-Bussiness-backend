import datetime
import json
import os
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from apps.sales.models import SalesOrder, SalesOrderItem
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.accounts.permissions import CanViewReports

@api_view(['GET'])
@permission_classes([CanViewReports])
def dashboard_summary(request):
    today = datetime.date.today()

    # Today's Purchases Aggregation
    today_pos = PurchaseOrder.objects.filter(purchase_date=today)
    po_agg = today_pos.aggregate(
        total_amt=Sum('grand_total'),
        boxes_in=Sum('items__quantity_boxes')
    )
    today_purchase_amt = po_agg['total_amt'] or Decimal('0')
    today_boxes_in = po_agg['boxes_in'] or 0

    # Today's Sales Aggregation
    today_sos = SalesOrder.objects.filter(order_date=today)
    so_agg = today_sos.aggregate(
        total_amt=Sum('grand_total'),
        boxes_sold=Sum('items__quantity_boxes')
    )
    today_sales_amt = so_agg['total_amt'] or Decimal('0')
    today_boxes_sold = so_agg['boxes_sold'] or 0
    today_weight_sold = Decimal('0')

    # Authoritative Stock from Active Inventory Lots
    stock_agg = InventoryLot.objects.filter(status='ACTIVE').aggregate(
        total_boxes=Sum('available_boxes'),
        total_weight=Sum('available_weight'),
        total_val=Sum(
            ExpressionWrapper(
                F('available_boxes') * F('landed_cost_per_box'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
        )
    )
    total_stock_boxes = stock_agg['total_boxes'] or 0
    total_stock_weight = stock_agg['total_weight'] or Decimal('0')
    total_stock_value = stock_agg['total_val'] or Decimal('0')

    # Wastage Aggregation
    wastage_agg = InventoryTransaction.objects.filter(transaction_type='WASTAGE').aggregate(
        boxes=Sum('quantity_boxes'),
        loss=Sum('total_cost')
    )
    wastage_boxes = abs(wastage_agg['boxes'] or 0)
    wastage_loss = wastage_agg['loss'] or Decimal('0')

    # Outstanding Balances
    cust_outstanding = Customer.objects.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
    supp_outstanding = Supplier.objects.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')

    # Top selling fruits
    top_items = (
        SalesOrderItem.objects.values('product__name')
        .annotate(total_boxes=Sum('quantity_boxes'), total_rev=Sum('line_total'))
        .order_by('-total_boxes')[:5]
    )
    top_fruits = [
        {'name': item['product__name'], 'boxes': item['total_boxes'] or 0, 'revenue': float(item['total_rev'] or 0)}
        for item in top_items
    ]

    # Recent Trucks from Supplier Truck Payments or Active Lots
    recent_lots = InventoryLot.objects.select_related('supplier', 'product').order_by('-purchase_date', '-id')[:6]
    truck_data = [
        {
            'id': lot.id,
            'truck_number': lot.truck_number or 'TRUCK-00',
            'party': lot.supplier.supplier_name if lot.supplier else 'Produce Transport',
            'slot': 'Produce Arrival',
            'status': lot.status,
            'net_weight': float(lot.available_weight),
            'purpose': f"{lot.product.name} ({lot.available_boxes}/{lot.received_boxes} boxes)"
        } for lot in recent_lots
    ]

    # 7-day trend
    chart_data = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.strftime('%d %b')
        s_val = SalesOrder.objects.filter(order_date=d).aggregate(s=Sum('grand_total'))['s'] or Decimal('0')
        p_val = PurchaseOrder.objects.filter(purchase_date=d).aggregate(p=Sum('grand_total'))['p'] or Decimal('0')
        chart_data.append({
            'date': d_str,
            'sales': float(s_val),
            'purchases': float(p_val)
        })

    return Response({
        'today_purchase': float(today_purchase_amt),
        'today_sales': float(today_sales_amt),
        'stock_value': float(total_stock_value),
        'boxes_in': today_boxes_in,
        'boxes_sold': today_boxes_sold,
        'weight_sold_kg': float(today_weight_sold),
        'wastage_boxes': wastage_boxes,
        'wastage_loss': float(wastage_loss),
        'customer_outstanding': float(cust_outstanding),
        'supplier_outstanding': float(supp_outstanding),
        'total_stock_boxes': total_stock_boxes,
        'total_stock_weight_kg': float(total_stock_weight),
        'top_fruits': top_fruits,
        'recent_trucks': truck_data,
        'trend_chart': chart_data
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def daily_sales_report(request):
    date_str = request.GET.get('date', str(datetime.date.today()))
    orders = SalesOrder.objects.filter(order_date=date_str)
    agg = orders.aggregate(
        total_orders=Count('id'),
        total_boxes=Sum('items__quantity_boxes'),
        gross_sales=Sum('subtotal'),
        net_sales=Sum('grand_total'),
        received=Sum('paid_amount'),
        outstanding=Sum('due_amount')
    )

    return Response({
        'date': date_str,
        'total_orders': agg['total_orders'] or 0,
        'total_boxes': agg['total_boxes'] or 0,
        'total_weight_kg': 0.0,
        'gross_sales': float(agg['gross_sales'] or 0),
        'discount': 0.0,
        'tax': 0.0,
        'net_sales': float(agg['net_sales'] or 0),
        'received': float(agg['received'] or 0),
        'outstanding': float(agg['outstanding'] or 0)
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def monthly_sales_report(request):
    year = int(request.GET.get('year', datetime.date.today().year))
    month = int(request.GET.get('month', datetime.date.today().month))

    orders = SalesOrder.objects.filter(order_date__year=year, order_date__month=month)
    agg = orders.aggregate(
        total_orders=Count('id'),
        total_boxes=Sum('items__quantity_boxes'),
        total_revenue=Sum('grand_total'),
        total_collected=Sum('paid_amount'),
        total_due=Sum('due_amount')
    )

    return Response({
        'year': year,
        'month': month,
        'total_orders': agg['total_orders'] or 0,
        'total_boxes': agg['total_boxes'] or 0,
        'total_revenue': float(agg['total_revenue'] or 0),
        'total_collected': float(agg['total_collected'] or 0),
        'total_due': float(agg['total_due'] or 0)
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def inventory_summary_report(request):
    lots = InventoryLot.objects.filter(status='ACTIVE').values(
        'product__name', 'variety__variety_name', 'warehouse_name'
    ).annotate(
        boxes=Sum('available_boxes'),
        weight=Sum('available_weight'),
        value=Sum(
            ExpressionWrapper(
                F('available_boxes') * F('landed_cost_per_box'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
        )
    ).order_by('product__name')

    return Response({
        'items': [
            {
                'fruit': l['product__name'],
                'variety': l['variety__variety_name'],
                'warehouse': l['warehouse_name'],
                'boxes': l['boxes'] or 0,
                'weight_kg': float(l['weight'] or 0),
                'value': float(l['value'] or 0)
            } for l in lots
        ]
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def customer_outstanding_report(request):
    customers = Customer.objects.filter(current_balance__gt=0).order_by('-current_balance')
    return Response({
        'total_outstanding': float(customers.aggregate(total=Sum('current_balance'))['total'] or 0),
        'customers': [
            {
                'id': c.id,
                'customer_code': c.customer_code,
                'customer_name': c.customer_name,
                'phone': c.phone,
                'balance': float(c.current_balance)
            } for c in customers
        ]
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def supplier_outstanding_report(request):
    suppliers = Supplier.objects.filter(current_balance__gt=0).order_by('-current_balance')
    return Response({
        'total_outstanding': float(suppliers.aggregate(total=Sum('current_balance'))['total'] or 0),
        'suppliers': [
            {
                'id': s.id,
                'supplier_code': s.supplier_code,
                'supplier_name': s.supplier_name,
                'phone': s.phone,
                'balance': float(s.current_balance)
            } for s in suppliers
        ]
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def profit_loss_report(request):
    # Total Revenue from sales
    sales_agg = SalesOrder.objects.exclude(status='CANCELLED').aggregate(
        revenue=Sum('grand_total'),
        sales_transport=Sum('transport_charge'),
        sales_loading=Sum('loading_charge')
    )
    total_revenue = sales_agg['revenue'] or Decimal('0')

    # COGS from sales issue inventory transactions
    sales_issue_agg = InventoryTransaction.objects.filter(
        transaction_type='SALES_ISSUE'
    ).aggregate(cogs=Sum('total_cost'))
    total_cogs = abs(sales_issue_agg['cogs'] or Decimal('0'))
    gross_profit = total_revenue - total_cogs

    # Real Operating Expenses from SupplierTruckPayment & Sales charges
    purchase_expenses_agg = SupplierTruckPayment.objects.aggregate(
        transport=Sum('transport_charge'),
        loading=Sum('loading_charge'),
        unloading=Sum('unloading_charge'),
        commission=Sum('commission_charge')
    )
    total_expenses = (
        (purchase_expenses_agg['transport'] or Decimal('0')) +
        (purchase_expenses_agg['loading'] or Decimal('0')) +
        (purchase_expenses_agg['unloading'] or Decimal('0')) +
        (purchase_expenses_agg['commission'] or Decimal('0')) +
        (sales_agg['sales_transport'] or Decimal('0')) +
        (sales_agg['sales_loading'] or Decimal('0'))
    )

    # Real Wastage Loss from Inventory transactions
    wastage_loss = InventoryTransaction.objects.filter(transaction_type='WASTAGE').aggregate(
        loss=Sum('total_cost')
    )['loss'] or Decimal('0')

    net_profit = gross_profit - total_expenses - wastage_loss

    return Response({
        'revenue': float(total_revenue),
        'cogs': float(total_cogs),
        'gross_profit': float(gross_profit),
        'expenses': float(total_expenses),
        'wastage_loss': float(wastage_loss),
        'net_profit': float(net_profit),
    })


REPORTS_FILE_PATH = os.path.join(settings.BASE_DIR, 'data', 'saved_daily_reports.json')

def _load_saved_reports():
    if not os.path.exists(REPORTS_FILE_PATH):
        return []
    try:
        with open(REPORTS_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def _save_saved_reports(reports_list):
    os.makedirs(os.path.dirname(REPORTS_FILE_PATH), exist_ok=True)
    with open(REPORTS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(reports_list, f, indent=2, ensure_ascii=False)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([CanViewReports])
def daily_saved_reports_view(request):
    """
    Endpoint to retrieve, save or delete daily closed financial reports with database persistence.
    """
    from .models import DailySavedReport

    if request.method == 'GET':
        db_records = DailySavedReport.objects.all().order_by('-report_date')
        if db_records.exists():
            return Response([r.report_data for r in db_records])

        # Seamless migration: if file has reports but DB is empty, backfill into DB
        file_reports = _load_saved_reports()
        for r in file_reports:
            r_date_str = str(r.get('date', '')).split('T')[0]
            if r_date_str:
                try:
                    d_parsed = datetime.datetime.strptime(r_date_str, '%Y-%m-%d').date()
                    DailySavedReport.objects.update_or_create(
                        report_date=d_parsed,
                        defaults={
                            'report_id': r.get('id') or f"RPT-{r_date_str}",
                            'saved_by': r.get('savedBy') or 'admin',
                            'is_locked': bool(r.get('isLocked', True)),
                            'report_data': r
                        }
                    )
                except Exception:
                    pass

        db_records_after = DailySavedReport.objects.all().order_by('-report_date')
        if db_records_after.exists():
            return Response([r.report_data for r in db_records_after])
        return Response(file_reports)

    elif request.method == 'POST':
        data = request.data
        if not data or not data.get('date'):
            return Response({'error': 'Report must include a date'}, status=status.HTTP_400_BAD_REQUEST)

        req_date_str = str(data.get('date')).split('T')[0]
        try:
            d_parsed = datetime.datetime.strptime(req_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format (must be YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        # Database persistence
        report_obj, _ = DailySavedReport.objects.update_or_create(
            report_date=d_parsed,
            defaults={
                'report_id': data.get('id') or f"RPT-{req_date_str}",
                'saved_by': data.get('savedBy') or (request.user.username if request.user.is_authenticated else 'admin'),
                'is_locked': bool(data.get('isLocked', True)),
                'report_data': data
            }
        )

        # File backup sync
        reports = _load_saved_reports()
        updated = [data] + [r for r in reports if str(r.get('date')).split('T')[0] != req_date_str]
        _save_saved_reports(updated)

        return Response({'status': 'saved', 'report': report_obj.report_data}, status=status.HTTP_201_CREATED)

    elif request.method == 'DELETE':
        target = request.GET.get('id') or request.GET.get('date')
        if not target:
            return Response({'error': 'Specify id or date to delete'}, status=status.HTTP_400_BAD_REQUEST)

        target_str = str(target).split('T')[0]
        DailySavedReport.objects.filter(Q(report_id=target) | Q(report_date=target_str)).delete()

        # File backup sync
        reports = _load_saved_reports()
        updated = [r for r in reports if r.get('id') != target and str(r.get('date')).split('T')[0] != target_str]
        _save_saved_reports(updated)

        return Response({'status': 'deleted'})


