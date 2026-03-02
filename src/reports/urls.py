from django.urls import path
from . import views
app_name = 'reports'
urlpatterns = [
    path('', views.report_dashboard, name='dashboard'),
    path('inventory/', views.inventory_report, name='inventory'),
    path('sales/', views.sales_report, name='sales'),
    path('expiry/', views.expiry_report, name='expiry'),
    path('low-stock/', views.low_stock_report, name='low_stock'),
    path('interactions/', views.interaction_report, name='interactions'),
    path('export/<str:report_type>/', views.export_report, name='export'),
]