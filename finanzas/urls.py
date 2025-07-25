from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transacciones/', views.lista_transacciones, name='lista_transacciones'),
    path('transacciones/nueva/', views.nueva_transaccion, name='nueva_transaccion'),
    path('transacciones/<int:id>/eliminar/', views.eliminar_transaccion, name='eliminar_transaccion'),
    path('transacciones/descargar/', views.descargar_transacciones, name='descargar_transacciones'),
    path('transacciones/descargar-pdf/', views.descargar_transacciones_pdf, name='descargar_transacciones_pdf'),
    path('objetivos/', views.lista_objetivos, name='lista_objetivos'),
    path('objetivos/nuevo/', views.nuevo_objetivo, name='nuevo_objetivo'),
    path('objetivos/<int:objetivo_id>/editar/', views.editar_objetivo, name='editar_objetivo'),
    path('objetivos/<int:objetivo_id>/añadir-dinero/', views.añadir_dinero_objetivo, name='añadir_dinero_objetivo'),
    path('objetivos/<int:objetivo_id>/eliminar-dinero/', views.eliminar_dinero_objetivo, name='eliminar_dinero_objetivo'),
    path('objetivos/<int:objetivo_id>/eliminar-objetivo/', views.eliminar_objetivo, name='eliminar_objetivo'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('presupuesto/', views.establecer_presupuesto, name='establecer_presupuesto'),
    path('establecer-balance-inicial/', views.establecer_balance_inicial, name='establecer_balance_inicial'),
    path('recurrentes/eliminar/<int:serie_id>/', views.eliminar_recurrente, name='eliminar_recurrente'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='finanzas/password_reset_form.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='finanzas/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='finanzas/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='finanzas/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('enviar-transacciones-mes/', views.enviar_transacciones_mes, name='enviar_transacciones_mes'),
    path('generar-recomendaciones/', views.generar_recomendaciones, name='generar_recomendaciones'),
]