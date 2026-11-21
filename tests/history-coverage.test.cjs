"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const source=fs.readFileSync(path.resolve(__dirname,"../mobile/history-coverage.js"),"utf8");
const getModule=()=>{const module={exports:{}};vm.runInNewContext(source,{module},{filename:"history-coverage.js"});return module.exports;};
const sample=[
  {player:"DEMO-A",date:"2026-01-02",minutes:32},
  {player:"DEMO-A",date:"2026-01-03",minutes:null},
  {player:"DEMO-A",date:"2026-01-04",minutes:0},
  {player:"DEMO-A",date:"2026-01-06",minutes:29},
  {player:"DEMO-B",date:"2026-01-03",minutes:30},
  {player:"DEMO-B",date:"2026-01-05",minutes:20},
];
test("coverage counts only completed observations through explicit cutoff",()=>{
  const result=getModule().auditHistoricalCoverage(sample,"2026-01-04");
  assert.equal(result.observedGames,4);
  assert.equal(result.excludedAfterCutoff,2);
  assert.equal(result.playerCount,2);
  assert.equal(result.missingMinutes,1);
  const p=result.players.find(x=>x.player==="DEMO-A");
  assert.equal(p.observedGames,3);
  assert.equal(p.playedGames,1);
  assert.equal(p.unknownParticipationGames,1);
  assert.equal(result.knownPlayedGames,2);
  assert.equal(result.unknownParticipationGames,1);
  assert.equal(p.zeroMinuteGames,1);
  assert.equal(p.status,"SMALL_HISTORICAL_SAMPLE");
  assert.equal(result.forecastReady,false);
});
test("invalid record or calendar date fails closed",()=>{
  const audit=getModule().auditHistoricalCoverage;
  assert.throws(()=>audit(sample,"2026-02-30"),/Invalid/);
  assert.throws(()=>audit([{player:"X",date:"bad",minutes:20}],"2026-01-04"),/Invalid/);
  assert.throws(()=>audit([{player:"X",date:"2026-01-02",minutes:"20"}],"2026-01-04"),/Invalid/);
  assert.throws(()=>audit({}, "2026-01-04"),/Invalid/);
});
test("descriptive full history does not imply future readiness",()=>{
  const rows=Array.from({length:6},(_,i)=>({player:"DEMO",date:"2026-01-"+String(i+1).padStart(2,"0"),minutes:30}));
  const result=getModule().auditHistoricalCoverage(rows,"2026-01-06");
  assert.equal(result.players[0].status,"DESCRIPTIVE_ONLY_UNVERIFIED");
  assert.equal(result.sourceAuthenticityVerified,false);
});
test("static UI wireup has no external API or persistent storage",()=>{
  const html=fs.readFileSync(path.resolve(__dirname,"../mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/history-coverage\.js" defer/);
  assert.match(html,/id="coverage-through"/);
  assert.match(html,/id="coverage-rows"/);
  assert.match(html,/id="coverage-note"/);
  assert.doesNotMatch(source,/\bfetch\s*\(|localStorage|sessionStorage|innerHTML|XMLHttpRequest/);
  assert.match(source,/sportprob:dataset-change/);
});

test("missing minutes cannot inflate confirmed participation or sample readiness",()=>{
  const rows=[
    ...Array.from({length:4},(_,i)=>({player:"DEMO",date:"2026-02-"+String(i+1).padStart(2,"0"),minutes:25})),
    ...Array.from({length:5},(_,i)=>({player:"DEMO",date:"2026-02-"+String(i+5).padStart(2,"0"),minutes:null})),
    {player:"DEMO",date:"2026-02-10",minutes:0},
  ];
  const audit=getModule().auditHistoricalCoverage;
  const result=audit(rows,"2026-02-10");
  assert.equal(result.observedGames,10);
  assert.equal(result.knownPlayedGames,4);
  assert.equal(result.unknownParticipationGames,5);
  assert.equal(result.players[0].zeroMinuteGames,1);
  assert.equal(result.players[0].playedGames,4);
  assert.equal(result.players[0].status,"SMALL_HISTORICAL_SAMPLE");

  // Only a fifth confirmed appearance, not a missing-minute row, lifts the small-sample flag.
  rows.push({player:"DEMO",date:"2026-02-11",minutes:30});
  const beforeCutoff=audit(rows,"2026-02-10");
  assert.equal(beforeCutoff.knownPlayedGames,4);
  assert.equal(beforeCutoff.excludedAfterCutoff,1);
  const afterCutoff=audit(rows,"2026-02-11");
  assert.equal(afterCutoff.knownPlayedGames,5);
  assert.equal(afterCutoff.players[0].status,"DESCRIPTIVE_ONLY_UNVERIFIED");
  assert.equal(afterCutoff.forecastReady,false);
});
