from django.urls import path
from . import views
app_name = 'sales'
urlpatterns = [
    path('pos/', views.pos, name='pos'),
    path('create/', views.sale_create, name='create'),
    path('create-from-rx/<int:prescription_id>/', views.create_from_prescription, name='create_from_rx'),
    path('history/', views.sale_history, name='history'),
    path('<int:pk>/', views.sale_detail, name='detail'),
    path('<int:pk>/receipt/', views.receipt, name='receipt'),
    path('<int:pk>/receipt/print/', views.print_receipt, name='print_receipt'),
    path('<int:pk>/receipt/email/', views.email_receipt, name='email_receipt'),
    path('api/search-drugs/', views.api_search_drugs, name='api_search_drugs'),
    path('api/calculate-total/', views.api_calculate_total, name='api_calculate_total'),
]