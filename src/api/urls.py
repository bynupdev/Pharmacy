from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
app_name = 'api'
router = DefaultRouter()
router.register(r'drugs', views.DrugViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'sales', views.SaleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-interactions/', views.check_interactions, name='api_check_interactions'),
    path('dashboard/stats/', views.dashboard_stats, name='api_dashboard_stats'),
    path('search/drugs/', views.search_drugs, name='api_search_drugs'),
    path('search/patients/', views.search_patients, name='api_search_patients'),
]