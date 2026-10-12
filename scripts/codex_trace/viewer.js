(() => {
  const report = JSON.parse(document.getElementById("report-data").textContent);
  const spec = JSON.parse(document.getElementById("chart-spec").textContent);
  const actions = new Map(report.actions.map((a) => [a.id, a]));
  const $ = (id) => document.getElementById(id);
  $("summary").textContent =
    `${report.actions.length.toLocaleString()} actions · ${report.agents.length} agent lanes · ${report.thread}`;
  $("origin").textContent =
    `Origin: ${new Date(report.origin_ms).toISOString()}`;
  $("sources").textContent = JSON.stringify(report.boundaries, null, 2);
  if (report.diagnostics.length) {
    const box = document.createElement("details");
    const title = document.createElement("summary");
    title.textContent = `Incomplete data / diagnostics (${report.diagnostics.length})`;
    box.append(title);
    const list = document.createElement("ul");
    for (const text of report.diagnostics) {
      const li = document.createElement("li");
      li.textContent = text;
      list.append(li);
    }
    box.append(list);
    $("notices").append(box);
  }
  function section(title, value, open = false) {
    const d = document.createElement("details");
    d.open = open;
    const s = document.createElement("summary");
    s.textContent = title;
    const p = document.createElement("pre");
    p.textContent =
      typeof value === "string" ? value : JSON.stringify(value, null, 2);
    d.append(s, p);
    return d;
  }
  function selectAction(id) {
    const a = actions.get(id);
    if (!a) return;
    const pane = $("details");
    pane.replaceChildren();
    const title = document.createElement("h2");
    title.textContent = a.name;
    pane.append(title);
    const anchor = [a.start, a.observed_start, a.end, a.observed_end].find(
      (v) => v !== null,
    );
    if (anchor !== undefined) {
      const focus = document.createElement("button");
      focus.textContent = "Zoom to action";
      focus.onclick = () => {
        const left = (anchor - report.origin_ms) / 1000;
        const end = a.start !== null ? a.end : a.observed_end;
        const span = Math.max(0.5, end !== null ? (end - anchor) / 1000 : 0.5);
        view
          .signal("time_window_start", [left - span / 2, left + span * 1.5])
          .runAsync();
        $("scroll").scrollTop = Math.max(0, a.row * 26 - 80);
      };
      pane.append(focus);
    }
    const facts = {
      agent: a.thread,
      turn: a.turn,
      status: a.status,
      category: a.category,
      start_utc: a.start_utc,
      end_utc: a.end_utc,
      duration: a.duration,
      duration_ms: a.duration_ms,
      observed_start_utc: a.observed_start_utc,
      observed_end_utc: a.observed_end_utc,
      timing: a.timing,
      parent: a.parent,
      nesting_depth: a.depth,
    };
    pane.append(section("Timing and identity", facts, true));
    for (const [source, value] of Object.entries(a.details))
      pane.append(section(source, value));
  }
  let category = "All",
    limit = 100,
    view;
  function updateList() {
    const query = $("search").value.toLowerCase();
    const matching = report.actions.filter(
      (a) =>
        (category === "All" || a.category === category) &&
        `${a.name} ${a.id}`.toLowerCase().includes(query),
    );
    $("action-count").textContent = `(${matching.length})`;
    $("action-list").replaceChildren();
    for (const a of matching.slice(0, limit)) {
      const b = document.createElement("button");
      const untimed = [a.start, a.end, a.observed_start, a.observed_end].every(
        (v) => v === null,
      );
      b.textContent = `${untimed ? "[untimed] " : ""}${a.category} · ${a.name}`;
      b.onclick = () => selectAction(a.id);
      $("action-list").append(b);
    }
    $("more").hidden = matching.length <= limit;
  }
  $("search").addEventListener("input", () => {
    limit = 100;
    updateList();
  });
  $("more").onclick = () => {
    limit += 100;
    updateList();
  };
  updateList();
  async function draw(focusLongest = true) {
    if (view) view.finalize();
    const result = await vegaEmbed("#chart", spec, {
      actions: false,
      renderer: "canvas",
    });
    view = result.view;
    if (focusLongest)
      await view.signal("time_window_start", spec.usermeta.initial_window).runAsync();
    view.addEventListener("click", (_, item) => {
      if (item && item.datum && item.datum.id) selectAction(item.datum.id);
    });
    view.addSignalListener("category", (_, value) => {
      category = value;
      limit = 100;
      updateList();
    });
    category = "All";
    updateList();
    const scale = view.scale("y");
    const padding = view.padding();
    $("lane-content").style.marginTop = `${padding.top + view.origin()[1]}px`;
    $("lane-content").style.height = `${view.height()}px`;
    $("lane-content").replaceChildren();
    for (const agent of report.agents) {
      const lane = document.createElement("div");
      lane.className = "lane";
      lane.style.top = `${scale(agent.row_start)}px`;
      lane.style.height = `${Math.max(24, scale(agent.row_start + agent.row_count) - scale(agent.row_start))}px`;
      lane.title = `${agent.id}\n${agent.title}`;
      const label = document.createElement("strong");
      label.textContent = agent.label;
      const count = document.createElement("small");
      count.textContent = agent.id.slice(0, 8);
      lane.append(label, count);
      $("lane-content").append(lane);
    }
    window.chartView = view;
    window.chartReady = true;
  }
  $("reset").onclick = () =>
    draw(false).catch((e) => {
      $("error").textContent = e.message;
    });
  draw().catch((e) => {
    $("error").textContent = e.message;
    window.chartError = e.message;
  });
})();
