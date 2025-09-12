from django.urls import path
from . import views

urlpatterns = [
    path("contratos/novo/", views.contrato_create, name="contrato_create"),
    path("contratos/", views.contrato_list, name="contratos_list"),  # já existia
    path('', views.contrato_list, name='home'),  # Nova rota para a página inicial
]
