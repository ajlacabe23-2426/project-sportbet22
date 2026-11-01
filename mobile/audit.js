"use strict";
// An independent, offline viewer of Python-exported retrospective model diagnostics.
// No network, odds, sportsbook links, or client-side forecasting.
(() => {
  const $=id=>document.getElementById(id);
  const validNumber=n=>typeof n==="number"&&Number.isFinite(n)&&n>=0;
  const positiveInteger=n=>Number.isSafeInteger(n)&&n>0&&n<=1000000;
  const bounded=(n,min,max)=>typeof n==="number"&&Number.isFinite(n)&&n>=min&&n<=max;
  const knownModels=new Set(["negative_binomial_provisional","poisson_same_mean_benchmark"]);
  function parseAuditJSON(text){
    const doc=JSON.parse(text);
    if(!doc||typeof doc!=="object"||Array.isArray(doc)||
       doc.schema!=="sportprob-frozen-model-audit-v1"||
       doc.research_only!==true||doc.rights_are_not_independently_verified!==true||
       typeof doc.synthetic!=="boolean"||doc.calibration_status!=="UNVERIFIED_RESEARCH_BASELINES")
      throw Error("Not an uncalibrated SportProb frozen-model audit");
    if(typeof doc.player_id!=="string"||!doc.player_id.trim()||doc.player_id.length>110||
       !["points","rebounds","assists"].includes(doc.stat)||
       typeof doc.dataset_id!=="string"||doc.dataset_id.length>200||!doc.dataset_id.trim()||
       typeof doc.source_name!=="string"||doc.source_name.length>200||!doc.source_name.trim()||
       !/^[0-9a-f]{64}$/.test(doc.dataset_sha256))
      throw Error("Audit is missing valid player, statistic or dataset provenance");
    if(!/^\d{4}-\d{2}-\d{2}$/.test(doc.holdout_start)||
       !positiveInteger(doc.training_games)||!positiveInteger(doc.evaluated_games)||
       doc.training_policy!=="frozen_pre_holdout_only"||
       !Array.isArray(doc.scores)||doc.scores.length!==2)
      throw Error("Audit is missing a valid frozen holdout or model scores");
    if(new Set(doc.scores.map(score=>score.model)).size!==2||
       doc.scores.some(score=>!knownModels.has(score.model)))
      throw Error("Unexpected model comparison");
    for(const score of doc.scores){
      if(score.evaluated_games!==doc.evaluated_games||
         !validNumber(score.mean_negative_log_likelihood)||
         !validNumber(score.mean_ranked_probability_score)||
         !validNumber(score.mean_absolute_error)||
         !bounded(score.mean_bias_observed_minus_expected,-10000,10000)||
         !bounded(score.coverage_80,0,1)||!bounded(score.coverage_90,0,1)||
         !validNumber(score.mean_interval_width_80)||
         !Array.isArray(score.coverage_80_wilson_95)||score.coverage_80_wilson_95.length!==2||
         !score.coverage_80_wilson_95.every(v=>bounded(v,0,1))||
         score.coverage_80_wilson_95[0]>score.coverage_80||
         score.coverage_80_wilson_95[1]<score.coverage_80)
        throw Error("Invalid model diagnostic values");
    }
    return doc;
  }
  let current=null;
  function renderAudit(doc){
    const rows=$("audit-rows");rows.replaceChildren();
    const digits=n=>n.toFixed(2);
    for(const score of doc.scores){
      const tr=document.createElement("tr");
      const label=score.model==="negative_binomial_provisional"?"Negative binomial":"Poisson baseline";
      for(const text of [
        label,String(score.evaluated_games),digits(score.mean_absolute_error),
        digits(score.mean_ranked_probability_score),digits(100*score.coverage_80)+"%",
        score.coverage_80_wilson_95.map(v=>digits(100*v)+"%").join(" – ")
      ]){
        const td=document.createElement("td");td.textContent=text;tr.append(td);
      }
      rows.append(tr);
    }
    $("audit-meta").hidden=false;
    $("audit-meta").textContent="Player "+doc.player_id+" · "+doc.stat.toUpperCase()+
      " · "+doc.evaluated_games+" historical held-out games · Source: "+doc.source_name+
      " · Dataset: "+doc.dataset_id+" · Input SHA-256: "+doc.dataset_sha256;
    const selectedPlayer=$("player")?.value||"";
    const selectedStat=$("stat")?.value||"points";
    const link=globalThis.SportProbIntegrity.assessAuditLink(
      doc,globalThis.SportProbDataset||null,selectedPlayer,selectedStat
    );
    $("audit-link").dataset.state=link.status;
    $("audit-link").textContent="LOCAL SOURCE LINK · "+link.status.replaceAll("_"," ")+" — "+link.description;
    const matchMessage=link.description;
    $("audit-status").textContent=(doc.synthetic
      ?"SYNTHETIC DEMONSTRATION — not NBA forecasting evidence. "
      :"USER-DECLARED HISTORICAL DATA — source rights and authenticity have not been independently verified. ")+matchMessage;
  }
  async function handleAudit(){
    const input=$("audit-json"),file=input.files?.[0];
    if(!file)return;
    try{
      if(file.size>120000)throw Error("Audit file exceeds 120 KB");
      const data=parseAuditJSON(await file.text());
      current=data;
      renderAudit(data);
    }catch(error){
      current=null;$("audit-meta").hidden=true;$("audit-meta").textContent="";
      $("audit-link").dataset.state="NO_AUDIT";
      $("audit-link").textContent="No audit available to compare against the local CSV.";
      const body=$("audit-rows");body.replaceChildren();
      const tr=document.createElement("tr"),td=document.createElement("td");
      td.colSpan=6;td.className="table-empty";
      td.textContent="No valid historical model audit loaded.";tr.append(td);body.append(tr);
      $("audit-status").textContent="AUDIT REJECTED — "+String(error.message||"Invalid JSON");
    }finally{input.value=""}
  }
  $("audit-json").addEventListener("change",handleAudit);
  $("player").addEventListener("change",()=>{if(current)renderAudit(current)});
  $("stat").addEventListener("change",()=>{if(current)renderAudit(current)});
  document.addEventListener("sportprob:dataset-change",()=>{if(current)renderAudit(current)});
  // Re-evaluate byte identity on every import, rejection or player/stat change.
  // A successful match proves equality of local input bytes only.
  if(typeof module!=="undefined"&&module.exports)module.exports={parseAuditJSON};
})();
