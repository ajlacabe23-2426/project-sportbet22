"use strict";
// Read-only deployed-pages smoke checks. Never sends game logs or personal data.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {setTimeout:sleep}=require("node:timers/promises");
const {createHash}=require("node:crypto");

const root=path.resolve(__dirname,"..");
const mobile=path.join(root,"mobile");
const expectedDemo=fs.readFileSync(path.join(root,"data/demo_games.csv"));

function localContract(){
  const html=fs.readFileSync(path.join(mobile,"index.html"),"utf8");
  const demo=fs.readFileSync(path.join(mobile,"demo_games.csv"));
  assert.deepEqual(demo,expectedDemo,
    "Bundled public demonstration must match only the repository's synthetic source");
  const catalog=JSON.parse(fs.readFileSync(path.join(mobile,"datasets/catalog.json"),"utf8"));
  assert.equal(catalog.schema,"sportprob-hosted-source-catalog-v1");
  assert.equal(catalog.datasets.length,1,"Public hosted data remains synthetic-only");
  const entry=catalog.datasets[0];
  assert.equal(entry.synthetic,true);
  assert.equal(entry.file,"demo_games.csv");
  assert.equal(entry.records,20);
  assert.equal(entry.sha256,createHash("sha256").update(demo).digest("hex"));
  for(const id of ["csv-file","manual-entry","instant-research","entry-form","instant-rows","source-manager","hosted-load"]){
    assert.ok(html.includes('id="'+id+'"'),"Missing static UI element: "+id);
  }
  assert.match(html,/href="\.\/demo_games\.csv"/);
  assert.match(html,/connect-src 'self'/);
  const scripts=[...html.matchAll(/<script src="\.\/([^"]+)" defer><\/script>/g)].map(match=>match[1]);
  assert.ok(scripts.length>=6,"Expected local JavaScript modules");
  assert.equal(scripts.length,new Set(scripts).size,"Duplicate script path");
  for(const file of [...scripts,"styles.css"]){
    assert.match(file,/^[a-z0-9._-]+$/i,"No external asset paths permitted");
    assert.ok(fs.statSync(path.join(mobile,file)).isFile(),"Missing static asset "+file);
  }
  return {html,scripts};
}
async function remoteFile(url){
  const response=await fetch(url,{redirect:"follow",signal:AbortSignal.timeout(12000)});
  const expectedOrigin=new URL(url).origin;
  assert.equal(new URL(response.url).origin,expectedOrigin,
    "Unexpected cross-origin redirect for "+url);
  return {response,bytes:Buffer.from(await response.arrayBuffer())};
}
async function smoke(url){
  const parsed=new URL(url);
  assert.equal(parsed.protocol,"https:","Pages must use HTTPS");
  const base=new URL(parsed.href.endsWith("/")?parsed.href:parsed.href+"/");
  assert.equal(parsed.search,"","Unexpected query in deployed page URL");
  assert.equal(parsed.hash,"","Unexpected hash in deployed page URL");
  const {scripts}=localContract();
  let page;
  for(let tryNo=0;tryNo<8;tryNo++){
    const result=await remoteFile(base.href);
    if(result.response.status===200&&result.bytes.toString("utf8").includes('id="manual-entry"')){
      page=result;break;
    }
    if(tryNo===7)throw Error("Published page unavailable or obsolete: HTTP "+
      result.response.status+" at "+base.href);
    await sleep(5000);
  }
  assert.match(page.response.headers.get("content-type")||"",/text\/html/i);
  const html=page.bytes.toString("utf8");
  assert.ok(html.includes('id="instant-research"'),"Published page lacks instant research panel");
  assert.ok(html.includes('id="csv-file"'),"Published page lacks CSV importer");
  assert.ok(html.includes("connect-src 'self'"),"Offline-only content policy missing");

  for(const asset of [...scripts,"styles.css","demo_games.csv","datasets/catalog.json"]){
    const location=new URL(asset,base);
    const file=await remoteFile(location.href);
    assert.equal(file.response.status,200,asset+" returned HTTP "+file.response.status);
    assert.ok(file.bytes.length>0,asset+" was empty");
    if(asset==="demo_games.csv")assert.deepEqual(file.bytes,expectedDemo,
      "Published synthetic CSV bytes changed");
    if(asset==="datasets/catalog.json"){
      const catalog=JSON.parse(file.bytes.toString("utf8"));
      assert.equal(catalog.schema,"sportprob-hosted-source-catalog-v1");
      assert.equal(catalog.datasets.length,1);
      assert.equal(catalog.datasets[0].synthetic,true);
      assert.equal(catalog.datasets[0].sha256,
        createHash("sha256").update(expectedDemo).digest("hex"));
    }
    if(asset==="instant-research.js")
      assert.ok(file.bytes.toString("utf8").includes("summarizeCompletedGames"));
    process.stdout.write("PASS "+asset+" HTTP 200\n");
  }
  for(const missing of ["data/demo_games.csv","src/sportprob/manual_research.py"]){
    const result=await remoteFile(new URL(missing,base).href);
    assert.equal(result.response.status,404,
      "Non-static repository source unexpectedly available at "+missing);
  }
  process.stdout.write("PASS hosted static page, assets, synthetic fixture, and source isolation: "+base.href+"\n");
}
(async()=>{
  localContract();
  if(process.argv.includes("--local-only")){
    process.stdout.write("PASS local static site contract and synthetic fixture\n");
    return;
  }
  const url=process.argv[2];
  if(!url)throw Error("Pass the deployment's official Pages URL or use --local-only");
  await smoke(url);
})().catch(error=>{console.error(error);process.exitCode=1;});
