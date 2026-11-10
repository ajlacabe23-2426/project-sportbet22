"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"mobile/instant-research.js"),"utf8");
function moduleUnderTest(){
  const module={exports:{}};
  vm.runInNewContext(source,{module,console},{filename:"mobile/instant-research.js"});
  return module.exports;
}
const row=(player,date,points,rebounds,assists,minutes=30,gameId="")=>
  ({player,date,points,rebounds,assists,minutes,gameId});

test("direct browser research calculates selected historical games from CSV rows",()=>{
  const {summarizeCompletedGames}=moduleUnderTest();
  const rows=Array.from({length:20},(_,i)=>row("DEMO","2026-01-"+String(i+1).padStart(2,"0"),i+1,4,2,30));
  const report=summarizeCompletedGames(rows,"DEMO","2026-01-20","5");
  assert.equal(report.status,"READY");
  assert.equal(report.used_games,5);
  assert.equal(report.eligible_games,20);
  assert.equal(report.first_game,"2026-01-16");
  assert.equal(report.statistics.points.mean,18);
  assert.equal(report.statistics.points.median,18);
  assert.equal(report.statistics.points.last_five_mean,18);
  assert.equal(report.statistics.points.preceding_five_mean,null);
  assert.equal(report.statistics.points.observed_p10,16);
  assert.equal(report.statistics.points.observed_p90,20);
  assert.equal(report.statistics.points.production_per_36_minutes,21.6);
  assert.equal(report.statistics.points.sample_standard_deviation,Math.sqrt(2.5));
});

test("inclusive cutoff protects from later games and excludes DNPs",()=>{
  const {summarizeCompletedGames}=moduleUnderTest();
  const rows=Array.from({length:10},(_,i)=>row("A","2026-02-"+String(i+1).padStart(2,"0"),10+i,2,1,25));
  rows.push(row("A","2026-02-11",0,0,0,0));
  rows.push(row("A","2026-02-12",200,25,20,35));
  rows.push(row("B","2026-02-05",100,20,10,40));
  const report=summarizeCompletedGames(rows,"A","2026-02-11","all");
  assert.equal(report.used_games,10);
  assert.equal(report.excluded_zero_minute_games,1);
  assert.equal(report.statistics.points.mean,14.5);
  assert.equal(report.statistics.points.preceding_five_mean,12);
  assert.equal(report.statistics.points.last_five_mean,17);
  assert.equal(report.last_game,"2026-02-10");
  const shortened=summarizeCompletedGames(rows,"A","2026-02-04","all");
  assert.equal(shortened.status,"INSUFFICIENT_HISTORY");
  assert.equal(shortened.statistics,null);
});

test("missing minutes remain missing: no invented per-36 rate",()=>{
  const {summarizeCompletedGames}=moduleUnderTest();
  const rows=Array.from({length:5},(_,i)=>row("A","2026-03-0"+(i+1),20,5,4,i===0?null:30));
  const report=summarizeCompletedGames(rows,"A","2026-03-05","all");
  assert.equal(report.status,"READY");
  assert.equal(report.missing_minutes,1);
  assert.equal(report.statistics.points.production_per_36_minutes,null);
  assert.equal(report.statistics.points.mean,20);
});

test("wrong source-like data, malformed dates or window values are rejected",()=>{
  const {summarizeCompletedGames}=moduleUnderTest();
  const rows=Array.from({length:5},(_,i)=>row("A","2026-04-0"+(i+1),18,3,2));
  assert.throws(()=>summarizeCompletedGames(rows,"A","2026-02-30"),/Invalid input/);
  assert.throws(()=>summarizeCompletedGames(rows,"A","2026-04-05","4"),/Invalid input/);
  assert.throws(()=>summarizeCompletedGames([...rows,row("A","2026-04-06",-1,4,4)],"A","2026-04-05"),/Invalid completed-game/);
  assert.throws(()=>summarizeCompletedGames([...rows,row("A","2026-04-06",1,0,0,0)],"A","2026-04-05"),/Invalid completed-game/);
});

test("dashboard script has no network or HTML injection APIs and is wired into mobile",()=>{
  assert.doesNotThrow(()=>new vm.Script(source));
  assert.doesNotMatch(source,/\bfetch\s*\(|XMLHttpRequest|innerHTML|localStorage|sessionStorage/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/instant-research\.js"/);
  assert.match(html,/connect-src 'none'/);
  for(const id of ["instant-research","instant-through","instant-window",
    "instant-status","instant-results","instant-rows","instant-provenance"])
    assert.ok(html.includes('id="'+id+'"'),"missing "+id);
  assert.match(source,/sportprob:dataset-change/);
  const app=fs.readFileSync(path.join(root,"mobile/app.js"),"utf8");
  assert.match(app,/directResearchHistory:games\.map/);
});
