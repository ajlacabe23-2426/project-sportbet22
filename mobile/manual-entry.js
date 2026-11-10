"use strict";
// In-memory manual entry of completed games. No network, persistent storage,
// sportsbook information, or future-game forecasts.
(function(root){
  const $=id=>document.getElementById(id);
  const HEADERS=["game_id","player_id","game_date","opponent","home","minutes","points","rebounds","assists"];
  const MAX_ROWS=500;
  const STATS=["points","rebounds","assists"];
  const clean=value=>String(value??"").trim();
  function validDate(value){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    const millis=Date.parse(value+"T00:00:00Z");
    return Number.isFinite(millis)&&new Date(millis).toISOString().slice(0,10)===value;
  }
  function validMinutes(value){
    if(!/^\d{1,2}(?::\d{2}|\.\d{1,3})?$/.test(value))return false;
    const clock=/^(\d{1,2}):(\d{2})$/.exec(value);
    if(clock&&Number(clock[2])>=60)return false;
    const minutes=clock?Number(clock[1])+Number(clock[2])/60:Number(value);
    return Number.isFinite(minutes)&&minutes>=0&&minutes<=80;
  }
  function validateRow(input,today=new Date().toISOString().slice(0,10)){
    if(!input||typeof input!=="object"||Array.isArray(input))throw Error("Invalid game entry");
    const row=Object.fromEntries(HEADERS.map(key=>[key,clean(input[key])]));
    if(!row.player_id||row.player_id.length>110)throw Error("Player ID or name is required (up to 110 characters)");
    if(!validDate(row.game_date)||row.game_date>today)throw Error("Game date must be a real completed calendar date");
    if(row.game_id.length>120||row.opponent.length>90)throw Error("Game ID or opponent label is too long");
    if(!["","true","false"].includes(row.home))throw Error("Location must be home, away, or unknown");
    if(!validMinutes(row.minutes))throw Error("Enter valid played minutes (e.g. 31 or 31:30)");
    for(const stat of STATS){
      if(!/^\d{1,3}$/.test(row[stat])||Number(row[stat])>200)
        throw Error(stat+" must be a whole number from 0 to 200");
    }
    const played=/^\d{1,2}:\d{2}$/.test(row.minutes)
      ? Number(row.minutes.split(":")[0])+Number(row.minutes.split(":")[1])/60
      : Number(row.minutes);
    if(played===0&&STATS.some(key=>Number(row[key])>0))
      throw Error("Zero-minute entries cannot have nonzero statistics");
    return row;
  }
  function checkUnique(rows){
    const games=new Set(),missingIds=new Set(),dates=new Set();
    for(const row of rows){
      const dateKey=JSON.stringify([row.player_id,row.game_date]);
      const gameKey=JSON.stringify([row.player_id,row.game_id]);
      if(row.game_id){
        if(games.has(gameKey)||missingIds.has(dateKey))throw Error("Duplicate player/game ID or ambiguous same-day entry");
        games.add(gameKey);
      }else{
        if(dates.has(dateKey))throw Error("Duplicate player/date without distinct game IDs");
        missingIds.add(dateKey);
      }
      dates.add(dateKey);
    }
  }
  function escapeCsv(value){
    const str=String(value);
    return /[,"\r\n]/.test(str)?'"'+str.replaceAll('"','""')+'"':str;
  }
  function buildManualCsv(input,today=new Date().toISOString().slice(0,10)){
    if(!Array.isArray(input)||!input.length||input.length>MAX_ROWS)throw Error("Draft needs 1–500 games");
    const rows=input.map(row=>validateRow(row,today));
    checkUnique(rows);
    return [HEADERS.join(","),...rows.map(row=>HEADERS.map(key=>escapeCsv(row[key])).join(","))].join("\n")+"\n";
  }

  let draft=[];
  function render(){
    const body=$("entry-rows");
    body.replaceChildren();
    for(let i=0;i<draft.length;i++){
      const item=draft[i],tr=document.createElement("tr");
      const fields=[item.game_date,item.player_id,item.opponent||"—",
        item.minutes,item.points+"/"+item.rebounds+"/"+item.assists];
      for(const field of fields){
        const cell=document.createElement("td");
        cell.textContent=field;tr.append(cell);
      }
      const last=document.createElement("td"),remove=document.createElement("button");
      remove.type="button";remove.textContent="Remove";remove.dataset.remove=String(i);
      remove.className="entry-remove";last.append(remove);tr.append(last);
      body.append(tr);
    }
    $("entry-count").textContent=draft.length+" completed game"+(draft.length===1?"":"s")+" in this device-only draft.";
    $("entry-analyze").disabled=!draft.length;
    $("entry-export").disabled=!draft.length;
  }
  function readForm(){
    const form=$("entry-form");
    return {
      game_id:form.elements.namedItem("game_id").value,
      player_id:form.elements.namedItem("player_id").value,
      game_date:form.elements.namedItem("game_date").value,
      opponent:form.elements.namedItem("opponent").value,
      home:form.elements.namedItem("home").value,
      minutes:form.elements.namedItem("minutes").value,
      points:form.elements.namedItem("points").value,
      rebounds:form.elements.namedItem("rebounds").value,
      assists:form.elements.namedItem("assists").value
    };
  }
  function status(message){$("entry-status").textContent=message}
  function add(event){
    event.preventDefault();
    try{
      if(draft.length>=MAX_ROWS)throw Error("500-entry draft limit reached");
      const row=validateRow(readForm());
      buildManualCsv([...draft,row]);
      draft.push(row);
      render();
      status("Entry validated and added locally. Export CSV to preserve the draft before closing the page.");
    }catch(error){status("ENTRY REJECTED · "+error.message)}
  }
  async function analyze(){
    try{
      const csv=buildManualCsv(draft);
      if(typeof root.SportProbIngestFile!=="function")
        throw Error("Dashboard importer is unavailable");
      if(!$("data-rights").checked||$("source-label").value.trim().length<3)
        throw Error("Declare your data source and confirm research permission under Dataset control first");
      const file=new File([csv],"manual-completed-games.csv",{type:"text/csv"});
      await root.SportProbIngestFile(file);
      const data=root.SportProbDataset;
      status(data?.records===draft.length
        ?"Draft analyzed using the existing validated CSV importer. Open Instant stats to explore."
        :"Draft was not accepted by the dataset importer; review Dataset control.");
    }catch(error){status("ANALYSIS UNAVAILABLE · "+error.message)}
  }
  function exportCsv(){
    try{
      const csv=buildManualCsv(draft);
      const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
      const anchor=document.createElement("a");
      anchor.href=url;anchor.download="sportprob-manual-history.csv";
      document.body.append(anchor);anchor.click();anchor.remove();
      // Revoke after click: browser owns the initiated download.
      setTimeout(()=>URL.revokeObjectURL(url),1000);
      status("CSV export requested. Save the file to keep your manually entered game logs.");
    }catch(error){status("CSV EXPORT UNAVAILABLE · "+error.message)}
  }
  if(typeof document!=="undefined"&&$("entry-form")){
    $("entry-form").addEventListener("submit",add);
    $("entry-analyze").addEventListener("click",analyze);
    $("entry-export").addEventListener("click",exportCsv);
    $("entry-rows").addEventListener("click",event=>{
      const i=event.target?.dataset?.remove;
      if(i===undefined)return;
      const index=Number(i);
      if(!Number.isInteger(index)||index<0||index>=draft.length)return;
      draft.splice(index,1);render();
      status("Draft row removed.");
    });
    $("entry-clear").addEventListener("click",()=>{
      draft=[];render();
      status("Draft cleared from this session. Previously imported CSV research is unchanged.");
    });
    render();
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={validateRow,buildManualCsv};
})(typeof globalThis!=="undefined"?globalThis:this);
