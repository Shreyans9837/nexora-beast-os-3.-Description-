async function postJSON(url, data) {
  const res = await fetch(url, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || "Something went wrong");
  return body;
}
function showToast(message, bad=false) {
  let t=document.createElement("div"); t.className="toast"+(bad?" bad":""); t.textContent=message;
  document.body.appendChild(t); setTimeout(()=>t.remove(),3000);
}
document.addEventListener("DOMContentLoaded",()=>{
 const run=document.getElementById("runCommand");
 if(run) run.addEventListener("click", async()=>{
   const input=document.getElementById("commandInput"), result=document.getElementById("commandResult");
   if(!input.value.trim()) return showToast("Enter a business command first.",true);
   run.disabled=true; run.textContent="…"; result.classList.remove("hidden");
   document.getElementById("answerText").innerHTML="<p>BEAST is thinking through your request…</p>";
   try { const d=await postJSON("/api/command",{prompt:input.value});
     document.getElementById("responseMode").textContent=d.mode.toUpperCase();
     document.getElementById("answerText").innerHTML=markdownLite(d.answer);
     showToast("Analysis complete. A review task was added.");
   } catch(e){showToast(e.message,true)} finally{run.disabled=false;run.textContent="↑"}
 });
 document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{
   const i=document.getElementById("commandInput"); if(i){i.value=b.dataset.prompt;i.focus();}
 }));
 document.querySelectorAll(".status-select").forEach(s=>s.addEventListener("change",async()=>{
   try{await postJSON(`/api/task/${s.dataset.task}/status`,{status:s.value});showToast("Task status updated.");}
   catch(e){showToast(e.message,true)}
 }));
 document.querySelectorAll("[data-approval]").forEach(b=>b.addEventListener("click",async()=>{
   try{const d=await postJSON(`/api/approval/${b.dataset.approval}`,{action:b.dataset.action});showToast(d.note);setTimeout(()=>location.reload(),600);}
   catch(e){showToast(e.message,true)}
 }));
});
function markdownLite(s){
 return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
 .replace(/^## (.*)$/gm,"<h3>$1</h3>").replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
 .replace(/^\d+\.\s(.*)$/gm,"<li>$1</li>").replace(/\n\n/g,"<br><br>").replace(/\n/g,"<br>");
}
function openTaskModal(){document.getElementById("taskModal").classList.remove("hidden")}
function closeTaskModal(){document.getElementById("taskModal").classList.add("hidden")}
async function createTask(){
 try{await postJSON("/api/task",{title:document.getElementById("newTaskTitle").value,agent:document.getElementById("newTaskAgent").value,priority:document.getElementById("newTaskPriority").value});showToast("Task added to workforce.");location.reload();}
 catch(e){showToast(e.message,true)}
}
async function saveBrainNote(){
 try{await postJSON("/api/brain",{note:document.getElementById("brainNote").value});showToast("Saved to Business Brain.");location.reload();}
 catch(e){showToast(e.message,true)}
}
async function runSimulator(){
 try{
  const d=await postJSON("/api/simulator",{revenue:document.getElementById("simRevenue").value,growth:document.getElementById("simGrowth").value,margin:document.getElementById("simMargin").value,months:document.getElementById("simMonths").value});
  document.getElementById("simResults").innerHTML=`<div class="result-stat"><small>PROJECTED MONTHLY REVENUE</small><b>₹${Number(d.revenue).toLocaleString("en-IN",{maximumFractionDigits:0})}</b><span>${d.change}% change vs current input</span></div><div class="result-stat"><small>ESTIMATED GROSS PROFIT</small><b>₹${Number(d.profit).toLocaleString("en-IN",{maximumFractionDigits:0})}</b><span>Based on entered gross margin</span></div><p class="muted">${d.disclaimer}</p>`;
 }catch(e){showToast(e.message,true)}
}
