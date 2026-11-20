"""Generate exact draft key allowlists from the existing three CRF section containers."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).parent
PAGES={'peri':'02_perioperative_30d_crf.py','d90':'03_day90_crf.py','fu':'04_followup_crf.py'}

def build():
    common=ast.parse((ROOT/'juog_common.py').read_text())
    labs=next(ast.literal_eval(n.value) for n in common.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LAB_FIELDS' for t in n.targets))
    manifest={}
    for page,file in PAGES.items():
        sections={}
        for node in ast.walk(ast.parse((ROOT/file).read_text())):
            if not isinstance(node,ast.With):continue
            section=None
            for item in node.items:
                call=item.context_expr
                if not isinstance(call,ast.Call):continue
                for kw in call.keywords:
                    if kw.arg=='key' and isinstance(kw.value,ast.Constant) and str(kw.value.value).startswith('autosection_'+page+'_'):
                        section=kw.value.value.rsplit('_',1)[1]
            if not section:continue
            keys=set();label=None
            for x in ast.walk(node):
                if not isinstance(x,ast.Call):continue
                for kw in x.keywords:
                    if kw.arg=='key' and isinstance(kw.value,ast.Constant) and str(kw.value.value).startswith(page+'_'):
                        keys.add(kw.value.value)
                if isinstance(x.func,ast.Attribute) and x.func.attr=='markdown' and x.args and isinstance(x.args[0],ast.Constant):
                    val=x.args[0].value
                    if isinstance(val,str) and 'juog-header">' in val:label=val.split('juog-header">')[1].split('</div>')[0]
                if not isinstance(x.func,ast.Name) or not x.args or not isinstance(x.args[0],ast.Constant):continue
                prefix=x.args[0].value
                if x.func.id=='render_submission_kind':keys.update([prefix+'_submission_kind',prefix+'_correction_reason'])
                if x.func.id=='render_cytology':keys.add(prefix+'_cytology')
                if x.func.id in ('render_optional_lab_panel','render_lab_panel'):
                    keys.update(prefix+'_'+lab[0] for lab in labs)
                    keys.update('widget_'+prefix+'_'+lab[0] for lab in labs)
            assert label and keys
            assert not any(keys.intersection(v['keys']) for v in sections.values()), 'Section key overlap'
            sections[section]={'label':label,'keys':sorted(keys)}
        manifest[page]=dict(sorted(sections.items()))
    (ROOT/'autosave_sections.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'autosave_sections_generated.gs').write_text('// GENERATED: python build_autosave_sections.py\nconst PR15_SECTIONS_='+json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+';\n')
    print('Sections:',{k:len(v) for k,v in manifest.items()})
if __name__=='__main__':build()
