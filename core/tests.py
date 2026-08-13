import datetime

from django.test import TestCase

from .models import Cliente, Contrato, Parcela, gerar_parcelas, renovar_parcelas


class ParcelaTests(TestCase):
    def setUp(self):
        cliente = Cliente.objects.create(razao_social="TESTE", cpf_cnpj="123", email="t@t.com")
        self.contrato = Contrato.objects.create(
            cliente=cliente,
            valor_mensalidade=100,
            vigencia_meses=12,
            data_assinatura=datetime.date(2026, 1, 10),
            data_vencimento_primeira_parcela=datetime.date(2026, 1, 31),
            data_vencimento_contrato=datetime.date(2026, 12, 31),
        )

    def test_gera_uma_parcela_por_mes_de_vigencia(self):
        gerar_parcelas(self.contrato, datetime.date(2026, 1, 31), self.contrato.vigencia_meses)
        parcelas = list(self.contrato.parcelas.all())

        assert len(parcelas) == 12, len(parcelas)
        assert parcelas[0].vencimento == datetime.date(2026, 1, 31)
        # fim de mês curto não pode estourar para março
        assert parcelas[1].vencimento == datetime.date(2026, 2, 28)
        assert parcelas[11].vencimento == datetime.date(2026, 12, 31)

    def test_renovacao_continua_do_ultimo_vencimento(self):
        gerar_parcelas(self.contrato, datetime.date(2026, 1, 31), 12)

        _, ciclo = renovar_parcelas(self.contrato, 6)
        self.contrato.save()

        novas = self.contrato.parcelas.filter(ciclo=2).order_by("numero")
        assert ciclo == 2
        assert novas.count() == 6
        assert novas.first().vencimento == datetime.date(2027, 1, 31)
        assert self.contrato.data_ultima_parcela == datetime.date(2027, 6, 30)
        # vencimento do contrato acompanha a renovação
        assert self.contrato.data_vencimento_contrato == datetime.date(2027, 6, 30)

    def test_situacao_derivada_da_data(self):
        hoje = datetime.date.today()
        paga = Parcela.objects.create(
            contrato=self.contrato, numero=1, vencimento=hoje - datetime.timedelta(days=30), pago_em=hoje
        )
        vencida = Parcela.objects.create(
            contrato=self.contrato, numero=2, vencimento=hoje - datetime.timedelta(days=1)
        )
        a_vencer = Parcela.objects.create(
            contrato=self.contrato, numero=3, vencimento=hoje + datetime.timedelta(days=1)
        )

        assert paga.situacao == "pago"
        assert vencida.situacao == "vencido"
        assert a_vencer.situacao == "a_vencer"
