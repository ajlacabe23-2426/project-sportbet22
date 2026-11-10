"use strict";
// Completed-game summaries calculated entirely inside the browser.
// No future outcome forecasts, betting logic, network access, or persistent storage.
(function(root){
  const STATS=["points","rebounds","assists"];
  const WINDOWS=new Set(["5","10","20","all"]);
  const byId=id=>document.getElementById(id);
  const dateOK=value=>{
    if(typeof value!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    const time=Date.parse(value+"T00:00:00.000Z");
    return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===value;
  };
  const average=nums=>nums.reduce((total,value)=>total+value,0)/nums.length;
  function sampleSD(nums){
    if(nums.length<2)return null;
    const avg=average(nums);
    return Math.sqrt(nums.reduce((sum,value)=>sum+(value-avg)**2,0)/(nums.length-1));
  }
  function median(nums){
    const ordered=[...nums].sort((a,b)=>a-b),middle=Math.floor(ordered.length/2);
    return nums.length%2?ordered[middle]:(ordered[middle-1]+ordered[middle])/2;
  }
  function percentile(nums,p){
    const ordered=[...nums].sort((a,b)=>a-b);
    return ordered[Math.max(0,Math.ceil(p*ordered.length)-1)];
  }
  function summarizeCompletedGames(records,player,through,window="20"){
    if(!Array.isArray(records)||records.length>20000||typeof player!=="string"||
       !player.trim()||!dateOK(through)||!WINDOWS.has(String(window)))
      throw Error("Invalid input to completed-game research");
    for(const row of records){
      if(!row||typeof row.player!=="string"||!row.player||
         !dateOK(row.date)||!STATS.every(k=>Number.isSafeInteger(row[k])&&row[k]>=0&&row[k]<=200)||
         !(row.minutes===null||typeof row.minutes==="number"&&Number.isFinite(row.minutes)&&row.minutes>=0&&row.minutes<=80)||
         (row.minutes===0&&STATS.some(k=>row[k]>0)))
        throw Error("Invalid completed-game record");
    }
    // One source CSV is all the input. Never read beyond the selected
    // completed-game cutoff, including same-day events from later dates.
    const eligible=records.filter(row=>
      row.player===player&&row.date<=through&&row.minutes!==0
    ).sort((a,b)=>a.date.localeCompare(b.date)||
      String(a.gameId||"").localeCompare(String(b.gameId||"")));
    const selected=window==="all"?eligible:eligible.slice(-Number(window));
    const base={
      player,through_inclusive:through,window:String(window),
      eligible_games:eligible.length,used_games:selected.length,
      excluded_zero_minute_games:records.filter(row=>
        row.player===player&&row.date<=through&&row.minutes===0
      ).length,
      missing_minutes:selected.filter(row=>row.minutes===null).length
    };
    if(selected.length<5)return {...base,status:"INSUFFICIENT_HISTORY",statistics:null};
    const totalMinutes=selected.reduce((total,row)=>total+(row.minutes||0),0);
    const allMinutes=base.missing_minutes===0&&totalMinutes>0;
    const statistics={};
    for(const stat of STATS){
      const values=selected.map(row=>row[stat]);
      statistics[stat]={
        mean:average(values),
        median:median(values),
        sample_standard_deviation:sampleSD(values),
        last_five_mean:average(values.slice(-5)),
        preceding_five_mean:values.length>=10?average(values.slice(-10,-5)):null,
        observed_p10:percentile(values,.1),
        observed_p90:percentile(values,.9),
        production_per_36_minutes:allMinutes?
          36*values.reduce((sum,v)=>sum+v,0)/totalMinutes:null
      };
    }
    return {...base,status:"READY",first_game:selected[0].date,
      last_game:selected.at(-1).date,statistics};
  }
  function tableCell(row,value,header=false){
    const el=document.createElement(header?"th":"td");
    el.textContent=String(value);
    if(header)el.scope="row";
    row.append(el);
  }
  const fmt=n=>n===null?"—":n.toFixed(2);
  function clear(message){
    byId("instant-status").textContent=message;
    byId("instant-results").hidden=true;
    byId("instant-rows").replaceChildren();
    byId("instant-provenance").textContent="";
  }
  function render(){
    if(typeof document==="undefined")return;
    const dataset=root.SportProbDataset;
    if(!dataset||!Array.isArray(dataset.directResearchHistory)){
      byId("instant-through").disabled=true;
      byId("instant-window").disabled=true;
      byId("instant-through").value="";
      clear("Import an authorized completed-game CSV to calculate research statistics on this device.");
      return;
    }
    const player=byId("player").value;
    const through=byId("instant-through").value;
    const window=byId("instant-window").value;
    if(!dateOK(through)){
      clear("Choose a valid completed-game cutoff date.");
      return;
    }
    try{
      const profile=summarizeCompletedGames(dataset.directResearchHistory,player,through,window);
      if(profile.status!=="READY"){
        clear("Insufficient history: "+profile.used_games+
          " selected played games. At least five earlier or same-day completed observations are needed.");
        return;
      }
      byId("instant-results").hidden=false;
      const table=byId("instant-rows");
      table.replaceChildren();
      for(const stat of STATS){
        const s=profile.statistics[stat],row=document.createElement("tr");
        tableCell(row,stat[0].toUpperCase()+stat.slice(1),true);
        for(const n of [s.mean,s.median,s.sample_standard_deviation,
          s.last_five_mean,s.preceding_five_mean,s.production_per_36_minutes])
          tableCell(row,fmt(n));
        tableCell(row,s.observed_p10+"–"+s.observed_p90);
        table.append(row);
      }
      byId("instant-status").textContent="Calculated locally for "+player+
        " · "+profile.used_games+" completed observations · "+profile.first_game+
        " to "+profile.last_game+". No Python or report JSON required.";
      byId("instant-provenance").textContent="Source: selected local CSV · "+
        (dataset.sha256?"SHA-256 "+dataset.sha256:"SHA-256 unavailable")+
        " · cutoff through "+through+" · "+profile.excluded_zero_minute_games+
        " zero-minute rows excluded · "+profile.missing_minutes+
        " selected rows without minutes (per-36 unavailable if any missing). "+
        (dataset.synthetic?"Synthetic demonstration. ":"")+
        "Source permission and completeness are user-declared, not independently verified. No forecast.";
    }catch(error){
      clear("Research data rejected: "+error.message);
    }
  }
  function syncDataset(){
    if(typeof document==="undefined")return;
    const data=root.SportProbDataset;
    const input=byId("instant-through"),window=byId("instant-window");
    if(!data?.directResearchHistory?.length){
      render();return;
    }
    input.disabled=false;window.disabled=false;
    input.max=new Date().toISOString().slice(0,10);
    const player=byId("player").value;
    const rows=data.directResearchHistory.filter(r=>r.player===player);
    input.value=rows.length?rows.reduce((last,r)=>r.date>last?r.date:last,rows[0].date):"";
    render();
  }
  if(typeof document!=="undefined"&&byId("instant-rows")){
    document.addEventListener("sportprob:dataset-change",syncDataset);
    byId("player").addEventListener("change",syncDataset);
    byId("instant-through").addEventListener("change",render);
    byId("instant-window").addEventListener("change",render);
    syncDataset();
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={summarizeCompletedGames};
})(typeof globalThis!=="undefined"?globalThis:this);
