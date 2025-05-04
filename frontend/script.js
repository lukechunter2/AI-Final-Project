// === script.js ===
document.addEventListener("DOMContentLoaded", () => {
  const focusSelect = document.getElementById("focus");
  const subcategorySelect = document.getElementById("subcategory");
  const accessSelect = document.getElementById("access");
  const planDiv = document.getElementById("plan");
  const form = document.getElementById("workout-form");

  let subcategoryMap = {};

  // Fetch dropdown options from backend
  fetch("/get_options")
    .then(res => res.json())
    .then(data => {
      populateSelect(focusSelect, data.focus);
      populateSelect(accessSelect, data.access);

      // Build map of focus → subcategories
      subcategoryMap = data.subcategory.reduce((map, tag) => {
        const [focus, sub] = tag.split("-");
        if (!map[focus]) map[focus] = new Set();
        map[focus].add(sub);
        return map;
      }, {});
    });

  focusSelect.addEventListener("change", () => {
    const selectedFocus = focusSelect.value;
    const subs = subcategoryMap[selectedFocus] || [];
    subcategorySelect.innerHTML = "";
    [...subs].forEach(sub => {
      const option = document.createElement("option");
      option.value = `${selectedFocus}-${sub}`;
      option.textContent = sub;
      subcategorySelect.appendChild(option);
    });
  });

  function populateSelect(select, options) {
    select.innerHTML = "";
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
          section.innerHTML = `<h2>${day}</h2><ul>${exercises.map(e =>
            `<li><a href="${e.url}" target="_blank">${e.exercise}</a> — Sets: ${e.sets}, Reps: ${e.reps}, Rest: ${e.rest}</li>`
          ).join('')}</ul>`;
          planDiv.appendChild(section);
        }
      });
  });
});

