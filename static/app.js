// Equity Research War Room — frontend controller.
// Streams Server-Sent Events from /api/run and renders each stage live.

const form = document.getElementById("run-form");
const input = document.getElementById("company-input");
const button = document.getElementById("run-button");
const statusEl = document.getElementById("status");
const stagesEl = document.getElementById("stages");

/** Minimal markdown -> HTML renderer, just enough for headers/bold/bullets/paragraphs. */
function renderMarkdown(text) {
  const escape = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const inline = (s) =>
    escape(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`(.+?)`/g, "<code>$1</code>");

  const lines = text.split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const bullet = line.match(/^[-*]\s+(.*)/);

    if (heading) {
      closeList();
      const level = Math.min(heading[1].length + 1, 6); // ## -> h3, so it nests under stage h2
      html += `<h${level}>${inline(heading[2])}</h${level}>`;
    } else if (bullet) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inline(bullet[1])}</li>`;
    } else if (line === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function setStatus(text, isError = false) {
  statusEl.hidden = !text;
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

function createStageEl(stage, title) {
  const el = document.createElement("section");
  el.className = `stage ${stage}`;
  el.innerHTML = `
    <div class="stage-header">
      <h2>${title}</h2>
      <span class="spinner" aria-label="working"></span>
      <span class="searching-badge" hidden>searching the web…</span>
    </div>
    <div class="stage-body"></div>
  `;
  stagesEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
  return el;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const company = input.value.trim();
  if (!company) return;

  button.disabled = true;
  stagesEl.innerHTML = "";
  setStatus("Assembling the War Room…");

  const stageEls = {};
  const stageText = {};

  const source = new EventSource(`/api/run?company=${encodeURIComponent(company)}`);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case "stage_start": {
        setStatus(`Running: ${data.title}`);
        stageText[data.stage] = "";
        stageEls[data.stage] = createStageEl(data.stage, data.title);
        break;
      }
      case "delta": {
        stageText[data.stage] = (stageText[data.stage] || "") + data.text;
        const el = stageEls[data.stage];
        if (el) {
          el.querySelector(".stage-body").innerHTML = renderMarkdown(
            stageText[data.stage]
          );
        }
        break;
      }
      case "search": {
        const el = stageEls[data.stage];
        if (el) el.querySelector(".searching-badge").hidden = false;
        break;
      }
      case "stage_end": {
        const el = stageEls[data.stage];
        if (el) {
          el.querySelector(".spinner").remove();
          const badge = el.querySelector(".searching-badge");
          if (badge) badge.hidden = true;
        }
        break;
      }
      case "done": {
        setStatus("Done. Scroll up for the Decision Dossier.");
        button.disabled = false;
        source.close();
        break;
      }
      case "error": {
        setStatus(`Error: ${data.message}`, true);
        button.disabled = false;
        source.close();
        break;
      }
    }
  };

  source.onerror = () => {
    setStatus("Connection lost. Refresh and try again.", true);
    button.disabled = false;
    source.close();
  };
});
