# core/metrics.py (ou onde você tiver)
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from core.models import Contrato
from django.db.models import Count, Avg
from core.models import Vendedor
from datetime import datetime

def faturamento_ultimos_seis_meses(user, vendedor=None):
    hoje = date.today()

    # cria lista de meses: 6 meses (do mais antigo -> mais recente)
    months = []
    for i in range(5, -1, -1):  # 5,4,3,2,1,0
        dt = (hoje - relativedelta(months=i)).replace(day=1)
        months.append((dt.year, dt.month))

    valor_total_expr = ExpressionWrapper(
        F("valor_mensalidade") * F("vigencia_meses"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    resultados = []
    for ano, mes in months:
        contratos = Contrato.objects.filter(data_assinatura__year=ano, data_assinatura__month=mes)

        if vendedor:
            contratos = contratos.filter(vendedor=vendedor)

        total = contratos.aggregate(total=Sum(valor_total_expr))["total"] or Decimal("0")
        resultados.append({
            "ano": ano,
            "mes": mes,
            "faturamento_total": float(total)  # já converte pra float aqui
        })

    return resultados


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
    hoje = datetime.today()
    seis_meses_atras = hoje - relativedelta(months=6)
    faturamento_por_mes = []

    for i in range(6):
        # Ajuste para pegar a data correta do mês
        data_inicio = (hoje - relativedelta(months=i)).replace(day=1)
        mes = data_inicio.month
        ano = data_inicio.year
        # Filtragem por data e por tipo de usuário (vendedor, supervisor ou superusuário)
        contratos = Contrato.objects.filter(
            data_assinatura__month=mes,
            data_assinatura__year=ano
        )
        if vendedor_id:
            # Filtra os contratos do vendedor especificado
            contratos = contratos.filter(vendedor=vendedor_id)
        faturamento_total = contratos.aggregate(total=Sum(valor_total_expr))["total"] or 0

        faturamento_por_mes.append({
            'ano': ano,
            'mes': mes,
            'faturamento_total': faturamento_total
        })

    # vendedores para o filtro
    vendedores = Vendedor.objects.all()

    return {
        "contratos_vendidos": contratos_vendidos,
        "faturamento": faturamento,
        "ticket_medio": ticket_medio,
        "metodos_pagamento": list(metodos_pagamento),
        "vendedores": vendedores,
        "faturamento_por_mes": list(reversed(faturamento_por_mes)),  # do mais antigo para o mais recente
    }