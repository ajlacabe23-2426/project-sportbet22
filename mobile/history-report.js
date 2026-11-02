"use strict";
// Local-only retrospective JSON report. Display requires an exact SHA-256 match
// with the CSV imported into the performance desk. Neither SHA nor JSON proves
// source authenticity, rights, model calibration, or future predictive accuracy.
(function(root){
  const $=id=>document.getElementById(id);
  const metrics=["points","rebounds","assists","minutes"];
  const phases=["training","calibration","historical_evaluation"];
  const SHA=/^[0-9a-f]{64}$/;
  const positiveInt=n=>Number.isSafeInteger(n)&&n>0&&n<=20000;
  const nonneg=n=>typeof n==="number"&&Number.isFinite(n)&&n>=0&&n<=200000;
  const dateOK=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
    Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
    new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
  const object=v=>v!==null&&typeof v==="object"&&!Array.isArray(v);
  function validateSummary(summary,expectedGames,allowEmpty=false){
    if(!object(summary)||!metrics.every(k=>Object.hasOwn(summary,k)))
      throw Error("Missing points, rebounds, assists or minutes summary");
    for(const metric of metrics){
      const s=summary[metric];
      if(allowEmpty&&expectedGames===0&&s===null)continue;
      if(!object(s)||s.games!==expectedGames||!nonneg(s.mean)||
         !nonneg(s.median)||!nonneg(s.observed_min)||
         !nonneg(s.observed_max)||s.observed_min>s.median||
         s.median>s.observed_max||s.mean<s.observed_min||
         s.mean>s.observed_max||
         !(s.standard_deviation===null&&expectedGames===1||
           nonneg(s.standard_deviation)&&expectedGames>1))
        throw Error("Invalid "+metric+" sample statistics");
      if(metric!=="minutes"&&!nonneg(s.observed_per_36_minutes))
        throw Error("Invalid observed per-36 value for "+metric);
    }
  }
  function parseHistoryJSON(text){
    const doc=JSON.parse(text);
    if(!object(doc)||doc.schema!=="sportprob-offline-historical-observations-v1"||
       doc.research_only!==true||doc.future_prediction!==false||
       doc.model_evaluation_performed!==false||doc.genuinely_blind_validation!==false||
       doc.source_rights_independently_verified!==false||
       doc.source_authenticity_independently_verified!==false)
      throw Error("Not an unverified SportProb historical observations report");
    if(typeof doc.player_id!=="string"||!/^(ESPN:[0-9]{1,20})$/.test(doc.player_id)||
       typeof doc.dataset_file!=="string"||doc.dataset_file.length>200||
       !SHA.test(doc.dataset_sha256)||!positiveInt(doc.selected_games)||
       !dateOK(doc.first_game)||!dateOK(doc.last_game)||
       doc.first_game>doc.last_game||!object(doc.cutoffs)||
       !dateOK(doc.cutoffs.training_end_exclusive)||
       !dateOK(doc.cutoffs.historical_evaluation_start_inclusive)||
       doc.cutoffs.training_end_exclusive>=doc.cutoffs.historical_evaluation_start_inclusive)
      throw Error("Historical report lacks valid player, source or chronological cutoffs");
    validateSummary(doc.overall,doc.selected_games);
    if(!object(doc.periods)||!phases.every(p=>object(doc.periods[p])))
      throw Error("Missing chronological research periods");
    const total=phases.reduce((sum,period)=>{
      const count=doc.periods[period].points.games;
      if(!positiveInt(count))throw Error("Historical report period has zero games");
      validateSummary(doc.periods[period],count);
      return sum+count;
    },0);
    if(total!==doc.selected_games)throw Error("Research period counts do not match the dataset");
    if(!object(doc.seasons)||!object(doc.venue)||!object(doc.season_to_season_mean_changes))
      throw Error("Missing season or venue breakdowns");
    const seasonEntries=Object.entries(doc.seasons);
    if(seasonEntries.length>6)throw Error("Excessive season breakdown");
    for(const [season,summary] of seasonEntries){
      if(!/^[0-9]{4}$/.test(season))throw Error("Invalid season label");
      if(!positiveInt(summary?.points?.games))throw Error("Invalid season sample size");
      validateSummary(summary,summary.points.games);
    }
    if(doc.source_verified_season_type_2===true &&
       seasonEntries.reduce((sum,[,s])=>sum+s.points.games,0)!==doc.selected_games)
      throw Error("Source-season counts do not reconcile");
    for(const side of ["home","away"]){
      const summary=doc.venue[side];
      if(!object(summary)||!Object.hasOwn(summary,"points"))
        throw Error("Missing historical venue sample");
      if(summary.points===null){
        validateSummary(summary,0,true);
      }else{
        if(!Number.isSafeInteger(summary.points.games)||summary.points.games<0)
          throw Error("Invalid venue count");
        validateSummary(summary,summary.points.games);
      }
    }
    if(!Number.isSafeInteger(doc.venue.unknown)||doc.venue.unknown<0 ||
       doc.venue.unknown>doc.selected_games)
      throw Error("Invalid unobserved venue count");
    const venueTotal=doc.venue.unknown+
      (doc.venue.home.points?.games||0)+(doc.venue.away.points?.games||0);
    if(venueTotal!==doc.selected_games)throw Error("Home/away counts do not reconcile");
    if(!object(doc.last_five_completed_games)||
       doc.last_five_completed_games.points?.games!==Math.min(doc.selected_games,5))
      throw Error("Invalid last-five sample");
    validateSummary(doc.last_five_completed_games,Math.min(doc.selected_games,5));
    if(doc.source_verified_season_type_2!==true&&doc.source_verified_season_type_2!==false)
      throw Error("Invalid source cross-check state");
    if(doc.source_verified_season_type_2){
      if(!object(doc.source_audit)||doc.source_audit.selected_rows_matched_to_archive!==doc.selected_games||
         doc.source_audit.selected_nonregular_rows!==0)
        throw Error("Local archive matching counts do not reconcile");
    }else if(doc.source_audit!==null){
      throw Error("Unexpected source archive verification");
    }
    return doc;
  }
  function assessReportLink(report,dataset){
    if(!dataset)return {status:"NO_DATASET",description:"Import the same source CSV in Dataset control."};
    if(!dataset.sha256)return {status:"HASH_UNAVAILABLE",description:"Browser could not fingerprint the CSV; source identity cannot be checked."};
    if(report.dataset_sha256!==dataset.sha256)return {status:"HASH_MISMATCH",description:"CSV bytes differ from the imported research report. Nothing from this report is displayed."};
    const label="(ESPN "+report.player_id.slice(5)+")";
    if(dataset.players.length!==1||!dataset.players[0].endsWith(label))
      return {status:"PLAYER_MISMATCH",description:"Report player does not match the locally selected CSV player."};
    if(dataset.records!==report.selected_games)
      return {status:"COUNT_MISMATCH",description:"Imported CSV row count differs from the report."};
    return {status:"BYTES_MATCHED",description:"Identical local CSV bytes and ESPN player ID. Provider rights and authenticity remain unverified."};
  }
  function td(tr,value,header=false){
    const el=document.createElement(header?"th":"td");
    el.textContent=String(value);
    if(header)el.scope="row";
    tr.append(el);
  }
  function resetTable(id,message,count){
    const body=$(id);body.replaceChildren();
    const tr=document.createElement("tr"),cell=document.createElement("td");
    cell.className="table-empty";cell.colSpan=count;cell.textContent=message;
    tr.append(cell);body.append(tr);
  }
  const fmt=value=>value===null||value===undefined?"—":Number(value).toFixed(2);
  let current=null,sequence=0;
  function render(){
    const link=current?assessReportLink(current,root.SportProbDataset):null;
    $("history-report-link").dataset.state=link?.status||"NO_REPORT";
    $("history-report-link").textContent=link
      ?("LOCAL FILE CHECK · "+link.status.replaceAll("_"," ")+" — "+link.description)
      :"No historical report loaded. Select a locally generated JSON report.";
    const visible=link?.status==="BYTES_MATCHED";
    $("history-report-results").hidden=!visible;
    if(!visible){
      const quality=root.SportProbDataset?.quality;
      $("history-quality").textContent=quality
        ?"LOCAL CSV COMPLETENESS · "+quality.records+" records · missing opponent "+quality.missingOpponent+
          " · minutes "+quality.missingMinutes+" · venue "+quality.missingLocation+
          ". Missing values are not inferred."
        :"Import a local CSV to examine its data completeness.";
      $("history-report-status").textContent=current
        ?"Report imported, but the displayed results are withheld until its original CSV bytes match."
        :"No consolidated report imported. Generate one locally with sportprob.season_report.";
      return;
    }
    const report=current,overall=report.overall,phasesData=report.periods;
    $("history-report-status").textContent="Matched "+report.selected_games+
      " completed games · "+report.first_game+" to "+report.last_game+
      ". Observational research only; no model accuracy is established.";
    $("history-quality").textContent="SOURCE QUALITY · "+
      (report.source_verified_season_type_2
        ?"Selected games were cross-checked against local season-type 2 source archives. "
        :"Source season categories were not verified against local archives. ")+
      "Rights and source authenticity remain independently unverified.";
    const table=$("history-report-rows");table.replaceChildren();
    for(const metric of metrics){
      const tr=document.createElement("tr");
      td(tr,metric[0].toUpperCase()+metric.slice(1),true);
      td(tr,fmt(overall[metric].mean));
      for(const phase of phases)td(tr,fmt(phasesData[phase][metric].mean));
      td(tr,fmt(overall[metric].standard_deviation));
      table.append(tr);
    }
    $("history-report-meta").textContent="Source: "+report.dataset_file+
      " · SHA-256 "+report.dataset_sha256+
      " · Historical periods: "+phases.map(p=>phasesData[p].points.games).join(" / ")+
      " games · Training cutoff "+report.cutoffs.training_end_exclusive+
      " · Evaluation begins "+report.cutoffs.historical_evaluation_start_inclusive+
      ". These results are retrospective; no independent validation or licensing clearance.";
    const deltas=$("history-season-deltas");deltas.replaceChildren();
    const changes=Object.entries(report.season_to_season_mean_changes);
    if(!changes.length){
      $("history-season-caption").textContent="No cross-checked season-to-season comparison available.";
    }else{
      $("history-season-caption").textContent=
        "Observed changes in season averages (later minus earlier), not future trend estimates.";
      for(const [name,change] of changes.slice(0,5)){
        if(!/^20\d{2} to 20\d{2}$/.test(name)||!object(change))continue;
        const tr=document.createElement("tr");td(tr,name,true);
        for(const metric of metrics)td(tr,
          typeof change[metric]==="number"&&Number.isFinite(change[metric])
            ?(change[metric]>0?"+":"")+change[metric].toFixed(2):"—");
        deltas.append(tr);
      }
    }
    $("history-report-archive").textContent=report.source_verified_season_type_2
      ?"Cross-checked "+report.source_audit.selected_rows_matched_to_archive+
         " selected games against local source archives. Did-not-play source records are never scored as zero games."
      :"No raw archive cross-check provided. Season classifications remain unverified.";
  }
  async function handleFile(){
    const input=$("history-report-json"),file=input.files?.[0];
    if(!file)return;
    const request=++sequence;
    try{
      if(file.size>160000)throw Error("History JSON exceeds the 160 KB limit");
      const parsed=parseHistoryJSON(await file.text());
      if(request!==sequence)return;
      current=parsed;render();
    }catch(error){
      if(request!==sequence)return;
      current=null;render();
      $("history-report-status").textContent="REPORT REJECTED · "+String(error.message||"Invalid JSON");
    }finally{input.value=""}
  }
  // Every dataset import (including rejection) must invalidate mismatched
  // report metrics immediately; no stale report remains on the screen.
  if(typeof document!=="undefined"&&$("history-report-json")){
    $("history-report-json").addEventListener("change",handleFile);
    document.addEventListener("sportprob:dataset-change",render);
    $("player").addEventListener("change",render);
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={parseHistoryJSON,assessReportLink};
})(typeof globalThis!=="undefined"?globalThis:this);
