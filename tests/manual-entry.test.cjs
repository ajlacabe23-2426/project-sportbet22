"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"mobile/manual-entry.js"),"utf8");
function load(){
  const module={exports:{}};
  vm.runInNewContext(source,{module,console},{filename:"mobile/manual-entry.js"});
  return module.exports;
}
const row=(date="2025-12-01",player="Demo Player")=>({
  game_id:"MAN-1",player_id:player,game_date:date,opponent:"Example Opp",
  home:"true",minutes:"30:30",points:"24",rebounds:"7",assists:"6"
});
test("manual input builds canonical CSV import contract and quotes hostile text",()=>{
  const {buildManualCsv}=load();
  const first=row();first.player_id='A, "B"';
  const csv=buildManualCsv([first],"2026-11-10");
  assert.equal(csv.split("\n").length,3);
  assert.match(csv,/game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists/);
  assert.match(csv,/"A, ""B"""/);
  assert.match(csv,/30:30,24,7,6/);
});
test("form rejects future and invalid completed-game dates",()=>{
  const {validateRow}=load();
  assert.throws(()=>validateRow(row("2026-02-30"),"2026-11-10"),/real completed/);
  assert.throws(()=>validateRow(row("2026-11-11"),"2026-11-10"),/real completed/);
  assert.equal(validateRow(row("2025-12-01"),"2026-11-10").points,"24");
});
test("duplicate game IDs and ambiguous same-day observations fail closed",()=>{
  const {buildManualCsv}=load();
  const first=row(),second=row("2025-12-02");
  assert.throws(()=>buildManualCsv([first,second],"2026-11-10"),/Duplicate/);
  second.game_id="MAN-2";
  assert.doesNotThrow(()=>buildManualCsv([first,second],"2026-11-10"));
  second.game_date=first.game_date;second.game_id="";
  assert.throws(()=>buildManualCsv([first,second],"2026-11-10"),/Duplicate/);
});
test("minute and stat validation prevents fabricated played minutes",()=>{
  const {validateRow}=load();
  for(const bad of ["80:59","99","30:61","NaN","1e2"]){
    const changed=row();changed.minutes=bad;
    assert.throws(()=>validateRow(changed,"2026-11-10"),/valid played minutes/);
  }
  const bad=row();bad.minutes="0";assert.throws(()=>validateRow(bad,"2026-11-10"),/Zero-minute/);
  bad.minutes="30";bad.points="-1";assert.throws(()=>validateRow(bad,"2026-11-10"),/whole number/);
  bad.points="201";assert.throws(()=>validateRow(bad,"2026-11-10"),/whole number/);
});
test("manual input is offline-only and connected to the same CSV validation path",()=>{
  assert.doesNotThrow(()=>new vm.Script(source));
  assert.doesNotMatch(source,/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|innerHTML/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/manual-entry\.js"/);
  assert.match(html,/connect-src 'none'/);
  for(const id of ["entry-form","entry-player","entry-date","entry-points",
    "entry-minutes","entry-analyze","entry-export","entry-clear","entry-rows"])
    assert.ok(html.includes('id="'+id+'"'));
  const app=fs.readFileSync(path.join(root,"mobile/app.js"),"utf8");
  assert.match(app,/SportProbIngestFile=importFile/);
});
