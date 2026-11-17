"""Telas do Brivony Gestão. Todas exigem login (RNF01)."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from . import services
from .forms import ClienteForm, ItemPedidoFormSet, NovoPedidoForm, ProdutoForm, StatusPedidoForm
from .models import Cliente, Pedido, Produto

SESSAO_ESTOQUE_ANTERIOR = "estoque_anterior"


class SaudeView(View):
    """Rota pública de saúde para o health check do Render e para o UptimeRobot.

    Responde 200 quando a aplicação e o banco estão funcionando e 503 quando o
    banco não responde, para o monitor marcar o serviço como DOWN.
    Não exibe nenhum dado da loja.
    """

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # noqa: BLE001 - qualquer falha de banco deixa o serviço indisponível
            return JsonResponse({"status": "erro", "banco": "indisponível"}, status=503)
        return JsonResponse({"status": "ok", "banco": "ok"})

    head = get


class PainelView(LoginRequiredMixin, TemplateView):
    """Tela 1 — Painel (RF06)."""

    template_name = "loja/painel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.resumo_painel())
        ctx["aba"] = "inicio"
        return ctx


# ---------------------------------------------------------------- Estoque (RF01)


class EstoqueView(LoginRequiredMixin, ListView):
    """Tela 3 — Estoque, com filtro de estoque baixo."""

    template_name = "loja/estoque.html"
    context_object_name = "produtos"

    def get_queryset(self):
        qs = Produto.objects.filter(ativo=True)
        if self.request.GET.get("filtro") == "baixo":
            qs = qs.filter(quantidade_estoque__lte=settings.ESTOQUE_BAIXO_LIMITE)
        busca = self.request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(cor__icontains=busca))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filtro"] = self.request.GET.get("filtro", "todas")
        ctx["busca"] = self.request.GET.get("q", "")
        # Quantidades antes do último pedido, para mostrar a baixa ("antes 3").
        ctx["estoque_anterior"] = self.request.session.pop(SESSAO_ESTOQUE_ANTERIOR, {})
        ctx["aba"] = "estoque"
        return ctx


class ProdutoCreateView(LoginRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "loja/form.html"
    extra_context = {"titulo": "Cadastrar peça", "aba": "estoque"}

    def get_success_url(self):
        messages.success(self.request, f"Peça “{self.object}” cadastrada.")
        return reverse("loja:estoque")


class ProdutoUpdateView(LoginRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "loja/form.html"
    extra_context = {"titulo": "Editar peça", "aba": "estoque"}
    queryset = Produto.objects.filter(ativo=True)

    def get_success_url(self):
        messages.success(self.request, f"Peça “{self.object}” atualizada.")
        return reverse("loja:estoque")


class ProdutoInativarView(LoginRequiredMixin, View):
    """Peças não são excluídas, para não perder o histórico de pedidos."""

    def post(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk, ativo=True)
        produto.ativo = False
        produto.save(update_fields=["ativo"])
        messages.success(request, f"Peça “{produto}” retirada do catálogo.")
        return redirect("loja:estoque")


# --------------------------------------------------------------- Clientes (RF02)


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "loja/clientes.html"
    context_object_name = "clientes"
    paginate_by = 30
    extra_context = {"aba": "clientes"}

    def get_queryset(self):
        qs = super().get_queryset()
        busca = self.request.GET.get("q", "").strip()
        if busca:
            digitos = "".join(c for c in busca if c.isdigit())
            filtro = Q(nome__icontains=busca)
            if digitos:
                filtro |= Q(telefone__contains=digitos)
            qs = qs.filter(filtro)
        return qs


class _ClienteFormMixin(LoginRequiredMixin):
    model = Cliente
    form_class = ClienteForm
    template_name = "loja/form.html"

    def get_success_url(self):
        destino = self.request.POST.get("next") or self.request.GET.get("next")
        if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            sep = "&" if "?" in destino else "?"
            return f"{destino}{sep}telefone={self.object.telefone}"
        return reverse("loja:clientes")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self.request.GET.get("next", "")
        return ctx


class ClienteCreateView(_ClienteFormMixin, CreateView):
    extra_context = {"titulo": "Cadastrar cliente", "aba": "clientes"}

    def get_initial(self):
        return {"telefone": self.request.GET.get("telefone", "")}

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f"Cliente {self.object.nome} cadastrada.")
        return resposta


class ClienteUpdateView(_ClienteFormMixin, UpdateView):
    extra_context = {"titulo": "Editar cliente", "aba": "clientes"}

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f"Dados de {self.object.nome} atualizados.")
        return resposta


class BuscarClienteView(LoginRequiredMixin, View):
    """Usado pela Tela 2 para mostrar “cliente encontrada” enquanto se digita."""

    def get(self, request):
        cliente = services.buscar_cliente_por_telefone(request.GET.get("telefone"))
        if cliente is None:
            return JsonResponse({"encontrada": False})
        return JsonResponse({"encontrada": True, "nome": cliente.nome})


# ---------------------------------------------------------- Pedidos (RF03–RF05)


class PedidoListView(LoginRequiredMixin, ListView):
    template_name = "loja/pedidos.html"
    context_object_name = "pedidos"
    paginate_by = 30

    def get_queryset(self):
        qs = Pedido.objects.select_related("cliente")
        status = self.request.GET.get("status")
        if status == "pendentes":
            qs = qs.filter(status__in=Pedido.STATUS_PENDENTES)
        elif status in Pedido.Status.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["status_opcoes"] = Pedido.Status.choices
        ctx["aba"] = "pedidos"
        return ctx


class PedidoDetailView(LoginRequiredMixin, DetailView):
    template_name = "loja/pedido_detalhe.html"
    context_object_name = "pedido"
    queryset = Pedido.objects.select_related("cliente").prefetch_related("itens__produto")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_form"] = StatusPedidoForm(initial={"status": self.object.status})
        ctx["aba"] = "pedidos"
        return ctx


class PedidoStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk)
        form = StatusPedidoForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Escolha um status válido.")
            return redirect("loja:pedido_detalhe", pk=pk)
        try:
            services.alterar_status(pedido, form.cleaned_data["status"])
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        else:
            pedido.refresh_from_db()
            if pedido.cancelado:
                messages.success(request, f"{pedido} cancelado. As peças voltaram ao estoque.")
            else:
                messages.success(request, f"{pedido} agora está “{pedido.get_status_display()}”.")
        return redirect("loja:pedido_detalhe", pk=pk)


class NovoPedidoView(LoginRequiredMixin, View):
    """Tela 2 — Novo pedido (RF03)."""

    template_name = "loja/novo_pedido.html"
    prefixo = "itens"

    def _contexto(self, form, formset, erros_itens=None):
        produtos = services.produtos_para_venda()
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "produtos": produtos,
                "erros_itens": erros_itens or {},
                "aba": "pedidos",
                "cliente_encontrada": getattr(form, "cliente", None)
                or services.buscar_cliente_por_telefone(form["telefone"].value()),
            },
        )

    def get(self, request):
        form = NovoPedidoForm(initial={"telefone": request.GET.get("telefone", "")})
        formset = ItemPedidoFormSet(prefix=self.prefixo)
        return self._contexto(form, formset)

    def post(self, request):
        form = NovoPedidoForm(request.POST)
        formset = ItemPedidoFormSet(request.POST, prefix=self.prefixo)
        if not (form.is_valid() and formset.is_valid()):
            return self._contexto(form, formset)

        itens = [
            (f.cleaned_data["produto"].pk, f.cleaned_data["quantidade"])
            for f in formset
            if f.cleaned_data and not f.cleaned_data.get("DELETE")
        ]
        antes = {
            str(p.pk): p.quantidade_estoque
            for p in Produto.objects.filter(pk__in=[pid for pid, _ in itens])
        }
        try:
            pedido = services.criar_pedido(form.cliente, itens, form.cleaned_data["status"])
        except services.EstoqueInsuficiente as erro:
            for item_form in formset:
                produto = item_form.cleaned_data.get("produto")
                if produto and produto.pk in erro.erros_por_produto:
                    item_form.add_error("quantidade", erro.erros_por_produto[produto.pk])
            return self._contexto(form, formset, erro.erros_por_produto)
        except ValidationError as erro:
            for msg in erro.messages:
                form.add_error(None, msg)
            return self._contexto(form, formset)

        request.session[SESSAO_ESTOQUE_ANTERIOR] = antes
        messages.success(request, f"Pedido nº {pedido.pk} registrado. Estoque atualizado.")
        return redirect("loja:estoque")
