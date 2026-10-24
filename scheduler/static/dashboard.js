"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const terminal = new Set(["completed", "failed", "canceled", "superseded"]);
  const active = new Set(["starting", "running", "validating", "recovering"]);
  const symbols = {completed:"✓", running:"●", starting:"●", validating:"●", ready:"◇", queued:"◇", "dependency-blocked":"⊘", blocked:"⊘", retrying:"↻", recovering:"↻", failed:"!", paused:"Ⅱ", "waiting-review":"!", canceled:"×", superseded:"×", draft:"◇"};
  let snapshot = null, lastSuccess = 0, hours = 8, offset = 0, loading = false, updateFailed = false, noticeTimer;
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
      throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
  }
  async function refresh() {
    if (loading) return;
    loading = true; $("refresh").disabled = true;
    try {
      const data = await request("/snapshot");
      if (!data || !Array.isArray(data.projects) || !data.projects.every(p => Array.isArray(p.tasks))) throw new Error("Snapshot contract is invalid; retaining the last successful data.");
      snapshot = data; lastSuccess = Date.now(); updateFailed = false;
      clearTimeout(noticeTimer); $("notice").style.display = "none"; render();
    } catch (error) { updateFailed = true; $("connection").textContent = "Update failed"; $("connection").classList.add("stale"); announce(error.message); }
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
    if (!loading) { $("connection").textContent = updateFailed ? "Update failed" : stale ? "Stale data" : !daemonHealthy ? "Daemon unhealthy at update" : snapshot.stopped ? "Emergency stop active" : `${snapshot.role === "reader" ? "Read only" : "Control"} · daemon healthy at update`; $("connection").classList.toggle("stale", stale || updateFailed || !daemonHealthy || snapshot.stopped); }
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
    const toggle = node("button",project.paused ? "Resume" : "Pause");
    toggle.addEventListener("click", () => action(`/projects/${encodeURIComponent(project.project_id)}/${project.paused ? "resume" : "pause"}`,{},toggle));
    const allocation = node("input"); allocation.type = "number"; allocation.min = "0"; allocation.max = String(snapshot.max_workers || 1000); allocation.step = "1"; allocation.value = project.max_workers ?? 0; allocation.setAttribute("aria-label",`${project.display_name || project.project_id} maximum workers`);
    const apply = node("button","Set cap");
    apply.addEventListener("click",() => { if (!allocation.checkValidity()) { allocation.reportValidity(); return; } action(`/projects/${encodeURIComponent(project.project_id)}/allocate`,{max_workers:Number(allocation.value)},apply); });
    actions.append(toggle,allocation,apply); head.append(description,actions); section.append(head);
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
  $("refresh").addEventListener("click",refresh);
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
