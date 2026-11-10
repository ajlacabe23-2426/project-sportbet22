"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"mobile/manual-report.js"),"utf8");

function loader(){
  const module={exports:{}};
  vm.runInNewContext(source,{module,console},{filename:"mobile/manual-report.js"});
  return module.exports;
}
function fixture(){
  const stats={};
  for(const stat of ["points","rebounds","assists"]){
    stats[stat]={
      schema:"sportprob-retrospective-context-v1",
      research_only:true,future_prediction:false,
      player_id:"DEMO-001",stat,
      as_of_exclusive:"2025-11-21",
      games_used:20,first_game:"2025-11-01",last_game:"2025-11-20",
      average:20,median:20,sample_standard_deviation:3.5,
      observed_10th_percentile:15,observed_90th_percentile:27,
      average_minutes:30,production_per_36_played_minutes:24,
      last_five_average:21,preceding_five_average:19,
      home_games:null,away_games:null,opponent_samples:{},
      missing_home_flags:0,note:"historical"
    };
  }
  return {
    schema:"sportprob-manual-statistics-v1",
    research_only:true,future_prediction:false,wagering_outputs:false,
    dataset:{id:"demo",source_name:"Synthetic fixture",source_reference:"local://demo",
      retrieved_at:"2026-10-24T00:00:00+00:00",sha256:"a".repeat(64),
      synthetic:true,rights_status_user_declared:"cleared",
      rights_independently_verified:false},
    total_input_records:20,history_games_limit:40,as_of_exclusive:"2025-11-21",
    players:[{player_id:"DEMO-001",played_games_before_cutoff:20,statistics:stats}],
    insufficient_history:[],limitations:"historical observations"
  };
}
test("manual dashboard JS validates syntax and never requests external data",()=>{
  assert.doesNotThrow(()=>new vm.Script(source));
  assert.doesNotMatch(source,/\bfetch\s*\(/);
  assert.doesNotMatch(source,/\bXMLHttpRequest\b/);
  assert.doesNotMatch(source,/\binnerHTML\b/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/manual-report\.js"/);
  for(const id of ["manual-report","manual-report-json","manual-report-link",
    "manual-report-results","manual-report-rows","manual-report-meta"]){
    assert.ok(html.includes('id="'+id+'"'),"missing "+id);
  }
  assert.match(source,/sportprob:dataset-change/);
});
test("valid historical manual report parses and matches original CSV",()=>{
  const {parseManualResearchJSON,assessManualResearchLink}=loader();
  const doc=parseManualResearchJSON(JSON.stringify(fixture()));
  assert.equal(doc.players[0].statistics.points.games_used,20);
  const dataset={sha256:"a".repeat(64),players:["DEMO-001"],records:20};
  assert.equal(assessManualResearchLink(doc,dataset,"DEMO-001").status,"BYTES_MATCHED");
  assert.equal(assessManualResearchLink(doc,null,"DEMO-001").status,"NO_DATASET");
  assert.equal(assessManualResearchLink(doc,{...dataset,sha256:null},"DEMO-001").status,"HASH_UNAVAILABLE");
  assert.equal(assessManualResearchLink(doc,{...dataset,sha256:"b".repeat(64)},"DEMO-001").status,"HASH_MISMATCH");
  assert.equal(assessManualResearchLink(doc,{...dataset,records:19},"DEMO-001").status,"COUNT_MISMATCH");
  assert.equal(assessManualResearchLink(doc,dataset,"UNLISTED").status,"NO_PLAYER");
});
test("rejects malformed manual reports and future-leaking periods",()=>{
  const {parseManualResearchJSON:parse}=loader();
  for(const edit of [
    x=>{x.dataset.sha256="nope";},
    x=>{x.dataset.rights_independently_verified=true;},
    x=>{x.wagering_outputs=true;},
    x=>{x.players[0].statistics.points.last_game="2025-11-21";},
    x=>{x.players[0].statistics.assists.games_used=4;},
    x=>{x.players[0].statistics.rebounds.average=-4;},
    x=>{x.total_input_records=-1;},
    x=>{x.players.push(x.players[0]);},
  ]){
    const doc=fixture();edit(doc);
    assert.throws(()=>parse(JSON.stringify(doc)));
  }
  assert.throws(()=>parse("{bad json}"));
});
