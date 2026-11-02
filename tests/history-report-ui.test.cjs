"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const vm=require("node:vm");
const fs=require("node:fs");
const path=require("node:path");

const root=path.resolve(__dirname,"..");
const client=fs.readFileSync(path.join(root,"mobile/history-report.js"),"utf8");
function moduleUnderTest(){
  const module={exports:{}};
  vm.runInNewContext(client,{module,console},{filename:"mobile/history-report.js"});
  return module.exports;
}
const stat=(games,mean=23)=>({
  games,mean,median:mean,standard_deviation:games>1?4:null,
  observed_min:mean-5,observed_max:mean+5,
  observed_per_36_minutes:mean*1.1
});
function group(games){
  return {
    points:stat(games,23),rebounds:stat(games,5),
    assists:stat(games,7),
    minutes:{games,mean:32,median:32,standard_deviation:games>1?4:null,
      observed_min:27,observed_max:37}
  };
}
function report(){
  return {
    schema:"sportprob-offline-historical-observations-v1",
    research_only:true,future_prediction:false,
    model_evaluation_performed:false,genuinely_blind_validation:false,
    player_id:"ESPN:3975",dataset_file:"local-history.csv",
    dataset_sha256:"a".repeat(64),selected_games:100,
    first_game:"2024-11-01",last_game:"2026-02-01",
    source_rights_independently_verified:false,
    source_authenticity_independently_verified:false,
    source_verified_season_type_2:true,
    cutoffs:{
      training_end_exclusive:"2025-09-01",
      historical_evaluation_start_inclusive:"2025-12-01"
    },
    overall:group(100),
    periods:{training:group(65),calibration:group(15),historical_evaluation:group(20)},
    seasons:{"2025":group(50),"2026":group(50)},
    season_to_season_mean_changes:{"2025 to 2026":{
      points:0.1,rebounds:-0.3,assists:0.2,minutes:-1.3}},
    venue:{home:group(48),away:group(52),unknown:0},
    last_five_completed_games:group(5),
    source_audit:{
      selected_rows_matched_to_archive:100,
      selected_nonregular_rows:0,
      source_rows_by_season_and_type:{"2025 | type 2":50,"2026 | type 2":50},
      did_not_play_rows_by_season_and_type:{}
    }
  };
}
test("Phase 5 report is locally parsed with stringent unverified-source flags",()=>{
  assert.doesNotThrow(()=>new vm.Script(client));
  assert.doesNotMatch(client,/\bfetch\s*\(/);
  assert.doesNotMatch(client,/XMLHttpRequest|innerHTML|localStorage/);
  const {parseHistoryJSON}=moduleUnderTest();
  assert.equal(parseHistoryJSON(JSON.stringify(report())).selected_games,100);
});
test("phase 5 report refuses fraudulent status, tampered provenance and inconsistent period totals",()=>{
  const {parseHistoryJSON}=moduleUnderTest();
  for(const [field,value] of [
    ["research_only",false],["future_prediction",true],
    ["model_evaluation_performed",true],
    ["genuinely_blind_validation",true],
    ["source_rights_independently_verified",true],
    ["source_authenticity_independently_verified",true],
    ["dataset_sha256","not-a-sha"],
    ["selected_games",120],
  ]){
    const doc=report();doc[field]=value;
    assert.throws(()=>parseHistoryJSON(JSON.stringify(doc)),field);
  }
  let doc=report();
  doc.periods.training.points.games=70;
  assert.throws(()=>parseHistoryJSON(JSON.stringify(doc)),/sample statistics/);
  doc=report();doc.source_audit.selected_rows_matched_to_archive=99;
  assert.throws(()=>parseHistoryJSON(JSON.stringify(doc)),/archive matching/);
  doc=report();doc.source_verified_season_type_2=false;doc.source_audit=null;
  assert.doesNotThrow(()=>parseHistoryJSON(JSON.stringify(doc)));
});
test("phase 5 report is withheld for missing, mismatched or stale source CSV",()=>{
  const {assessReportLink}=moduleUnderTest(),doc=report();
  const dataset={sha256:doc.dataset_sha256,players:["Example Player (ESPN 3975)"],
    records:100,quality:{records:100,missingMinutes:0,missingOpponent:0,missingLocation:0}};
  assert.equal(assessReportLink(doc,null).status,"NO_DATASET");
  assert.equal(assessReportLink(doc,{...dataset,sha256:null}).status,"HASH_UNAVAILABLE");
  assert.equal(assessReportLink(doc,{...dataset,sha256:"b".repeat(64)}).status,"HASH_MISMATCH");
  assert.equal(assessReportLink(doc,{...dataset,players:["Other (ESPN 500)"]}).status,"PLAYER_MISMATCH");
  assert.equal(assessReportLink(doc,{...dataset,records:115}).status,"COUNT_MISMATCH");
  assert.equal(assessReportLink(doc,dataset).status,"BYTES_MATCHED");
});
test("dashboard includes offline report section and imports with no remote scripts",()=>{
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/history-report\.js"/);
  for(const id of ["history-report","history-report-json","history-report-link",
      "history-report-results","history-quality","history-report-rows",
      "history-season-deltas"]){
    assert.ok(html.includes('id="'+id+'"'),"missing id "+id);
  }
  assert.ok(html.indexOf("history-report.js")>html.indexOf("app.js"));
  assert.match(html,/connect-src 'none'/);
  assert.match(client,/sportprob:dataset-change/);
});
