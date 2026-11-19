/* Same pinned UI rules compiled by build_clinical_contract.py. No clinical policy edits. */
function ctTruth(x){return x!==null&&x!==undefined&&x!==false&&x!==0&&x!==''&&(!Array.isArray(x)||x.length>0)&&(!(x&&x.constructor===Object)||Object.keys(x).length>0);}
function ctGet(o,k,d){return o&&Object.prototype.hasOwnProperty.call(o,k)?o[k]:(d===undefined?null:d);}
function ctCmp(op,a,b){if(op==='Is'||op==='Eq')return JSON.stringify(a)===JSON.stringify(b);if(op==='IsNot'||op==='NotEq')return !ctCmp('Eq',a,b);if(op==='In')return Array.from(b||[]).some(x=>ctCmp('Eq',a,x));if(op==='NotIn')return !ctCmp('In',a,b);return ({Lt:()=>a<b,LtE:()=>a<=b,Gt:()=>a>b,GtE:()=>a>=b})[op]();}
function ctDate(s){return new Date(s+'T00:00:00Z');}
function ctPlus(s,d){const dt=ctDate(s);dt.setUTCDate(dt.getUTCDate()+d);return dt.toISOString().slice(0,10);}
function ctBin(op,a,b){if(op==='Sub'&&typeof a==='string'&&typeof b==='string'&&/^\d{4}-/.test(a)&&/^\d{4}-/.test(b))return {days:(ctDate(a)-ctDate(b))/86400000};if(op==='Add'&&b&&b.delta!==undefined)return ctPlus(a,b.delta);if(op==='Sub')return a-b;if(op==='Add')return a+b;throw Error('UNSUPPORTED_CLINICAL_OPERATION');}
function ctTrace(v,id,value){if(v.__trace){if(!v.__trace[id])v.__trace[id]=[];if(!v.__trace[id].includes(value))v.__trace[id].push(value);}return value;}
function ctLabs(raw,required){const parsed={},errors=[],warnings=[];for(const [key,label] of CT_CONTRACT.labs){const val=ctGet(raw,key,''),s=val===null?'':String(val).trim();if(!s){parsed[key]=null;if(required)errors.push(label+'：空欄です（未測定の場合はNAと入力）');}else if(['NA','N/A','未実施','欠測'].includes(s.toUpperCase())){parsed[key]=null;warnings.push(label+'：NA');}else if(!/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/.test(s)||!Number.isFinite(Number(s))){parsed[key]=null;errors.push(label+'：数値またはNAで入力してください');}else{parsed[key]=Number(s);if(parsed[key]<0)errors.push(label+'：負の値は入力できません');if(CT_CONTRACT.diff_keys.includes(key)&&parsed[key]>100)errors.push(label+'：100%を超えています');}}return [parsed,[...new Set(errors)],[...new Set(warnings)]];}
function ctHelpers(v){return {
 text:x=>typeof x==='string'?x.trim():'',len:x=>x.length,any:x=>x.some(ctTruth),abs:Math.abs,int:x=>parseInt(x,10),
 today_jst:()=>v.__today,timedelta:d=>({delta:d}),unique_messages:x=>[...new Set(x.filter(ctTruth))],
 valid_registration_id:x=>/^JUOG-\p{Decimal_Number}{3,4}$/u.test(String(x||'').trim().toUpperCase()),valid_email:x=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(x||'').trim()),
 window_info:(d,tol,span)=>({target:ctPlus(d,tol),min:ctPlus(d,tol-span),max:ctPlus(d,tol+span)}),
 add_months:(s,n)=>{const d=ctDate(s),day=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()+n);const end=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate();d.setUTCDate(Math.min(day,end));return d.toISOString().slice(0,10);},
 validate_cytology:(x,required)=>required&&[null,'','選択してください'].includes(x)?['尿細胞診']:[],
 validate_lab_panel:ctLabs,
 validate_optional_lab_panel:r=>{const [p,e]=ctLabs(r,false);return [p,e.map(x=>x.replace('数値またはNAで入力してください','数値で入力してください（未測定・欠測は空欄）'))];},
 validate_vitals:(sbp,dbp,pulse,temp,prefix)=>{const out=[],lead=prefix?prefix+'：':'';for(const [x,min,max,msg] of [[sbp,40,300,'収縮期血圧は40〜300 mmHgの範囲で入力してください（桁を確認してください）'],[dbp,20,200,'拡張期血圧は20〜200 mmHgの範囲で入力してください（桁を確認してください）'],[pulse,20,250,'脈拍は20〜250 /minの範囲で入力してください（桁を確認してください）'],[temp,25,45,'体温は25〜45 ℃の範囲で入力してください（桁・単位を確認してください）']])if(x!==null&&!(min<=Number(x)&&Number(x)<=max))out.push(lead+msg);if(sbp!==null&&dbp!==null&&Number(dbp)>=Number(sbp))out.push(lead+'拡張期血圧が収縮期血圧以上になっています。入力を確認してください');return out;}
};}
function ctPath(p,path){for(const k of path){if(!p||typeof p!=='object')return null;p=ctGet(p,k);}return p;}
function juogClinicalValidate_(p,today,trace){
 try{
  const spec=CT_CONTRACT.contracts[p.crf_type];if(!spec||!p.data||Array.isArray(p.data))throw Error('SCHEMA');
  for(const key of ['day30_labs_raw','discharge_labs_raw','labs_raw','pathology'])if(key in p.data&&p.data[key]!==null&&(typeof p.data[key]!=='object'||Array.isArray(p.data[key])))throw Error('SCHEMA');
  const shape=[];
  for(const field of ['registration_id','reporter_email','facility_code','facility_name','submission_kind','correction_reason'])if(p[field]!==undefined&&p[field]!==null&&typeof p[field]!=='string')shape.push('TEXT_TYPE:'+field);
  const source=p.data.source_30d_record_version;if(source!==undefined&&source!==null&&source!==''&&(!Number.isInteger(source)||source<0))shape.push('VERSION_TYPE');
  if(p.crf_type==='followup'&&p.data.visit_month!==String(p.visit||'').replace('m','ヶ月')+(p.visit==='24m'?'（終了）':''))shape.push('VISIT_LABEL_MISMATCH');
  const pairs=p.crf_type==='perioperative_30d'?[['day30_labs_raw','day30_labs'],['discharge_labs_raw','inpatient_labs']]:[['labs_raw','labs']];
  for(const [raw,parsed] of pairs){if(p.crf_type==='followup'&&p.data.lab_status!=='実施あり')continue;const expected=ctLabs(p.data[raw]||{},false)[0],actual=p.data[parsed];if(!actual||Object.keys(actual).length!==Object.keys(expected).length||Object.keys(expected).some(k=>actual[k]!==expected[k]))shape.push('LAB_REPRESENTATION:'+parsed);}
  for(const name of spec.dates){const x=ctPath(p,spec.mapping[name]);if(x!==null&&x!==''){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))shape.push('DATE_TYPE:'+name);else if(!Number.isFinite(+ctDate(x))||ctDate(x).toISOString().slice(0,10)!==x)shape.push('DATE_INVALID:'+name);}}
  const prefix={perioperative_30d:'02',day90:'03',followup:'04'}[p.crf_type];
  for(const w of CT_CONTRACT.widgets){if(!w.path||!w.file.startsWith(prefix))continue;const x=ctPath(p,w.path),rules=w.constraints;if(x===null||x===''||Array.isArray(x)&&!x.length)continue;
   if(w.widget==='number_input'){if(typeof x!=='number'||!Number.isFinite(x)){shape.push('NUMBER_TYPE:'+w.path.join('.'));continue;}if(typeof rules.min_value==='number'&&x<rules.min_value||typeof rules.max_value==='number'&&x>rules.max_value)shape.push('RANGE:'+w.path.join('.'));}
   if(['text_input','text_area'].includes(w.widget)&&typeof x!=='string')shape.push('TEXT_TYPE:'+w.path.join('.'));
   if(w.widget==='checkbox'&&typeof x!=='boolean')shape.push('BOOL_TYPE:'+w.path.join('.'));
   if(Array.isArray(rules.options)){const values=w.widget==='multiselect'&&Array.isArray(x)?x:[x];if(w.widget==='multiselect'&&!Array.isArray(x))shape.push('LIST_TYPE:'+w.path.join('.'));if(values.some(z=>typeof z!=='string'||!rules.options.includes(z)))shape.push('OPTION:'+w.path.join('.'));}
  }
  if(shape.length)return {ok:false,missing:[],errors:[...new Set(shape)].sort(),warnings:[]};
  const v={__today:today||Utilities.formatDate(new Date(),'Asia/Tokyo','yyyy-MM-dd'),__trace:trace};
  for(const [key,path] of Object.entries(spec.mapping))v[key]=ctPath(p,path);
  for(const key of spec.dates)if(v[key]==='')v[key]=null;
  for(const key of ['day30_labs_raw','discharge_labs_raw','labs_raw','path'])if(key in v&&v[key]===null)v[key]={};
  v.lab_status=ctGet(p.data,'lab_status');v.cytology_not_done_now=p.data.urine_cytology==='未実施';
  if('approaches' in v&&v.approaches===null)v.approaches=[];
  if('source_30d_record_version' in v&&(v.source_30d_record_version===null||v.source_30d_record_version===''))v.source_30d_record_version=0;
  for(const w of CT_CONTRACT.widgets){if(!w.file.startsWith(prefix)||!(w.target in v))continue;if(v[w.target]===null||v[w.target]===''){if(w.widget==='number_input')v[w.target]=null;else if(w.widget==='multiselect')v[w.target]=[];else if(w.widget==='selectbox')v[w.target]='選択してください';else if(w.widget==='radio')v[w.target]=w.target==='approach_pattern'?'':null;}}
  v.st={session_state:{peri_op_other:p.data.operation_type_other||'',peri_g2_detail:p.data.unrecovered_ae_detail||'',peri_noop_other:p.data.no_operation_other||''}};
  const result=({perioperative_30d:ctRules_perioperative_30d,day90:ctRules_day90,followup:ctRules_followup})[p.crf_type](v);
  return {ok:!result[0].length&&!result[1].length,missing:result[0],errors:result[1],warnings:result[2]};
 }catch(e){return {ok:false,missing:[],errors:['CLINICAL_SCHEMA_INVALID'],warnings:[]};}
}
