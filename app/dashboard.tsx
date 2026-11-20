"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Task, Source, TaskStatus as Status, TaskPhase as Phase } from "@/lib/types";
import { Activity, AlertCircle, ArrowDownToLine, BookOpen, Check, CheckCircle2, ChevronRight, Circle, Clock3, CloudCheck, ExternalLink, FileCheck2, Fingerprint, Flag, GitBranch, GitCommitHorizontal, LayoutList, LoaderCircle, LockKeyhole, Search, ShieldCheck, X, RefreshCw, ListChecks, Link2, FileText, ScanLine } from "lucide-react";

type Payload = {tasks:Task[]; sources:Source[]; meta:{baselineCommit:string; repositoryUrl:string; productPrice:string|number; deadline:string}; syncedAt:string};
type View = "backlog" | "quality" | "sources";
const phases:Phase[] = ["Základ","Integrácia","Kvalita","Balenie","Predaj"];
const statusNames:Record<Status,string> = {todo:"Čaká",in_progress:"Rozpracované",blocked:"Blokované",done:"Hotové"};

function StatusIcon({status,size=21}:{status:Status;size?:number}){return status==="done"?<CheckCircle2 size={size}/>:status==="blocked"?<AlertCircle size={size}/>:status==="in_progress"?<Activity size={size}/>:<Circle size={size}/>}
function shortTime(value:string){const date=new Date(value);return Number.isNaN(date.getTime())?"práve teraz":new Intl.DateTimeFormat("sk-SK",{hour:"2-digit",minute:"2-digit",timeZone:"Europe/Bratislava"}).format(date)}
function progress(items:Task[]){return items.length?Math.round(items.filter(t=>t.status==="done").length/items.length*100):0}

export default function Dashboard(){
  const [data,setData]=useState<Payload|null>(null);
  const [loading,setLoading]=useState(true);
  const [refreshing,setRefreshing]=useState(false);
  const [error,setError]=useState("");
  const [exportError,setExportError]=useState("");
  const [exporting,setExporting]=useState(false);
  const [authRequired,setAuthRequired]=useState(false);
  const [view,setView]=useState<View>("backlog");
  const [query,setQuery]=useState("");
  const [phase,setPhase]=useState("all");
  const [status,setStatus]=useState("all");
  const [priority,setPriority]=useState("all");
  const [selectedId,setSelectedId]=useState<string|null>(null);
  const [toast,setToast]=useState("");
  const refresh=useCallback(async()=>{
    setRefreshing(true);setError("");setExportError("");setAuthRequired(false);
    try{const response=await fetch("/api/tasks",{cache:"no-store"});if(response.status===401)setAuthRequired(true);const payload=await response.json().catch(()=>null) as (Payload & {error?:string})|null;if(!response.ok)throw new Error(payload?.error||"Úlohy sa nepodarilo načítať.");if(!payload||!Array.isArray(payload.tasks)||!Array.isArray(payload.sources)||!payload.meta)throw new Error("Server nevrátil očakávané údaje backlogu. Skús načítanie znova.");setData(payload)}catch(err){setError(err instanceof Error?err.message:"Úlohy sa nepodarilo načítať.")}finally{setLoading(false);setRefreshing(false)}
  },[]);
  const exportBacklog=async()=>{
    setExporting(true);setExportError("");
    try{
      const response=await fetch("/api/export",{cache:"no-store"});
      if(response.status===401)setAuthRequired(true);
      const snapshot=await response.json().catch(()=>null) as {error?:string;formatVersion?:number;tasks?:unknown[]}|null;
      if(!response.ok)throw new Error(snapshot?.error||"Export sa nepodaril. Skús to znova.");
      if(!snapshot||snapshot.formatVersion!==1||!Array.isArray(snapshot.tasks))throw new Error("Server nevrátil platný export backlogu. Skús to znova.");
      const href=URL.createObjectURL(new Blob([JSON.stringify(snapshot,null,2)],{type:"application/json"}));
      const link=document.createElement("a");link.href=href;link.download=`forenzx-backlog-${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
      setAuthRequired(false);setToast("Export backlogu je pripravený na stiahnutie.");
    }catch(err){setExportError(err instanceof Error?err.message:"Export sa nepodaril.")}finally{setExporting(false)}
  };
  useEffect(()=>{void refresh()},[refresh]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(""),4200);return()=>clearTimeout(timer)},[toast]);
  const tasks=data?.tasks??[];
  const gates=tasks.filter(t=>t.gate);
  const done=tasks.filter(t=>t.status==="done").length;
  const doneGates=gates.filter(t=>t.status==="done").length;
  const openP0=tasks.filter(t=>t.priority==="P0"&&t.status!=="done").length;
  const blocked=tasks.filter(t=>t.status==="blocked").length;
  const selected=tasks.find(t=>t.id===selectedId);
  const taskMap=useMemo(()=>new Map(tasks.map(t=>[t.id,t])),[tasks]);
  const dependenciesDone=(task:Task)=>task.dependencies.every(id=>taskMap.get(id)?.status==="done");
  const nextTask=tasks.find(t=>t.status==="in_progress"&&dependenciesDone(t))??tasks.find(t=>t.status==="todo"&&t.priority==="P0"&&dependenciesDone(t))??tasks.find(t=>t.status==="todo"&&dependenciesDone(t));
  const filtered=tasks.filter(t=>(phase==="all"||t.phase===phase)&&(status==="all"||t.status===status)&&(priority==="all"||t.priority===priority)&&`${t.id} ${t.title} ${t.description}`.toLocaleLowerCase("sk").includes(query.trim().toLocaleLowerCase("sk")));
  const hasFilters=query||phase!=="all"||status!=="all"||priority!=="all";
  const releaseReady=gates.length>0&&doneGates===gates.length&&openP0===0;
  const viewNames:Record<View,string>={backlog:"Backlog",quality:"Brány kvality",sources:"Odborné zdroje"};
  const saveTask=async(task:Task,patch:{status:Status;evidence:string;checks:number[]})=>{
    const response=await fetch(`/api/tasks/${encodeURIComponent(task.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({...patch,revision:task.revision})});
    const payload=await response.json() as {task:Task;error?:string};
    if(!response.ok)throw new Error(payload.error||"Uloženie sa nepodarilo. Skús to znova.");
    setData(current=>current?{...current,tasks:current.tasks.map(t=>t.id===task.id?payload.task:t),syncedAt:new Date().toISOString()}:current);
    setSelectedId(null);setToast(`${task.id} · Zmeny sú uložené.`);
  };
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Navigácia pracovného priestoru">
      <a className="brand" href="/" aria-label="ForenZX Release Board"><span className="brand-mark"><Fingerprint size={27} strokeWidth={1.8}/></span><span><span className="brand-name">Foren<span>ZX</span></span><span className="brand-caption">RELEASE BOARD</span></span></a>
      <p className="workspace-label">PRACOVNÝ PRIESTOR</p>
      <nav className="main-nav" aria-label="Sekcie dashboardu">
        {([{id:"backlog",label:"Backlog",Icon:LayoutList},{id:"quality",label:"Brány kvality",Icon:ShieldCheck},{id:"sources",label:"Odborné zdroje",Icon:BookOpen}] as const).map(({id,label,Icon})=><button type="button" key={id} className={`nav-button ${view===id?"active":""}`} aria-current={view===id?"page":undefined} onClick={()=>setView(id)}><Icon size={18}/>{label}{id==="backlog"&&data&&<span className="nav-count">{tasks.length}</span>}</button>)}
      </nav>
      <div className="sidebar-project"><p className="small-label">Aktívny produkt</p><p className="project-label">ForenZX<br/>Analysis Brief</p><span className="project-version">Prvé vydanie · v0.1</span></div>
      <div className="sidebar-footer"><p className="privacy-label"><LockKeyhole size={13}/>Súkromný pracovný priestor</p><p className="vorkei-label">VORKEI</p></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="breadcrumbs"><span>ForenZX Analysis Brief</span><ChevronRight size={14}/><strong>{viewNames[view]}</strong></div><div className="topbar-actions"><span className="private-badge"><LockKeyhole size={12}/>Súkromné</span><span className="avatar" aria-label="Pracovný priestor VORKEI">VK</span></div></header>
      <main className="main-content" id="main-content">
        <div className="page-heading"><div><p className="eyebrow">OD OVERENIA K PRVÉMU VYDANIU</p><h1>{view==="backlog"?"Prehľad vydania":view==="quality"?"Kvalita má svoje podmienky.":"Podklady, o ktoré sa opierame."}</h1><p>{view==="backlog"?"Jeden workflow. Jasné úlohy. Ku každému splnenému bodu overiteľný podklad.":view==="quality"?"Rozsah, funkčnosť a presnosť výsledku musia byť preukázané pred predajom.":"Odborné definície, technické pravidlá a zdroje použité pri návrhu produktu."}</p></div><div className="heading-actions"><button type="button" className="button secondary" onClick={()=>void refresh()} disabled={refreshing}><RefreshCw size={15} className={refreshing?"spin":""}/>{refreshing?"Načítavam":"Obnoviť"}</button>{data&&<button type="button" className="button" onClick={()=>void exportBacklog()} disabled={exporting}>{exporting?<LoaderCircle size={15} className="spin"/>:<ArrowDownToLine size={15}/>} {exporting?"Pripravujem export…":"Export backlogu"}</button>}</div></div>
        {loading?<div className="loading-state" aria-live="polite"><p className="loading-label"><LoaderCircle className="spin" size={18}/>Načítavam uložený backlog…</p><div className="skeleton"/><div className="skeleton tall"/></div>:<>
          {(error||exportError)&&<div className="error-box" role="alert"><AlertCircle size={19}/><div><p>{error||exportError}</p>{authRequired?<a className="button primary" href="/signin-with-chatgpt?return_to=/" target="_top">Prihlásiť sa do pracovného priestoru</a>:<button className="button secondary compact" type="button" onClick={()=>void (exportError&&!error?exportBacklog():refresh())} disabled={refreshing||exporting}>Skúsiť znova</button>}</div></div>}
          {data&&<>
            <section className="metrics-grid" aria-label="Stav prípravy produktu">
              <div className="metric"><div className="metric-top"><span>Celkový postup</span><ListChecks size={17}/></div><div className="metric-value">{done}<span className="metric-denominator"> / {tasks.length}</span></div><p className="metric-note">úloh je doložených a hotových</p><div className="mini-progress" role="progressbar" aria-label="Dokončené úlohy" aria-valuenow={progress(tasks)} aria-valuemin={0} aria-valuemax={100}><span style={{width:`${progress(tasks)}%`}}/></div></div>
              <div className="metric"><div className="metric-top"><span>Povinné brány</span><ShieldCheck size={17}/></div><div className="metric-value green">{doneGates}<span className="metric-denominator"> / {gates.length}</span></div><p className="metric-note">podmienok vydania splnených</p></div>
              <div className="metric"><div className="metric-top"><span>Otvorené P0</span><Flag size={17}/></div><div className="metric-value">{openP0}</div><p className="metric-note">najvyššia priorita · {blocked} blokovaných</p></div>
              <div className="metric"><div className="metric-top"><span>Navrhnutá cena</span><FileText size={17}/></div><div className="metric-value">{typeof data.meta.productPrice==="number"?`$${data.meta.productPrice}`:data.meta.productPrice}</div><p className="metric-note">jednorazovo · pracovný návrh</p></div>
            </section>
            <div className={`release-strip ${releaseReady?"passed":""}`}><div className="release-message"><span className="release-symbol">{releaseReady?<CheckCircle2 size={20}/>:<LockKeyhole size={19}/>}</span><div><p className="release-title">{releaseReady?"Pripravené na podanie na Agensi.":"Podanie čaká na splnenie povinných podmienok."}</p><p className="release-description">{releaseReady?"Schválenie Agensi je samostatný krok. Splnenie brán nie je odborná certifikácia.":`${gates.length-doneGates} otvorených brán. Hotový kód, test a odborné schválenie sú samostatné kroky.`}</p></div></div><span className="release-status">{releaseReady?"MOŽNO PODAŤ":"PRÍPRAVA PREBIEHA"}</span></div>
            {view==="backlog"&&<>
              {nextTask&&<section className="next-step"><div><p className="small-label">Najbližší odblokovaný krok</p><h2><span className="next-id">{nextTask.id}</span>{nextTask.title}</h2><p>{nextTask.phase} · {nextTask.estimate} · {nextTask.acceptance.length} podmienok dokončenia</p></div><button type="button" className="button primary" onClick={()=>setSelectedId(nextTask.id)}>Otvoriť úlohu</button></section>}
              <div className="section-heading"><h2>Pracovný backlog<span className="section-count">{tasks.length}</span></h2><span className="section-caption">Odškrtávame až s dôkazom.</span></div>
              <div className="filters"><label className="search-field"><span className="sr-only">Hľadať úlohy</span><Search size={17}/><input className="field-input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Hľadať úlohu alebo ID…" type="search"/></label><label><span className="sr-only">Filter fázy</span><select className="field-select" value={phase} onChange={e=>setPhase(e.target.value)}><option value="all">Všetky fázy</option>{phases.map(p=><option key={p}>{p}</option>)}</select></label><label><span className="sr-only">Filter priority</span><select className="field-select" value={priority} onChange={e=>setPriority(e.target.value)}><option value="all">Všetky priority</option><option value="P0">P0 · kritické</option><option value="P1">P1 · dôležité</option><option value="P2">P2 · neskôr</option></select></label><label><span className="sr-only">Filter stavu</span><select className="field-select" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">Všetky stavy</option>{Object.entries(statusNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></div>
              {hasFilters&&<div className="filter-summary"><span>{filtered.length} z {tasks.length} úloh</span><button type="button" className="button ghost compact" onClick={()=>{setQuery("");setPhase("all");setStatus("all");setPriority("all")}}><X size={13}/>Vymazať filtre</button></div>}
              {filtered.length===0?<div className="empty-state"><Search size={26}/><h3>Žiadna zodpovedajúca úloha</h3><p>Skús iný výraz alebo zmeň filtre.</p></div>:phases.map((p,i)=>{const group=filtered.filter(t=>t.phase===p);const allGroup=tasks.filter(t=>t.phase===p);return group.length>0&&<section className="phase-group" key={p}><div className="phase-heading"><h3 className="phase-name"><span className="phase-number">0{i+1}</span>{p}</h3><div className="phase-progress"><span>{allGroup.filter(t=>t.status==="done").length} / {allGroup.length}</span><span className="phase-track"><span style={{width:`${progress(allGroup)}%`}}/></span></div></div><div className="task-list">{group.map(t=><TaskRow key={t.id} task={t} onOpen={()=>setSelectedId(t.id)} pendingDependencies={t.dependencies.filter(id=>taskMap.get(id)?.status!=="done").length}/>)}</div></section>})}
            </>}
            {view==="quality"&&<><p className="quality-intro">Tieto úlohy tvoria kontrolu pred podaním na Agensi. Dokončenie vyžaduje splnené akceptačné body, uvedený dôkaz a hotové závislosti. Zelený stav vyjadruje zaznamenané splnenie našich podmienok; nenahrádza nezávislé odborné posúdenie.</p><div className="quality-columns"><section><div className="section-heading"><h2>Povinné brány<span className="section-count">{gates.length}</span></h2></div><div className="task-list">{gates.map(t=><TaskRow key={t.id} task={t} onOpen={()=>setSelectedId(t.id)} pendingDependencies={t.dependencies.filter(id=>taskMap.get(id)?.status!=="done").length}/>)}</div></section><aside className="principles"><h3>Pravidlá každého výstupu</h3><div className="principle"><strong><Link2 size={16}/>Dohľadateľné podklady</strong><p>Každý nález musí viesť ku konkrétnemu záznamu alebo artefaktu. Chýbajúca referencia musí zostať viditeľná.</p></div><div className="principle"><strong><ScanLine size={16}/>Rozsah overenia</strong><p>Načítaný hash či podpis ešte neznamená vykonané kryptografické overenie. Uvádzame presne, čo bolo skontrolované.</p></div><div className="principle"><strong><FileCheck2 size={16}/>Nálezy a interpretácia</strong><p>Pôvodné výsledky, obmedzenia a AI vysvetlenie musia byť zreteľne oddelené. Finálny prehľad schvaľuje človek.</p></div><div className="principle"><strong><AlertCircle size={16}/>Poctivé negatívne výsledky</strong><p>Neprítomnosť známeho indikátora nie je dôkaz bezpečnosti. Zlyhaná úloha nesmie vyústiť do čistého výsledku.</p></div><p className="principles-footnote">Presné zdroje a ich použiteľnosť nájdeš v sekcii Odborné zdroje.</p><button className="button secondary compact" type="button" onClick={()=>setView("sources")}><BookOpen size={14}/>Otvoriť zdroje</button></aside></div></>}
            {view==="sources"&&<><div className="source-banner"><BookOpen size={21}/><div><strong>Metodická opora, jasný rozsah.</strong><br/>Pracujeme s primárnymi odbornými a technickými zdrojmi. Ich použitie neznamená certifikáciu produktu ani splnenie celého štandardu. Pri každom zdroji uvádzame, na čo sa vzťahuje.</div></div><div className="source-grid">{data.sources.map(source=><article className="source-card" key={source.id}><div className="source-card-top"><span className="source-org">{source.organization}</span><span className="source-year">{source.year}</span></div><h3>{source.title}</h3><p>{source.note}</p><a href={source.url} target="_blank" rel="noopener noreferrer">Prečítať pôvodný zdroj<ExternalLink size={14}/></a></article>)}</div></>}
            <div className={`sync-line ${error?"error":""}`} aria-live="polite">{error?<AlertCircle size={14}/>:<CloudCheck size={14}/>}{error?"Zobrazený posledný načítaný stav. Obnovenie zlyhalo.":`Uložené v pracovnom priestore · načítané ${shortTime(data.syncedAt)} · Europe/Bratislava`}</div>
            <footer className="footer-note"><div className="deadline-line"><Clock3 size={13}/>{data.meta.deadline||"Nie je určený externý deadline."}</div><a href={data.meta.repositoryUrl} target="_blank" rel="noopener noreferrer"><GitBranch size={14}/>Zdrojový MCP repozitár<ExternalLink size={11}/></a><span className="deadline-line"><GitCommitHorizontal size={13}/>Základ MCP: {data.meta.baselineCommit.slice(0,7)}</span></footer>
          </>}
        </>}
      </main>
    </div>
    {selected&&data&&<TaskDialog key={`${selected.id}-${selected.revision}`} task={selected} tasks={tasks} sources={data.sources} onClose={()=>setSelectedId(null)} onSave={saveTask} onRefresh={refresh}/>}
    {toast&&<div className="toast" role="status"><CheckCircle2 size={17}/>{toast}</div>}
  </div>
}

function TaskRow({task,onOpen,pendingDependencies}:{task:Task;onOpen:()=>void;pendingDependencies:number}){return <button className="task-row" type="button" onClick={onOpen} data-status={task.status} aria-label={`Otvoriť úlohu ${task.id}: ${task.title}, ${statusNames[task.status]}`}><span className={`task-status-icon ${task.status}`}><StatusIcon status={task.status}/></span><span><span className="task-title">{task.title}</span><span className="task-meta"><span className="task-id">{task.id}</span><span className="task-meta-separator">·</span><span>{task.estimate}</span>{task.gate&&<span className="gate-icon"><ShieldCheck size={11}/>Brána vydania</span>}{pendingDependencies>0&&<span className="gate-icon"><GitBranch size={11}/>{pendingDependencies} závisl.</span>}</span></span><span className="task-trailing"><span className={`priority-badge ${task.priority}`}>{task.priority}</span><span className={`status-badge ${task.status}`}>{statusNames[task.status]}</span></span><ChevronRight size={14} className="task-chevron"/></button>}

function TaskDialog({task,tasks,sources,onClose,onSave,onRefresh}:{task:Task;tasks:Task[];sources:Source[];onClose:()=>void;onSave:(task:Task,patch:{status:Status;evidence:string;checks:number[]})=>Promise<void>;onRefresh:()=>Promise<void>}){
  const dialogRef=useRef<HTMLDialogElement>(null);
  const [status,setStatus]=useState<Status>(task.status);
  const [checks,setChecks]=useState<number[]>(task.checks??[]);
  const [evidence,setEvidence]=useState(task.evidence??"");
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [conflict,setConflict]=useState(false);
  useEffect(()=>{const dialog=dialogRef.current;const previous=document.body.style.overflow;document.body.style.overflow="hidden";dialog?.showModal();return()=>{dialog?.close();document.body.style.overflow=previous}},[]);
  const dependencies=task.dependencies.map(id=>tasks.find(t=>t.id===id)??{id,title:"Neznáma závislosť",status:"blocked" as Status});
  const outstandingDependencies=dependencies.filter(t=>t.status!=="done");
  const accepted=task.acceptance.filter((_,i)=>checks.includes(i)).length;
  const canComplete=accepted===task.acceptance.length&&evidence.trim().length>0&&outstandingDependencies.length===0;
  const isDirty=status!==task.status||evidence!==task.evidence||JSON.stringify([...checks].sort())!==JSON.stringify([...(task.checks??[])].sort());
  const close=()=>{if(saving)return;if(isDirty&&!window.confirm("Neuložené zmeny sa zahodia. Zavrieť úlohu?"))return;onClose()};
  const submit=async(e:FormEvent)=>{e.preventDefault();setSaving(true);setError("");setConflict(false);try{await onSave(task,{status,evidence,checks})}catch(err){const message=err instanceof Error?err.message:"Uloženie zlyhalo.";setError(message);setConflict(/verzi|zmen|revision|conflict|obnov/i.test(message))}finally{setSaving(false)}};
  return <dialog ref={dialogRef} className="task-dialog" aria-labelledby="task-dialog-title" onCancel={e=>{e.preventDefault();close()}} onClick={e=>{if(e.target===e.currentTarget)close()}}><form className="dialog-shell" onSubmit={submit}><header className="dialog-header"><p className="dialog-heading-label">{task.id} · {task.phase}</p><button type="button" className="icon-button" onClick={close} disabled={saving} aria-label="Zavrieť detail úlohy"><X size={19}/></button></header><div className="dialog-scroll"><div className="dialog-meta"><span className={`priority-badge ${task.priority}`}>{task.priority}</span><span className={`status-badge ${task.status}`}>{statusNames[task.status]}</span>{task.gate&&<span className="gate-icon" style={{fontSize:12}}><ShieldCheck size={13}/>Povinná brána pred podaním</span>}</div><h2 className="dialog-title" id="task-dialog-title">{task.title}</h2><p className="dialog-description">{task.description}</p><p className="helper">Pracovný odhad: {task.estimate}</p><section className="dialog-section"><h3>Podmienky dokončenia<span>{accepted} / {task.acceptance.length}</span></h3><div className="acceptance-list">{task.acceptance.map((criterion,index)=><label key={index} className={`acceptance-label ${checks.includes(index)?"checked":""}`}><input type="checkbox" checked={checks.includes(index)} disabled={saving} onChange={e=>{setChecks(current=>e.target.checked?[...current,index]:current.filter(i=>i!==index));setError("")}}/><span>{criterion}</span></label>)}</div></section>{dependencies.length>0&&<section className="dialog-section"><h3>Závislosti<span>{dependencies.length-outstandingDependencies.length} / {dependencies.length} hotové</span></h3><div className="dependency-list">{dependencies.map(dependency=><div key={dependency.id} className={`dependency-item ${dependency.status==="done"?"done":"pending"}`}><StatusIcon status={dependency.status} size={14}/><span><code>{dependency.id}</code>{dependency.title}</span></div>)}</div></section>}<section className="dialog-section"><label htmlFor="task-evidence" className="field-label">Dôkaz a poznámky k overeniu</label><textarea id="task-evidence" className="field-textarea" value={evidence} disabled={saving} onChange={e=>{setEvidence(e.target.value);setError("")}} placeholder="Odkaz na commit, výsledok testu, dokument alebo opis overenia. Kto, čo a kedy skontroloval?" maxLength={4000}/><p className="helper">Uveď konkrétny podklad. Samotné odškrtnutie nenahrádza vykonaný test. Nevkladaj heslá, API kľúče ani skutočné dôkazové dáta.</p></section><section className="dialog-section"><label htmlFor="task-status" className="field-label">Stav úlohy</label><select id="task-status" className="field-select" value={status} disabled={saving} onChange={e=>{setStatus(e.target.value as Status);setError("")}}>{Object.entries(statusNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></section>{task.sourceIds.length>0&&<section className="dialog-section"><h3>Podklady k tejto úlohe</h3><div className="dialog-source-list">{task.sourceIds.map(id=>sources.find(s=>s.id===id)).filter((source):source is Source=>!!source).map(source=><a key={source.id} href={source.url} target="_blank" rel="noopener noreferrer"><ExternalLink size={13}/>{source.title}</a>)}</div></section>}{task.updatedAt&&<p className="helper" style={{marginTop:22}}>Posledná zmena: {new Intl.DateTimeFormat("sk-SK",{dateStyle:"medium",timeStyle:"short",timeZone:"Europe/Bratislava"}).format(new Date(task.updatedAt))} · revízia {task.revision}</p>}{error&&<div className="dialog-error" role="alert">{error}{conflict&&<button type="button" className="button secondary compact" style={{marginTop:10}} onClick={async()=>{await onRefresh();onClose()}}>Načítať aktuálny stav</button>}</div>}</div><footer className="dialog-footer"><p className={`dialog-save-hint ${status==="done"&&!canComplete?"warning":""}`}>{status==="done"&&!canComplete?"Na dokončenie odškrtni všetky podmienky, doplň dôkaz a dokonči závislosti.":isDirty?"Zmeny sa uložia až po potvrdení. Budú dostupné aj na ďalšom zariadení.":"Zaznamenaný stav sa nemení, kým neuložíš úpravy."}</p><div className="dialog-footer-actions"><button type="button" className="button secondary" onClick={close} disabled={saving}>Zavrieť</button><button type="submit" className="button primary" disabled={saving||!isDirty||(status==="done"&&!canComplete)}>{saving?<LoaderCircle className="spin" size={15}/>:<Check size={15}/>} {saving?"Ukladám…":"Uložiť zmeny"}</button></div></footer></form></dialog>
}
