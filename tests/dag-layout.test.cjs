const assert = require('node:assert/strict');
const {test} = require('node:test');
const {layoutDag} = require('../scheduler/static/dag-layout.js');

test('positions independent roots, forks, and a three-way join from dependencies', () => {
  const tasks = [
    {task_id:'publish',depends_on:['review','security','assets']},
    {task_id:'review',depends_on:['draft']},
    {task_id:'security',depends_on:['draft']},
    {task_id:'assets',depends_on:['source']},
    {task_id:'draft',depends_on:['source']},
    {task_id:'source',depends_on:[]},
    {task_id:'unrelated',depends_on:[]},
  ];
  const result = layoutDag(tasks);
  const byId = new Map(result.nodes.map(item => [item.task.task_id,item]));
  assert.equal(result.nodes.length,7);
  assert.equal(result.edges.length,7);
  assert.equal(result.layers,4);
  assert.equal(byId.get('source').layer,0);
  assert.equal(byId.get('unrelated').layer,0);
  assert.equal(byId.get('publish').layer,3);
  for (const edge of result.edges) assert.ok(edge.from.x < edge.to.x);
  assert.deepEqual(result.edges.filter(edge => edge.to.task.task_id === 'publish')
    .map(edge => edge.from.task.task_id),['review','security','assets']);
});

test('rejects invalid dependencies rather than drawing a misleading graph', () => {
  assert.throws(() => layoutDag([{task_id:'a',depends_on:['missing']}]),/Unknown task dependency/);
  assert.throws(() => layoutDag([{task_id:'a',depends_on:['b']},{task_id:'b',depends_on:['a']}]),/Cyclic/);
  assert.throws(() => layoutDag([{task_id:'a'},{task_id:'a'}]),/Duplicate/);
});
