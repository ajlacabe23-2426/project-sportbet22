"use strict";
// Local historical comparison only. No predictions, betting lines, ranking
// by expected future performance, persistent storage, or network requests.
(function(root){
  const WINDOWS=new Set(["5","10","20","all"]);
  const METRICS=["points","rebounds","assists"];
  function historicalPlayerComparison(records,window="10"){
    if(!WINDOWS.has(String(window)))throw Error("Unsupported historical comparison window");
    if(!Array.isArray(records)||records.length>20000)throw Error("Invalid completed-game records");
    const byPlayer=new Map();
    for(const row of records){
      if(!row||typeof row.player!=="string"||!row.player||
         typeof row.date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(row.date)||
         !METRICS.every(metric=>Number.isSafeInteger(row[metric])&&row[metric]>=0&&row[metric]<=200))
        throw Error("Invalid completed-game observation");
      if(!byPlayer.has(row.player))byPlayer.set(row.player,[]);
      byPlayer.get(row.player).push(row);
    }
    return [...byPlayer].map(([player,observed])=>{
      observed.sort((a,b)=>a.date.localeCompare(b.date));
      const selected=window==="all"?observed:observed.slice(-Number(window));
      const mean=metric=>Number((selected.reduce((sum,row)=>sum+row[metric],0)/selected.length).toFixed(2));
      return {
        player,
        observedGames:selected.length,
        availableGames:observed.length,
        firstDate:selected[0].date,
        lastDate:selected.at(-1).date,
        averages:{points:mean("points"),rebounds:mean("rebounds"),assists:mean("assists")}
      };
    }).sort((a,b)=>a.player.localeCompare(b.player));
  }
  function renderHistoricalComparison(){
    if(typeof document==="undefined")return;
    const body=document.getElementById("comparison-rows");
    const select=document.getElementById("comparison-window");
    const note=document.getElementById("comparison-note");
    if(!body||!select||!note)return;
    body.replaceChildren();
    const dataset=root.SportProbDataset;
    if(!dataset||!Array.isArray(dataset.comparisonHistory)||!dataset.comparisonHistory.length){
      select.disabled=true;
      note.textContent="Import completed game histories to compare observed player averages.";
      return;
    }
    select.disabled=false;
    const summaries=historicalPlayerComparison(dataset.comparisonHistory,select.value);
    for(const item of summaries.slice(0,100)){
      const tr=document.createElement("tr");
      for(const value of [
        item.player,
        item.observedGames+" / "+item.availableGames,
        item.lastDate,
        item.averages.points.toFixed(1),
        item.averages.rebounds.toFixed(1),
        item.averages.assists.toFixed(1)
      ]){
        const td=document.createElement("td");td.textContent=String(value);tr.append(td);
      }
      body.append(tr);
    }
    const windowName=select.value==="all"?"all available":"last "+select.value;
    note.textContent="Historical averages from each player's "+windowName+
      " completed games; windows and opponents may differ. "+summaries.length+
      " player(s) loaded" +(summaries.length>100?" (showing first 100)":"")+". Source remains unverified. No future prediction.";
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={historicalPlayerComparison};
  if(typeof document!=="undefined"){
    document.addEventListener("sportprob:dataset-change",renderHistoricalComparison);
    document.getElementById("comparison-window")?.addEventListener("change",renderHistoricalComparison);
  }
})(typeof globalThis!=="undefined"?globalThis:this);
