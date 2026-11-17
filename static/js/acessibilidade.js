// RNF04 — Botão "A+": aumenta todo o texto do sistema em 25% e lembra a escolha neste aparelho.
(function () {
  "use strict";
  var raiz = document.documentElement;
  var botoes = document.querySelectorAll("[data-texto-maior]");

  function aplicar(ligado) {
    raiz.classList.toggle("texto-maior", ligado);
    botoes.forEach(function (b) {
      b.setAttribute("aria-pressed", ligado ? "true" : "false");
      b.querySelector(".visually-hidden").textContent = ligado ? "Texto normal" : "Texto maior";
    });
  }

  aplicar(raiz.classList.contains("texto-maior"));
  botoes.forEach(function (b) {
    b.addEventListener("click", function () {
      var ligado = !raiz.classList.contains("texto-maior");
      aplicar(ligado);
      try { localStorage.setItem("texto-maior", ligado ? "1" : "0"); } catch (e) {}
    });
  });
})();
