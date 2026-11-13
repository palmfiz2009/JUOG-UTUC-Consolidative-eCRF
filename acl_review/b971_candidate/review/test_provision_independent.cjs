const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict');
const path=process.argv[2];if(!path)throw Error('CANDIDATE_FILE_REQUIRED');
const source=fs.readFileSync(path,'utf8'),ident=JSON.parse(fs.readFileSync(require('path').resolve(path,'../source_identity.json')));
const {Domain,provision}=new Function(source+';return {Domain:JuogDomainServiceV3,provision:juogProvisionFixture971Core_};')();
const clone=x=>JSON.parse(JSON.stringify(x)),hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const results=[];
function setup(){
 const header=['registered_at','registration_id','status','facility_code','facility_name','consent_date'];
 const state={baseline:{Registry:[header,['2026-04-01','JUOG-970','ACTIVE','TEST01','完全架空施設','2026-03-25']],Other:[['key'],['970 unchanged']]},intents:[],audits:[],commits:[],requests:[{id:'old-request',operation:{payload:{registration_id:'JUOG-970'}}}],requestEvents:[{id:'old-event'}]};
 const store={read:()=>clone(state),assertFits:()=>{},appendIntent:i=>state.intents.push(clone(i)),appendAudit:i=>state.audits.push(clone(i)),appendCommit:i=>state.commits.push(clone(i))};
 const domain=new Domain({store,hash,now:()=> '2026-11-13T04:00:00Z',withLock:f=>f(),authenticate:()=>({id:'seed',enabled:true}),authorize:()=>({ok:true}),privacy:()=>false,plan:(a,p,t)=>({ok:true,after:{...t,marker:p.n},result:{n:p.n}})});
 for(let n=1;n<=7;n++)assert.equal(domain.execute('offline',{id:'seed'+n,action:'seed',payload:{n},expected_revision:n-1}).ok,true);
 return {state,store,domain,deps:{guard:()=>{},store,hash,now:()=> '2026-11-13T04:00:00Z',fixtureSha:ident.fixture_sha256}};
}
function check(name,f){f();results.push({name,passed:true});}
check('populated revision7 append preserves complete old view/history',()=>{
 const x=setup(),old=clone(x.state),before=x.domain.readView(); const r=provision(x.deps);assert.equal(r.ok,true);assert.equal(r.revision,8);
 const after=x.domain.readView();after.tables.Registry.pop();assert.deepEqual(after.tables,before.tables);
 for(const k of ['intents','audits','commits'])assert.deepEqual(x.state[k].slice(0,7),old[k]);
 for(const k of ['baseline','requests','requestEvents'])assert.deepEqual(x.state[k],old[k]);
});
check('same fixed operation id retry is idempotent',()=>{const x=setup();assert.equal(provision(x.deps).ok,true);const before=clone(x.state);assert.equal(provision(x.deps).existing,true);assert.deepEqual(x.state,before)});
for(const stage of ['appendAudit','appendCommit'])check('partial '+stage+' same operation recovery',()=>{
 const x=setup(),original=x.store[stage];let first=true;x.store[stage]=item=>{if(first){first=false;throw Error('offline interruption')}original(item)};
 assert.equal(provision(x.deps).ok,false);assert.equal(x.state.intents.length,8);assert.equal(provision(x.deps).ok,true);assert.equal(x.state.intents.length,8);assert.equal(x.state.commits.length,8);assert.equal(x.state.audits.length,8);
});
for(const location of ['requests','requestEvents'])check('971 collision in '+location+' refuses before write',()=>{const x=setup();x.state[location].push({id:'collision',case_id:'JUOG-971'});const before=clone(x.state);assert.throws(()=>provision(x.deps),/FIXTURE_ALREADY_USED/);assert.deepEqual(x.state,before)});
check('971 collision in existing Registry refuses',()=>{const x=setup();x.state.baseline.Registry.push(['','JUOG-971']);const before=clone(x.state);assert.throws(()=>provision(x.deps),/FIXTURE_ALREADY_USED/);assert.deepEqual(x.state,before)});
check('wrong base revision refuses',()=>{const x=setup();for(const k of ['intents','audits','commits'])x.state[k].pop();const before=clone(x.state);assert.throws(()=>provision(x.deps),/FIXTURE_BASE_REVISION/);assert.deepEqual(x.state,before)});
check('guard refusal produces no writes',()=>{const x=setup(),before=clone(x.state);x.deps.guard=()=>{throw Error('GUARD')};assert.throws(()=>provision(x.deps),/GUARD/);assert.deepEqual(x.state,before)});
check('prior unrelated pending intent blocks new initialization',()=>{const x=setup();x.state.intents.push({id:'unrelated',revision:8});const before=clone(x.state);assert.equal(provision(x.deps).error,'DOMAIN_RECOVERY_REQUIRED');assert.deepEqual(x.state,before)});
console.log(JSON.stringify({scope:'OFFLINE_INDEPENDENT_PROVISIONING_TEST',source_sha256:hash(source),passed:results.length,results,formal_uat_delta:0},null,2));
