import datetime
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from core.models import Contrato, Vendedor, FormaPagamento


def get_dashboard_data(vendedor_id=None, mes=None):
    qs = Contrato.objects.all()

    # expressão para calcular valor_total (mensalidade * vigência)
    valor_total_expr = ExpressionWrapper(
        F("valor_mensalidade") * F("vigencia_meses"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    # filtro por vendedor
    if vendedor_id:
        qs = qs.filter(vendedor_id=vendedor_id)

    # filtro por mês (baseado em data de assinatura)
    if mes:
        ano, mes_num = map(int, mes.split("-"))
        qs = qs.filter(data_assinatura__year=ano, data_assinatura__month=mes_num)

    # aplicar o valor_total no queryset filtrado
    qs = qs.annotate(valor_total=valor_total_expr)

    # contratos vendidos
    contratos_vendidos = qs.count()

    # faturamento total
    faturamento = qs.aggregate(total=Sum("valor_total"))["total"] or 0

    # ticket médio
    ticket_medio = qs.aggregate(avg=Avg("valor_total"))["avg"] or 0

    # métodos de pagamento
    metodos_pagamento = (
        qs.values("forma_pagamento__nome")
        .annotate(total=Count("id_contrato"))
        .order_by("-total")
    )

    # faturamento últimos 6 meses (independente do filtro acima, mas sempre pela data de assinatura)
    hoje = datetime.date.today()
    seis_meses_atras = hoje - datetime.timedelta(days=180)

    faturamento_por_mes = (
        Contrato.objects.filter(data_assinatura__gte=seis_meses_atras)
        .annotate(valor_total=valor_total_expr)
        .values("data_assinatura__year", "data_assinatura__month")
        .annotate(total=Sum("valor_total"))
        .order_by("data_assinatura__year", "data_assinatura__month")
    )

    # vendedores para o filtro
    vendedores = Vendedor.objects.all()

    return {
        "contratos_vendidos": contratos_vendidos,
        "faturamento": faturamento,
        "ticket_medio": ticket_medio,
        "metodos_pagamento": list(metodos_pagamento),
        "faturamento_por_mes": list(faturamento_por_mes),
        "vendedores": vendedores,
    }