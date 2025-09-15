from django.urls import path
from . import views

urlpatterns = [
    path("contratos/novo/", views.contrato_create, name="contrato_create"),
    path("contratos/", views.contrato_list, name="contratos_list"),
    path("contrato/<int:pk>/", views.contrato_detail, name="contrato_detail"),
    path("", views.contrato_list, name="home"),
    path("contratos/vencimentos/", views.contratos_vencendo, name="contratos_vencendo"),
    path("contratos/<int:pk>/renovar/", views.renovar_contrato, name="renovar_contrato"),

    # Pendências globais
    path("pendencias/video/", views.pendencias_video, name="pendencias_video"),
    path("pendencias/pagamento/", views.pendencias_pagamento, name="pendencias_pagamento"),

    # Ações
    path("contrato/<int:video_id>/ativar_video/", views.ativar_video, name="ativar_video"),
    path("contrato/<int:contrato_id>/marcar_pagamento/<int:parcela>/", views.marcar_pagamento, name="marcar_pagamento"),

    # Exclusão de documento
    path("documento/<int:pk>/delete/", views.documento_delete, name="documento_delete"),

    #video novo
    path("contrato/<int:contrato_id>/video/add/", views.video_create_modal, name="video_create_modal"),

    path("dashboard/", views.dashboard_view, name="dashboard"),

]
