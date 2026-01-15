document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".examen-card");
  const btnConfirmar = document.getElementById("btnConfirmar");
  const mensaje = document.getElementById("mensaje");

  cards.forEach((card) => {
    card.addEventListener("click", () => {
      const checkbox = card.querySelector("input[type='checkbox']");
      checkbox.checked = !checkbox.checked;

      card.classList.toggle("selected", checkbox.checked);
    });
  });

  btnConfirmar.addEventListener("click", (e) => {
    const seleccionados = document.querySelectorAll(
      "input[name='examenes']:checked"
    );

    if (seleccionados.length === 0) {
      e.preventDefault();
      mensaje.textContent = "⚠️ Selecciona al menos un examen.";
      mensaje.style.color = "red";
    }
  });
});