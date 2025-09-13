from django import forms
from django.forms import inlineformset_factory
from .models import Cliente, Contrato, Video, Banco, Vendedor, Local, FormaPagamento, DocumentoContrato
import re


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["razao_social", "cpf_cnpj", "email", "telefone", "telefone_financeiro", "email_financeiro"]
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone_financeiro': forms.TextInput(attrs={'class': 'form-control'}),
            'email_financeiro': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_cpf_cnpj(self):
        cpf_cnpj = self.cleaned_data['cpf_cnpj']
        cpf_cnpj = re.sub(r'\D', '', cpf_cnpj)
        return cpf_cnpj
    
    def clean_telefone(self):
        if not self.cleaned_data.get('telefone'):
            return ''
        telefone = self.cleaned_data.get('telefone', '')
        telefone = re.sub(r'\D', '', telefone)
        return telefone
    
    def clean_telefone_financeiro(self):
        if not self.cleaned_data.get('telefone_financeiro'):
            return ''
        telefone_financeiro = self.cleaned_data.get('telefone_financeiro', '')
        telefone_financeiro = re.sub(r'\D', '', telefone_financeiro)
        return telefone_financeiro


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ["tempo_video", "local"]
        widgets = {
            'tempo_video': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 00:03:25'}),
            'local': forms.Select(attrs={'class': 'form-select'}),
        }
        
VideoFormSet = inlineformset_factory(
    Contrato,
    Video,
    form=VideoForm,
    extra=1,           # começa com 1 formulário vazio
    can_delete=True    # permite remover vídeos
)


class ContratoForm(forms.ModelForm):
    vendedor = forms.ModelChoiceField(
        queryset=Vendedor.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )
    banco = forms.ModelChoiceField(
        queryset=Banco.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.all(),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input', 'required': True})
    )

    class Meta:
        model = Contrato
        exclude = [
            'created_by', 'updated_by',
            'cliente', 'status', 'cobranca_gerada',
            'video', 'data_cancelamento_contrato'
        ]
        widgets = {
            'vigencia_meses': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'valor_mensalidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'primeiro_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'segundo_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_assinatura': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento_primeira_parcela': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_ultima_parcela': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'vigencia_meses': 'Vigência (em meses)',
            'valor_mensalidade': 'Valor da Mensalidade',
            'valor_total': 'Valor Total (calculado automaticamente)',
            'primeiro_pagamento': 'Primeiro Pagamento',
            'segundo_pagamento': 'Segundo Pagamento',
            'data_assinatura': 'Data da Assinatura',
            'data_vencimento_primeira_parcela': 'Vencimento da Primeira Parcela',
            'data_ultima_parcela': 'Data da Última Parcela',
            'observacoes': 'Observações',
        }


class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["primeiro_pagamento", "segundo_pagamento"]
        widgets = {
            "primeiro_pagamento": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "segundo_pagamento": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

class DocumentoContratoForm(forms.ModelForm):
    class Meta:
        model = DocumentoContrato
        fields = ["arquivo", "descricao"]
        widgets = {
            "arquivo": forms.FileInput(attrs={"class": "form-control"}),
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
        }