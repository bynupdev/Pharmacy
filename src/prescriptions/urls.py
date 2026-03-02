from django.urls import path
from . import views
app_name = 'prescriptions'
urlpatterns = [
    path('', views.prescription_list, name='list'),
    path('create/', views.prescription_create, name='create'),
    path('<int:pk>/', views.prescription_detail, name='detail'),
    path('<int:pk>/edit/', views.prescription_edit, name='edit'),
    path('<int:pk>/verify/', views.prescription_verify, name='verify'),
    path('<int:pk>/dispense/', views.prescription_dispense, name='dispense'),
    path('<int:pk>/cancel/', views.prescription_cancel, name='cancel'),
    path('<int:pk>/print/', views.prescription_print, name='print'),
    path('api/check-interactions/', views.check_interactions_api, name='check_interactions'),
    path('api/override/<int:interaction_id>/', views.override_interaction, name='override_interaction'),
    path('interaction-logs/', views.interaction_logs, name='interaction_logs'),
    path('debug-api/', views.debug_api, name='debug_api'),
    ]