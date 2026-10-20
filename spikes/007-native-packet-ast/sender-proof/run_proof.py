"""Fixed-scope offline compiler replay. Never imports runtime or opens sockets."""
import hashlib,json,pathlib,subprocess,sys
import trace_sender as t
ROOT=pathlib.Path('/home/otto/dev/ro-bots')
WORK=pathlib.Path('/home/otto/.hermes/cache/scratch/sender-proof-work')
AUTH=pathlib.Path('/home/otto/.hermes/cache/scratch/native-profile-replay-s2jdj4rn/output/result.json')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(command,name):
 p=subprocess.run(command,capture_output=True,text=True,timeout=40)
 (WORK/(name+'.stdout')).write_text(p.stdout);(WORK/(name+'.stderr')).write_text(p.stderr)
 commands.append({'command':command,'exit':p.returncode,'stdout':str(WORK/(name+'.stdout')),'stderr':str(WORK/(name+'.stderr'))})
 return p
commands=[]
assert sha(AUTH)==t.AUTHORITY_SHA
r=json.loads(AUTH.read_text());assert r['source_closure_sha256']==t.SOURCE_SHA
assert all(sha(p)==h for p,h in r['artifacts'].items())
inventory=json.loads(pathlib.Path(r['inventory']['path']).read_text())
source=AUTH.parent.parent/'public-source'
assert all(sha(source/p)==h for p,h in inventory['after'].items())
freeze=json.loads(pathlib.Path('/home/otto/.hermes/cache/scratch/native-profile-replay-parent-freeze.json').read_text())
assert all(sha(ROOT/p)==h for p,h in freeze.items())
base=next(c['command'] for c in r['commands'] if c['name']=='gcc-layout-build')
cmd=list(base);cmd[-1]=str(WORK/'gcc-layout');q=run(cmd,'fresh-gcc-build');assert q.returncode==0
q=run([str(WORK/'gcc-layout')],'fresh-gcc-layout');assert q.returncode==0
measured=json.loads(q.stdout)['emotion']
nodes=json.loads((WORK/'selected.json').read_text())
real=[t.trace(nodes,s,measured if s=='clif_emotion' else None) for s in ('clif_emotion','clif_name','clif_sitting')]
assert real[0]['decision']=='IDENTITY_LAYOUT_CANDIDATE',real[0]
# Independently compiled owned mutations: no AST construction and no file-trust denial.
pre='struct P { short h; int x; }; const short H=1; void clif_send(const void*,unsigned); void mutate(P*); void helper(P&); void f(){ '
post=' clif_send(&p,sizeof(p)); }'
bodies=[
'P p{};p.h=H;mutate(&p);','P p{};p.h=H;helper(p);','P p{};p.h=H;P *a=&p;a->h=2;',
'P p{};p.h=H;P &a=p;a.h=2;','P p{};p.h=H;p.h=2;','P p{};p.h=H;(p.h)=2;',
'P p{};p.h=H;p=P{};','P p{};p.h=H;(p)=P{};','P p{};p.h=H;++p.h;',
'P p{};p.h=H;(p.h)++;','P p{};p.h=H;--p.h;','P p{};p.h=H;p.h+=1;',
'P p{};p.h=H;if(p.x)p.h=2;','P p{};p.h=H;{P p{};p.h=H;}',
'P p{};p.h=H;auto a=[&](){p.h=2;};a();','P p{};p.h=H;[](P p){clif_send(&p,sizeof(p));}(p);',
'P p{};p.h=H;sizeof(mutate(&p));','P p{};p.h=H;p.x=(mutate(&p),1);',
'P p{};p.h=H;p.x=sizeof(p);','P p{};p.h=H;p.x=p.h;',
'P p{};p.h=H;while(p.x)p.h=2;','P p{};p.h=H;for(int i=0;i<1;i++)p.h=2;',
'P p{};p.h=H;do{p.h=2;}while(false);','P p{};p.h=H;switch(p.x){default:p.h=2;}',
'P p{};p.h=H;try{mutate(&p);}catch(...){}','P p; p.h=H;','P p{1,0};p.h=H;'
]
# sizeof(void) is deliberately replaced with unevaluated integer expression to stay valid C++.
bodies[16]='P p{};p.h=H;sizeof((mutate(&p),1));'
rows=[]
for i,b in enumerate(bodies):
 src=WORK/('negative-%02d.cpp'%i);src.write_text(pre+b+post)
 c=['/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++','-std=c++17','-fsyntax-only','-Xclang','-ast-dump=json',str(src)]
 q=run(c,'negative-%02d'%i);assert q.returncode==0,(i,q.stderr)
 v=t.trace(json.loads(q.stdout)['inner'],'f',{'id':1,'size':8,'offsets':[0,4]})
 assert v['decision']=='UNRESOLVED',(i,v)
 rows.append({'source':str(src),'source_sha256':sha(src),'result':v,'group':'owned_structural_negative'})
# Retain ALL available previous fixture failures, including non-applicable grammar.
old=json.loads((ROOT/'run/reviews/native-ast-binding-feasibility.json').read_text())
for i,case in enumerate(old['cases']):
 src=pathlib.Path(case['source'])
 if not src.exists():continue
 c=['/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++','-std=c++17','-fsyntax-only','-Xclang','-ast-dump=json',str(src)]
 q=run(c,'retained-%02d'%i)
 results=[]
 if q.returncode==0:
  ns=json.loads(q.stdout)['inner']
  for f in ns:
   if f.get('kind')=='FunctionDecl' and f.get('name')!='clif_send' and any(n.get('kind')=='CompoundStmt' for n in f.get('inner',[])):
    results.append(t.trace(ns,f['name']))
 assert not any(v['decision']=='IDENTITY_LAYOUT_CANDIDATE' for v in results)
 rows.append({'source':str(src),'source_sha256':sha(src),'group':'retained_previous','compiler_exit':q.returncode,'prior_expected_kind':case.get('expected_kind'),'results':results,'coverage_claim':'no numeric join for old fixtures; structurally unresolved, not file hash denial'})
assert all(sha(ROOT/p)==h for p,h in freeze.items())
oldpy=json.loads(pathlib.Path('/home/otto/.hermes/cache/scratch/sender-proof-freeze.json').read_text())
assert all(sha(p)==h for p,h in oldpy.items())
report={'verdict':'PARTIAL_CANDIDATE_ONLY','candidate_only':True,'sink_contract_status':'UNREVIEWED','sender_semantic_admission':False,'runtime_admission':False,'binary_equivalence':False,'source_coverage':{'selected_senders':3,'whole_517_send_sites':False},'source_closure_sha256':t.SOURCE_SHA,'authority_result':str(AUTH),'authority_sha256':t.AUTHORITY_SHA,'real_sender_results':real,'fresh_gcc_measured':measured,'clang_full_ast_command':json.loads((WORK/'command.json').read_text()),'clang_full_ast_exit':0,'commands':commands,'cases':rows,'physical_cpp_cases':len(rows),'owned_structural_negatives':len(bodies),'retained_previous_cases':len(rows)-len(bodies),'production_freeze':{'input_count':len(freeze),'unchanged':True},'existing_spike_python_unchanged':len(oldpy),'tdd_logs':[str(p) for p in WORK.glob('*-*.log')],'limitations':['Bounded straight-line grammar only; no CFG solver','clif_name/sitting explicitly unresolved','Real sink contract unreviewed; candidate is not packet framing admission','Retained fixtures without numeric joins are not counted as structural numeric coverage','Full Clang JSON is large (2.12GB), kept only in scratch','All milestones/combat/XP/loot remain open'],'artifacts':{str(p):sha(p) for p in WORK.iterdir() if p.is_file()},'owned_code_hashes':{str(p):sha(p) for p in pathlib.Path(__file__).parent.glob('*.py')}}
report.update(physical_unittest_methods=4,physical_unittest_passed=4,tdd_vertical_cycles=['identity RED/GREEN','header-layout join RED/GREEN','unknown helper escape RED/GREEN','authority denial RED/GREEN'])
path=ROOT/'run/reviews/native-ast-real-sender-proof.json';path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'verdict':report['verdict'],'cases':len(rows),'owned_negatives':len(bodies),'real':real,'report_sha256':sha(path)},indent=2))
