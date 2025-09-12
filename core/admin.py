from django.contrib import admin
from .models import Contrato, Cliente, Banco, Vendedor, Video, Local, FormaPagamento, StatusContrato, Registro


class BaseAuditAdmin(admin.ModelAdmin):
    """
    Classe base que cuida de created_by e updated_by automaticamente no Admin
    """
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # objeto novo
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Contrato)
class ContratoAdmin(BaseAuditAdmin):
    list_display = ("id_formatado", "cliente", "valor_mensalidade", "valor_total", "status", "data_assinatura")
    list_filter = ("status", "forma_pagamento", "banco", "vendedor", "data_assinatura")
    search_fields = ("cliente__razao_social", "cliente__cpf_cnpj")
    ordering = ("-data_assinatura",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def id_formatado(self, obj):
        return f"{obj.id_contrato:05d}"
    id_formatado.short_description = "ID"


@admin.register(Cliente)
class ClienteAdmin(BaseAuditAdmin):
    list_display = ("razao_social", "cpf_cnpj", "email", "telefone")
    search_fields = ("razao_social", "cpf_cnpj")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Banco)
class BancoAdmin(BaseAuditAdmin):
    list_display = ("nome",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Vendedor)
class VendedorAdmin(BaseAuditAdmin):
    list_display = ("nome",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Video)
class VideoAdmin(BaseAuditAdmin):
    list_display = ("id", "tempo_video", "local", "status")
    list_filter = ("status", "local")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Local)
class LocalAdmin(BaseAuditAdmin):
    list_display = ("nome",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(BaseAuditAdmin):
    list_display = ("nome",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(StatusContrato)
class StatusContratoAdmin(BaseAuditAdmin):
    list_display = ("nome_status",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Registro)
class RegistroAdmin(BaseAuditAdmin):
    list_display = ("contrato", "data_hora", "observacao")
    list_filter = ("data_hora",)
    search_fields = ("contrato__id_contrato", "observacao")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")