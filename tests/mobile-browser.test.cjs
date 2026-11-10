"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {createServer}=require("node:http");
const {spawn}=require("node:child_process");
const {readFile,writeFile,mkdtemp,rm}=require("node:fs/promises");
const {readFileSync}=require("node:fs");
const {createHash}=require("node:crypto");
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
function manualDoc(sha){
  const byStat=Object.fromEntries(["points","rebounds","assists"].map(stat=>[
    stat,{
      schema:"sportprob-retrospective-context-v1",
      research_only:true,future_prediction:false,player_id:"DEMO-001",stat,
      as_of_exclusive:"2025-11-21",games_used:20,
      first_game:"2025-11-01",last_game:"2025-11-20",
      average:20,median:20,sample_standard_deviation:3,
      observed_10th_percentile:12,observed_90th_percentile:28,
      average_minutes:30,production_per_36_played_minutes:24,
      last_five_average:21,preceding_five_average:19
    }
  ]));
  return {
    schema:"sportprob-manual-statistics-v1",
    research_only:true,future_prediction:false,wagering_outputs:false,
    dataset:{id:"synthetic-manual-demo",source_name:"Synthetic authored browser fixture",
      sha256:sha,synthetic:true,rights_status_user_declared:"cleared",
      rights_independently_verified:false},
    total_input_records:20,history_games_limit:40,
    as_of_exclusive:"2025-11-21",
    players:[{player_id:"DEMO-001",played_games_before_cutoff:20,statistics:byStat}],
    insufficient_history:[]
  };
}
function historicalDoc(sha){
  const csv=readFileSync(path.join(root,"data/demo_games.csv"),"utf8").trim().split(/\r?\n/);
  const headers=csv.shift().split(",");
  const records=csv.map(line=>{
    const values=line.split(",");
    return Object.fromEntries(headers.map((h,i)=>[h,values[i]]));
  });
  const metrics=["points","rebounds","assists","minutes"];
  function summary(items){
    return Object.fromEntries(metrics.map(metric=>{
      const vals=items.map(x=>Number(x[metric]));
      if(vals.length===0)return [metric,null];
      const avg=vals.reduce((a,b)=>a+b,0)/vals.length;
      const sd=vals.length>1?Math.sqrt(vals.reduce((t,v)=>t+(v-avg)**2,0)/(vals.length-1)):null;
      const sorted=[...vals].sort((a,b)=>a-b),middle=Math.floor(vals.length/2);
      const median=vals.length%2?sorted[middle]:(sorted[middle-1]+sorted[middle])/2;
      const x={games:vals.length,mean:+avg.toFixed(2),median:+median.toFixed(2),
        standard_deviation:sd===null?null:+sd.toFixed(2),
        observed_min:Math.min(...vals),observed_max:Math.max(...vals)};
      if(metric!=="minutes")x.observed_per_36_minutes=+(
        36*vals.reduce((a,b)=>a+b,0)/
        items.reduce((a,b)=>a+Number(b.minutes),0)
      ).toFixed(2);
      return [metric,x];
    }));
  }
  return {
    schema:"sportprob-offline-historical-observations-v1",
    research_only:true,future_prediction:false,model_evaluation_performed:false,
    genuinely_blind_validation:false,source_rights_independently_verified:false,
    source_authenticity_independently_verified:false,
    player_id:"ESPN:3975",dataset_file:"demo_games.csv",
    dataset_sha256:sha,selected_games:records.length,
    first_game:records[0].game_date,last_game:records.at(-1).game_date,
    source_verified_season_type_2:false,
    cutoffs:{training_end_exclusive:"2025-11-14",
      historical_evaluation_start_inclusive:"2025-11-17"},
    overall:summary(records),periods:{
      training:summary(records.slice(0,13)),
      calibration:summary(records.slice(13,16)),
      historical_evaluation:summary(records.slice(16))
    },
    seasons:{},season_to_season_mean_changes:{},
    venue:{
      home:summary(records.filter(x=>x.home==="true")),
      away:summary(records.filter(x=>x.home==="false")),
      unknown:0
    },
    last_five_completed_games:summary(records.slice(-5)),source_audit:null,
  };
}
test("headless Chrome imports CSV and audit, then detects edited source bytes",
  {skip:process.env.RUN_BROWSER_ACCEPTANCE!=="1",timeout:85000},async()=>{
    const dir=await mkdtemp(path.join(tmpdir(),"sportprob-browser-"));
    const allowed=new Set([
      "/mobile/index.html","/mobile/styles.css","/mobile/app.js",
      "/mobile/integrity.js","/mobile/audit.js","/mobile/history-report.js",
      "/mobile/manual-report.js",
      "/mobile/instant-research.js",
      "/mobile/manual-entry.js",
      "/mobile/player-comparison.js"
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
      const manualFile=path.join(dir,"manual.json");
      const reportFile=path.join(dir,"history.json");
      const historyCsv=path.join(dir,"synthetic-espn-history.csv");
      const multiplePlayerCsv=path.join(dir,"two-synthetic-players.csv");
      const manifest=JSON.parse(readFileSync(path.join(root,"data/demo_games.manifest.json"),"utf8"));
      await writeFile(altered,Buffer.concat([readFileSync(original),Buffer.from([10])]));
      await writeFile(auditFile,JSON.stringify(auditDoc(manifest.sha256)));
      await writeFile(manualFile,JSON.stringify(manualDoc(manifest.sha256)));
      const historyBytes=readFileSync(original,"utf8").replaceAll("DEMO-001","Example Player (ESPN 3975)");
      const historySha=createHash("sha256").update(historyBytes).digest("hex");
      await writeFile(historyCsv,historyBytes);
      await writeFile(reportFile,JSON.stringify(historicalDoc(historySha)));
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
      await eventually(()=>js("document.getElementById('instant-results').hidden===false"),"phone research completes from CSV without Python");
      assert.equal(await js("document.getElementById('instant-rows').children.length"),3);
      assert.equal(await js("document.getElementById('instant-through').value"),"2025-11-20");
      await js("(()=>{const el=document.getElementById('instant-through');el.value='2025-11-04';el.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('instant-results').hidden"),true);
      assert.equal(await js("document.getElementById('instant-status').textContent.includes('Insufficient history')"),true);
      await js("(()=>{const el=document.getElementById('instant-through');el.value='2025-11-20';el.dispatchEvent(new Event('change'));return true;})()");
      await eventually(()=>js("document.getElementById('instant-results').hidden===false"),"cutoff restoration");

      await attach("#manual-report-json",manualFile);
      await eventually(()=>js("document.getElementById('manual-report-link').dataset.state==='BYTES_MATCHED'"),"manual report linked to CSV");
      assert.equal(await js("document.getElementById('manual-report-results').hidden"),false);
      assert.equal(await js("document.getElementById('manual-report-rows').children.length"),3);
      await attach("#audit-json",auditFile);
      await eventually(()=>js("document.getElementById('audit-link').dataset.state==='BYTES_MATCHED'"),"byte-level CSV/audit match");
      await js("(()=>{const s=document.getElementById('stat');s.value='rebounds';s.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('audit-link').dataset.state"),"SELECTION_MISMATCH");
      await js("(()=>{const s=document.getElementById('stat');s.value='points';s.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('audit-link').dataset.state"),"BYTES_MATCHED");
      // The same synthetic file is used only to verify the UI's file-identity
      // link. The report player deliberately differs from DEMO-001, so this
      // first import must fail closed on identity rather than show any metrics.
      await attach("#history-report-json",reportFile);
      await eventually(()=>js("document.getElementById('history-report-link').dataset.state==='HASH_MISMATCH'"),"historical report source mismatch");
      assert.equal(await js("document.getElementById('history-report-results').hidden"),true);
      await attach("#csv-file",historyCsv);
      await eventually(()=>js("document.getElementById('history-report-link').dataset.state==='BYTES_MATCHED'"),"historical report matched to exact synthetic history bytes");
      assert.equal(await js("document.getElementById('history-report-results').hidden"),false);
      assert.equal(await js("document.getElementById('history-report-rows').children.length"),4);
      await attach("#csv-file",altered);
      await eventually(()=>js("document.getElementById('audit-link').dataset.state==='HASH_MISMATCH'"),"mutated CSV fingerprint rejection");
      await eventually(()=>js("document.getElementById('manual-report-link').dataset.state==='HASH_MISMATCH'"),"manual report invalidation on changed source");
      assert.equal(await js("document.getElementById('manual-report-results').hidden"),true);
      await eventually(()=>js("document.getElementById('history-report-link').dataset.state==='HASH_MISMATCH'"),"phase 5 report invalidation on changed source");
      // Exercise the actual comparison script with two synthetic players in
      // headless Chromium, after the earlier audit invalidation checks.
      const originalText=readFileSync(original,"utf8").trim();
      const secondPlayerLines=originalText.split(/\r?\n/).slice(1)
        .map(line=>line.replace("DEMO-001","DEMO-002"));
      await writeFile(multiplePlayerCsv,originalText+"\n"+secondPlayerLines.join("\n")+"\n");
      await attach("#csv-file",multiplePlayerCsv);
      await eventually(()=>js("document.querySelectorAll('#comparison-rows tr').length===2"),"two-player comparison rendering");
      assert.equal(await js("document.getElementById('comparison-window').disabled"),false);
      assert.equal(await js("document.getElementById('comparison-rows').children[0].cells[0].textContent"),"DEMO-001");
      assert.equal(await js("document.getElementById('comparison-rows').children[1].cells[0].textContent"),"DEMO-002");
      await js("(()=>{const s=document.getElementById('comparison-window');s.value='5';s.dispatchEvent(new Event('change'));return true;})()");
      assert.equal(await js("document.getElementById('comparison-rows').children[0].cells[1].textContent"),"5 / 20");
      assert.equal(await js("document.getElementById('comparison-rows').children[0].cells[2].textContent"),"2025-11-20");
      assert.equal(await js("document.getElementById('history-report-results').hidden"),true);

      await js("(()=>{const p=document.getElementById('player');p.value='DEMO-002';p.dispatchEvent(new Event('change'));return true;})()");
      await eventually(()=>js("document.getElementById('instant-status').textContent.includes('DEMO-002')"),"selected player updates phone research");
      const invalidCsv=path.join(dir,"invalid.csv");
      await writeFile(invalidCsv,"player,date,points,rebounds,assists\nBroken,2026-02-30,20,3,4\n");
      await attach("#csv-file",invalidCsv);
      await eventually(()=>js("document.getElementById('load-status').textContent.includes('IMPORT REJECTED')"),"invalid replacement CSV rejection");
      assert.equal(await js("document.getElementById('instant-results').hidden"),true);
      assert.equal(await js("document.getElementById('instant-through').disabled"),true);

      // Enter five completed-game observations on phone UI, without uploading
      // a CSV file or calling the Python manual-report generator.
      const rowsAdded=await js("(()=>{const f=document.getElementById('entry-form');for(let i=1;i<=5;i++){const v={game_id:'',player_id:'Manual Player',game_date:'2025-12-0'+i,opponent:'Example',home:'true',minutes:'30',points:'20',rebounds:'5',assists:'4'};for(const [k,val] of Object.entries(v))f.elements.namedItem(k).value=val;f.requestSubmit();}return document.getElementById('entry-rows').children.length;})()");
      assert.equal(rowsAdded,5,"all five manually entered records are validated");
      await js("document.getElementById('entry-analyze').click()");
      await eventually(()=>js("document.getElementById('load-status').textContent.includes('LOCAL DATASET LOADED')"),"manual draft passed through shared importer");
      assert.equal(await js("document.getElementById('instant-results').hidden"),false);
      assert.equal(await js("document.getElementById('player').value"),"Manual Player");
      assert.equal(await js("document.getElementById('instant-rows').children.length"),3);
      assert.equal(await js("document.getElementById('entry-status').textContent.includes('Draft analyzed')"),true);
      // Closing the page would discard the draft unless its CSV is exported.
      assert.deepEqual(conn.exceptions,[],"browser produces no unhandled script exceptions");
    }finally{
      conn?.close();
      chrome?.kill("SIGTERM");
      await new Promise(resolve=>server.close(resolve));
      await rm(dir,{recursive:true,force:true,maxRetries:3,retryDelay:200});
    }
  }
);
