/* Append-only chunk journal for a NEW approved isolation workbook only.
 * Precreated sheet D3_Journal: batch_id,kind,part,total,sha256,data.
 * No create/delete/overwrite. Incomplete chunk batches remain uncommitted evidence.
 * Must run under the same project-wide ScriptLock for every reader and writer. */
function juogDomainSheetsStoreV3_(ss,hash,uuid) {
 const sh=ss.getSheetByName('D3_Journal'),header=['batch_id','kind','part','total','sha256','data'];
 if(!sh||JSON.stringify(sh.getRange(1,1,1,6).getValues()[0])!==JSON.stringify(header))throw Error('DOMAIN_STORE_SCHEMA');
 function append(kind,value){const text=JSON.stringify(value);if(text.length>4000000)throw Error('DOMAIN_SIZE_LIMIT');const id=uuid(),n=Math.max(1,Math.ceil(text.length/20000)),digest=hash(text);
  for(let k=0;k<n;k++)sh.appendRow([id,kind,k,n,digest,text.slice(k*20000,(k+1)*20000)]);
  SpreadsheetApp.flush();sh.appendRow([id,kind,'SEALED',n,digest,'']);SpreadsheetApp.flush();
 }
 function read(){const rows=sh.getDataRange().getValues().slice(1),groups={};
  for(const row of rows){const id=String(row[0]);if(!groups[id])groups[id]=[];groups[id].push(row);}
  const data={baseline:null,intents:[],audits:[],commits:[],requests:[],requestEvents:[]};
  for(const entries of Object.values(groups)){
   const seals=entries.filter(r=>r[2]==='SEALED');if(!seals.length)continue;if(seals.length!==1)throw Error('JOURNAL_DUPLICATE_SEAL');
   const seal=seals[0],kind=seal[1],n=Number(seal[3]),parts=entries.filter(r=>r[2]!=='SEALED');
   if(!Number.isInteger(n)||n<1||parts.length!==n)throw Error('JOURNAL_INCOMPLETE');
   parts.sort((a,b)=>Number(a[2])-Number(b[2]));if(parts.some((r,i)=>Number(r[2])!==i||r[1]!==kind||r[3]!==seal[3]||r[4]!==seal[4]))throw Error('JOURNAL_CONFLICT');
   const text=parts.map(r=>r[5]).join('');if(hash(text)!==seal[4])throw Error('JOURNAL_HASH_MISMATCH');const value=JSON.parse(text);
   if(kind==='baseline'){if(data.baseline)throw Error('BASELINE_DUPLICATE');data.baseline=value;}
   else if(['intents','audits','commits','requests','requestEvents'].includes(kind))data[kind].push(value);else throw Error('JOURNAL_KIND');
  }
  if(!data.baseline)throw Error('BASELINE_MISSING');return data;
 }
 return {read,assertFits:i=>{if(JSON.stringify(i).length>4000000)throw Error('DOMAIN_SIZE_LIMIT');},appendIntent:i=>append('intents',i),appendAudit:a=>append('audits',a),appendCommit:c=>append('commits',c),appendRequest:r=>append('requests',r),appendRequestEvent:e=>append('requestEvents',e)};
}
