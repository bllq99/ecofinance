from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transacciones/', views.lista_transacciones, name='lista_transacciones'),
    path('transacciones/nueva/', views.nueva_transaccion, name='nueva_transaccion'),
    path('objetivos/', views.lista_objetivos, name='lista_objetivos'),
    path('objetivos/nuevo/', views.nuevo_objetivo, name='nuevo_objetivo'),
    path('registro/', views.registro_view, name='registro'),
    path('presupuesto/', views.establecer_presupuesto, name='establecer_presupuesto'),
]
