"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const script=fs.readFileSync(path.join(root,"mobile/app.js"),"utf8");
function loadParser(){
  const document={
    getElementById:()=>({addEventListener:()=>{}}),
    querySelectorAll:()=>[]
  };
  const context=vm.createContext({document,console});
  vm.runInContext(script,context,{filename:"mobile/app.js"});
  return csv=>vm.runInContext("parseGames("+JSON.stringify(csv)+")",context);
}
test("mobile application has valid JavaScript syntax and uses no network APIs",()=>{
  assert.doesNotThrow(()=>new vm.Script(script));
  assert.doesNotMatch(script,/\bfetch\s*\(/);
  assert.doesNotMatch(script,/\bXMLHttpRequest\b/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/app\.js"/);
  assert.match(html,/href="\.\/styles\.css"/);
  assert.match(html,/connect-src 'none'/);
  for(const id of ["csv-file","player","stat","series-chart","game-rows","load-status"])
    assert.match(html,new RegExp('id="'+id+'"'));
});
test("the bundled synthetic research fixture loads with its native player_id and game_date columns",()=>{
  const csv=fs.readFileSync(path.join(root,"data/demo_games.csv"),"utf8");
  const records=loadParser()(csv);
  assert.equal(records.length,20);
  assert.equal(records[0].player,"DEMO-001");
  assert.equal(records[0].date,"2025-11-01");
  assert.equal(records[0].points,19);
  assert.equal(records[0].minutes,30);
  assert.equal(records[0].home,true);
  assert.equal(records[1].home,false);
  assert.equal(records.at(-1).date,"2025-11-20");
});
test("player/date aliases work and optional context remains nullable when absent",()=>{
  const parsed=loadParser()("player,date,points,rebounds,assists\nA,2026-01-03,20,8,6\n");
  assert.equal(parsed.length,1);
  assert.equal(parsed[0].player,"A");
  assert.equal(parsed[0].minutes,null);
  assert.equal(parsed[0].home,null);
  assert.equal(parsed[0].opponent,"");
});
test("invalid calendar days, duplicates and fractional counts are rejected",()=>{
  const parse=loadParser();
  const header="player,date,points,rebounds,assists\n";
  assert.throws(()=>parse(header+"A,2026-02-30,10,5,4\n"),/calendar date/);
  assert.throws(()=>parse(header+"A,2026-02-19,10,5,4\nA,2026-02-19,20,6,5\n"),/Duplicate player/);
  assert.throws(()=>parse(header+"A,2026-02-19,10.5,5,4\n"),/Invalid points/);
  assert.throws(()=>parse(header+"A,2026-02-19,10,-1,4\n"),/Invalid rebounds/);
});
test("quoted CSV context fields remain literal data, never markup",()=>{
  const input='player,date,points,rebounds,assists,opponent\n"A","2026-01-09",20,5,4,"Team ""Example"""';
  const data=loadParser()(input);
  assert.equal(data[0].opponent,'Team "Example"');
});

test("common shorthand stats exports and MM:SS duration import without rounding minutes to a whole game",()=>{
  const csv=fs.readFileSync(path.join(root,"data/IMPORT_TEMPLATE.csv"),"utf8");
  const result=loadParser()(csv);
  assert.equal(result.length,2);
  assert.equal(result[0].player,"EXAMPLE-PLAYER");
  assert.equal(result[0].points,18);
  assert.equal(result[0].rebounds,6);
  assert.equal(result[0].assists,4);
  assert.equal(result[0].minutes,28.5);
  assert.equal(result[0].home,true);
  assert.equal(result[1].home,false);
  assert.equal(result[0].opponent,"EXAMPLE-OPP");
});

test("import form requires a source declaration and acknowledgement",()=>{
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/id="source-label"/);
  assert.match(html,/id="data-rights"/);
  assert.match(script,/Confirm permission to use this dataset/);
  assert.match(script,/Enter the data source or creator/);
});
