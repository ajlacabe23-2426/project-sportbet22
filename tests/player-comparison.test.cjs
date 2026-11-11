"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"mobile/player-comparison.js"),"utf8");
function load(){
  const module={exports:{}};
  vm.runInNewContext(source,{module,console},{filename:"mobile/player-comparison.js"});
  return module.exports.historicalPlayerComparison;
}
const row=(player,date,points,rebounds,assists)=>({player,date,points,rebounds,assists});

test("comparison shows descriptive averages from each player's latest completed games",()=>{
  const compare=load();
  const rows=[
    row("Z", "2026-01-03", 25,6,8),
    row("A", "2026-01-02", 10,2,5),
    row("Z", "2026-01-01", 15,4,2),
    row("A", "2026-01-05", 20,6,7)
  ];
  const result=compare(rows,"5");
  assert.equal(result.length,2);
  assert.equal(result[0].player,"A");
  assert.equal(result[0].averages.points,15);
  assert.equal(result[0].averages.rebounds,4);
  assert.equal(result[1].lastDate,"2026-01-03");
  assert.equal(result[1].averages.assists,5);
  assert.equal(result[1].availableGames,2);
  assert.equal(rows[0].date,"2026-01-03","original observation data remains unchanged");
});
test("window selects trailing completed games, not earliest games",()=>{
  const compare=load();
  const rows=Array.from({length:22},(_,index)=>row("A",
    "2026-01-"+String(index+1).padStart(2,"0"),index,1,2));
  assert.equal(compare(rows,"5")[0].averages.points,19);
  assert.equal(compare(rows,"10")[0].observedGames,10);
  assert.equal(compare(rows,"20")[0].observedGames,20);
  assert.equal(compare(rows,"all")[0].observedGames,22);
  assert.throws(()=>compare(rows,"3"),/Unsupported/);
});
test("malformed or oversized records fail closed",()=>{
  const compare=load();
  assert.throws(()=>compare([row("A","2026-01-05",-1,1,1)]),/Invalid/);
  assert.throws(()=>compare(new Array(20001).fill(row("A","2026-01-05",1,1,1))),/Invalid/);
});
test("comparison is offline and only uses text-only DOM rendering",()=>{
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/player-comparison\.js"/);
  assert.match(html,/id="comparison-rows"/);
  assert.match(html,/id="comparison-window"/);
  assert.match(html,/connect-src 'self'/);
  assert.doesNotMatch(source,/\bfetch\s*\(|XMLHttpRequest|innerHTML|localStorage/);
  assert.match(source,/sportprob:dataset-change/);
});
