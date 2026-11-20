import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
const tasks=JSON.parse(readFileSync(new URL("../data/backlog.json",import.meta.url),"utf8"));
const sources=[...JSON.parse(readFileSync(new URL("../data/sources.json",import.meta.url),"utf8")),...JSON.parse(readFileSync(new URL("../data/engineering-sources.json",import.meta.url),"utf8"))];
const ids=new Set(tasks.map(t=>t.id)), sourceIds=new Set(sources.map(s=>s.id));
assert.equal(ids.size,tasks.length,"Duplicate task ID");
assert.equal(sourceIds.size,sources.length,"Duplicate source ID");
for(const task of tasks){
 assert(task.acceptance.length>0,task.id+" missing acceptance");
 assert.equal(new Set(task.acceptance).size,task.acceptance.length,task.id+" duplicate acceptance criteria");
 assert.equal(new Set(task.dependencies).size,task.dependencies.length,task.id+" duplicate dependency");
 for(const id of task.dependencies)assert(ids.has(id),task.id+" unknown dependency "+id);
 for(const id of task.sourceIds)assert(sourceIds.has(id),task.id+" unknown source "+id);
 if(task.status==="done"){assert(task.evidence.trim());assert.deepEqual([...task.checks].sort((a,b)=>a-b),task.acceptance.map((_,i)=>i));for(const id of task.dependencies)assert.equal(tasks.find(t=>t.id===id).status,"done");}
}
function walk(id,trail){assert(!trail.includes(id),"Dependency cycle: "+[...trail,id].join(" -> "));for(const child of tasks.find(t=>t.id===id).dependencies)walk(child,[...trail,id]);}
tasks.forEach(t=>walk(t.id,[]));
console.log("Catalog valid: "+tasks.length+" tasks, "+tasks.filter(t=>t.gate).length+" gates, "+sources.length+" sources.");

