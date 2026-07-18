document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-static-form]").forEach(form => {
    form.noValidate = true;
    const endpointName = form.dataset.staticForm;
    const endpoint = window.SITE_CONFIG?.[endpointName];
    const button = form.querySelector("button[type=submit]");
    const message = form.querySelector(".form-message");
    const fields = [...form.querySelectorAll("input, select, textarea")];

    fields.forEach(field => {
      const error = document.createElement("p");
      error.className = "field-error";
      error.id = `${field.id}-error`;
      error.hidden = true;
      field.insertAdjacentElement("afterend", error);
      field.setAttribute("aria-describedby", error.id);
      field.addEventListener("input", () => validateField(field, error));
      field.addEventListener("change", () => validateField(field, error));
    });

    if (!endpoint) {
      fields.forEach(field => { field.disabled = true; });
      button.disabled = true;
      button.textContent = form.dataset.closedLabel || "Responses open with the public pilot";
      showMessage(message, "Response collection is closed in this build. No form data is transmitted or stored.", "status");
      return;
    }

    form.addEventListener("submit", async event => {
      event.preventDefault();
      const valid = fields.map(field => validateField(field, document.getElementById(`${field.id}-error`))).every(Boolean);
      if (!valid) {
        const firstInvalid = fields.find(field => field.getAttribute("aria-invalid") === "true");
        firstInvalid?.focus();
        showMessage(message, "Some details need attention. Each affected field explains what to change.", "error");
        return;
      }
      button.disabled = true;
      button.textContent = "Sending…";
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Accept": "application/json" },
          body: new FormData(form)
        });
        if (!response.ok) throw new Error("Form submission failed");
        form.reset();
        showMessage(message, "Thank you — your note has been sent.", "success");
      } catch (error) {
        showMessage(message, "The response was not sent because the form service could not be reached. Try again when your connection is stable.", "error");
      } finally {
        button.disabled = false;
        button.textContent = form.dataset.submitLabel || "Send";
      }
    });
  });
});

function validateField(field, error) {
  let text = "";
  if (field.required && !field.value.trim()) text = requiredMessage(field.name);
  else if (field.type === "email" && field.validity.typeMismatch) text = "Enter an email address in the format name@example.com.";
  const valid = text === "";
  field.setAttribute("aria-invalid", String(!valid));
  error.textContent = text;
  error.hidden = valid;
  return valid;
}

function requiredMessage(name) {
  const messages = {
    route: "Choose the route you tried.",
    worked_as_expected: "Tell us whether the route worked as expected.",
    feedback: "Describe what was inaccurate, awkward or unexpectedly good.",
    area: "Name the neighbourhood or area.",
    suggested_stops: "Add at least one stop and explain why it belongs in the route.",
    future_collection: "Choose the collection you would genuinely use.",
    contact_topic: "Choose what you would like to talk about.",
    contact_message: "Write a short message so we know how to help."
  };
  return messages[name] || "Complete this field so the response can be processed.";
}

function showMessage(message, text, type = "status") {
  message.textContent = text;
  message.classList.remove("success", "error", "status");
  message.classList.add("show", type);
}
