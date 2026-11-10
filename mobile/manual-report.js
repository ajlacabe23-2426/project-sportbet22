"use strict";
// Offline manual-statistics report display. Exact CSV SHA-256 is required before
// showing metrics; byte identity does not independently verify the source.
(function(root){
  const $=id=>document.getElementById(id);
  const keys=["points","rebounds","assists"];
  const SHA=/^[0-9a-f]{64}$/;
  const object=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const bounded=(n,max=200000)=>typeof n==="number"&&Number.isFinite(n)&&n>=0&&n<=max;
  const positiveInt=(n,max=20000)=>Number.isSafeInteger(n)&&n>0&&n<=max;
  const dateOK=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
    Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
    new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;

  function parseManualResearchJSON(text){
    const doc=JSON.parse(text);
    if(!object(doc)||doc.schema!=="sportprob-manual-statistics-v1"||
       doc.research_only!==true||doc.future_prediction!==false||
       doc.wagering_outputs!==false)
      throw Error("Not a SportProb manual historical-statistics report");
    const meta=doc.dataset;
    if(!object(meta)||typeof meta.id!=="string"||!meta.id.trim()||meta.id.length>200||
       typeof meta.source_name!=="string"||!meta.source_name.trim()||
       meta.source_name.length>250||!SHA.test(meta.sha256)||
       typeof meta.synthetic!=="boolean"||
       meta.rights_independently_verified!==false||
       meta.rights_status_user_declared!=="cleared"||
       !dateOK(doc.as_of_exclusive)||
       !positiveInt(doc.history_games_limit,200)||
       doc.history_games_limit<5||
       !positiveInt(doc.total_input_records)||
       !Array.isArray(doc.players)||!Array.isArray(doc.insufficient_history)||
       doc.players.length>1000||doc.insufficient_history.length>1000)
      throw Error("Invalid report provenance, cutoff, or sample limits");
    const seen=new Set();
    for(const player of doc.players){
      if(!object(player)||typeof player.player_id!=="string"||
         !player.player_id.trim()||player.player_id.length>120||
         seen.has(player.player_id)||
         !positiveInt(player.played_games_before_cutoff)||
         !object(player.statistics))
        throw Error("Invalid or duplicate player summary");
      seen.add(player.player_id);
      if(player.played_games_before_cutoff<5)
        throw Error("Player summary has fewer than five prior games");
      const records=keys.map(stat=>{
        const s=player.statistics[stat];
        if(!object(s)||s.research_only!==true||s.future_prediction!==false||
           s.player_id!==player.player_id||s.stat!==stat||
           s.as_of_exclusive!==doc.as_of_exclusive||
           !positiveInt(s.games_used,200)||
           s.games_used>doc.history_games_limit||
           s.games_used>player.played_games_before_cutoff||
           !dateOK(s.first_game)||!dateOK(s.last_game)||
           s.first_game>s.last_game||
           s.last_game>=doc.as_of_exclusive||
           !bounded(s.average)||!bounded(s.median)||
           !bounded(s.sample_standard_deviation)||
           !bounded(s.production_per_36_played_minutes)||
           !bounded(s.last_five_average)||
           !bounded(s.average_minutes,80)||
           !bounded(s.observed_10th_percentile)||
           !bounded(s.observed_90th_percentile)||
           s.observed_10th_percentile>s.observed_90th_percentile)
          throw Error("Invalid completed-game summary for "+stat);
        return s;
      });
      if(records.some(s=>s.games_used!==records[0].games_used||
         s.first_game!==records[0].first_game||
         s.last_game!==records[0].last_game))
        throw Error("Three-stat sample dates or counts do not reconcile");
    }
    for(const missing of doc.insufficient_history){
      if(!object(missing)||typeof missing.player_id!=="string"||
         !missing.player_id.trim()||missing.player_id.length>120||
         seen.has(missing.player_id)||
         !Number.isSafeInteger(missing.played_games_before_cutoff)||
         missing.played_games_before_cutoff<0||
         missing.played_games_before_cutoff>4)
        throw Error("Invalid insufficient-history entry");
      seen.add(missing.player_id);
    }
    if(!seen.size)throw Error("Report has no player records");
    return doc;
  }

  function assessManualResearchLink(report,dataset,selectedPlayer){
    if(!dataset)return {status:"NO_DATASET",description:"Import the same completed-game CSV under Dataset control."};
    if(!dataset.sha256)return {status:"HASH_UNAVAILABLE",description:"This browser cannot fingerprint the CSV."};
    if(dataset.sha256!==report.dataset.sha256)
      return {status:"HASH_MISMATCH",description:"Report and locally selected CSV have different file bytes."};
    if(dataset.records!==report.total_input_records)
      return {status:"COUNT_MISMATCH",description:"Row counts disagree despite matching file bytes."};
    if(!selectedPlayer||!dataset.players.includes(selectedPlayer))
      return {status:"NO_PLAYER",description:"Select a player from the imported CSV."};
    if(!report.players.some(p=>p.player_id===selectedPlayer))
      return {status:"PLAYER_UNAVAILABLE",description:"Selected player was excluded or has fewer than five earlier played games."};
    return {status:"BYTES_MATCHED",description:"CSV file bytes match the report. Upstream source and rights remain unverified."};
  }

  function cell(row,value,heading=false){
    const el=document.createElement(heading?"th":"td");
    el.textContent=String(value);
    if(heading)el.scope="row";
    row.append(el);
  }
  const fmt=value=>Number(value).toFixed(2);
  let current=null,sequence=0;
  function render(){
    if(typeof document==="undefined")return;
    const dataset=root.SportProbDataset||null;
    const selected=$("player")?.value||"";
    const link=current?assessManualResearchLink(current,dataset,selected):null;
    $("manual-report-link").dataset.state=link?.status||"NO_REPORT";
    $("manual-report-link").textContent=link
      ?"LOCAL FILE CHECK · "+link.status.replaceAll("_"," ")+" — "+link.description
      :"No manual statistics report imported.";
    const match=link?.status==="BYTES_MATCHED";
    $("manual-report-results").hidden=!match;
    if(!match){
      $("manual-report-status").textContent=current
        ?"Report imported; statistics withheld until the exact local CSV and selected player match."
        :"No manual statistics report imported. Generate one locally with sportprob.manual_research.";
      $("manual-report-rows").replaceChildren();
      $("manual-report-meta").textContent="";
      return;
    }
    const profile=current.players.find(p=>p.player_id===selected);
    const summary=profile.statistics.points;
    const table=$("manual-report-rows");table.replaceChildren();
    for(const stat of keys){
      const s=profile.statistics[stat],row=document.createElement("tr");
      cell(row,stat[0].toUpperCase()+stat.slice(1),true);
      cell(row,s.games_used);
      cell(row,fmt(s.average));
      cell(row,fmt(s.median));
      cell(row,fmt(s.sample_standard_deviation));
      cell(row,fmt(s.last_five_average));
      cell(row,fmt(s.production_per_36_played_minutes));
      cell(row,s.observed_10th_percentile+"–"+s.observed_90th_percentile);
      table.append(row);
    }
    $("manual-report-status").textContent="Showing observed statistics for "+selected+
      " · "+summary.games_used+" prior played games · last observed "+summary.last_game+".";
    $("manual-report-meta").textContent="Cutoff (exclusive): "+current.as_of_exclusive+
      " · Source: "+current.dataset.source_name+
      " · SHA-256: "+current.dataset.sha256+
      " · "+(current.dataset.synthetic?"SYNTHETIC EXAMPLE · ":"")+
      "Source rights are user-declared, not independently verified. All values are descriptive.";
  }

  async function importReport(){
    const input=$("manual-report-json"),file=input.files?.[0];
    if(!file)return;
    const attempt=++sequence;
    try{
      if(file.size>2_000_000)throw Error("Manual report exceeds 2 MB");
      const parsed=parseManualResearchJSON(await file.text());
      if(attempt!==sequence)return;
      current=parsed;
      render();
    }catch(error){
      if(attempt!==sequence)return;
      current=null;
      render();
      $("manual-report-status").textContent="REPORT REJECTED · "+String(error.message||"Invalid JSON");
    }finally{input.value=""}
  }

  if(typeof document!=="undefined"&&$("manual-report-json")){
    $("manual-report-json").addEventListener("change",importReport);
    $("player").addEventListener("change",render);
    document.addEventListener("sportprob:dataset-change",render);
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={parseManualResearchJSON,assessManualResearchLink};
})(typeof globalThis!=="undefined"?globalThis:this);
