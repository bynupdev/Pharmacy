from django.urls import path
from . import views
app_name = 'inventory'
urlpatterns = [
    path('', views.inventory_list, name='list'),
    path('add/', views.inventory_add, name='add'),
    path('<int:pk>/', views.inventory_detail, name='detail'),
    path('<int:pk>/edit/', views.inventory_edit, name='edit'),
    path('<int:pk>/delete/', views.inventory_delete, name='delete'),
    path('<int:pk>/add-batch/', views.add_batch, name='add_batch'),
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('alerts/', views.stock_alerts, name='stock_alerts'),
    path('alerts/<int:pk>/resolve/', views.resolve_alert, name='resolve_alert'),
    path('api/search/', views.api_search_drugs, name='api_search_drugs'),
    path('api/supplier/<int:supplier_id>/products/', views.api_supplier_products, name='api_supplier_products'),
]