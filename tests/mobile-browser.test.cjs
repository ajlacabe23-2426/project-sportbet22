"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {createServer}=require("node:http");
const {spawn}=require("node:child_process");
const {readFile,writeFile,mkdtemp,rm}=require("node:fs/promises");
const {readFileSync}=require("node:fs");
const {tmpdir}=require("node:os");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function eventually(check,label,timeout=20000){
  const deadline=Date.now()+timeout;
  let error;
  while(Date.now()<deadline){
    try{if(await check())return;}catch(err){error=err;}
    await pause(120);
  }
  throw Error("Timed out waiting for "+label+(error?": "+error.message:""));
}
async function cdp(port){
  let target;
  await eventually(async()=>{
    const res=await fetch("http://127.0.0.1:"+port+"/json/list");
    const list=await res.json();
    target=list.find(item=>item.type==="page"&&item.url.includes("/mobile/index.html"));
    return Boolean(target?.webSocketDebuggerUrl);
  },"headless browser target");
  const ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    ws.addEventListener("open",resolve,{once:true});
    ws.addEventListener("error",reject,{once:true});
  });
  const pending=new Map(),exceptions=[];
  let seq=0;
  ws.addEventListener("message",event=>{
    let msg;
    try{msg=JSON.parse(String(event.data));}catch{return;}
    if(msg.method==="Runtime.exceptionThrown")exceptions.push(msg.params?.exceptionDetails?.text||"unknown exception");
    if(!msg.id)return;
    const waiter=pending.get(msg.id);
    if(!waiter)return;
    pending.delete(msg.id);
    if(msg.error)waiter.reject(Error(JSON.stringify(msg.error)));
    else waiter.resolve(msg.result);
  });
  const send=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++seq;
    pending.set(id,{resolve,reject});
    ws.send(JSON.stringify({id,method,params}));
  });
  const evaluate=async expression=>{
    const reply=await send("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});
    if(reply.exceptionDetails)throw Error(reply.exceptionDetails.text||"Browser evaluation failed");
    return reply.result?.value;
  };
  await send("Runtime.enable");
  await send("DOM.enable");
  return {send,evaluate,exceptions,close:()=>ws.close()};
}
function auditDoc(sha){
  const score=model=>({
    model,evaluated_games:5,mean_negative_log_likelihood:2.1,
    mean_ranked_probability_score:1.8,mean_absolute_error:3.2,
    mean_bias_observed_minus_expected:-0.1,coverage_80:0.8,coverage_90:1,
    mean_interval_width_80:11,coverage_80_wilson_95:[0.4,0.95]
  });
  return {
    schema:"sportprob-frozen-model-audit-v1",
    research_only:true,rights_are_not_independently_verified:true,
    synthetic:true,calibration_status:"UNVERIFIED_RESEARCH_BASELINES",
    dataset_id:"sportprob-synthetic-demo-v1",dataset_sha256:sha,
    source_name:"Bundled synthetic browser fixture",player_id:"DEMO-001",
    stat:"points",holdout_start:"2025-11-16",
    training_games:15,evaluated_games:5,training_policy:"frozen_pre_holdout_only",
    scores:[score("negative_binomial_provisional"),score("poisson_same_mean_benchmark")]
  };
}
test("headless Chrome imports CSV and audit, then detects edited source bytes",
  {skip:process.env.RUN_BROWSER_ACCEPTANCE!=="1",timeout:85000},async()=>{
    const dir=await mkdtemp(path.join(tmpdir(),"sportprob-browser-"));
    const allowed=new Set([
      "/mobile/index.html","/mobile/styles.css","/mobile/app.js",
      "/mobile/integrity.js","/mobile/audit.js"
    ]);
    const server=createServer(async(req,res)=>{
      const url=new URL(req.url,"http://localhost"),location=url.pathname;
      if(!allowed.has(location)){res.writeHead(404);res.end();return;}
      const mime=location.endsWith(".js")?"text/javascript":
        location.endsWith(".css")?"text/css":"text/html";
      try{
        const bytes=await readFile(path.join(root,location.slice(1)));
        res.writeHead(200,{"Content-Type":mime,"Cache-Control":"no-store"});
        res.end(bytes);
      }catch{res.writeHead(500);res.end();}
    });
    let chrome=null,conn=null;
    try{
      await new Promise((resolve,reject)=>server.once("error",reject).listen(0,"127.0.0.1",resolve));
      const address=server.address();
      const base="http://127.0.0.1:"+address.port;
      const original=path.join(root,"data/demo_games.csv");
      const altered=path.join(dir,"altered.csv");
      const auditFile=path.join(dir,"audit.json");
      const manifest=JSON.parse(readFileSync(path.join(root,"data/demo_games.manifest.json"),"utf8"));
      await writeFile(altered,Buffer.concat([readFileSync(original),Buffer.from([10])]));
      await writeFile(auditFile,JSON.stringify(auditDoc(manifest.sha256)));
      chrome=spawn(process.env.CHROME_BIN||"google-chrome",[
        "--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
        "--no-first-run","--no-default-browser-check",
        "--user-data-dir="+path.join(dir,"chrome"),"--remote-debugging-port=0",
        base+"/mobile/index.html"
      ],{stdio:"ignore"});
      chrome.once("error",error=>{chrome.startError=error;});
      let chromePort;
      await eventually(async()=>{
        if(chrome.startError)throw chrome.startError;
        try{
          const text=await readFile(path.join(dir,"chrome","DevToolsActivePort"),"utf8");
          chromePort=Number(text.split("\n")[0]);return Number.isInteger(chromePort)&&chromePort>0;
        }catch{return false;}
      },"Chromium debugging port",30000);
      conn=await cdp(chromePort);
      const js=conn.evaluate;
      await eventually(()=>js("Boolean(document.getElementById('csv-file'))"),"loaded offline dashboard");
      const page=await conn.send("DOM.getDocument");
      async function attach(selector,file){
        const {nodeId}=await conn.send("DOM.querySelector",{nodeId:page.root.nodeId,selector});
        assert.ok(nodeId,"file input exists: "+selector);
        await conn.send("DOM.setFileInputFiles",{nodeId,files:[file]});
      }
      await js("(()=>{document.getElementById('source-label').value='Bundled synthetic demo';document.getElementById('data-rights').checked=true;return true;})()");
      await attach("#csv-file",original);
      await eventually(()=>js("document.getElementById('load-status').textContent.includes('SYNTHETIC SAMPLE LOADED')"),"synthetic historical CSV load");
      assert.equal(await js("document.getElementById('csv-sha256').textContent.includes('"+manifest.sha256+"')"),true);
      await attach("#audit-json",auditFile);
      await eventually(()=>js("document.getElementById('audit-link').dataset.state==='BYTES_MATCHED'"),"byte-level CSV/audit match");
      await js("(()=>{const s=document.getElementById('stat');s.value='rebounds';s.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('audit-link').dataset.state"),"SELECTION_MISMATCH");
      await js("(()=>{const s=document.getElementById('stat');s.value='points';s.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('audit-link').dataset.state"),"BYTES_MATCHED");
      await attach("#csv-file",altered);
      await eventually(()=>js("document.getElementById('audit-link').dataset.state==='HASH_MISMATCH'"),"mutated CSV fingerprint rejection");
      assert.deepEqual(conn.exceptions,[],"browser produces no unhandled script exceptions");
    }finally{
      conn?.close();
      chrome?.kill("SIGTERM");
      await new Promise(resolve=>server.close(resolve));
      await rm(dir,{recursive:true,force:true,maxRetries:3,retryDelay:200});
    }
  }
);
