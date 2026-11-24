"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
const code=fs.readFileSync(path.join(root,"mobile/draft-store.js"),"utf8");
const entryCode=fs.readFileSync(path.join(root,"mobile/manual-entry.js"),"utf8");
function fakeIndexedDB(){
  const values=new Map();
  let created=false;
  const db={
    objectStoreNames:{contains:name=>created&&name==="drafts"},
    createObjectStore(){created=true},
    close(){},
    transaction(name,mode){
      assert.equal(name,"drafts");
      const tx={
        objectStore(){
          return {
            get(key){return schedule(key,"get")},
            put(value,key){return schedule(key,"put",value)},
            delete(key){return schedule(key,"delete")}
          };
        }
      };
      function schedule(key,operation,value){
        const request={result:undefined};
        queueMicrotask(()=>{
          if(operation==="put")values.set(key,structuredClone(value));
          else if(operation==="delete")values.delete(key);
          else request.result=structuredClone(values.get(key));
          request.onsuccess?.();
          tx.oncomplete?.();
        });
        return request;
      }
      return tx;
    }
  };
  return {
    values,
    open(){
      const request={result:db};
      queueMicrotask(()=>{
        if(!created)request.onupgradeneeded?.();
        request.onsuccess?.();
      });
      return request;
    }
  };
}
function getModules(database=fakeIndexedDB()){
  const context={module:{exports:{}},indexedDB:database,TextEncoder,console};
  vm.runInNewContext(code,context,{filename:"draft-store.js"});
  const store=context.module.exports;
  const entry={module:{exports:{}},console};
  vm.runInNewContext(entryCode,entry,{filename:"manual-entry.js"});
  return {store,buildCsv:entry.module.exports.buildManualCsv,database};
}
const hash=async(csv)=>({
  hash:crypto.createHash("sha256").update(csv,"utf8").digest("hex"),
  byteLength:Buffer.byteLength(csv,"utf8")
});
const sample=[
  {game_id:"G1",player_id:"SYN-A",game_date:"2025-11-01",opponent:"SYN-B",home:"true",minutes:"32",points:"18",rebounds:"4",assists:"6"},
  {game_id:"G2",player_id:"SYN-A",game_date:"2025-11-02",opponent:"SYN-C",home:"false",minutes:"28:30",points:"21",rebounds:"5",assists:"3"}
];
test("versioned snapshot seals canonical CSV and restores validated rows",async()=>{
  const {store,buildCsv}=getModules();
  const snap=await store.sealDraft(sample,buildCsv,hash);
  assert.equal(snap.schema,"sportprob-manual-draft-v1");
  assert.equal(snap.revision,1);
  assert.equal(snap.rowCount,2);
  assert.equal(snap.byteLength,Buffer.byteLength(buildCsv(sample),"utf8"));
  assert.equal(snap.sha256,(await hash(buildCsv(sample))).hash);
  const restored=await store.openDraft(snap,buildCsv,hash);
  assert.equal(JSON.stringify(restored),JSON.stringify(sample));
});
test("corrupt, ambiguous, replayed-schema or mismatched snapshots fail closed",async()=>{
  const {store,buildCsv}=getModules();
  const snap=await store.sealDraft(sample,buildCsv,hash);
  const changed=structuredClone(snap);
  changed.rows[0].points="199";
  await assert.rejects(store.openDraft(changed,buildCsv,hash),/checksum/);
  for(const bad of [
    {...snap,revision:2},
    {...snap,schema:"unexpected"},
    {...snap,rowCount:3},
    {...snap,sha256:"not-a-digest"}
  ]) await assert.rejects(store.openDraft(bad,buildCsv,hash));
  const duplicate=structuredClone(snap);
  duplicate.rows[1].game_id="G1";
  await assert.rejects(store.openDraft(duplicate,buildCsv,hash),/Duplicate/);
});
test("on-device persistence writes, restores, and deletes only on explicit requests",async()=>{
  const {store,buildCsv}=getModules();
  assert.equal(await store.loadSnapshot(),undefined);
  const snap=await store.sealDraft(sample,buildCsv,hash);
  await store.saveSnapshot(snap);
  const loaded=await store.loadSnapshot();
  assert.equal(JSON.stringify(await store.openDraft(loaded,buildCsv,hash)),JSON.stringify(sample));
  await store.deleteSnapshot();
  assert.equal(await store.loadSnapshot(),undefined);
});
test("checksum unavailability blocks persistence instead of silently saving",async()=>{
  const {store,buildCsv}=getModules();
  await assert.rejects(store.sealDraft(sample,buildCsv),/SHA-256/);
});
test("static isolation: no network or silent storage writes at load",()=>{
  assert.doesNotThrow(()=>new vm.Script(code));
  assert.doesNotMatch(code,/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|innerHTML/);
  assert.match(code,/root\.indexedDB\.open/);
  assert.doesNotMatch(code,/onload\s*=/);
  const html=fs.readFileSync(path.join(root,"mobile/index.html"),"utf8");
  for(const id of ["entry-save","entry-restore","entry-delete-saved"])
    assert.ok(html.includes('id="'+id+'"'));
  assert.match(html,/src="\.\/draft-store\.js" defer/);
  assert.match(entryCode,/store\.openDraft\(envelope,buildManualCsv\)/);
});
