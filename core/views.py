from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Contrato, Vendedor, Local, Cliente, StatusContrato
from .forms import ClienteForm, ContratoForm, VideoForm, PagamentoForm
from django.contrib import messages
from django.shortcuts import redirect
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import get_object_or_404


@login_required
def contrato_list(request):
    query_nome = request.GET.get("nome", "")
    query_cnpj = request.GET.get("cnpj", "")
    query_vendedor = request.GET.get("vendedor", "")
    query_data_inicio = request.GET.get("data_inicio", "")
    query_data_fim = request.GET.get("data_fim", "")
    query_local = request.GET.get("local", "")
    itens_por_pagina = request.GET.get("itens", 10)

    contratos = Contrato.objects.select_related("cliente", "vendedor", "status", "video__local").all()

    if query_nome:
        contratos = contratos.filter(cliente__razao_social__icontains=query_nome)
    if query_cnpj:
        contratos = contratos.filter(cliente__cpf_cnpj__icontains=query_cnpj)
    if query_vendedor:
        contratos = contratos.filter(vendedor_id=query_vendedor)
    if query_data_inicio:
        contratos = contratos.filter(data_assinatura__gte=query_data_inicio)
    if query_data_fim:
        contratos = contratos.filter(data_assinatura__lte=query_data_fim)
    if query_local:
        contratos = contratos.filter(video__local_id=query_local)

    paginator = Paginator(contratos, itens_por_pagina)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    vendedores = Vendedor.objects.all()
    locais = Local.objects.all()

    # Criando query extra (sem o parâmetro page)
    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    extra_query = "&" + params.urlencode() if params else ""

    context = {
        "page_obj": page_obj,
        "query_nome": query_nome,
        "query_cnpj": query_cnpj,
        "query_vendedor": query_vendedor,
        "query_data_inicio": query_data_inicio,
        "query_data_fim": query_data_fim,
        "query_local": query_local,
        "itens_por_pagina": int(itens_por_pagina),
        "vendedores": vendedores,
        "locais": locais,
        "extra_query": extra_query,
    }
    return render(request, "contratos.html", context)


@login_required
def contrato_create(request):
    cliente_existente = None

    if request.method == "POST":
        cliente_form = ClienteForm(request.POST)
        contrato_form = ContratoForm(request.POST)
        video_form = VideoForm(request.POST)

        # Verificar se todos os formulários são válidos
        if cliente_form.is_valid() and contrato_form.is_valid() and video_form.is_valid():
            # Verificar se o cliente já existe
            cpf_cnpj = cliente_form.cleaned_data.get("cpf_cnpj")
            cliente_existente = Cliente.objects.filter(cpf_cnpj=cpf_cnpj).first()

            if cliente_existente:
                cliente = cliente_existente
            else:
                cliente = cliente_form.save(commit=False)
                cliente.created_by = request.user
                cliente.updated_by = request.user
                cliente.save()

            # Criar vídeo
            video = video_form.save(commit=False)
            video.created_by = request.user
            video.updated_by = request.user
            video.save()

            # Criar contrato
            contrato = contrato_form.save(commit=False)
            contrato.cliente = cliente
            contrato.video = video
            contrato.created_by = request.user
            contrato.updated_by = request.user

            # Calcular valor total
            contrato.valor_total = contrato.valor_mensalidade * contrato.vigencia_meses

            # Calcular data de vencimento do contrato
            contrato.data_vencimento_contrato = contrato.data_assinatura + relativedelta(
                months=contrato.vigencia_meses - 1
            )

            # Calcular última parcela, se primeira foi informada
            if contrato.data_vencimento_primeira_parcela:
                contrato.data_ultima_parcela = contrato.data_vencimento_primeira_parcela + relativedelta(
                    months=contrato.vigencia_meses - 1
                )

            # Definir status padrão como "Ativo"
            status_ativo, _ = StatusContrato.objects.get_or_create(
                nome_status="Ativo",
                defaults={'created_by': request.user, 'updated_by': request.user}
            )
            contrato.status = status_ativo
            contrato.save()

            messages.success(request, "Contrato criado com sucesso!")
            return redirect("contratos_list")

        else:
            # Adicionar mensagens de erro específicas para cada formulário
            for field, errors in cliente_form.errors.items():
                for error in errors:
                    messages.error(request, f"Cliente - {field}: {error}")
            for field, errors in contrato_form.errors.items():
                for error in errors:
                    messages.error(request, f"Contrato - {field}: {error}")
            for field, errors in video_form.errors.items():
                for error in errors:
                    messages.error(request, f"Vídeo - {field}: {error}")

    else:
        cliente_form = ClienteForm()
        contrato_form = ContratoForm(initial={'data_assinatura': timezone.now().date()})
        video_form = VideoForm()

    return render(
        request,
        "contrato_form.html",  # Ajustado para o caminho correto
        {
            "cliente_form": cliente_form,
            "contrato_form": contrato_form,
            "video_form": video_form,
            "cliente_existente": cliente_existente,
        },
    )

@login_required
def contrato_detail(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    cliente = contrato.cliente
    video = contrato.video
    registros = contrato.registro_set.all().order_by("-data_hora")  # histórico de registros

    return render(
        request,
        "contrato_detail.html",
        {
            "contrato": contrato,
            "cliente": cliente,
            "video": video,
            "registros": registros,
        },
    )


# Tela de pendências de vídeo
def pendencias_video(request):
    contratos = Contrato.objects.filter(
        primeiro_pagamento__isnull=False,
        video__status=False
    ).select_related("cliente", "video")
    return render(request, "pendencias_video.html", {"contratos": contratos})


# Tela de pendências de pagamento
def pendencias_pagamento(request):
    contratos = Contrato.objects.filter(
        # pelo menos uma parcela pendente
    ).select_related("cliente", "video")
    pendentes = []
    for c in contratos:
        if not c.primeiro_pagamento or not c.segundo_pagamento:
            pendentes.append(c)
    return render(request, "pendencias_pagamento.html", {"contratos": pendentes})


def marcar_pagamento(request, contrato_id, parcela):
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    if request.method == "POST":
        data = request.POST.get("data_pagamento")
        if data:
            data_pagto = data  # string YYYY-MM-DD
        else:
            data_pagto = timezone.now().date()

        if parcela == 1:
            contrato.primeiro_pagamento = data_pagto
            contrato.save()
            messages.success(request, f"Primeiro pagamento do contrato {contrato.id_contrato:05d} registrado em {data_pagto}.")
        elif parcela == 2:
            contrato.segundo_pagamento = data_pagto
            contrato.save()
            messages.success(request, f"Segundo pagamento do contrato {contrato.id_contrato:05d} registrado em {data_pagto}.")
        
        # Decide se volta para lista de pendências ou detail
        if "from_detail" in request.POST:
            return redirect("contrato_detail", contrato_id=contrato.id_contrato)
        return redirect("pendencias_pagamento")

    # Se não for POST, redireciona
    return redirect("pendencias_pagamento")


def ativar_video(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.video:
        contrato.video.status = True
        contrato.video.save()
        messages.success(request, f"Vídeo do contrato {contrato.id_contrato:05d} ativado com sucesso!")
    if request.POST.get("from_detail"):
        return redirect("contrato_detail", contrato_id=contrato.id_contrato)
    return redirect("pendencias_video")