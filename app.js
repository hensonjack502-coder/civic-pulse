"use strict";

async function readApiResponse(response) {
  try {
    return await response.json();
  } catch (_error) {
    return { success: false, message: "The server returned an unreadable response." };
  }
}

async function refreshDashboard() {
  try {
    const response = await fetch("/api/complaints/summary");
    const data = await readApiResponse(response);
    if (!response.ok || !data.success) throw new Error(data.message || "Could not load dashboard totals.");
    const errorMessage = document.querySelector("#dashboardError");
    errorMessage.hidden = true;
    errorMessage.textContent = "";
    document.querySelector("#totalCount").textContent = data.total;
    document.querySelector("#pendingCount").textContent = data.pending;
    document.querySelector("#resolvedCount").textContent = data.resolved;
  } catch (error) {
    console.error("Dashboard could not connect to Civic Pulse.", error);
    const errorMessage = document.querySelector("#dashboardError");
    errorMessage.hidden = false;
    errorMessage.textContent = "Dashboard totals are temporarily unavailable. Please refresh the page to try again.";
  }
}

document.querySelector("#reportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  const message = document.querySelector("#formMessage");
  submitButton.disabled = true;
  message.className = "form-message";
  message.textContent = "Sending your complaint…";

  try {
    const response = await fetch("/api/complaints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category: form.elements.category.value,
        location: form.elements.location.value.trim(),
        description: form.elements.description.value.trim()
      })
    });
    const data = await readApiResponse(response);
    if (!response.ok || !data.success) throw new Error(data.message || "The complaint could not be saved.");

    message.textContent = `${data.message} Tracking ID: ${data.complaint.id}`;
    form.reset();
    await refreshDashboard();
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message || "Could not reach the server. Start Flask and try again.";
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#trackingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const complaintId = document.querySelector("#trackId").value.trim();
  const result = document.querySelector("#trackResult");
  result.className = "track-result";
  result.textContent = "Looking up your complaint…";

  try {
    const response = await fetch(`/api/complaints/${encodeURIComponent(complaintId)}`);
    const data = await readApiResponse(response);
    if (!response.ok || !data.success) throw new Error(data.message || "The complaint could not be found.");

    const complaint = data.complaint;
    result.className = "track-result success";
    result.replaceChildren();
    const id = document.createElement("b");
    id.textContent = complaint.id;
    const status = document.createElement("b");
    status.textContent = complaint.status;
    result.append(id, ` · ${complaint.category} · `, status, document.createElement("br"));
    result.append(document.createTextNode(complaint.location), document.createElement("br"));
    const note = document.createElement("small");
    note.textContent = `Demo record · Submitted ${complaint.created_at}`;
    result.append(note);
  } catch (error) {
    result.className = "track-result error";
    result.textContent = error.message || "Could not reach the server. Start Flask and try again.";
  }
});

const answers = [
  { match: /scheme|benefit|eligib/, text: "For schemes and eligibility, search the official MyScheme directory. Rules differ by scheme and location, so confirm the current details on the scheme’s official page.", link: "https://www.myscheme.gov.in/", label: "Open MyScheme" },
  { match: /complaint|report|civic issue|problem|garbage|road|water|light/, text: "This Civic Pulse form creates a demo record in the project database. To reach a real city office, check your municipal corporation’s official website or verified helpline for your area.", link: "https://www.india.gov.in/", label: "Find official government services" },
  { match: /contact|government|department|official/, text: "For official contacts and government services in India, start with the National Portal of India. For city services, use your municipal body’s official contact page. This demo cannot submit or verify a request.", link: "https://www.india.gov.in/", label: "Open India.gov.in" },
  { match: /notice|update|announcement|urgent|live/, text: "This page’s notices are sample content, not live advisories. Please check your municipal body’s official website or verified public channels for current announcements." }
];

function appendChat(text, kind, link, label) {
  const messages = document.querySelector("#chatMessages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${kind === "user" ? "user-bubble" : "bot-bubble"}`;
  bubble.textContent = text;
  messages.appendChild(bubble);
  if (link) {
    const linkBubble = document.createElement("a");
    linkBubble.className = "chat-bubble bot-bubble chat-source";
    linkBubble.href = link;
    linkBubble.target = "_blank";
    linkBubble.rel = "noopener noreferrer";
    linkBubble.textContent = `${label} ↗`;
    messages.appendChild(linkBubble);
  }
  messages.scrollTop = messages.scrollHeight;
}

function askAssistant(question) {
  const cleaned = question.trim();
  if (!cleaned) return;
  appendChat(cleaned, "user");
  const answer = answers.find((item) => item.match.test(cleaned));
  if (answer) appendChat(answer.text, "bot", answer.link, answer.label);
  else appendChat("I don’t have a verified answer for that. Try the National Portal of India or your municipal body’s official website. I won’t guess at policies or current local information.", "bot", "https://www.india.gov.in/", "Open India.gov.in");
}

document.querySelector("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#chatInput");
  askAssistant(input.value);
  input.value = "";
});
document.querySelectorAll(".quick-questions button").forEach((button) => button.addEventListener("click", () => askAssistant(button.dataset.question)));

const menuToggle = document.querySelector("#menuToggle");
menuToggle.addEventListener("click", () => {
  const open = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  document.querySelector("#mainNav").classList.toggle("open", open);
});
document.querySelectorAll("#mainNav a").forEach((link) => link.addEventListener("click", () => {
  menuToggle.setAttribute("aria-expanded", "false");
  menuToggle.setAttribute("aria-label", "Open navigation");
  document.querySelector("#mainNav").classList.remove("open");
}));

refreshDashboard();
