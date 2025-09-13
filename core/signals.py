from .models import Video, Contrato
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta


@receiver(post_save, sender=Video)
def update_contrato_vencimento(sender, instance, **kwargs):
    print("Sinal recebido para Video salvo:", instance)
    if instance.status:  # Se o vídeo foi ativado
        contrato = instance.contrato
        print("Verificando contrato:", contrato)
        if not contrato.data_vencimento_contrato:  # Se a data de vencimento ainda não estiver definida
            # Calcula a nova data de vencimento com base na data do vídeo
            print("Atualizando data de vencimento do contrato...")
            nova_data_vencimento = instance.data_subiu + timedelta(days=contrato.vigencia_meses * 30)
            contrato.data_vencimento_contrato = nova_data_vencimento
            print("Nova data de vencimento definida para:", nova_data_vencimento)
            contrato.save()