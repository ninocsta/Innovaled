from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Contrato, Vendedor, Local, Cliente, StatusContrato, DocumentoContrato, Video
from .forms import ClienteForm, ContratoForm, DocumentoContratoForm, VideoFormSet, VideoForm
from django.contrib import messages
from django.shortcuts import redirect
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from django.db.models import Q, Count
from core.services import dashboard as dashboard_service


@login_required
def contrato_list(request):
    # 🔍 Filtros
    query_nome = request.GET.get("nome", "").strip()
    query_cnpj = request.GET.get("cnpj", "").strip()
    query_vendedor = request.GET.get("vendedor", "").strip()
    query_data_inicio = request.GET.get("data_inicio", "").strip()
    query_data_fim = request.GET.get("data_fim", "").strip()
    query_local = request.GET.get("local", "").strip()

    # 📄 Itens por página (com fallback seguro)
    try:
        itens_por_pagina = int(request.GET.get("itens", 10))
        if itens_por_pagina <= 0:
            itens_por_pagina = 10
    except ValueError:
        itens_por_pagina = 10

    # 🔄 Consulta principal
    contratos = (
        Contrato.objects
        .select_related("cliente", "vendedor", "status")   # FK/OneToOne
        .prefetch_related("videos__local")                 # ManyToMany / OneToMany
        .all()
    )

    # Aplicando filtros
    if query_nome:
        contratos = contratos.filter(cliente__razao_social__icontains=query_nome)
    if query_cnpj:
        contratos = contratos.filter(cliente__cpf_cnpj__icontains=query_cnpj)
    if query_vendedor:
        contratos = contratos.filter(vendedor_id=query_vendedor)
    if query_local:
        contratos = contratos.filter(videos__local_id=query_local).distinct()

    # Datas com validação
    if query_data_inicio:
        try:
            data_inicio = datetime.strptime(query_data_inicio, "%Y-%m-%d").date()
            contratos = contratos.filter(data_assinatura__gte=data_inicio)
        except ValueError:
            pass
    if query_data_fim:
        try:
            data_fim = datetime.strptime(query_data_fim, "%Y-%m-%d").date()
            contratos = contratos.filter(data_assinatura__lte=data_fim)
        except ValueError:
            pass

    # 🔄 Paginação
    paginator = Paginator(contratos, itens_por_pagina)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 🔗 Preservando querystring (sem o parâmetro "page")
    params = request.GET.copy()
    params.pop("page", None)
    extra_query = "&" + params.urlencode() if params else ""

    context = {
        "page_obj": page_obj,
        "query_nome": query_nome,
        "query_cnpj": query_cnpj,
        "query_vendedor": query_vendedor,
        "query_data_inicio": query_data_inicio,
        "query_data_fim": query_data_fim,
        "query_local": query_local,
        "itens_por_pagina": itens_por_pagina,
        "vendedores": Vendedor.objects.all(),
        "locais": Local.objects.all(),
        "extra_query": extra_query,
    }
    return render(request, "contratos/contratos.html", context)

@login_required
def contrato_create(request):
    cliente_existente = None
    data_ultima_parcela = None

    if request.method == "POST":
        cliente_form = ClienteForm(request.POST)
        contrato_form = ContratoForm(request.POST)
        documento_form = DocumentoContratoForm(request.POST, request.FILES)
        video_formset = VideoFormSet(request.POST, prefix='video')

        if (
            cliente_form.is_valid()
            and contrato_form.is_valid()
            and documento_form.is_valid()
            and video_formset.is_valid()
        ):
            # 🔎 Verifica se já existe cliente com o mesmo CPF/CNPJ
            cpf_cnpj = cliente_form.cleaned_data.get("cpf_cnpj")
            cliente = Cliente.objects.filter(cpf_cnpj=cpf_cnpj).first()

            if cliente:
                cliente_existente = cliente
                messages.info(
                    request,
                    f"⚠ Cliente {cliente.razao_social} ({cliente.cpf_cnpj}) já existe e será reutilizado.",
                )
            else:
                cliente = cliente_form.save(commit=False)
                cliente.created_by = request.user
                cliente.updated_by = request.user
                cliente.save()

            # Criar contrato
            contrato = contrato_form.save(commit=False)
            contrato.cliente = cliente
            contrato.created_by = request.user
            contrato.updated_by = request.user


            if contrato.data_vencimento_primeira_parcela:
                contrato.data_ultima_parcela = (
                    contrato.data_vencimento_primeira_parcela
                    + relativedelta(months=contrato.vigencia_meses - 1)
                )

            status_ativo, _ = StatusContrato.objects.get_or_create(
                nome_status="Ativo",
                defaults={"created_by": request.user, "updated_by": request.user},
            )
            contrato.status = status_ativo
            contrato.save()

            # Salvar vídeos vinculados
            video_formset.instance = contrato
            videos = video_formset.save(commit=False)
            for video in videos:
                video.contrato = contrato
                video.created_by = request.user
                video.updated_by = request.user
                video.save()
            video_formset.save()  # processa deletes

            # Salvar documento
            if documento_form.cleaned_data.get("arquivo"):
                documento = documento_form.save(commit=False)
                documento.contrato = contrato
                documento.created_by = request.user
                documento.updated_by = request.user
                documento.save()

            messages.success(request, "✅ Contrato criado com sucesso!")
            return redirect("contrato_detail", pk=contrato.pk)

        else:
            # ⚡ Mantém os valores calculados mesmo em caso de erro
            try:
                vigencia = int(request.POST.get("vigencia_meses", 0))
                mensalidade = float(request.POST.get("valor_mensalidade", 0))     
            except (ValueError, TypeError):
                vigencia = 0
                

            try:
                data_inicial = request.POST.get("data_vencimento_primeira_parcela")
                if data_inicial and vigencia:
                    data_inicial = datetime.strptime(data_inicial, "%Y-%m-%d").date()
                    data_ultima_parcela = data_inicial + relativedelta(
                        months=vigencia - 1
                    )
            except Exception:
                data_ultima_parcela = None

            # Mensagens de erro detalhadas
            for form_name, form in [
                ("Cliente", cliente_form),
                ("Contrato", contrato_form),
                ("Documento", documento_form),
            ]:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form_name} - {field}: {error}")

            for i, form in enumerate(video_formset.forms):
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(
                            request, f"Vídeo #{i+1} - {field}: {error}"
                        )

    else:
        cliente_form = ClienteForm()
        contrato_form = ContratoForm(
            initial={"data_assinatura": timezone.now().date()}
        )
        documento_form = DocumentoContratoForm()
        video_formset = VideoFormSet(prefix='video')

    return render(
        request,
        "contratos/contrato_form.html",
        {
            "cliente_form": cliente_form,
            "contrato_form": contrato_form,
            "documento_form": documento_form,
            "video_formset": video_formset,
            "cliente_existente": cliente_existente,
            "data_ultima_parcela": data_ultima_parcela,
        },
    )


@login_required
def contrato_detail(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    documentos = contrato.documentos.all()
    videos = contrato.videos.all()
    locais = Local.objects.all()  # Para popular o select no modal

    # Preparar vídeos pendentes e ativos
    videos_pendentes = videos.filter(status=False)
    videos_ativos = videos.filter(status=True)

    # Flags para pendências
    tem_video_pendente = videos_pendentes.exists()
    tem_pagamento_pendente = not contrato.primeiro_pagamento or not contrato.segundo_pagamento

    if request.method == "POST":
        form = DocumentoContratoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.contrato = contrato
            documento.save()
            messages.success(request, "📂 Documento anexado com sucesso!")
            return redirect("contrato_detail", pk=contrato.pk)
    else:
        form = DocumentoContratoForm()

    return render(request, "contratos/contrato_detail.html", {
        "contrato": contrato,
        "documentos": documentos,
        "documento_form": form,
        "videos": videos,
        "videos_pendentes": videos_pendentes,
        "videos_ativos": videos_ativos,
        "tem_video_pendente": tem_video_pendente,
        "tem_pagamento_pendente": tem_pagamento_pendente,
        "locais": locais,
    })



@login_required
def pendencias_video(request):
    # Filtra contratos que têm pelo menos um vídeo OFF
    # e que já possuem primeiro_pagamento
    contratos = (
        Contrato.objects.annotate(
            videos_pendentes=Count("videos", filter=Q(videos__status=False))
        )
        .filter(videos_pendentes__gt=0, primeiro_pagamento__isnull=False)
        .select_related("cliente")
        .prefetch_related("videos")  # otimiza query dos vídeos
    )

    return render(request, "pendencias/pendencias_video.html", {"contratos": contratos})


# Tela de pendências de pagamento
@login_required
def pendencias_pagamento(request):
    contratos = Contrato.objects.filter(
        Q(primeiro_pagamento__isnull=True) | Q(segundo_pagamento__isnull=True)
    ).select_related("cliente")

    return render(request, "pendencias/pendencias_pagamento.html", {"contratos": contratos})



@login_required
def marcar_pagamento(request, contrato_id, parcela):
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    if request.method == "POST":
        data = request.POST.get("data_pagamento")
        if data:
            data_pagto = datetime.strptime(data, "%Y-%m-%d").date()
        else:
            data_pagto = timezone.now().date()

        if parcela == 1:
            contrato.primeiro_pagamento = data_pagto
        elif parcela == 2:
            contrato.segundo_pagamento = data_pagto

        contrato.save()
        messages.success(
            request,
            f"{'Primeiro' if parcela==1 else 'Segundo'} pagamento do contrato {contrato.id_contrato:05d} registrado em {data_pagto}."
        )

        # Redirecionamento inteligente
        next_page = request.POST.get("from_detail")
        if next_page:
            return redirect("contrato_detail", contrato.pk)
        return redirect("pendencias_pagamento")

    return redirect("pendencias_pagamento")



@login_required
def ativar_video(request, video_id):
    video = get_object_or_404(Video, pk=video_id)

    if request.method == "POST":
        data_subiu_str = request.POST.get("data_subiu")
        if data_subiu_str:
            try:
                video.data_subiu = datetime.strptime(data_subiu_str, "%Y-%m-%d").date()
            except ValueError:
                video.data_subiu = timezone.now().date()
        else:
            video.data_subiu = timezone.now().date()

        video.status = True
        video.save()
        messages.success(request, f"🎬 Vídeo {video.id} ativado com sucesso!")

        # Redirecionamento inteligente
        from_detail = request.POST.get("from_detail")
        if from_detail:
            return redirect("contrato_detail", pk=video.contrato.pk)

    return redirect("pendencias_video")




@login_required
def documento_delete(request, pk):
    documento = get_object_or_404(DocumentoContrato, pk=pk)
    contrato_id = documento.contrato.id_contrato
    if request.method == "POST":
        documento.delete()
        messages.success(request, "Documento excluído com sucesso!")
    return redirect("contrato_detail", pk=contrato_id)


@login_required
def video_create_modal(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    if request.method == "POST":
        tempo_segundos = int(request.POST.get("tempo_video", 0))
        local_id = request.POST.get("local")

        if tempo_segundos > 0 and local_id:
            local = get_object_or_404(Local, pk=local_id)
            video = Video.objects.create(
                contrato=contrato,
                tempo_video=timedelta(seconds=tempo_segundos),
                local=local,
                created_by=request.user,
                updated_by=request.user
            )
            messages.success(request, "🎬 Vídeo adicionado com sucesso!")
        else:
            messages.error(request, "❌ Preencha todos os campos corretamente.")

    return redirect("contrato_detail", pk=contrato.pk)


@login_required
def contratos_vencendo(request):
    hoje = timezone.now().date()
    # Pega contratos que têm data de vencimento e ainda não foram cancelados
    contratos = (
        Contrato.objects.filter(
            data_vencimento_contrato__isnull=False,
            data_cancelamento_contrato__isnull=True,
        )
        .order_by("data_vencimento_contrato")
    )
    return render(request, "contratos/contratos_vencendo.html", {"contratos": contratos, "hoje": hoje})


@login_required
def renovar_contrato(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)

    if contrato.data_vencimento_contrato:
        contrato.data_vencimento_contrato += relativedelta(months=1)
        contrato.save()
        messages.success(
            request,
            f"📅 Contrato #{contrato.id_contrato} renovado por mais 30 dias (novo vencimento: {contrato.data_vencimento_contrato.strftime('%d/%m/%Y')}).",
        )
    else:
        messages.warning(request, f"⚠ O contrato #{contrato.id_contrato} não possui data de vencimento definida.")

    return redirect("contratos_vencendo")


@login_required
def dashboard_view(request):
    vendedor_id = request.GET.get("vendedor")  # filtro opcional por vendedor
    mes = request.GET.get("mes")  # filtro opcional por mês (formato YYYY-MM)
    print(mes)
    if mes == None or mes == "":
        mes = datetime.now().strftime("%Y-%m")  # padrão para mês atual


    data = dashboard_service.get_dashboard_data(vendedor_id, mes)

    return render(request, "dashboard.html", {
        "data": data,
        "vendedores": data["vendedores"],  # lista de vendedores p/ select
        "selected_vendedor": vendedor_id,
        "selected_mes": mes,
    })