import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const output=mkdtempSync(join(tmpdir(),"forenzx-state-tests-"));
try{
 const compilation=spawnSync(process.execPath,["node_modules/typescript/bin/tsc","tests/task-state.test.ts","lib/task-state.ts","lib/types.ts","--module","commonjs","--target","ES2022","--types","node,@cloudflare/workers-types","--skipLibCheck","--esModuleInterop","--strict","--outDir",output,"--noEmit","false"],{stdio:"inherit"});
 if(compilation.status!==0)process.exitCode=compilation.status??1;
 else{const tests=spawnSync(process.execPath,["--test",join(output,"tests/task-state.test.js")],{stdio:"inherit"});process.exitCode=tests.status??1;}
}finally{rmSync(output,{recursive:true,force:true});}

