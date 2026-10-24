/* Deterministic dependency layout shared by preview and stored project views. */
(function (root) {
  "use strict";
  function layoutDag(tasks) {
    const byId = new Map();
    for (const task of tasks) {
      if (!task.task_id || byId.has(task.task_id)) throw new Error("Duplicate or missing task ID in plan");
      byId.set(task.task_id, task);
    }
    const level = new Map(), visiting = new Set();
    function depth(id) {
      if (level.has(id)) return level.get(id);
      if (visiting.has(id)) throw new Error("Cyclic task dependencies in plan");
      const task = byId.get(id);
      if (!task) throw new Error(`Unknown task dependency: ${id}`);
      visiting.add(id);
      const parents = task.depends_on || [];
      const result = parents.length ? Math.max(...parents.map(depth)) + 1 : 0;
      visiting.delete(id);
      level.set(id, result);
      return result;
    }
    for (const id of byId.keys()) depth(id);
    const columnWidth = 206, nodeHeight = 76, columnGap = 76, rowGap = 34, margin = 24;
    const layers = [];
    for (const task of tasks) {
      const index = level.get(task.task_id);
      (layers[index] ||= []).push(task);
    }
    const maxRows = Math.max(1, ...layers.map(layer => layer.length));
    const width = margin * 2 + layers.length * columnWidth + Math.max(0, layers.length - 1) * columnGap;
    const height = margin * 2 + maxRows * nodeHeight + Math.max(0, maxRows - 1) * rowGap;
    const nodes = [], positions = new Map();
    layers.forEach((layer, column) => {
      const usedHeight = layer.length * nodeHeight + Math.max(0, layer.length - 1) * rowGap;
      const top = margin + (height - margin * 2 - usedHeight) / 2;
      layer.forEach((task, row) => {
        const item = {task, x: margin + column * (columnWidth + columnGap),
          y: top + row * (nodeHeight + rowGap), width: columnWidth, height: nodeHeight,
          layer: column};
        nodes.push(item);
        positions.set(task.task_id, item);
      });
    });
    const edges = [];
    for (const task of tasks) for (const parent of task.depends_on || []) {
      edges.push({from: positions.get(parent), to: positions.get(task.task_id)});
    }
    return {width, height, nodes, edges, layers: layers.length};
  }
  root.schedulerDagLayout = layoutDag;
  if (typeof module === "object" && module.exports) module.exports = {layoutDag};
})(typeof window === "object" ? window : globalThis);
