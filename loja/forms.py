"""Formulários com validação no servidor (RNF02)."""
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS

from .models import Cliente, Pedido, Produto, somente_digitos


class BootstrapMixin:
    """Aplica as classes do Bootstrap e marca campos com erro (aria-invalid)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            classe = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
            campo.widget.attrs.setdefault("class", classe)
            if self.is_bound and nome in self.errors:
                campo.widget.attrs["class"] += " is-invalid"
                campo.widget.attrs["aria-invalid"] = "true"


class ProdutoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "categoria", "tamanho", "cor", "preco", "quantidade_estoque", "foto"]
        labels = {"preco": "Preço (R$)", "quantidade_estoque": "Quantidade em estoque"}
        error_messages = {
            NON_FIELD_ERRORS: {"unique_together": "Já existe uma peça com esse nome, tamanho e cor."}
        }
        widgets = {
            "preco": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal"}),
            "quantidade_estoque": forms.NumberInput(attrs={"min": "0", "inputmode": "numeric"}),
        }


class ClienteForm(BootstrapMixin, forms.ModelForm):
    # Aceita máscara na digitação, ex.: (11) 90000-0000; o servidor guarda só os dígitos.
    telefone = forms.CharField(
        label="Telefone",
        max_length=20,
        help_text="Com DDD. Pode digitar com ou sem parênteses e traço.",
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "(11) 90000-0000"}
        ),
    )

    class Meta:
        model = Cliente
        fields = ["nome", "telefone", "instagram", "endereco", "observacoes"]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_telefone(self):
        return somente_digitos(self.cleaned_data.get("telefone"))

    def clean_instagram(self):
        return (self.cleaned_data.get("instagram") or "").strip().lstrip("@")


class NovoPedidoForm(BootstrapMixin, forms.Form):
    telefone = forms.CharField(
        label="Telefone da cliente",
        max_length=20,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
    )
    status = forms.ChoiceField(
        label="Status do pedido",
        choices=[c for c in Pedido.Status.choices if c[0] != Pedido.Status.CANCELADO],
        initial=Pedido.Status.AGUARDANDO_PAGAMENTO,
    )

    def clean_telefone(self):
        digitos = somente_digitos(self.cleaned_data["telefone"])
        if len(digitos) not in (10, 11):
            raise forms.ValidationError("Informe o telefone com DDD (10 ou 11 dígitos).")
        cliente = Cliente.objects.filter(telefone=digitos).first()
        if cliente is None:
            raise forms.ValidationError("Cliente não encontrada. Cadastre a cliente antes de salvar.")
        self.cliente = cliente
        return digitos


class ItemPedidoForm(BootstrapMixin, forms.Form):
    produto = forms.ModelChoiceField(
        label="Peça",
        queryset=Produto.objects.filter(ativo=True),
        empty_label="Escolha a peça",
    )
    quantidade = forms.IntegerField(label="Quantidade", min_value=1, initial=1)


ItemPedidoFormSet = forms.formset_factory(
    ItemPedidoForm, extra=0, min_num=1, validate_min=True, max_num=30, validate_max=True
)


class StatusPedidoForm(BootstrapMixin, forms.Form):
    status = forms.ChoiceField(label="Status do pedido", choices=Pedido.Status.choices)
