"use strict";
// Public, read-only historical CSV snapshots served by the same static host.
// Does not fetch third-party APIs, upload user data, store records, or forecast.
(function(root){
  const $=id=>document.getElementById(id);
  const HASH=/^[0-9a-f]{64}$/;
  const DATE=/^\d{4}-\d{2}-\d{2}$/;
  const CSV_NAME=/^[a-z][a-z0-9_-]{0,60}\.csv$/;
  const MAX_CATALOG_BYTES=32000;
  const MAX_SOURCE_BYTES=2000000;
  function validDate(date){
    if(typeof date!=="string"||!DATE.test(date))return false;
    const time=Date.parse(date+"T00:00:00.000Z");
    return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===date;
  }
  function parseHostedCatalog(raw){
    if(typeof raw!=="string"||raw.length>MAX_CATALOG_BYTES)
      throw Error("Catalog is not valid bounded JSON");
    let parsed;
    try{parsed=JSON.parse(raw)}catch{throw Error("Invalid hosted-source catalog JSON")}
    if(parsed?.schema!=="sportprob-hosted-source-catalog-v1"||
       !Array.isArray(parsed.datasets)||parsed.datasets.length<1||
       parsed.datasets.length>20||!validDate(parsed.last_catalog_review))
      throw Error("Invalid hosted-source catalog schema");
    const ids=new Set(),files=new Set();
    const datasets=parsed.datasets.map(entry=>{
      if(!entry||typeof entry!=="object"||
         typeof entry.id!=="string"||!/^[a-z][a-z0-9-]{2,80}$/.test(entry.id)||
         typeof entry.label!=="string"||!entry.label.trim()||entry.label.length>110||
         typeof entry.source!=="string"||entry.source.length<3||entry.source.length>100||
         typeof entry.file!=="string"||!CSV_NAME.test(entry.file)||
         typeof entry.sha256!=="string"||!HASH.test(entry.sha256)||
         !Number.isInteger(entry.records)||entry.records<5||entry.records>20000||
         !validDate(entry.last_game_date)||!validDate(entry.snapshot_date)||
         entry.last_game_date>entry.snapshot_date||
         entry.synthetic!==true||entry.distribution!=="public_static"||
         typeof entry.rights_basis!=="string"||entry.rights_basis.length<20||
         entry.rights_basis.length>300)
        throw Error("Unapproved or invalid hosted dataset. Only original synthetic samples are allowed.");
      if(ids.has(entry.id)||files.has(entry.file))throw Error("Duplicate catalog source ID or file");
      ids.add(entry.id);files.add(entry.file);
      return Object.freeze({
        id:entry.id,label:entry.label,source:entry.source,file:entry.file,
        sha256:entry.sha256,records:entry.records,synthetic:true,
        last_game_date:entry.last_game_date,snapshot_date:entry.snapshot_date,
        rights_basis:entry.rights_basis,distribution:entry.distribution
      });
    });
    return Object.freeze({last_catalog_review:parsed.last_catalog_review,datasets});
  }
  function hostedUrl(filename,baseUrl){
    if(!CSV_NAME.test(filename))throw Error("Unsafe dataset filename");
    const base=new URL("./",baseUrl);
    const target=new URL("./"+filename,base);
    if(!["https:","http:"].includes(base.protocol)||
       target.origin!==base.origin||!target.pathname.startsWith(base.pathname)||
       target.search||target.hash)
      throw Error("Dataset must be served from this website");
    return target.href;
  }
  async function fetchBounded(url,maxBytes){
    const response=await fetch(url,{
      method:"GET",mode:"same-origin",credentials:"omit",
      cache:"no-store",redirect:"error"
    });
    if(!response.ok)throw Error("Hosted file unavailable: HTTP "+response.status);
    const declared=Number(response.headers.get("content-length"));
    if(Number.isFinite(declared)&&declared>maxBytes)throw Error("Hosted file exceeds size limit");
    const bytes=await response.arrayBuffer();
    if(bytes.byteLength>maxBytes)throw Error("Hosted file exceeds size limit");
    return bytes;
  }

  let catalog=null,busy=false;
  function status(message){$("hosted-source-status").textContent=message}
  function selected(){
    return catalog?.datasets.find(entry=>entry.id===$("hosted-source-select").value)||null;
  }
  function renderSelected(){
    const entry=selected();
    $("hosted-load").disabled=busy||!entry;
    $("hosted-source-details").textContent=entry
      ?entry.source+" · "+entry.records+" fictional game records · last game "+
        entry.last_game_date+" · snapshot "+entry.snapshot_date+
        " · synthetic data only · static snapshot, not live. Rights: "+entry.rights_basis+"."
      :"No approved hosted dataset is available.";
  }
  async function discover(){
    if(typeof location!=="undefined"&&location.protocol==="file:"){
      status("Hosted source catalog needs the published website. Local CSV imports still work.");
      return;
    }
    try{
      const url=new URL("./datasets/catalog.json",document.baseURI);
      if(url.origin!==location.origin)throw Error("Catalog URL is not same-origin");
      const bytes=await fetchBounded(url.href,MAX_CATALOG_BYTES);
      const raw=new TextDecoder("utf-8",{fatal:true}).decode(bytes);
      catalog=parseHostedCatalog(raw);
      const selector=$("hosted-source-select");selector.replaceChildren();
      for(const entry of catalog.datasets){
        const option=document.createElement("option");option.value=entry.id;
        option.textContent=entry.label;selector.append(option);
      }
      selector.disabled=false;
      renderSelected();
      status(catalog.datasets.length+" approved synthetic hosted source available. "+
        "Confirm research permission under Dataset control, then load it.");
    }catch(error){
      catalog=null;
      $("hosted-source-select").disabled=true;
      $("hosted-load").disabled=true;
      status("Hosted catalog unavailable · "+error.message+
        ". Manual CSV import is still supported.");
    }
  }
  async function loadHosted(){
    if(busy)return;
    const entry=selected();
    if(!entry){status("Choose a hosted dataset first.");return}
    if(!$("data-rights").checked){
      status("Confirm permission under Dataset control before loading this dataset.");return;
    }
    busy=true;renderSelected();
    status("Checking hosted snapshot integrity before importing…");
    try{
      const bytes=await fetchBounded(hostedUrl(entry.file,document.baseURI),MAX_SOURCE_BYTES);
      const hash=await root.SportProbIntegrity.sha256ArrayBuffer(bytes);
      if(!hash||hash!==entry.sha256)
        throw Error("Hosted data checksum mismatch or SHA-256 unavailable; no import performed");
      if(typeof root.SportProbIngestFile!=="function")throw Error("CSV importer unavailable");
      $("source-label").value=entry.source;
      const file=new File([bytes],entry.file,{type:"text/csv"});
      const ok=await root.SportProbIngestFile(file,{
        expectedSha256:entry.sha256,
        expectedRecords:entry.records,
        id:entry.id,
        snapshotDate:entry.snapshot_date,
        sourceKind:"static-hosted-synthetic"
      });
      if(ok!==true)throw Error("CSV validation rejected this hosted snapshot");
      if(root.SportProbDataset?.sha256!==entry.sha256)throw Error("Dataset selection changed");
      status("HOSTED SYNTHETIC SNAPSHOT LOADED · "+entry.records+
        " completed fictional games · snapshot "+entry.snapshot_date+
        ". Only the same-origin public CSV was downloaded; no user data was uploaded.");
    }catch(error){
      status("HOSTED LOAD REJECTED · "+error.message+
        ". Existing local dataset, if any, remains as indicated in Dataset control.");
    }finally{
      busy=false;renderSelected();
    }
  }
  if(typeof document!=="undefined"&&$("hosted-source-select")){
    $("hosted-source-select").addEventListener("change",renderSelected);
    $("hosted-load").addEventListener("click",loadHosted);
    discover();
  }
  if(typeof module!=="undefined"&&module.exports)
    module.exports={parseHostedCatalog,hostedUrl};
})(typeof globalThis!=="undefined"?globalThis:this);
