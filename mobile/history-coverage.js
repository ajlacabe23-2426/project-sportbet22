"use strict";
// Offline source-coverage review for completed game logs. No prediction or wagering.
(function(root){
  const validDate=value=>{
    if(typeof value!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    const time=Date.parse(value+"T00:00:00.000Z");
    return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===value;
  };
  function auditHistoricalCoverage(records,through){
    if(!Array.isArray(records)||records.length>20000||!validDate(through))
      throw Error("Invalid historical coverage input");
    const groups=new Map();
    // Match the CSV parser's game identity invariants even if this helper is
    // called by another browser module with untrusted direct records.
    const seenGames=new Set(),seenDates=new Set(),seenDatesWithoutId=new Set();
    let excludedAfterCutoff=0;
    for(const row of records){
      if(!row||typeof row.player!=="string"||!row.player.trim()||
         row.player!==row.player.trim()||row.player.length>110||
         !validDate(row.date)||!(row.minutes===null||
          typeof row.minutes==="number"&&Number.isFinite(row.minutes)&&row.minutes>=0&&row.minutes<=80)||
         !(row.gameId===undefined||typeof row.gameId==="string"&&row.gameId.length<=120))
        throw Error("Invalid source observation");
      const gameId=row.gameId||"";
      const dateIdentity=JSON.stringify([row.player,row.date]);
      if(gameId){
        const stableIdentity=JSON.stringify([row.player,gameId]);
        if(seenGames.has(stableIdentity)||seenDatesWithoutId.has(dateIdentity))
          throw Error("Duplicate or ambiguous player/game identity");
        seenGames.add(stableIdentity);
      }else{
        if(seenDates.has(dateIdentity))
          throw Error("Duplicate or ambiguous player/game identity");
        seenDatesWithoutId.add(dateIdentity);
      }
      seenDates.add(dateIdentity);
      if(row.date>through){excludedAfterCutoff++;continue;}
      const list=groups.get(row.player)||[];
      list.push(row);
      groups.set(row.player,list);
    }
    const players=[...groups].map(([player,items])=>{
      const ordered=[...items].sort((a,b)=>a.date.localeCompare(b.date));
      const missingMinutes=ordered.filter(x=>x.minutes===null).length;
      const zeroMinute=ordered.filter(x=>x.minutes===0).length;
      // Unknown minutes do not establish that the player appeared in a game.
      const played=ordered.length-zeroMinute-missingMinutes;
      return {
        player,observedGames:ordered.length,playedGames:played,
        firstGame:ordered[0].date,lastGame:ordered.at(-1).date,
        missingMinutes,unknownParticipationGames:missingMinutes,zeroMinuteGames:zeroMinute,
        status:played<5?"SMALL_HISTORICAL_SAMPLE":"DESCRIPTIVE_ONLY_UNVERIFIED",
      };
    }).sort((a,b)=>a.player.localeCompare(b.player));
    return {
      schema:"sportprob-browser-history-coverage-v1",
      throughInclusive:through,
      observedGames:players.reduce((total,p)=>total+p.observedGames,0),
      excludedAfterCutoff,playerCount:players.length,
      missingMinutes:players.reduce((total,p)=>total+p.missingMinutes,0),
      knownPlayedGames:players.reduce((total,p)=>total+p.playedGames,0),
      unknownParticipationGames:players.reduce((total,p)=>total+p.unknownParticipationGames,0),
      players,
      sourceAuthenticityVerified:false,forecastReady:false,
    };
  }

  function render(){
    if(typeof document==="undefined")return;
    const select=document.getElementById("coverage-through");
    const note=document.getElementById("coverage-note");
    const body=document.getElementById("coverage-rows");
    if(!select||!note||!body)return;
    body.replaceChildren();
    const history=root.SportProbDataset?.directResearchHistory;
    if(!Array.isArray(history)||!history.length){
      select.disabled=true;select.value="";
      note.textContent="Import completed game logs to inspect source coverage and missing minutes.";
      return;
    }
    select.disabled=false;
    if(!validDate(select.value)){
      select.value=history.reduce((last,row)=>row.date>last?row.date:last,history[0].date);
    }
    try{
      const report=auditHistoricalCoverage(history,select.value);
      for(const player of report.players.slice(0,100)){
        const tr=document.createElement("tr");
        for(const value of [player.player,player.playedGames+" / "+player.observedGames,
          player.firstGame,player.lastGame,String(player.missingMinutes),
          player.status==="SMALL_HISTORICAL_SAMPLE"?"Small confirmed sample":"Descriptive only"]){
          const td=document.createElement("td");td.textContent=value;tr.append(td);
        }
        body.append(tr);
      }
      note.textContent=report.observedGames+" historical records through "+report.throughInclusive+
        " across "+report.playerCount+" player(s); "+report.excludedAfterCutoff+
        " future-to-cutoff rows excluded; "+report.missingMinutes+
        " missing minute values (participation unconfirmed); "+report.knownPlayedGames+
        " confirmed appearances. "+(report.players.length>100?"Showing first 100 players. ":"")+
        "Origin rights, completeness and source accuracy are not independently verified. No forecasts.";
    }catch(error){
      body.replaceChildren();
      note.textContent="Historical coverage rejected: "+error.message;
    }
  }
  function reset(){
    const select=document.getElementById("coverage-through");
    if(select)select.value="";
    render();
  }
  if(typeof document!=="undefined"&&document.getElementById("coverage-rows")){
    document.addEventListener("sportprob:dataset-change",reset);
    document.getElementById("coverage-through").addEventListener("change",render);
    render();
  }
  if(typeof module!=="undefined"&&module.exports)module.exports={auditHistoricalCoverage};
})(typeof globalThis!=="undefined"?globalThis:this);
