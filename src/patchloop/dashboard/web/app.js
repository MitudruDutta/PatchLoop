"use strict";
const $ = id => document.getElementById(id);
let sessionId = null, state = null, busy = false, jobId = null, recorded = false, closed = false;
function element(tag, className, text) { const node = document.createElement(tag); if(className) node.className=className; if(text !== undefined) node.textContent=text; return node; }
function notice(text, error=false) { $("notice").textContent=text; $("notice").className=error?"error":""; }
async function api(path, body) { const response=await fetch(path, body===undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); const value=await response.json(); if(!response.ok) throw new Error(value.error || "Local request failed"); return value; }
async function refresh() { state=await api("/api/state"); $("version").textContent=state.source_hash.slice(0,12); $("interface").textContent=(state.activated?"Activated guard":"Unrepaired baseline")+" · "+state.interface; $("budget").textContent=state.model_requests+" / "+state.request_limit; $("model").textContent=state.model || "Nebius model not configured"; if(!jobId) $("source").textContent=state.source; $("challenge").disabled=busy || !state.configured; $("send").disabled=busy || recorded || closed || !state.configured; $("confirm").disabled=busy || recorded || closed; $("new-session").disabled=busy || !state.configured; $("mode").disabled=busy; if(!state.configured) notice("Configure NEBIUS_API_KEY and NEBIUS_MODEL in the server environment to run conversations. Saved guard source is available without keys."); }
function render(view) {
  closed=view.closed;
  const transcript=$("transcript"), effects=$("effects"); transcript.replaceChildren(); effects.replaceChildren(); let records=0;
  for(const item of view.timeline) {
    if(item.kind==="user" || item.kind==="assistant" || item.kind==="error") {
      const box=element("div","message "+item.kind); box.append(element("div","speaker",item.kind==="user"?"CUSTOMER":item.kind==="assistant"?"NEMOTRON AGENT":"RUN STOPPED"),element("p",null,item.text)); transcript.append(box);
    } else if(item.kind==="tool") {
      const event=item.event, box=element("div","message tool"), details=element("details");
      const labels=event.executed_violations.length ? " · VIOLATION" : "";
      details.append(element("summary",null,event.tool+" · "+event.outcome+labels),element("pre",null,JSON.stringify({arguments:event.arguments,result:event.result,executed_violations:event.executed_violations},null,2))); box.append(details); transcript.append(box);
      for(const [table, rows] of Object.entries(item.diff || {})) for(const [key, record] of Object.entries(rows)) {
        records++; const block=element("div","record"), grid=element("div","record-grid"); block.append(element("h3",null,table+" / "+key));
        for(const side of ["before","after"]) { const column=element("div"); column.append(element("span",null,side.toUpperCase()),element("pre",null,JSON.stringify(record[side],null,2))); grid.append(column); } block.append(grid); effects.append(block);
      }
    } else if(item.kind==="proposal") { const box=element("div","message"); box.append(element("p",null,"Proposed action: "+item.tool+". Waiting for the customer’s exact confirmation.")); transcript.append(box); }
    else if(item.kind==="protocol_error") { const box=element("div","message error"); box.append(element("p",null,item.text)); transcript.append(box); }
  }
  if(!records) effects.append(element("p","muted","No records changed. Check tool events for blocked calls and unauthorized private reads."));
  $("effect-count").textContent=records+" RECORD CHANGE"+(records===1?"":"S");
  $("violations").textContent=view.executed_violations; $("tokens").textContent=view.tokens.toLocaleString();
  $("finding-caption").textContent="Tool events with executed violations";
  $("conversation-status").textContent=view.closed?"CLOSED":"OPEN";
  $("pending").hidden=!view.pending; if(view.pending) $("pending-action").textContent=JSON.stringify({tool:view.pending.tool,arguments:view.pending.arguments},null,2);
  transcript.scrollTop=transcript.scrollHeight;
}
async function start() { const result=await api("/api/session",{mode:$("mode").value}); sessionId=result.session_id; recorded=false; render(result.conversation); }
async function send(text) { if(busy || recorded || closed) return; busy=true; $("send").disabled=true; $("confirm").disabled=true; $("new-session").disabled=true; $("mode").disabled=true; notice("Agent is working…"); try { if(!sessionId) await start(); const view=await api("/api/turn",{session_id:sessionId,text}); render(view); $("message").value=""; notice(view.closed?"Conversation ended or reached its budget. Start a new conversation to continue.":"Conversation recorded. Tool effects are independently checked."); } catch(error) { notice(error.message,true); } finally {busy=false;await refresh();} }
$("composer").addEventListener("submit",event=>{event.preventDefault();send($("message").value);});
$("message").addEventListener("keydown",event=>{if(event.key==="Enter"&&(event.metaKey||event.ctrlKey)){event.preventDefault();send($("message").value);}});
$("confirm").addEventListener("click",()=>send("yes"));
$("new-session").addEventListener("click",async()=>{try{await start();notice("New conversation with fresh data and the selected condition.");await refresh();}catch(error){notice(error.message,true);}});
$("mode").addEventListener("change",async()=>{if(busy)return;sessionId=null;try{if(state?.configured){await start();await refresh();}notice("New conversation uses the selected condition.");}catch(error){notice(error.message,true);}});
$("example").addEventListener("click",()=>{if(state){$("message").value=state.example.opener;$("message").focus();}});
$("reproduce").addEventListener("click",()=>{if(jobId) window.location.assign("/api/bundle/"+jobId);});
function showJob(job) {
  sessionId=null; recorded=true;
  const result=job.result, before=result.before || result, campaign=result.after || before;
  if(campaign.scenarios.length) render(campaign.scenarios[0].conversation);
  $("conversation-status").textContent="RECORDED CHALLENGE";
  $("violations").textContent=campaign.executed_violations; $("tokens").textContent=(result.total_tokens || campaign.total_tokens || 0).toLocaleString();
  $("finding-caption").textContent=result.after ? "After retest · before: "+before.executed_violations : campaign.unique_findings+" unique violation signatures";
  const checks=$("checks");checks.replaceChildren(); const validation=job.patch && job.patch.validation;
  if(validation) { const values=[["Acceptance",validation.accepted],["Development",validation.security_development?.passed],["Sealed",validation.sealed_security?.passed],["Utility "+(validation.utility_passed ?? "—")+" / "+(validation.utility_tasks ?? "—"),validation.coverage_complete]];for(const [label, passed] of values) checks.append(element("span","check"+(passed?"":" fail"),(passed?"✓ ":"· ")+label)); }
  else checks.append(element("p","muted",before.findings.length?"Findings recorded. Repair checks are available when a candidate is evaluated.":"No observed violation. No patch generated; this is not a proof of safety."));
  $("source").textContent=job.patch?.diff || job.patch?.source || job.source || state.source; $("patch-status").textContent=job.patch?.status || "NO PATCH";
  $("reproduce").disabled=false; notice("Challenge finished: "+result.status+". Local artifacts retained. Select New conversation to chat again.");
}
async function poll() { try { const job=await api("/api/jobs/"+jobId); if(job.status==="running"){setTimeout(poll,1500);return;} busy=false; if(job.status==="finished") showJob(job);else notice(job.error,true); await refresh(); } catch(error){busy=false;notice(error.message,true);await refresh();} }
$("challenge").addEventListener("click",async()=>{if(busy)return;busy=true;$("challenge").disabled=true;$("send").disabled=true;$("new-session").disabled=true;$("confirm").disabled=true;$("mode").disabled=true;$("reproduce").disabled=true;notice("Challenging this version. The tester and target use bounded model calls; validation may take several minutes.");try{const job=await api("/api/challenge",{cycle:$("cycle").checked});jobId=job.id;poll();}catch(error){busy=false;notice(error.message,true);await refresh();}});
refresh().catch(error=>notice(error.message,true));
