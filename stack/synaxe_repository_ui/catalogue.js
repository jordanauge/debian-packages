"use strict";
(() => {
  const el = id => document.getElementById(id);
  const platform = document.body.dataset.platform;
  const scope = document.body.dataset.scope;
  document.querySelectorAll(".platforms a").forEach(link => {
    if (link.dataset.platform === platform) link.setAttribute("aria-current", "page");
  });
  const tabs = [el("install-tab"), el("packages-tab")];
  function activate(index) {
    tabs.forEach((tab, i) => {
      tab.setAttribute("aria-selected", String(i === index));
      tab.tabIndex = i === index ? 0 : -1;
      el(tab.getAttribute("aria-controls")).hidden = i !== index;
    });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(index));
    tab.addEventListener("keydown", event => {
      const positions = {ArrowRight: 1 - index, ArrowLeft: 1 - index, Home: 0, End: 1};
      if (event.key in positions) {
        event.preventDefault();
        const next = positions[event.key];
        activate(next);
        tabs[next].focus();
      }
    });
  });
  function text(tag, value, className) {
    const node = document.createElement(tag);
    node.textContent = String(value ?? "");
    if (className) node.className = className;
    return node;
  }
  async function copy(value) {
    try {
      await navigator.clipboard.writeText(value);
      el("copy-status").textContent = "Copied to clipboard.";
    } catch (error) {
      el("copy-status").textContent = "Copy failed: " + error.message + ". Select and copy the command manually.";
    }
  }
  document.querySelectorAll("[data-copy]").forEach(button => {
    button.addEventListener("click", () => copy(el(button.dataset.copy).textContent));
  });
  // Keep the existing Debian bootstrap handler available to generated instructions.
  window.copyText = copy;
  function download(value, label) {
    const url = new URL(value, location.href);
    if (url.origin !== location.origin || !["http:", "https:"].includes(url.protocol)) {
      throw new Error("Package download must stay on this repository");
    }
    const link = text("a", label);
    link.href = url.href;
    return link;
  }
  let data = [];
  let page = 0;
  function render() {
    const query = el("q").value.toLowerCase();
    const selected = data.filter(p =>
      (p.Package + " " + p.Description).toLowerCase().includes(query)
      && (!el("suite").value || p.Suite === el("suite").value)
      && (!el("component").value || p.Component === el("component").value)
      && (!el("arch").value || p.Architecture === el("arch").value)
      && (!el("meta").checked || (p.Section || "").endsWith("metapackages")));
    const groups = new Map();
    for (const record of selected) {
      if (!groups.has(record.Package)) groups.set(record.Package, []);
      groups.get(record.Package).push(record);
    }
    const packages = [...groups.values()];
    packages.forEach(versions => versions.sort((a, b) =>
      platform === "F-Droid" ? b.VersionCode - a.VersionCode :
        String(b.Version).localeCompare(String(a.Version), undefined, {numeric: true})));
    packages.sort((a, b) => String(a[0][el("sort").value]).localeCompare(
      String(b[0][el("sort").value]), undefined, {numeric: true}));
    const pages = Math.max(1, Math.ceil(packages.length / 25));
    page = Math.min(page, pages - 1);
    el("rows").replaceChildren();
    for (const versions of packages.slice(page * 25, (page + 1) * 25)) {
      const p = versions[0], card = document.createElement("details");
      card.className = "package-card";
      const summary = document.createElement("summary");
      const heading = text("span", "", "package-heading");
      heading.append(text("strong", p.Name || p.Package, "package-name"),
        text("span", p.Description.split("\n")[0], "package-description"));
      summary.append(heading, text("span", p.Version, "version"));
      const releases = text("div", "", "releases");
      for (const v of versions) {
        const release = text("div", "", "release");
        release.append(text("strong", "Version " + v.Version));
        release.append(text("p", [v.Architecture, v.Suite, v.Component].filter(Boolean).join(" / ")));
        release.append(text("p", v.Description));
        if (v.Depends) release.append(text("p", "Dependencies: " + v.Depends));
        if (platform === "Debian") release.append(text("p", "Source: " + (v.Source || v.Package)));
        if (platform === "F-Droid") release.append(text("p", v.Package + " · version code " + v.VersionCode));
        if (v.SHA256) release.append(text("p", "SHA-256: " + v.SHA256));
        if (v.Filename) release.append(download(v.Filename, v.DownloadLabel || "Download"));
        let command = v.Install;
        if (platform === "Debian") command = "sudo apt install " + v.Package;
        if (command) {
          release.append(text("pre", command));
          const button = text("button", "Copy install command");
          button.addEventListener("click", () => copy(command));
          release.append(button);
        }
        releases.append(release);
      }
      card.append(summary, releases);
      el("rows").append(card);
    }
    if (!packages.length) el("rows").append(text("p", "No packages match your selection.", "notice"));
    el("count").textContent = packages.length + (packages.length === 1 ? " package · " : " packages · ")
      + selected.length + (selected.length === 1 ? " release" : " releases");
    el("page").textContent = (page + 1) + " / " + pages;
    el("prev").disabled = page === 0;
    el("next").disabled = page === pages - 1;
  }
  function ready(rows) {
    data = rows;
    for (const [id, key] of [["suite", "Suite"], ["component", "Component"], ["arch", "Architecture"]]) {
      const values = [...new Set(data.map(p => p[key]).filter(Boolean))].sort();
      el(id + "-filter").hidden = !values.length;
      values.forEach(value => el(id).add(new Option(value, value)));
    }
    el("meta-filter").hidden = platform !== "Debian";
    render();
  }
  for (const id of ["q", "suite", "component", "arch", "sort", "meta"]) {
    el(id).addEventListener("input", () => { page = 0; render(); });
  }
  el("prev").addEventListener("click", () => { page--; render(); });
  el("next").addEventListener("click", () => { page++; render(); });
  async function load() {
    try {
      if (platform !== "F-Droid") {
        ready(JSON.parse(el("package-data").textContent));
        return;
      }
      const response = await fetch("/repo/index-v1.json", {credentials: "same-origin"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      const index = await response.json();
      if (!index.packages || !Array.isArray(index.apps)) throw new Error("Unsupported F-Droid index");
      const metadata = new Map(index.apps.map(app => [app.packageName, app]));
      const rows = [];
      for (const [id, versions] of Object.entries(index.packages)) {
        const meta = metadata.get(id) || {};
        for (const version of versions) {
          rows.push({
            Package: id, Name: meta.name || id, Version: version.versionName || String(version.versionCode),
            VersionCode: version.versionCode, Description: meta.summary || "",
            Architecture: (version.nativecode || []).join(", "),
            Filename: "/repo/" + encodeURIComponent(version.apkName), DownloadLabel: "Download APK",
            SHA256: version.hashType === "sha256" ? version.hash : "",
          });
        }
      }
      ready(rows);
    } catch (error) {
      el("count").textContent = "Could not load packages: " + error.message;
      el("count").classList.add("error");
      el("prev").disabled = el("next").disabled = true;
    }
  }
  load();
})();
