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

const auditScript=fs.readFileSync(path.join(root,"mobile/audit.js"),"utf8");
function auditParser(){
  const module={exports:{}};
  const document={getElementById:()=>({addEventListener:()=>{}}),addEventListener:()=>{}};
  vm.runInNewContext(auditScript,{module,document},{filename:"mobile/audit.js"});
  return module.exports.parseAuditJSON;
}
function validAudit(){
  const score=name=>({
    model:name,evaluated_games:5,mean_negative_log_likelihood:2.1,
    mean_ranked_probability_score:1.8,mean_absolute_error:3.2,
    mean_bias_observed_minus_expected:-0.1,coverage_80:0.8,coverage_90:1,
    mean_interval_width_80:11,
    coverage_80_wilson_95:[0.4,0.95]
  });
  return {
    schema:"sportprob-frozen-model-audit-v1",
    research_only:true,rights_are_not_independently_verified:true,
    synthetic:true,calibration_status:"UNVERIFIED_RESEARCH_BASELINES",
    dataset_id:"sample-demo",dataset_sha256:"a".repeat(64),
    source_name:"Synthetic unit test",player_id:"DEMO-001",stat:"points",
    holdout_start:"2025-11-16",training_games:15,evaluated_games:5,
    training_policy:"frozen_pre_holdout_only",
    scores:[score("negative_binomial_provisional"),
            score("poisson_same_mean_benchmark")]
  };
}
test("offline model-audit interface parses strict, explicitly uncalibrated diagnostics",()=>{
  assert.doesNotThrow(()=>new vm.Script(auditScript));
  assert.doesNotMatch(auditScript,/\bfetch\s*\(/);
  assert.doesNotMatch(auditScript,/\binnerHTML\b/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.match(html,/src="\.\/audit\.js"/);
  for(const id of ["model-audit","audit-json","audit-status","audit-meta","audit-rows"])
    assert.match(html,new RegExp('id="'+id+'"'));
  const parsed=auditParser()(JSON.stringify(validAudit()));
  assert.equal(parsed.player_id,"DEMO-001");
  assert.equal(parsed.scores.length,2);
});
test("offline model-audit viewer rejects forged and malformed source data",()=>{
  const parse=auditParser();
  const mutate=(field,value)=>{
    const input=validAudit();input[field]=value;
    assert.throws(()=>parse(JSON.stringify(input)));
  };
  mutate("synthetic","false");
  mutate("research_only",false);
  mutate("dataset_sha256","not-a-hash");
  mutate("calibration_status","PRODUCTION_READY");
  mutate("scores",[]);
  const negative=validAudit();
  negative.scores[0].mean_absolute_error=-1;
  assert.throws(()=>parse(JSON.stringify(negative)),/Invalid model diagnostic/);
  const duplicates=validAudit();
  duplicates.scores[1].model=duplicates.scores[0].model;
  assert.throws(()=>parse(JSON.stringify(duplicates)),/Unexpected model/);
});

const {webcrypto}=require("node:crypto");
const integrityScript=fs.readFileSync(path.join(root,"mobile/integrity.js"),"utf8");
function loadIntegrity(){
  const module={exports:{}};
  vm.runInNewContext(integrityScript,{module,crypto:webcrypto},{filename:"mobile/integrity.js"});
  return module.exports;
}
test("offline CSV fingerprint matches Python's checked synthetic input byte-for-byte",async()=>{
  const helper=loadIntegrity();
  const bytes=fs.readFileSync(path.join(root,"data/demo_games.csv"));
  const manifest=JSON.parse(fs.readFileSync(path.join(root,"data/demo_games.manifest.json"),"utf8"));
  const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
  assert.equal(await helper.sha256ArrayBuffer(buffer,webcrypto),manifest.sha256);
  const tampered=Buffer.concat([bytes,Buffer.from([10])]);
  const modified=tampered.buffer.slice(tampered.byteOffset,tampered.byteOffset+tampered.byteLength);
  assert.notEqual(await helper.sha256ArrayBuffer(modified,webcrypto),manifest.sha256);
  assert.equal(await helper.sha256ArrayBuffer(buffer,null),null,"nonsecure/unsupported browser must report unavailable, not match");
});
test("audit/CSV linking is fail-closed on absent or different source, player and statistic",()=>{
  const {assessAuditLink}=loadIntegrity();
  const audit=validAudit(),dataset={sha256:audit.dataset_sha256,players:["DEMO-001"],synthetic:true};
  assert.equal(assessAuditLink(audit,null,"DEMO-001","points").status,"NO_DATASET");
  assert.equal(assessAuditLink(audit,{...dataset,sha256:null},"DEMO-001","points").status,"HASH_UNAVAILABLE");
  assert.equal(assessAuditLink(audit,{...dataset,sha256:"b".repeat(64)},"DEMO-001","points").status,"HASH_MISMATCH");
  assert.equal(assessAuditLink(audit,{...dataset,players:["OTHER"]},"DEMO-001","points").status,"PLAYER_MISMATCH");
  assert.equal(assessAuditLink(audit,dataset,"DEMO-001","rebounds").status,"SELECTION_MISMATCH");
  assert.equal(assessAuditLink(audit,dataset,"DEMO-001","points").status,"BYTES_MATCHED");
});
test("integrity application wires dataset replacement to audit re-evaluation without networking",()=>{
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  assert.ok(html.includes('src="./integrity.js"'));
  for(const id of ["csv-sha256","audit-link"])assert.ok(html.includes('id="'+id+'"'));
  assert.ok(script.includes("SportProbIntegrity.sha256ArrayBuffer(bytes)"));
  assert.ok(script.includes("sportprob:dataset-change"));
  assert.ok(auditScript.includes('document.addEventListener("sportprob:dataset-change"'));
  for(const source of [script,auditScript,integrityScript]){
    assert.equal(source.includes("fetch("),false);
    assert.equal(source.includes("innerHTML"),false);
  }
});
