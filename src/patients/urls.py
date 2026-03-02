from django.urls import path
from . import views
app_name = 'patients'
urlpatterns = [
    path('', views.patient_list, name='list'),
    path('add/', views.patient_add, name='add'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/edit/', views.patient_edit, name='edit'),
    path('<int:pk>/delete/', views.patient_delete, name='delete'),
    path('<int:pk>/prescriptions/', views.patient_prescriptions, name='prescriptions'),
    path('<int:pk>/add-allergy/', views.add_allergy, name='add_allergy'),
    path('search/', views.patient_search, name='search'),
    path('api/search/', views.api_search_patients, name='api_search'),
]