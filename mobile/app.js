"use strict";
// This browser-only explorer is descriptive research, not wagering software.
// No requests, storage, telemetry, third-party scripts or future predictions.
const $=id=>document.getElementById(id);
const SVGN="http://www.w3.org/2000/svg";
const FIELDS=["points","rebounds","assists"];
const SHORT={points:"PTS",rebounds:"REB",assists:"AST"};
let games=[],sampleRange="10",sourceName="",demo=false;
const validDate=value=>{
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const stamp=Date.parse(value+"T00:00:00.000Z");
  return Number.isFinite(stamp)&&new Date(stamp).toISOString().slice(0,10)===value;
};
function rowsFromCsv(raw){
  const rows=[];let line=[],field="",quoted=false;
  for(let i=0;i<raw.length;i++){
    const c=raw[i];
    if(c==='"'){
      if(quoted&&raw[i+1]==='"'){field+='"';i++}
      else if(!quoted&&field.trim().length>0)throw Error("Unexpected CSV quote");
      else quoted=!quoted;
    }else if(c===","&&!quoted){line.push(field);field=""}
    else if((c==="\n"||c==="\r")&&!quoted){
      if(c==="\r"&&raw[i+1]==="\n")i++;
      line.push(field);if(line.some(x=>x.trim()))rows.push(line);
      if(rows.length>20001)throw Error("CSV exceeds 20,000 game rows");
      line=[];field="";
    }else field+=c;
  }
  if(quoted)throw Error("Unclosed CSV quote");
  line.push(field);if(line.some(x=>x.trim()))rows.push(line);
  return rows;
}
function parseGames(raw){
  const lines=rowsFromCsv(raw.replace(/^\uFEFF/,""));
  if(lines.length<2)throw Error("CSV contains no game records");
  const header=lines.shift().map(x=>x.trim().toLowerCase());
  if(header.length>60||new Set(header).size!==header.length)throw Error("Duplicate or excessive CSV columns");
  const lookup=aliases=>{
    const found=aliases.map(key=>header.indexOf(key)).find(n=>n>=0);
    return found===undefined?-1:found;
  };
  const index={
    player:lookup(["player","player_id","player_name","name"]),
    date:lookup(["date","game_date","match_date"]),
    points:lookup(["points","pts"]),
    rebounds:lookup(["rebounds","reb"]),
    assists:lookup(["assists","ast"]),
    home:lookup(["home","home_away","location"]),
    opponent:lookup(["opponent","opp","opponent_team"]),
    minutes:lookup(["minutes","min","mp"]),
    gameId:lookup(["game_id"])
  };
  if(["player","date",...FIELDS].some(k=>index[k]<0))
    throw Error("Required columns: player/date or player_id/game_date, points, rebounds, assists");
  if(lines.length>20000)throw Error("CSV exceeds 20,000 game rows");
  const seen=new Set();
  const parsed=lines.map((columns,i)=>{
    if(columns.length!==header.length)throw Error("CSV row "+(i+2)+" has a different number of columns");
    const get=key=>index[key]<0?"":columns[index[key]].trim();
    const player=get("player"),date=get("date");
    if(!player||player.length>110||!validDate(date))throw Error("Invalid player or calendar date at row "+(i+2));
    const record={player,date,opponent:get("opponent").slice(0,90),gameId:get("gameId"),home:null,minutes:null};
    for(const key of FIELDS){
      const v=get(key);
      if(!/^\d+$/.test(v)||!Number.isSafeInteger(Number(v))||Number(v)>200)
        throw Error("Invalid "+key+" at row "+(i+2));
      record[key]=Number(v);
    }
    if(index.minutes>=0&&get("minutes")!==""){
      const v=get("minutes");
      const clock=/^(\d{1,2}):(\d{2})$/.exec(v);
      const minutes=clock?Number(clock[1])+Number(clock[2])/60:Number(v);
      if((clock&&Number(clock[2])>=60)||(!clock&&!/^\d+(?:\.\d+)?$/.test(v))||
         !Number.isFinite(minutes)||minutes>75)
        throw Error("Invalid minutes at row "+(i+2));
      record.minutes=minutes;
    }
    if(index.home>=0&&get("home")!==""){
      const rawHome=get("home").toLowerCase();
      if(["true","1","home","h"].includes(rawHome))record.home=true;
      else if(["false","0","away","a"].includes(rawHome))record.home=false;
      else throw Error("Invalid home/away value at row "+(i+2));
    }
    const unique=player+"|"+date;
    if(seen.has(unique))throw Error("Duplicate player and game date at row "+(i+2));
    seen.add(unique);
    return record;
  });
  parsed.sort((a,b)=>a.date.localeCompare(b.date)||a.player.localeCompare(b.player));
  return parsed;
}
function mean(nums){return nums.reduce((sum,n)=>sum+n,0)/nums.length}
function median(nums){
  const ordered=[...nums].sort((a,b)=>a-b),center=Math.floor(ordered.length/2);
  return ordered.length%2?ordered[center]:(ordered[center-1]+ordered[center])/2;
}
function deviation(nums){
  if(nums.length<2)return null;
  const avg=mean(nums);
  return Math.sqrt(nums.reduce((total,n)=>total+(n-avg)**2,0)/(nums.length-1));
}
const fmt=(num,places=1)=>num===null||num===undefined?"—":Number(num).toFixed(places);
function svgAdd(parent,tag,attrs={},label){
  const el=document.createElementNS(SVGN,tag);
  for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));
  if(label!==undefined)el.textContent=String(label);
  parent.append(el);return el;
}
function drawChart(dataset,metric){
  const svg=$("series-chart");svg.replaceChildren();
  const empty=$("chart-empty");
  if(!dataset.length){empty.hidden=false;return}
  empty.hidden=true;
  const shown=dataset.slice(-60),values=shown.map(g=>g[metric]);
  const max=Math.max(1,...values)*1.15,lowest=0;
  const top=23,bottom=257,left=50,right=734;
  const x=i=>left+(right-left)*i/Math.max(1,shown.length-1);
  const y=value=>bottom-(value-lowest)/(max-lowest)*(bottom-top);
  for(let i=0;i<5;i++){
    const v=max*(4-i)/4,yp=top+(bottom-top)*i/4;
    svgAdd(svg,"line",{x1:left,x2:right,y1:yp,y2:yp,stroke:"#334957","stroke-width":1,"stroke-dasharray":"4 6"});
    svgAdd(svg,"text",{x:6,y:yp+3,fill:"#92a8b6","font-size":11},Math.round(v));
  }
  const moving=shown.map((g,i)=>{
    // Historical, trailing average only. No game outcome from the future enters.
    if(i<4)return null;
    return mean(values.slice(i-4,i+1));
  });
  const observedPoints=values.map((v,i)=>x(i).toFixed(2)+","+y(v).toFixed(2)).join(" ");
  svgAdd(svg,"polyline",{points:observedPoints,fill:"none",stroke:"#d9fc77","stroke-width":3,"stroke-linejoin":"round","stroke-linecap":"round"});
  const trailing=moving.map((v,i)=>v===null?null:[x(i),y(v)]).filter(Boolean);
  if(trailing.length>=2)
    svgAdd(svg,"polyline",{points:trailing.map(point=>point.map(v=>v.toFixed(2)).join(",")).join(" "),fill:"none",stroke:"#65adc3","stroke-width":2.5,"stroke-dasharray":"6 6","stroke-linejoin":"round"});
  shown.forEach((g,i)=>{
    const point=svgAdd(svg,"circle",{cx:x(i),cy:y(g[metric]),r:shown.length>30?2.7:3.5,fill:"#d9fc77"});
    svgAdd(point,"title",{},g.date+": "+g[metric]+" "+SHORT[metric]);
  });
  svgAdd(svg,"text",{x:left,y:289,fill:"#8faab4","font-size":11},shown[0].date);
  svgAdd(svg,"text",{x:right,y:289,"text-anchor":"end",fill:"#8faab4","font-size":11},shown.at(-1).date);
  svg.setAttribute("aria-label",shown.length+" observed games for "+$("player").value+", "+metric+"; dates "+shown[0].date+" to "+shown.at(-1).date);
  $("chart-footer").textContent="Observed "+shown.length+" of "+dataset.length+" selected games · "+shown[0].date+" to "+shown.at(-1).date+". 5-game line is trailing and descriptive.";
}
function render(){
  if(!games.length)return;
  const player=$("player").value,metric=$("stat").value;
  const playerGames=games.filter(g=>g.player===player);
  const data=sampleRange==="all"?playerGames:playerGames.slice(-Number(sampleRange));
  const values=data.map(g=>g[metric]);
  if(!data.length)return;
  const average=mean(values),low=Math.min(...values),high=Math.max(...values);
  $("metric-games").textContent=String(data.length);
  $("metric-games-caption").textContent="Of "+playerGames.length+" available games";
  $("metric-unit").textContent=SHORT[metric];
  $("metric-average").textContent=fmt(average);
  $("metric-median").textContent=fmt(median(values),1);
  $("metric-range").textContent=low+"–"+high;
  $("chart-title").textContent=player+" · "+SHORT[metric]+" game history";
  $("metric-column").textContent=SHORT[metric];
  $("metric-deviation").textContent=fmt(deviation(values));
  const home=data.filter(g=>g.home===true),away=data.filter(g=>g.home===false);
  $("home-average").textContent=home.length?fmt(mean(home.map(g=>g[metric])))+" ("+home.length+")":"—";
  $("away-average").textContent=away.length?fmt(mean(away.map(g=>g[metric])))+" ("+away.length+")":"—";
  $("metric-trend").textContent=data.length>=10
    ?((mean(values.slice(-5))-mean(values.slice(-10,-5)))>=0?"+":"")+fmt(mean(values.slice(-5))-mean(values.slice(-10,-5)))
    :"—";
  $("context-note").textContent=(home.length+away.length===0)
    ?"Home/away information was not provided in this CSV."
    :"Home and away means use only observations with an explicit location. Counts are in parentheses.";
  drawChart(data,metric);
  const body=$("game-rows");body.replaceChildren();
  for(const g of data.slice(-40).reverse()){
    const tr=document.createElement("tr");
    for(const value of [g.date,g.opponent||"—",g.home===null?"—":g.home?"HOME":"AWAY",g.minutes===null?"—":fmt(g.minutes),g[metric]]){
      const td=document.createElement("td");td.textContent=String(value);tr.append(td);
    }body.append(tr);
  }
  $("rows-label").textContent=data.length+" GAME"+(data.length===1?"":"S")+" IN VIEW";
  $("method-detail").textContent=demo?"SYNTHETIC DEMONSTRATION":"UNVERIFIED LOCAL CSV";
}
function setBusy(busy){
  $("player").disabled=busy;$("stat").disabled=busy;
  document.querySelector(".range-field").disabled=busy;
}
async function handleFile(){
  const chosen=$("csv-file").files?.[0];
  if(!chosen)return;
  setBusy(true);
  $("load-status").textContent="VALIDATING LOCAL CSV…";
  try{
    if(chosen.size>2_000_000)throw Error("File exceeds 2 MB limit");
    const declaredSource=$("source-label").value.trim();
    if(declaredSource.length<3)throw Error("Enter the data source or creator (at least 3 characters)");
    if(!$("data-rights").checked)throw Error("Confirm permission to use this dataset");
    const imported=parseGames(await chosen.text());
    // Do not retain prior records if the new file is invalid.
    games=imported;sourceName=chosen.name+" · source declared: "+declaredSource;
    demo=/demo/i.test(chosen.name)||games.some(x=>/^DEMO[-_]/i.test(x.player)||/^SYN[-_]/i.test(x.gameId));
    const players=[...new Set(games.map(g=>g.player))].sort();
    const select=$("player");select.replaceChildren();
    for(const name of players){const opt=document.createElement("option");opt.value=name;opt.textContent=name;select.append(opt)}
    $("stat").value="points";
    $("quality-badge").textContent=demo?"SYNTHETIC DEMO":"USER-SUPPLIED / UNVERIFIED";
    const missingOpponent=games.filter(g=>!g.opponent).length;
    const missingMinutes=games.filter(g=>g.minutes===null).length;
    const missingLocation=games.filter(g=>g.home===null).length;
    $("dataset-details").textContent=sourceName+" · "+games.length+" records · "+players.length+
      " player(s) · "+games[0].date+" to "+games.at(-1).date+
      ". Missing opponent: "+missingOpponent+"; minutes: "+missingMinutes+
      "; home/away: "+missingLocation+". "+(demo?"Explicitly synthetic sample; not real game history.":"Declared local file only; authenticity and usage permissions not verified.");
    $("load-status").textContent=demo
      ?"SYNTHETIC SAMPLE LOADED · "+games.length+" ROWS"
      :"LOCAL DATASET LOADED · "+games.length+" ROWS · SOURCE UNVERIFIED";
    setBusy(false);
    render();
  }catch(error){
    games=[];sourceName="";demo=false;setBusy(true);
    $("load-status").textContent="IMPORT REJECTED · "+error.message;
    $("quality-badge").textContent="DATASET ERROR";
    $("chart-empty").hidden=false;$("series-chart").replaceChildren();
    $("chart-empty").textContent="No valid dataset loaded. Correct the source and file, then import again.";
    $("dataset-details").textContent="Dataset rejected; no records are currently loaded.";
    $("method-detail").textContent="AWAITING VALID SOURCE";
    $("chart-footer").textContent="No historical observations loaded.";
    $("rows-label").textContent="0 GAMES";
    $("player").replaceChildren(new Option("Import a valid CSV first",""));
    for(const id of ["metric-games","metric-average","metric-median","metric-range","home-average",
                     "away-average","metric-deviation","metric-trend"])
      $(id).textContent="—";
    const table=$("game-rows");table.replaceChildren();
    const row=document.createElement("tr"),cell=document.createElement("td");
    cell.colSpan=5;cell.className="table-empty";cell.textContent="No valid game history loaded.";
    row.append(cell);table.append(row);
    $("csv-file").value="";
  }
}
$("csv-file").addEventListener("change",handleFile);
$("player").addEventListener("change",render);
$("stat").addEventListener("change",render);
for(const button of document.querySelectorAll("[data-range]")){
  button.addEventListener("click",()=>{
    sampleRange=button.dataset.range;
    for(const other of document.querySelectorAll("[data-range]"))
      other.setAttribute("aria-pressed",String(other===button));
    render();
  });
}
