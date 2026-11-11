"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {createHash}=require("node:crypto");
const root=path.resolve(__dirname,"..");
const moduleText=fs.readFileSync(path.join(root,"mobile/source-manager.js"),"utf8");
const catalogText=fs.readFileSync(path.join(root,"mobile/datasets/catalog.json"),"utf8");
const sourceBytes=fs.readFileSync(path.join(root,"mobile/demo_games.csv"));
const moduleExports=()=>{
  const module={exports:{}};
  vm.runInNewContext(moduleText,{module,console},{filename:"mobile/source-manager.js"});
  return module.exports;
};
test("only fictional, public-static source entries with exact provenance pass",()=>{
  const {parseHostedCatalog}=moduleExports();
  const parsed=parseHostedCatalog(catalogText);
  assert.equal(parsed.datasets.length,1);
  assert.equal(parsed.datasets[0].synthetic,true);
  assert.equal(parsed.datasets[0].records,20);
  assert.equal(parsed.datasets[0].file,"demo_games.csv");
  assert.equal(parsed.datasets[0].last_game_date,"2025-11-20");
  assert.equal(parsed.datasets[0].sha256,createHash("sha256").update(sourceBytes).digest("hex"));
  assert.equal(sourceBytes.compare(fs.readFileSync(path.join(root,"data/demo_games.csv"))),0);
});
test("unreviewed real sources, invalid identifiers and traversal are rejected",()=>{
  const {parseHostedCatalog,hostedUrl}=moduleExports();
  const change=(mutate)=>{
    const data=JSON.parse(catalogText);
    mutate(data.datasets[0]);
    assert.throws(()=>parseHostedCatalog(JSON.stringify(data)));
  };
  change(entry=>{entry.synthetic=false;});
  change(entry=>{entry.distribution="third_party";});
  change(entry=>{entry.sha256="not-a-hash";});
  change(entry=>{entry.file="../../secrets.csv";});
  change(entry=>{entry.file="https://another.test/game.csv";});
  change(entry=>{entry.records=0;});
  change(entry=>{entry.snapshot_date="2025-02-30";});
  change(entry=>{entry.last_game_date="2026-12-30";});
  change(entry=>{entry.rights_basis="";});
  assert.throws(()=>hostedUrl("../private.csv","https://example.org/project/index.html"));
  assert.throws(()=>hostedUrl("https://evil.test/data.csv","https://example.org/project/index.html"));
  assert.equal(hostedUrl("demo_games.csv","https://example.org/project/index.html"),
    "https://example.org/project/demo_games.csv");
  assert.equal(hostedUrl("demo_games.csv","http://localhost:3211/mobile/index.html"),
    "http://localhost:3211/mobile/demo_games.csv");
});
test("duplicate or excessive catalog entries and invalid schema are rejected",()=>{
  const {parseHostedCatalog}=moduleExports();
  const data=JSON.parse(catalogText);
  data.datasets.push({...data.datasets[0]});
  assert.throws(()=>parseHostedCatalog(JSON.stringify(data)),/Duplicate/);
  const invalid=JSON.parse(catalogText);invalid.schema="unexpected";
  assert.throws(()=>parseHostedCatalog(JSON.stringify(invalid)),/schema/);
  assert.throws(()=>parseHostedCatalog("x".repeat(32001)),/bounded/);
});
test("hosted catalog has only a same-site explicit network path and static UI integration",()=>{
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  const app=fs.readFileSync(path.join(root,"mobile/app.js"),"utf8");
  assert.doesNotThrow(()=>new vm.Script(moduleText));
  assert.match(html,/src="\.\/source-manager\.js" defer/);
  assert.match(html,/id="hosted-source-select"/);
  assert.match(html,/id="hosted-load"/);
  assert.match(html,/id="hosted-source-status"/);
  assert.match(html,/connect-src 'self'/);
  assert.doesNotMatch(html,/connect-src \*/);
  assert.match(moduleText,/credentials:"omit"/);
  assert.match(moduleText,/mode:"same-origin"/);
  assert.match(moduleText,/redirect:"error"/);
  assert.doesNotMatch(moduleText,/XMLHttpRequest|localStorage|sessionStorage|innerHTML/);
  assert.match(app,/expectedRecords/);
  assert.match(app,/Hosted dataset integrity mismatch/);
});
