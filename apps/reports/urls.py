from django.urls import path
from .views import (
    dashboard_summary,
    daily_sales_report,
    monthly_sales_report,
    inventory_summary_report,
    customer_outstanding_report,
    supplier_outstanding_report,
    profit_loss_report,
    daily_saved_reports_view
)

urlpatterns = [
    path('dashboard/', dashboard_summary, name='report_dashboard'),
    path('daily-sales/', daily_sales_report, name='report_daily_sales'),
    path('monthly-sales/', monthly_sales_report, name='report_monthly_sales'),
    path('inventory-summary/', inventory_summary_report, name='report_inventory_summary'),
    path('customer-outstanding/', customer_outstanding_report, name='report_customer_outstanding'),
    path('supplier-outstanding/', supplier_outstanding_report, name='report_supplier_outstanding'),
    path('profit-loss/', profit_loss_report, name='report_profit_loss'),
    path('saved-daily/', daily_saved_reports_view, name='report_saved_daily'),
]
