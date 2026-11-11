"use strict";

(function () {
  const kit = window.SocialCutIcons;
  const $ = selector => document.querySelector(selector);
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  if (!kit) {
    $("#count").textContent = "The Icon Data Did Not Load. Run node art/build.mjs To Regenerate icons.global.js.";
    return;
  }

  const SIZES = [16, 20, 24, 32, 48, 64];
  const WEIGHTS = [1, 1.5, 2];
  const FORMATS = ["Module", "Markup", "SVG"];
  const state = { group: "All", asset: null, weight: 1.5, format: "Module" };
  const query = $("#query");
  const preview = $("#preview");
  const stage = $("#stage");
  const tiles = [];
  const sections = [];

  function tileFor(asset) {
    const tile = make("button", "tile");
    tile.type = "button";
    const thumb = make("span", "thumb");
    if (asset.animated) {
      const image = make("img");
      image.src = asset.file;
      image.width = 53;
      image.height = 53;
      image.alt = "";
      image.loading = "lazy";
      thumb.append(image);
    } else {
      thumb.innerHTML = kit.icon(asset.name, { size: 36 });
    }
    tile.append(thumb, make("span", "tile-label", asset.title));
    tile.title = asset.animated ? asset.usage : kit.motions[asset.name];
    tile.addEventListener("click", () => openPreview(asset));
    const haystack = [asset.title, asset.name, asset.group, asset.usage, asset.motion || "", (asset.tags || []).join(" ")].join(" ").toLocaleLowerCase();
    tiles.push({ tile, asset, haystack });
    return tile;
  }

  function build() {
    const filters = $("#filters");
    for (const name of ["All", ...kit.catalog.groups]) {
      const button = make("button", "", name);
      button.type = "button";
      button.dataset.filter = name;
      button.addEventListener("click", () => {
        state.group = name;
        showMatches();
      });
      filters.append(button);
    }
    const holder = $("#groups");
    for (const name of kit.catalog.groups) {
      const section = make("section", "group");
      const heading = make("h2", "group-title", name);
      const grid = make("div", "grid");
      for (const asset of kit.catalog.assets) if (asset.group === name) grid.append(tileFor(asset));
      section.append(heading, grid);
      holder.append(section);
      sections.push({ name, section });
    }
  }

  function showMatches() {
    const words = query.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let icons = 0;
    let overlays = 0;
    const shown = new Set();
    for (const { tile, asset, haystack } of tiles) {
      const match = (state.group === "All" || asset.group === state.group) && words.every(word => haystack.includes(word));
      tile.hidden = !match;
      if (!match) continue;
      shown.add(asset.group);
      if (asset.animated) overlays++;
      else icons++;
    }
    for (const { name, section } of sections) section.hidden = !shown.has(name);
    const plural = (count, word) => count + " " + word + (count === 1 ? "" : "s");
    $("#count").textContent = plural(icons, "Icon") + " And " + plural(overlays, "Overlay");
    $("#empty").hidden = icons + overlays !== 0;
    for (const button of document.querySelectorAll("[data-filter]")) {
      button.setAttribute("aria-pressed", String(button.dataset.filter === state.group));
    }
  }

  function snippet(asset) {
    const stroke = state.weight === 1.5 ? "" : ", strokeWidth: " + state.weight;
    if (state.format === "Module") {
      return 'import { icon } from "./icons.js";\n\nbutton.innerHTML = icon("' + asset.name + '", { size: 24' + stroke + " });";
    }
    if (state.format === "Markup") {
      const attribute = state.weight === 1.5 ? "" : ' data-icon-stroke="' + state.weight + '"';
      return '<button type="button">\n  <span data-icon="' + asset.name + '"' + attribute + "></span>\n  " + asset.title + "\n</button>";
    }
    return kit.icon(asset.name, { size: 24, strokeWidth: state.weight });
  }

  function segment(holder, values, current, choose) {
    holder.textContent = "";
    for (const value of values) {
      const button = make("button", "", String(value));
      button.type = "button";
      button.setAttribute("aria-pressed", String(value === current));
      button.addEventListener("click", () => choose(value));
      holder.append(button);
    }
  }

  function renderIcon() {
    const asset = state.asset;
    stage.textContent = "";
    const hero = make("button", "hero sck-trigger");
    hero.type = "button";
    hero.setAttribute("aria-label", "Play Motion");
    hero.innerHTML = kit.icon(asset.name, { size: 120, strokeWidth: state.weight });
    hero.addEventListener("click", replay);
    stage.append(hero);
    const sizes = $("#sizes");
    sizes.textContent = "";
    for (const size of SIZES) {
      const cell = make("span", "size-cell sck-trigger");
      cell.innerHTML = kit.icon(asset.name, { size, strokeWidth: state.weight });
      cell.append(make("span", "size-label", String(size)));
      sizes.append(cell);
    }
    segment($("#weights"), WEIGHTS, state.weight, value => {
      state.weight = value;
      renderIcon();
    });
    segment($("#formats"), FORMATS, state.format, value => {
      state.format = value;
      renderIcon();
    });
    $("#code").textContent = snippet(asset);
    $("#copied").textContent = "";
  }

  function replay() {
    const icon = stage.querySelector(".sck-icon");
    if (!icon) return;
    icon.classList.remove("sck-play");
    void icon.getBoundingClientRect();
    icon.classList.add("sck-play");
    icon.addEventListener("animationend", () => icon.classList.remove("sck-play"), { once: true });
  }

  function openPreview(asset) {
    state.asset = asset;
    $("#preview-title").textContent = asset.title;
    $("#preview-group").textContent = asset.group;
    $("#preview-usage").textContent = asset.usage;
    $("#preview-motion").textContent = asset.animated ? "" : "Motion: " + asset.motion;
    $("#preview-motion").hidden = asset.animated;
    $("#icon-controls").hidden = asset.animated;
    if (asset.animated) {
      stage.textContent = "";
      const image = make("img");
      image.src = asset.file;
      image.width = 124;
      image.height = 124;
      image.alt = "";
      stage.append(image);
    } else {
      renderIcon();
    }
    const save = $("#save");
    save.href = asset.file;
    save.download = asset.file.split("/").pop();
    $("#open").href = asset.file;
    if (!preview.open) {
      if (typeof preview.showModal === "function") preview.showModal();
      else preview.setAttribute("open", "");
    }
    if (!asset.animated) replay();
  }

  async function copyCode() {
    const text = $("#code").textContent;
    let done = false;
    try {
      await navigator.clipboard.writeText(text);
      done = true;
    } catch (error) {
      const area = make("textarea");
      area.value = text;
      preview.append(area);
      area.select();
      try {
        done = document.execCommand("copy");
      } catch (inner) {
        done = false;
      }
      area.remove();
    }
    $("#copied").textContent = done ? "Copied." : "Select The Code And Copy It By Hand.";
  }

  build();
  query.addEventListener("input", showMatches);
  $("#reset").addEventListener("click", () => {
    state.group = "All";
    query.value = "";
    showMatches();
    query.focus();
  });
  $("#close").addEventListener("click", () => preview.close());
  preview.addEventListener("click", event => {
    if (event.target === preview) preview.close();
  });
  $("#replay").addEventListener("click", replay);
  $("#copy").addEventListener("click", copyCode);
  $("#surface").addEventListener("click", () => {
    const enabled = stage.classList.toggle("checker");
    $("#surface").setAttribute("aria-pressed", String(enabled));
  });

  // Optional address fragment, for example index.html#group=Files or index.html#icon=trash-bin.
  const wanted = new URLSearchParams(location.hash.slice(1));
  if (wanted.has("group") && ["All", ...kit.catalog.groups].includes(wanted.get("group"))) state.group = wanted.get("group");
  if (wanted.has("q")) query.value = wanted.get("q");
  showMatches();
  if (wanted.has("icon")) {
    const found = kit.catalog.assets.find(asset => asset.name === wanted.get("icon"));
    if (found) openPreview(found);
  }
})();
