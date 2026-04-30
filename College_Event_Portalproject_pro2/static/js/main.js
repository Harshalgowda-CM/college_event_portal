document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".auth-tab");
  const forms = document.querySelectorAll(".auth-form");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.dataset.authTarget;
      tabs.forEach((item) => item.classList.remove("active"));
      forms.forEach((form) => form.classList.remove("active"));
      tab.classList.add("active");
      const targetForm = document.getElementById(targetId);
      if (targetForm) {
        targetForm.classList.add("active");
      }
    });
  });

  setTimeout(() => {
    document.querySelectorAll(".flash").forEach((flash) => {
      flash.classList.add("flash-hide");
    });
  }, 3500);

  if (document.body.classList.contains("celebration-page")) {
    const layer = document.getElementById("confetti-layer");
    const colors = ["#59e8ff", "#ff61c7", "#ffd76d", "#79ffb5", "#8c79ff"];
    for (let index = 0; index < 44; index += 1) {
      const piece = document.createElement("span");
      piece.className = "confetti-piece";
      piece.style.left = `${Math.random() * 100}%`;
      piece.style.animationDelay = `${Math.random() * 5}s`;
      piece.style.animationDuration = `${5 + Math.random() * 5}s`;
      piece.style.background = colors[index % colors.length];
      piece.style.transform = `rotate(${Math.random() * 360}deg)`;
      layer.appendChild(piece);
    }
  }
});
