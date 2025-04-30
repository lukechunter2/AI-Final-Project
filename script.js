document.addEventListener("DOMContentLoaded", () => {
  const focusSelect = document.getElementById("focus");
  const subcategorySelect = document.getElementById("subcategory");
  const accessSelect = document.getElementById("access");
  const planDiv = document.getElementById("plan");
  const form = document.getElementById("workout-form");

  // Fetch dropdown options from backend
  fetch("/get_options")
    .then(res => res.json())
    .then(data => {
      populateSelect(focusSelect, data.focus);
      populateSelect(subcategorySelect, data.subcategory);
      populateSelect(accessSelect, data.access);
    });

  function populateSelect(select, options) {
    options.forEach(opt => {
      const option = document.createElement("option");
      option.value = opt;
      option.textContent = opt;
      select.appendChild(option);
    });
  }

  form.addEventListener("submit", e => {
    e.preventDefault();

    const params = new URLSearchParams({
      focus: focusSelect.value,
      subcategory: subcategorySelect.value,
      access: accessSelect.value,
      days: document.getElementById("days").value
    });

    fetch(`/get_workouts?${params.toString()}`)
      .then(res => res.json())
      .then(plan => {
        planDiv.innerHTML = "";
        for (const [day, exercises] of Object.entries(plan)) {
          const section = document.createElement("div");
          section.innerHTML = `<h2>${day}</h2><ul>${exercises.map(e => `<li>${e}</li>`).join('')}</ul>`;
          planDiv.appendChild(section);
        }
      });
  });
});
