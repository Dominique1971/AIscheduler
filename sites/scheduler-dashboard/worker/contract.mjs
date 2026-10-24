export class Failure extends Error {
  constructor(status, code) { super(code); this.status = status; }
}
const id = value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value);
export const states = new Set(["draft","queued","dependency-blocked","ready","starting","running","validating","completed","retrying","recovering","waiting-review","paused","failed","canceled","superseded"]);
export function command(input) {
  if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).some(k => !["action","project","task","value","confirmed"].includes(k))) throw new Failure(422,"invalid_command");
  const {action, project, task, value, confirmed} = input;
  if (["pause","resume","allocate","hold","unhold","retry"].includes(action)) {
    if (!id(project)) throw new Failure(422,"invalid_project");
    if (["hold","unhold","retry"].includes(action) ? !id(task) : task !== undefined) throw new Failure(422,"invalid_task");
    if (action === "allocate" ? !Number.isInteger(value) || value < 0 || value > 128 : value !== undefined) throw new Failure(422,"invalid_value");
    if (confirmed !== undefined) throw new Failure(422,"unexpected_confirmation");
    return {action,project,...(task ? {task} : {}),...(action === "allocate" ? {value} : {})};
  }
  if (["emergency-stop","start"].includes(action) && project === undefined && task === undefined && value === undefined) {
    if (action === "emergency-stop" && confirmed !== true || action === "start" && confirmed !== undefined) throw new Failure(422,"confirmation_required");
    return {action,...(action === "emergency-stop" ? {confirmed:true} : {})};
  }
  throw new Failure(422,"unsupported_action");
}
export function projectSnapshot(input) {
  if (!input || !Number.isFinite(Date.parse(input.updated_at)) || !Array.isArray(input.projects) || input.projects.length > 100 || !Number.isInteger(input.max_workers) || input.max_workers < 1 || input.max_workers > 128 || !Number.isInteger(input.workers) || input.workers < 0 || input.workers > 128) throw new Failure(422,"invalid_snapshot");
  let count=0;
  const projects=input.projects.map(p => {
    if (!id(p.project_id) || typeof p.display_name !== "string" || p.display_name.length > 200 || !Array.isArray(p.tasks) || !Number.isInteger(p.max_workers) || p.max_workers < 0 || p.max_workers > 128) throw new Failure(422,"invalid_project_snapshot");
    if(p.goal!==undefined&&(typeof p.goal!=="string"||p.goal.length>500))throw new Failure(422,"invalid_project_goal");
    const tasks=p.tasks.map(t => {
      if (++count > 1000 || !id(t.task_id) || typeof t.title !== "string" || t.title.length > 300 || !states.has(t.state) || !Array.isArray(t.depends_on) || t.depends_on.some(d => !id(d)) || !Number.isFinite(t.estimate_minutes) || t.estimate_minutes <= 0) throw new Failure(422,"invalid_task_snapshot");
      for (const key of ["started_at","ended_at"]) if (t[key] != null && !Number.isFinite(Date.parse(t[key]))) throw new Failure(422,"invalid_task_timestamp");
      if(t.description!==undefined&&(typeof t.description!=="string"||t.description.length>500))throw new Failure(422,"invalid_task_description");
      if(t.acceptance_criteria!==undefined&&(!Array.isArray(t.acceptance_criteria)||t.acceptance_criteria.length>8||t.acceptance_criteria.some(c=>typeof c!=="string"||c.length>300)))throw new Failure(422,"invalid_task_acceptance");
      return {task_id:t.task_id,title:t.title,description:t.description??"",acceptance_criteria:t.acceptance_criteria??[],state:t.state,depends_on:t.depends_on,estimate_minutes:t.estimate_minutes,started_at:t.started_at??null,ended_at:t.ended_at??null,attempt_count:Number.isInteger(t.attempt_count)?t.attempt_count:0};
    });
    const byId=new Map(tasks.map(t=>[t.task_id,t]));
    if(byId.size!==tasks.length)throw new Failure(422,"duplicate_task_id");
    const visiting=new Set(),done=new Set();
    function visit(taskId){
      if(done.has(taskId))return;
      if(visiting.has(taskId))throw new Failure(422,"cyclic_dependencies");
      const task=byId.get(taskId);if(!task)throw new Failure(422,"unknown_dependency");
      visiting.add(taskId);for(const dependency of task.depends_on)visit(dependency);visiting.delete(taskId);done.add(taskId);
    }
    for(const task of tasks)visit(task.task_id);
    return {project_id:p.project_id,display_name:p.display_name,goal:p.goal??"",paused:p.paused === true,max_workers:p.max_workers,tasks};
  });
  // Explicit reusable projection. Never send prompts, repository paths, stdout,
  // arbitrary errors, environment, credentials or complete task contracts to cloud.
  return {schema_version:"remote-snapshot/2",updated_at:input.updated_at,max_workers:input.max_workers,workers:input.workers,
    stopped:input.stopped === true,daemon:{healthy:input.daemon?.healthy === true},executor:"simulation-only",projects};
}
