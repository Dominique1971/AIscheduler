"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const terminal = new Set(["completed", "failed", "canceled", "superseded"]);
  const active = new Set(["starting", "running", "validating", "recovering"]);
  const symbols = {completed:"✓", running:"●", starting:"●", validating:"●", ready:"◇", queued:"◇", "dependency-blocked":"⊘", blocked:"⊘", retrying:"↻", recovering:"↻", failed:"!", paused:"Ⅱ", "waiting-review":"!", canceled:"×", superseded:"×", draft:"◇"};
  let snapshot = null, lastSuccess = 0, hours = 8, offset = 0, loading = false, updateFailed = false, authRequired = false, noticeTimer;
  let reviewedIntake = null, intakeGeneration = 0;
  let token = "";
  try { token = sessionStorage.getItem("scheduler-token") || ""; } catch (_) { /* Storage may be disabled; memory still works. */ }
  const localDate = value => value ? new Date(value).toLocaleString("en-US", {timeZone:"America/New_York",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",second:"2-digit"}) + " NY" : "Unavailable";
  const stamp = value => { const n = Date.parse(value); return Number.isFinite(n) ? n : null; };
  const node = (tag, text, className) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; };
  function announce(message) { $("notice").textContent = message; $("notice").style.display = "block"; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => { $("notice").style.display = "none"; }, 10000); }
  async function request(path, body) {
    const headers = {"Accept":"application/json"};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) { headers["Content-Type"] = "application/json"; headers["Idempotency-Key"] = crypto.randomUUID(); }
    const response = await fetch(`/api/v1${path}`, {method:body === undefined ? "GET" : "POST",headers,body:body === undefined ? undefined : JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(20000)});
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      if (response.status === 401) message = "Authentication required or token expired. Connect with a valid token.";
      if (response.status === 403) message = "This token cannot perform that action. A read-only token permits inspection only.";
      if (response.status === 404) message = "This operation is unavailable on the connected server.";
      if (response.status === 409) { const problem = await response.json().catch(()=>null); message = typeof problem?.message === "string" ? problem.message.slice(0,400) : "The project changed; preview again before importing."; }
      if (response.status === 422) { const problem = await response.json().catch(()=>null); if (typeof problem?.message === "string") message = problem.message.slice(0,400); }
      const error = new Error(message); error.status = response.status; throw error;
    }
    return response.status === 204 ? null : response.json();
  }
  async function refresh() {
    if (loading) return;
    loading = true; $("refresh").disabled = true;
    try {
      const data = await request("/snapshot");
      if (!data || !Array.isArray(data.projects) || !data.projects.every(p => Array.isArray(p.tasks))) throw new Error("Snapshot contract is invalid; retaining the last successful data.");
      snapshot = data; lastSuccess = Date.now(); updateFailed = false; authRequired = false;
      clearTimeout(noticeTimer); $("notice").style.display = "none"; render();
    } catch (error) {
      updateFailed = true; authRequired = error.status === 401;
      $("connection").textContent = authRequired ? "Connect required" : "Update failed";
      $("connection").classList.add("stale"); announce(error.message);
      if (authRequired && !$("auth-dialog").open) $("auth-dialog").showModal();
    }
    finally { loading = false; $("refresh").disabled = false; updateAge(); }
  }
  async function action(path, body, button) {
    button.disabled = true;
    try { await request(path, body); announce("Command accepted. Refreshing authoritative state."); await refresh(); }
    catch (error) { announce(error.message); }
    finally { button.disabled = false; }
  }
  function updateAge() {
    if (!lastSuccess) return;
    const sourceTime = stamp(snapshot.updated_at);
    const age = sourceTime === null ? null : Math.max(0, Math.floor((Date.now() - sourceTime) / 1000));
    const stale = age === null || age > 330 || Date.now() - lastSuccess > 330000;
    $("updated").textContent = `Source: ${localDate(snapshot.updated_at)} · ${age === null ? "age unavailable" : age < 60 ? `${age}s old` : `${Math.floor(age/60)}m old`}`;
    $("updated").classList.toggle("stale", stale);
    const daemonHealthy = snapshot.daemon?.healthy === true;
    if (!loading) { $("connection").textContent = authRequired ? "Connect required" : updateFailed ? "Update failed" : stale ? "Stale data" : !daemonHealthy ? "Daemon unhealthy at update" : snapshot.stopped ? "Emergency stop active" : `${snapshot.role === "reader" ? "Read only" : "Control"} · daemon healthy at update`; $("connection").classList.toggle("stale", stale || updateFailed || !daemonHealthy || snapshot.stopped); }
  }
  function showTask(project, task) {
    $("detail-title").textContent = task.title || task.task_id;
    const body = $("detail-body"); body.replaceChildren();
    const details = node("dl");
    const entries = {Project:project.display_name || project.project_id,"Task ID":task.task_id,State:task.state,Estimate:`${task.estimate_minutes ?? "Unavailable"} minutes`,Started:localDate(task.started_at),Ended:localDate(task.ended_at),Attempts:task.attempt_count ?? "Unavailable",Dependencies:(task.depends_on || []).join(", ") || "None",Error:task.error || "None reported"};
    for (const [key,value] of Object.entries(entries)) details.append(node("dt",key),node("dd",String(value)));
    body.append(details,node("p","Historical attempts, plan revisions, logs, and token usage are not included in this snapshot. Inspect the API or CLI for available records."));
    $("details").showModal();
  }
  function render() {
    const tasks = snapshot.projects.flatMap(p => p.tasks);
    const busy = Number.isFinite(snapshot.workers) ? snapshot.workers : tasks.filter(t => active.has(t.state)).reduce((sum,t)=>sum+(Number(t.resources?.slots)||1),0);
    const capacity = Number(snapshot.max_workers) || 0;
    const done = tasks.filter(t => t.state === "completed").length;
    const simulationOnly = snapshot.metrics?.forecast_confidence === "simulation-only" || tasks.length > 0 && tasks.every(t => t.executor === "simulation");
    $("completion-label").textContent = simulationOnly ? "Simulation completed" : "Completed task states";
    $("workers").textContent = `${busy} / ${capacity}`;
    $("idle").textContent = `${Math.max(0,capacity-busy)} global slots unoccupied`;
    $("ready").textContent = tasks.filter(t => t.state === "ready").length;
    $("blocked").textContent = `${tasks.filter(t => ["dependency-blocked","blocked"].includes(t.state)).length} dependency blocked`;
    $("complete").textContent = `${done} / ${tasks.length}`;
    $("percent").textContent = `${tasks.length ? Math.round(done/tasks.length*100) : 0}% complete`;
    $("utilization").textContent = capacity ? `${Math.round(busy/capacity*100)}%` : "—";
    $("warnings").textContent = `${tasks.filter(t => ["failed","waiting-review","recovering","retrying"].includes(t.state)).length} tasks need attention`;
    const selected = $("focus").value;
    $("focus").replaceChildren(new Option("All projects", ""), ...snapshot.projects.map(p => new Option(p.display_name || p.project_id,p.project_id)));
    if (snapshot.projects.some(p => p.project_id === selected)) $("focus").value = selected;
    const end = Date.now() + offset, start = end - hours*3600000;
    $("window-label").textContent = offset === 0 ? `Last ${hours} hours · New York time` : `${localDate(start)} → ${localDate(end)}`;
    const container = $("projects"); container.replaceChildren();
    container.classList.toggle("overview", !$("focus").value);
    const visible = snapshot.projects.filter(p => !$("focus").value || p.project_id === $("focus").value);
    for (const project of visible) renderProject(container,project,start,end);
    if (!visible.length) container.append(node("div","No projects imported. Import a validated dummy plan through the CLI.","empty"));
    renderTrends(tasks,start,end);
    $("operational").textContent = `${snapshot.daemon?.healthy ? "Daemon lease healthy" : "Daemon unhealthy: dispatch is not assured"}${snapshot.stopped ? " · EMERGENCY STOP ACTIVE" : ""}. ${simulationOnly ? "Simulation results do not verify arbitrary task acceptance criteria. " : ""}${snapshot.projects.filter(p => p.paused).length} projects paused · ${tasks.filter(t => t.state === "waiting-review").length} awaiting review. Historical utilization unavailable.`;
    updateAge();
  }
  function renderProject(container,project,start,end) {
    const section = node("article",undefined,"project"), head = node("div",undefined,"project-head"), description = node("div");
    const projectFocus = node("button",project.display_name || project.project_id,"project-name");
    projectFocus.title = "Focus this project's timeline and tasks";
    projectFocus.addEventListener("click",()=>{$("focus").value=project.project_id;render();});
    description.append(projectFocus);
    const busy = project.tasks.filter(t => active.has(t.state)).reduce((sum,t)=>sum+(Number(t.resources?.slots)||1),0);
    description.append(node("div",`${project.paused ? "Ⅱ Paused" : "● Dispatch enabled"} · ${busy} busy / ${project.max_workers ?? "—"} cap · ${project.tasks.length} tasks`,"project-meta"));
    const actions = node("div",undefined,"project-actions");
    const viewPlan = node("button","View plan");
    viewPlan.addEventListener("click",()=>showProjectPlan(project));
    const toggle = node("button",project.paused ? "Resume" : "Pause");
    toggle.addEventListener("click", () => action(`/projects/${encodeURIComponent(project.project_id)}/${project.paused ? "resume" : "pause"}`,{},toggle));
    const allocation = node("input"); allocation.type = "number"; allocation.min = "0"; allocation.max = String(snapshot.max_workers || 1000); allocation.step = "1"; allocation.value = project.max_workers ?? 0; allocation.setAttribute("aria-label",`${project.display_name || project.project_id} maximum workers`);
    const apply = node("button","Set cap");
    apply.addEventListener("click",() => { if (!allocation.checkValidity()) { allocation.reportValidity(); return; } action(`/projects/${encodeURIComponent(project.project_id)}/allocate`,{max_workers:Number(allocation.value)},apply); });
    actions.append(viewPlan,toggle,allocation,apply); head.append(description,actions); section.append(head);
    const timeline = node("div",undefined,"timeline"), axis = node("div",undefined,"axis");
    for(let i=0;i<=4;i++) axis.append(node("span",new Date(start+(end-start)*i/4).toLocaleTimeString("en-US",{timeZone:"America/New_York",hour:"numeric",minute:"2-digit"})));
    timeline.append(axis);
    const laneEnds = [], lanes = [], unscheduled = [];
    const sorted = [...project.tasks].sort((a,b)=>(stamp(a.started_at)??Infinity)-(stamp(b.started_at)??Infinity));
    for(const task of sorted) {
      const taskStart = stamp(task.started_at);
      if(taskStart === null) { unscheduled.push(task); continue; }
      const realEnd = stamp(task.ended_at);
      const estimatedEnd = taskStart + Math.max(1,Number(task.estimate_minutes)||1)*60000;
      const taskEnd = realEnd ?? (terminal.has(task.state) ? taskStart : Math.max(Date.now(),estimatedEnd));
      if(taskEnd < start || taskStart > end) continue;
      let lane = laneEnds.findIndex(time => time <= taskStart);
      if(lane < 0) {lane = laneEnds.length; laneEnds.push(0); const row = node("div",undefined,"lane"); row.setAttribute("aria-label",`Parallel lane ${lane+1}`); lanes.push(row); timeline.append(row);}
      laneEnds[lane] = taskEnd;
      const bar = node("button",`${symbols[task.state]||"?"} ${task.title || task.task_id} · ${task.state}`,`task ${Object.hasOwn(symbols,task.state) ? task.state : "queued"}`);
      const left = Math.max(start,taskStart), right = Math.min(end,taskEnd);
      bar.style.left = `${(left-start)/(end-start)*100}%`; bar.style.width = `${Math.max(.7,(right-left)/(end-start)*100)}%`;
      if(realEnd === null && !terminal.has(task.state)) bar.style.borderRightStyle = "dashed";
      bar.title = `${task.task_id}: ${task.title} · ${task.state}\nStarted ${localDate(task.started_at)}\n${realEnd === null ? "Dashed edge: estimated finish, not actual completion" : `Ended ${localDate(task.ended_at)}`}\nDependencies: ${(task.depends_on||[]).join(", ") || "none"}`;
      bar.setAttribute("aria-label",bar.title); bar.addEventListener("click",()=>showTask(project,task)); lanes[lane].append(bar);
    }
    if(lanes.length) section.append(timeline);
    else section.append(node("div","No recorded execution intersects this time window.","project-meta task-list"));
    if(project.tasks.length) {
      const chips = node("div",undefined,"task-list");
      for(const task of project.tasks) {const chip = node("button",`${symbols[task.state]||"?"} ${task.title || task.task_id} · ${task.state}`,`task-chip ${Object.hasOwn(symbols,task.state) ? task.state : "queued"}`); chip.title = `${task.state} · dependencies: ${(task.depends_on||[]).join(", ")||"none"}`; chip.addEventListener("click",()=>showTask(project,task)); chips.append(chip);}
      section.append(chips);
    }
    container.append(section);
  }
  function renderTrends(tasks,start,end) {
    const done = tasks.filter(t => t.state === "completed" && stamp(t.ended_at) !== null).sort((a,b)=>stamp(a.ended_at)-stamp(b.ended_at));
    const svg = $("completion-chart"); svg.replaceChildren();
    const counts = Array.from({length:25},(_,i)=>done.filter(t=>stamp(t.ended_at)<=start+(end-start)*i/24).length);
    const maximum = Math.max(1,...counts);
    if(done.length) { const line = document.createElementNS("http://www.w3.org/2000/svg","polyline"); line.setAttribute("points",counts.map((n,i)=>`${i/24*400},${60-n/maximum*52}`).join(" ")); line.setAttribute("fill","none"); line.setAttribute("stroke","#72dfb2"); line.setAttribute("stroke-width","2"); svg.append(line); }
    $("completion-caption").textContent = done.length ? "Cumulative completions from current task timestamps" : "No completed task timestamps available";
    const measured = done.filter(t=>stamp(t.started_at)!==null);
    const estimated = measured.reduce((s,t)=>s+(Number(t.estimate_minutes)||0),0);
    const actual = measured.reduce((s,t)=>s+Math.max(0,(stamp(t.ended_at)-stamp(t.started_at))/60000),0);
    const bars = $("duration-bars"); bars.replaceChildren();
    for(const [label,value] of [["Estimated",estimated],["Actual",actual]]) {const row=node("div",undefined,`duration-row ${label.toLowerCase()}`), track=node("div"), bar=node("i"); bar.style.width=`${value/Math.max(estimated,actual,1)*100}%`; track.append(bar); row.append(node("span",label),track,node("span",`${value.toFixed(1)}m`)); bars.append(row);}
    $("duration-caption").textContent = `${measured.length} completed tasks · elapsed duration, including waits`;
  }
  function downloadDraft(name, data) {
    const link = node("a"), url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
    link.href = url; link.download = name; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function downloadSource(name, sourceText) {
    const link = node("a"), url = URL.createObjectURL(new Blob([sourceText],{type:name.endsWith(".md")?"text/markdown":"application/json"}));
    link.href = url; link.download = name; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  let dagSequence = 0;
  function intakeGraph(tasks) {
    const graph = node("div",undefined,"intake-graph");
    const layout = window.schedulerDagLayout(tasks);
    const namespace = "http://www.w3.org/2000/svg", arrowId = `intake-arrow-${++dagSequence}`;
    const svgNode = (tag, attributes = {}, value) => {
      const element = document.createElementNS(namespace,tag);
      for (const [key, attribute] of Object.entries(attributes)) element.setAttribute(key,String(attribute));
      if (value !== undefined) element.textContent = value;
      return element;
    };
    const svg = svgNode("svg",{viewBox:`0 0 ${layout.width} ${layout.height}`,
      width:layout.width,height:layout.height,role:"img",
      "aria-label":`Task dependency graph: ${layout.nodes.length} tasks, ${layout.edges.length} dependency arrows`});
    const defs = svgNode("defs"), marker = svgNode("marker",{id:arrowId,markerWidth:9,markerHeight:9,
      refX:8,refY:4.5,orient:"auto",markerUnits:"userSpaceOnUse"});
    marker.append(svgNode("path",{d:"M 0 0 L 9 4.5 L 0 9 z",class:"dag-arrowhead"}));
    defs.append(marker); svg.append(defs);
    for (const edge of layout.edges) {
      const x1 = edge.from.x + edge.from.width + 2, y1 = edge.from.y + edge.from.height/2;
      const x2 = edge.to.x - 8, y2 = edge.to.y + edge.to.height/2;
      const bend = Math.max(24,(x2-x1)/2);
      const path = svgNode("path",{d:`M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}`,
        class:"dag-edge","marker-end":`url(#${arrowId})`});
      path.append(svgNode("title",{},`${edge.from.task.task_id} precedes ${edge.to.task.task_id}`));
      svg.append(path);
    }
    for (const item of layout.nodes) {
      const group = svgNode("g",{class:"dag-node"});
      group.append(svgNode("title",{},`${item.task.task_id}: ${item.task.title}; ${item.task.estimate_minutes} minutes`),
        svgNode("rect",{x:item.x,y:item.y,width:item.width,height:item.height,rx:8}),
        svgNode("text",{x:item.x+12,y:item.y+23,class:"dag-id"},item.task.task_id),
        svgNode("text",{x:item.x+12,y:item.y+45,class:"dag-title"},
          item.task.title.length > 25 ? `${item.task.title.slice(0,24)}…` : item.task.title),
        svgNode("text",{x:item.x+12,y:item.y+64,class:"dag-estimate"},`${item.task.estimate_minutes} min`));
      svg.append(group);
    }
    graph.append(svg);
    return graph;
  }
  async function showProjectPlan(project) {
    const content = $("plan-content"); content.replaceChildren(node("p","Loading reviewed plan…"));
    $("plan-title").textContent = `${project.display_name || project.project_id} · plan`;
    $("plan-dialog").showModal();
    try {
      const result = await request(`/projects/${encodeURIComponent(project.project_id)}/plan`);
      const summary = result.summary;
      content.replaceChildren(node("p",summary.description),
        node("p",`${summary.task_count} tasks · ${summary.total_estimate_minutes} minutes authored effort · ${summary.critical_path_estimate_minutes} minute dependency critical path. ${summary.estimate_note}`),
        node("p",`Revision ${result.revision} · plan SHA-256 ${result.plan_sha256}`),
        node("h3","Dependency graph"),intakeGraph(summary.tasks));
      if (result.source) content.append(node("p",`Intake SHA-256 ${result.source.source_sha256} · ${result.source.transform_version}`));
      const list = node("ol");
      for (const task of summary.tasks) {
        const item = node("li");
        item.append(node("strong",`${task.title} (${task.task_id})`),node("p",task.description),
          node("p",`${task.estimate_minutes} min · after ${task.depends_on.join(", ") || "nothing"}`),
          node("p",`Acceptance: ${task.acceptance_criteria.join("; ")}`));
        list.append(item);
      }
      content.append(node("h3","Task details"),list);
    } catch(error) {content.replaceChildren(node("p",error.message,"intake-error"));}
  }
  async function loadExamples() {
    const catalog = $("example-catalog"); catalog.replaceChildren(node("p","Loading packaged examples…"));
    try {
      const data = await request("/examples"); catalog.replaceChildren(node("h3","Packaged examples"));
      for (const example of data.items) {
        const card = node("div",undefined,"example-card");
        const button = node("button",`Review ${example.intake.display_name}`); button.type = "button";
        button.addEventListener("click",async()=>{
          button.disabled=true; intakeGeneration++; const generation=intakeGeneration;
          try {
            const draft=await request("/intake/preview",{intake:example.intake});
            const diff=await request("/plans/preview",{plan:draft.plan});
            if(generation!==intakeGeneration)return;
            reviewedIntake={draft,diff,source:example.intake,filename:`${example.id}-intake.json`,mode:"catalog"}; showIntakeResult(draft,example.intake,diff);
            $("intake-result").scrollIntoView({behavior:"smooth",block:"start"});
          } catch(error) {$("intake-result").replaceChildren(node("p",error.message,"intake-error"));}
          finally {button.disabled=false;}
        });
        card.append(button,node("p",example.intake.description),
          node("small",`${example.summary.task_count} tasks · ${example.summary.total_estimate_minutes} min effort · ${example.summary.critical_path_estimate_minutes} min critical path`));
        catalog.append(card);
      }
    } catch(error) {catalog.replaceChildren(node("p",error.message,"intake-error"));}
  }
  function showIntakeResult(draft, source, diff) {
    const target = $("intake-result"); target.replaceChildren();
    target.append(node("h3","Review before import"),node("p",`${source.display_name} (${source.project_id}) · ${source.repository.path} at ${source.repository.base_branch}`),
      node("p",source.description),
      node("p",`${draft.summary.task_count} tasks · ${draft.summary.total_estimate_minutes} minutes of authored effort · ${draft.summary.critical_path_estimate_minutes} minute dependency critical path. These are estimates, not delivery forecasts.`),
      node("p",draft.summary.execution_note),
      node("p",`Source SHA-256: ${draft.source_sha256} · Plan SHA-256: ${draft.plan_sha256} · Transform: ${draft.transform_version}`),
      node("h3","Dependencies"),intakeGraph(draft.summary.tasks));
    const list = node("ol");
    for (const task of draft.summary.tasks) {
      const item = node("li"), title = node("strong",`${task.task_id}: ${task.title}`);
      item.append(title,node("p",task.description),node("p",`${task.estimate_minutes} min · depends on ${task.depends_on.join(", ") || "nothing"} · ${task.executor}`),
        node("p",`Acceptance: ${task.acceptance_criteria.join("; ")}`)); list.append(item);
    }
    target.append(node("h3","Task details"),list,node("p",`Operational defaults added: ${draft.defaults_applied.join(", ") || "none"}.`),
      node("p",`Plan preview: ${diff.risk} · revision ${diff.from_revision ?? "new"} → ${diff.to_revision}. Added: ${diff.added.join(", ") || "none"}; modified: ${diff.modified.join(", ") || "none"}; removed: ${diff.removed.join(", ") || "none"}.`));
    const actions = node("div",undefined,"dialog-actions");
    const sourceButton = node("button","Download reviewed source"), reviewedFilename=reviewedIntake?.filename || `${source.project_id}-intake.json`; sourceButton.type = "button";
    sourceButton.addEventListener("click",()=>downloadSource(reviewedFilename,draft.source_text)); actions.append(sourceButton);
    for (const [label,suffix,data] of [["Download canonical plan","plan.json",draft.plan],
      ["Download provenance","provenance.json",Object.fromEntries(Object.entries(draft).filter(([key])=>key!=="plan"&&key!=="source_text"))]]) {
      const button = node("button",label); button.type = "button";
      button.addEventListener("click",()=>downloadDraft(`${source.project_id}-${suffix}`,data)); actions.append(button);
    }
    target.append(actions);
    const repositoryPath = source.repository.path.replaceAll("\\","/");
    const safeDummy = /^(demo|dummy)-/.test(source.project_id) &&
      /^(?:\.\/)?runtime\/[^/]/.test(repositoryPath) &&
      !repositoryPath.split("/").some(part=>part==="..") &&
      draft.plan.tasks.every(task=>task.executor==="simulation") && diff.from_revision===null;
    if (safeDummy) {
      const approval = node("label",undefined,"intake-approval"), check = node("input");
      check.type = "checkbox";
      approval.append(check,node("span","I reviewed the source, tasks, dependencies, defaults and plan preview. Import this new disposable simulation project."));
      const apply = node("button","Import reviewed dummy plan"); apply.type = "button"; apply.disabled = true;
      check.addEventListener("change",()=>{apply.disabled=!check.checked;});
      apply.addEventListener("click",async()=>{
        const reviewed = reviewedIntake;
        if (!reviewed || reviewed.draft !== draft || !check.checked) return;
        const generation = intakeGeneration;
        apply.disabled = true;
        try {
          const current = await request("/plans/preview",{plan:draft.plan});
          if (JSON.stringify(current) !== JSON.stringify(diff)) throw new Error("The plan preview changed. Preview the intake again before importing.");
          if (generation !== intakeGeneration || reviewedIntake !== reviewed) throw new Error("Inputs changed. Preview the intake again before importing.");
          const fileControl = $("intake-file"); fileControl.disabled=true;
          let result;
          try {
            result = reviewed.mode === "markdown"
              ? await request("/intake/file/import",{filename:reviewed.filename,source_text:draft.source_text,expected_source_sha256:draft.source_sha256,expected_preview:diff,approved:true})
              : await request("/intake/import",{intake:source,expected_source_sha256:draft.source_sha256,expected_preview:diff,approved:true});
          } finally { fileControl.disabled=false; }
          reviewedIntake = null; check.disabled = true;
          target.append(node("p",`Imported ${result.project_id} revision ${result.to_revision}. Refreshing authoritative state.`,"intake-success"));
          await refresh();
        } catch(error) { target.append(node("p",error.message,"intake-error")); }
        finally { if (reviewedIntake === reviewed) apply.disabled = !check.checked; }
      });
      target.append(approval,apply);
    } else {
      target.append(node("p","Dashboard import is limited to new demo-/dummy- simulation projects under ./runtime/. Review other plans through the CLI and its separate approval workflow."));
    }
    target.append(node("p","Preview and downloads do not import or start work. Import may make queued simulation tasks eligible for a running daemon."));
  }
  $("refresh").addEventListener("click",refresh);
  $("intake-open").addEventListener("click",()=>{$("intake-dialog").showModal();loadExamples();});
  $("plan-close").addEventListener("click",()=>$("plan-dialog").close());
  $("intake-close").addEventListener("click",()=>$("intake-dialog").close());
  $("intake-file").addEventListener("change",()=>{intakeGeneration++;reviewedIntake=null;$("intake-result").replaceChildren();});
  $("intake-file-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const file = $("intake-file").files?.[0];
    if (!file) {$("intake-file").reportValidity();return;}
    const button = $("intake-preview"), generation = ++intakeGeneration; button.disabled = true;
    try {
      if (!/^[A-Za-z0-9_.-]{1,124}\.md$/.test(file.name) || file.size > 512*1024) throw new Error("Choose a .md file under 512 KiB with a simple filename.");
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (bytes[0]===0xef && bytes[1]===0xbb && bytes[2]===0xbf) throw new Error("Save the Markdown file as UTF-8 without a byte-order mark.");
      const sourceText = new TextDecoder("utf-8",{fatal:true}).decode(bytes);
      const draft = await request("/intake/file/preview",{filename:file.name,source_text:sourceText});
      const diff = await request("/plans/preview",{plan:draft.plan});
      if (generation !== intakeGeneration) return;
      reviewedIntake = {draft,diff,source:draft.intake,filename:file.name,mode:"markdown"}; showIntakeResult(draft,draft.intake,diff);
    }
    catch(error) { $("intake-result").replaceChildren(node("p",error.message,"intake-error")); }
    finally { button.disabled = false; }
  });
  $("credentials").addEventListener("click",()=>{ $("token").value=token; $("auth-dialog").showModal(); });
  $("auth-cancel").addEventListener("click",()=>$("auth-dialog").close());
  $("auth-form").addEventListener("submit",event=>{event.preventDefault(); token=$("token").value.trim(); try {sessionStorage.setItem("scheduler-token",token);} catch (_) {} $("token").value=""; $("auth-dialog").close(); refresh();});
  $("close-details").addEventListener("click",()=>$("details").close());
  $("zoom").addEventListener("change",()=>{hours=Number($("zoom").value);if(snapshot)render();});
  $("earlier").addEventListener("click",()=>{offset-=hours*3600000/2;if(snapshot)render();});
  $("later").addEventListener("click",()=>{offset=Math.min(0,offset+hours*3600000/2);if(snapshot)render();});
  $("now").addEventListener("click",()=>{offset=0;if(snapshot)render();});
  $("focus").addEventListener("change",()=>{if(snapshot)render();});
  $("emergency").addEventListener("click",()=>$("stop-dialog").showModal());
  $("stop-cancel").addEventListener("click",()=>$("stop-dialog").close());
  $("stop-form").addEventListener("submit",event=>{event.preventDefault();$("stop-dialog").close();action("/system/emergency-stop",{confirmed:true},$("emergency"));});
  setInterval(refresh,300000); setInterval(updateAge,10000); refresh();
})();
