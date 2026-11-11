"use strict";

const tiles = Array.from(document.querySelectorAll(".tile"));
const filters = Array.from(document.querySelectorAll("[data-filter]"));
const query = document.querySelector("#query");
const count = document.querySelector("#count");
const empty = document.querySelector("#empty");
const preview = document.querySelector("#preview");
const stage = document.querySelector("#stage");
const surface = document.querySelector("#surface");
let category = "All";

function showMatches() {
  const words = query.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  let visible = 0;
  for (const tile of tiles) {
    const text = [tile.textContent, tile.dataset.group, tile.dataset.usage].join(" ").toLocaleLowerCase();
    const match = (category === "All" || tile.dataset.group === category) && words.every(word => text.includes(word));
    tile.hidden = !match;
    if (match) visible++;
  }
  count.textContent = visible + (visible === 1 ? " Overlay" : " Overlays");
  empty.hidden = visible !== 0;
  for (const button of filters) button.setAttribute("aria-pressed", String(button.dataset.filter === category));
}

function openPreview(tile) {
  const href = tile.getAttribute("href");
  document.querySelector("#preview-title").textContent = tile.querySelector(".tile-label").textContent;
  document.querySelector("#preview-group").textContent = tile.dataset.group;
  document.querySelector("#preview-usage").textContent = tile.dataset.usage;
  document.querySelector("#preview-image").src = href;
  const save = document.querySelector("#save");
  save.href = href;
  save.download = href.split("/").pop();
  document.querySelector("#open").href = href;
  preview.showModal();
  document.querySelector("#close").focus();
}

for (const button of filters) {
  button.addEventListener("click", () => {
    category = button.dataset.filter;
    showMatches();
  });
}
query.addEventListener("input", showMatches);
document.querySelector("#reset").addEventListener("click", () => {
  category = "All";
  query.value = "";
  showMatches();
  query.focus();
});

for (const tile of tiles) {
  tile.addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || typeof preview.showModal !== "function") return;
    event.preventDefault();
    openPreview(tile);
  });
}
document.querySelector("#close").addEventListener("click", () => preview.close());
preview.addEventListener("click", event => {
  if (event.target === preview) preview.close();
});
surface.addEventListener("click", () => {
  const enabled = stage.classList.toggle("checker");
  surface.setAttribute("aria-pressed", String(enabled));
});
