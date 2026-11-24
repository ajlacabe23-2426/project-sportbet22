"use strict";
// Explicit opt-in IndexedDB persistence for manually entered, completed-game
// research drafts. No background writes, server transfers or wagering features.
// SHA-256 detects accidental corruption; it is not source authentication.
(function(root){
  const SCHEMA="sportprob-manual-draft-v1";
  const STORE="drafts";
  const DB="sportprob-local-research-v1";
  const KEY="manual-completed-games";
  const FIELDS=["game_id","player_id","game_date","opponent","home","minutes",
    "points","rebounds","assists"];
  const DIGEST=/^[0-9a-f]{64}$/;
  function normalizedRows(rows){
    if(!Array.isArray(rows)||rows.length<1||rows.length>500)
      throw Error("Draft must have 1–500 entries");
    return rows.map(row=>{
      if(!row||typeof row!=="object"||Array.isArray(row))
        throw Error("Invalid saved draft row");
      return Object.fromEntries(FIELDS.map(field=>{
        if(typeof row[field]!=="string")throw Error("Invalid saved draft field");
        return [field,row[field]];
      }));
    });
  }
  async function checksum(csv){
    if(typeof csv!=="string")throw Error("Invalid draft CSV");
    if(typeof TextEncoder==="undefined")throw Error("Text encoding unavailable");
    const bytes=new TextEncoder().encode(csv);
    const hash=await root.SportProbIntegrity?.sha256ArrayBuffer(bytes.buffer);
    if(!hash||!DIGEST.test(hash))
      throw Error("SHA-256 is unavailable; local persistence requires a secure browser context");
    return {hash,byteLength:bytes.byteLength};
  }
  async function sealDraft(rows,buildCsv,hashFn=checksum){
    if(typeof buildCsv!=="function")throw Error("CSV validator unavailable");
    const copies=normalizedRows(rows);
    const csv=buildCsv(copies);
    const {hash,byteLength}=await hashFn(csv);
    if(!DIGEST.test(hash)||!Number.isSafeInteger(byteLength)||byteLength<1||byteLength>2_000_000)
      throw Error("Invalid checksum");
    return {
      schema:SCHEMA,revision:1,rows:copies,rowCount:copies.length,
      byteLength,sha256:hash,savedAt:new Date().toISOString()
    };
  }
  async function openDraft(snapshot,buildCsv,hashFn=checksum){
    if(!snapshot||typeof snapshot!=="object"||Array.isArray(snapshot)||
       snapshot.schema!==SCHEMA||snapshot.revision!==1||
       !Number.isSafeInteger(snapshot.rowCount)||snapshot.rowCount<1||
       !DIGEST.test(snapshot.sha256||"")||
       !Number.isSafeInteger(snapshot.byteLength)||snapshot.byteLength<1||
       snapshot.byteLength>2_000_000||
       typeof snapshot.savedAt!=="string"||
       !Number.isFinite(Date.parse(snapshot.savedAt)))
      throw Error("Unknown or invalid saved draft format");
    if(typeof buildCsv!=="function")throw Error("CSV validator unavailable");
    const rows=normalizedRows(snapshot.rows);
    if(rows.length!==snapshot.rowCount)throw Error("Saved draft row count mismatch");
    const csv=buildCsv(rows); // Canonical parser/identity rules checked anew.
    const {hash,byteLength}=await hashFn(csv);
    if(hash!==snapshot.sha256||byteLength!==snapshot.byteLength)
      throw Error("Saved draft failed checksum verification");
    return rows;
  }
  function openDatabase(){
    if(!root.indexedDB) return Promise.reject(Error("On-device database unavailable"));
    return new Promise((resolve,reject)=>{
      const request=root.indexedDB.open(DB,1);
      request.onupgradeneeded=()=>{
        if(!request.result.objectStoreNames.contains(STORE))
          request.result.createObjectStore(STORE);
      };
      request.onsuccess=()=>resolve(request.result);
      request.onerror=()=>reject(request.error||Error("Could not open on-device storage"));
      request.onblocked=()=>reject(Error("On-device storage is blocked by another tab"));
    });
  }
  async function transact(mode,operation,value){
    const db=await openDatabase();
    return new Promise((resolve,reject)=>{
      let settled=false,result;
      const close=()=>{try{db.close()}catch(_){}};
      try{
        const transaction=db.transaction(STORE,mode);
        const store=transaction.objectStore(STORE);
        const request=operation==="put"?store.put(value,KEY):
          operation==="delete"?store.delete(KEY):store.get(KEY);
        request.onsuccess=()=>{result=request.result;};
        transaction.oncomplete=()=>{if(!settled){settled=true;close();resolve(result)}};
        transaction.onerror=()=>{if(!settled){settled=true;close();reject(transaction.error||Error("On-device storage failed"))}};
        transaction.onabort=()=>{if(!settled){settled=true;close();reject(transaction.error||Error("On-device storage aborted"))}};
      }catch(error){close();reject(error)}
    });
  }
  const saveSnapshot=snapshot=>transact("readwrite","put",snapshot);
  const loadSnapshot=()=>transact("readonly","get");
  const deleteSnapshot=()=>transact("readwrite","delete");
  const api={sealDraft,openDraft,saveSnapshot,loadSnapshot,deleteSnapshot};
  root.SportProbDraftStore=api;
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
})(typeof window!=="undefined"?window:globalThis);
