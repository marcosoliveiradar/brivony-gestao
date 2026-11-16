// Tela 2 — Novo pedido. Melhorias no navegador; todas as regras são conferidas de novo no servidor.
(function () {
  "use strict";
  var form = document.getElementById("form-pedido");
  if (!form) return;
  var itens = document.getElementById("itens");
  var modelo = document.getElementById("modelo-item");
  var totalForms = form.querySelector("input[name$='TOTAL_FORMS']");
  var moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

  function criarAlerta(texto) {
    var div = document.createElement("div");
    div.className = "alert alerta alerta-error mb-0";
    var icone = document.createElement("i");
    icone.className = "bi bi-x-circle-fill";
    icone.setAttribute("aria-hidden", "true");
    var span = document.createElement("span");
    span.textContent = texto; // textContent evita injeção de HTML
    div.appendChild(icone);
    div.appendChild(span);
    return div;
  }

  function atualizarItem(item) {
    var select = item.querySelector("[data-produto]");
    var qtd = item.querySelector("[data-qtd]");
    var opt = select.options[select.selectedIndex];
    var dispTexto = item.querySelector("[data-disp-texto]");
    var erro = item.querySelector("[data-erro]");
    var n = parseInt(qtd.value, 10) || 0;
    if (!opt || !opt.value) {
      dispTexto.textContent = "–";
      return 0;
    }
    var disp = parseInt(opt.dataset.disp, 10);
    dispTexto.textContent = disp;
    var valido = n >= 1 && n <= disp;
    item.classList.toggle("cartao-erro", !valido);
    qtd.setAttribute("aria-invalid", valido ? "false" : "true");
    erro.innerHTML = "";
    if (n > disp) {
      var unid = disp === 1 ? "unidade" : "unidades";
      var verbo = disp === 1 ? "Só resta " : "Só restam ";
      erro.appendChild(criarAlerta(verbo + disp + " " + unid + " do tamanho " + opt.dataset.tam + ". Ajuste a quantidade."));
    } else if (n < 1) {
      erro.appendChild(criarAlerta("A quantidade deve ser pelo menos 1."));
    }
    return valido ? parseFloat(opt.dataset.preco) * n : 0;
  }

  function atualizarTotal() {
    var total = 0;
    itens.querySelectorAll("[data-item]").forEach(function (item) { total += atualizarItem(item); });
    document.getElementById("total").textContent = moeda.format(total);
  }

  function renumerar() {
    var lista = itens.querySelectorAll("[data-item]");
    lista.forEach(function (item, i) {
      item.querySelectorAll("[name],[id],[for],[aria-describedby]").forEach(function (el) {
        ["name", "id", "for", "aria-describedby"].forEach(function (attr) {
          var v = el.getAttribute(attr);
          if (v) el.setAttribute(attr, v.replace(/itens-(\d+|__prefix__)-/, "itens-" + i + "-"));
        });
      });
    });
    totalForms.value = lista.length;
  }

  itens.addEventListener("click", function (e) {
    var item = e.target.closest("[data-item]");
    if (!item) return;
    var qtd = item.querySelector("[data-qtd]");
    if (e.target.closest("[data-menos]")) qtd.value = Math.max(1, (parseInt(qtd.value, 10) || 1) - 1);
    if (e.target.closest("[data-mais]")) qtd.value = (parseInt(qtd.value, 10) || 0) + 1;
    if (e.target.closest("[data-remover]") && itens.querySelectorAll("[data-item]").length > 1) {
      item.remove();
      renumerar();
    }
    atualizarTotal();
  });
  itens.addEventListener("input", atualizarTotal);
  itens.addEventListener("change", atualizarTotal);

  document.getElementById("adicionar-item").addEventListener("click", function () {
    itens.appendChild(modelo.content.cloneNode(true));
    renumerar();
    filtrar();
    atualizarTotal();
    var ultimos = itens.querySelectorAll("[data-produto]");
    ultimos[ultimos.length - 1].focus();
  });

  // Buscar peça: esconde opções que não combinam com o texto digitado.
  var busca = document.getElementById("buscar-peca");
  function filtrar() {
    var termo = busca.value.trim().toLowerCase();
    itens.querySelectorAll("[data-produto] option[value]").forEach(function (opt) {
      if (!opt.value) return;
      var ok = !termo || opt.dataset.busca.indexOf(termo) !== -1 || opt.selected;
      opt.hidden = !ok;
      opt.disabled = !ok;
    });
  }
  busca.addEventListener("input", filtrar);
  busca.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });

  // Busca da cliente pelo telefone.
  var tel = form.querySelector("input[name='telefone']");
  var status = document.getElementById("cliente-status");
  var link = document.getElementById("link-cadastrar");
  var urlBusca = form.dataset.buscarCliente;
  var temporizador;
  tel.addEventListener("input", function () {
    clearTimeout(temporizador);
    var digitos = tel.value.replace(/\D/g, "");
    link.href = link.href.split("&telefone=")[0] + "&telefone=" + digitos;
    if (digitos.length < 10) { status.textContent = ""; return; }
    temporizador = setTimeout(function () {
      fetch(urlBusca + "?telefone=" + encodeURIComponent(digitos), { headers: { "Accept": "application/json" } })
        .then(function (r) { return r.json(); })
        .then(function (dados) {
          status.innerHTML = "";
          var span = document.createElement("span");
          var icone = document.createElement("i");
          icone.setAttribute("aria-hidden", "true");
          if (dados.encontrada) {
            span.className = "texto-ok";
            icone.className = "bi bi-check-circle";
            span.appendChild(icone);
            span.appendChild(document.createTextNode(" " + dados.nome + " – cliente encontrada"));
          } else {
            span.className = "fw-semibold";
            icone.className = "bi bi-info-circle";
            span.appendChild(icone);
            span.appendChild(document.createTextNode(" Cliente não cadastrada. Use “+ Cadastrar cliente”."));
          }
          status.appendChild(span);
        })
        .catch(function () { status.textContent = ""; });
    }, 300);
  });

  // Evita envio duplicado.
  form.addEventListener("submit", function () {
    var botao = document.getElementById("salvar");
    setTimeout(function () { botao.disabled = true; botao.textContent = "Salvando…"; }, 0);
  });

  atualizarTotal();
})();
