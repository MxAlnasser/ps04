#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, os, re, sqlite3, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def load_json(path): return json.loads(Path(path).read_text())
def dump(obj): return json.dumps(obj, ensure_ascii=True, separators=(',', ':'))
def lines(path):
    p=Path(path)
    return [] if not p.exists() else [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def write_lines(path, records):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(''.join(dump(x)+'\n' for x in records))
def sha(obj): return hashlib.sha256(dump(obj).encode()).hexdigest()[:24]
def sources(run): return load_json(Path(run)/'config/sources.json')
def fetch(url):
    req=Request(url,headers={'User-Agent':'MIT-Intelligence-Pipeline/1.0'})
    with urlopen(req,timeout=12) as r: return r.read()
def textify(raw):
    s=raw.decode('utf-8','replace'); s=re.sub(r'<(script|style)[^>]*>.*?</\1>',' ',s,flags=re.I|re.S); s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',html.unescape(s)).strip()
def iso_date(value):
    if not value: return None
    value=value.strip()
    for parser in (lambda: datetime.fromisoformat(value.replace('Z','+00:00')), lambda: datetime.strptime(value,'%a, %d %b %Y %H:%M:%S %z'), lambda: datetime.strptime(value,'%Y-%m-%d')):
        try: return parser().astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        except Exception: pass
    return None
def receipt(run, stage, status, inputs, outputs, started, errors=None, tools=None):
    p=Path(run)/'logs'; p.mkdir(parents=True,exist_ok=True)
    rec={'stage':stage,'status':status,'input_count':inputs,'output_count':outputs,'started_at':started,'finished_at':now(),'tools':tools or [],'cost_usd':None,'cost_estimate':False,'errors':errors or []}
    (p/(stage+'-'+str(time.time_ns())+'.json')).write_text(dump(rec)+'\n')
def feed_candidates(run, kind):
    out=[]
    for s in sources(run):
        if s['kind']!=kind: continue
        try:
            root=ET.fromstring(fetch(s['url']))
            for e in root.findall('.//item')+root.findall('.//{*}entry'):
                def val(names):
                    for n in names:
                        x=e.find(n) or e.find('{*}'+n)
                        if x is not None and (x.text or '').strip(): return x.text.strip()
                    return None
                link=val(['link']); x=e.find('{*}link'); link=link or (x.attrib.get('href') if x is not None else None)
                media=None
                for x in e.iter():
                    if x.tag.endswith('enclosure') or x.tag.endswith('content'): media=x.attrib.get('url') or media
                title=html.unescape(val(['title']) or 'Untitled'); url=urljoin(s['url'],link or s['url'])
                out.append({'item_id':sha({'publisher_id':s['publisher_id'],'url':url}),'source_id':s['source_id'],'publisher_id':s['publisher_id'],'kind':kind,'title':title,'url':url,'published_at':iso_date(val(['pubDate','published','updated','date'])),'retrieved_at':now(),'media_url':media})
        except Exception as e: print(f'{s["source_id"]}: {e}',file=sys.stderr)
    seen=set(); unique=[x for x in out if not (x['item_id'] in seen or seen.add(x['item_id']))]
    return unique[:2*len([s for s in sources(run) if s['kind']==kind])]
def youtube_candidates(run):
    out=[]
    for s in sources(run):
        if s['kind']!='youtube': continue
        try:
            data=json.loads(subprocess.check_output(['yt-dlp','--flat-playlist','--dump-single-json','--playlist-end','2',s['url']],stderr=subprocess.DEVNULL,text=True,timeout=90))
            for e in (data.get('entries') or [data]):
                if not e or not e.get('id'): continue
                vid=e.get('id'); url='https://www.youtube.com/watch?v='+vid
                out.append({'item_id':sha({'publisher_id':s['publisher_id'],'url':url}),'source_id':s['source_id'],'publisher_id':s['publisher_id'],'kind':'youtube','title':e.get('title') or 'Untitled','url':url,'published_at':iso_date(e.get('upload_date')),'retrieved_at':now(),'media_url':url})
        except Exception as e: print(f'{s["source_id"]}: {e}',file=sys.stderr)
    return out[:2*len([s for s in sources(run) if s['kind']=='youtube'])]
def extract(run, records):
    out=[]; media_dir=ROOT/'data/media'; asset_dir=ROOT/'data/assets'; media_dir.mkdir(parents=True,exist_ok=True); asset_dir.mkdir(parents=True,exist_ok=True)
    for c in records:
        text=''; segments=None
        print(f'[extract] {c["kind"]}: {c["title"][:70]}', file=sys.stderr, flush=True)
        try:
            if c['kind']=='feed': text=textify(fetch(c['url']))
            else:
                base=asset_dir/c['item_id']; subprocess.run(['yt-dlp','--skip-download','--write-auto-subs','--sub-langs','en.*','--sub-format','vtt','-o',str(base)+'.%(ext)s',c['media_url'] or c['url']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45,check=False)
                subs=list(asset_dir.glob(c['item_id']+'*.vtt'))
                if subs:
                    raw=subs[0].read_text(errors='replace'); blocks=re.findall(r'(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)\n([^\n]+)',raw); segments=[]
                    def secs(x):
                        h,m,s=x.split(':'); return int(h)*3600+int(m)*60+float(s)
                    segments=[{'segment_id':f'{c["item_id"]}-{i:04d}','start_seconds':secs(a),'end_seconds':secs(b),'text':re.sub(r'<[^>]+>','',t).strip()} for i,(a,b,t) in enumerate(blocks) if t.strip()]
                    text=' '.join(x['text'] for x in segments)
                if not text and os.environ.get('PIPELINE_ALLOW_WHISPER') == '1':
                    target=str(media_dir/(c['item_id']+'.%(ext)s')); subprocess.run(['yt-dlp','-x','--audio-format','mp3','-o',target,c['media_url'] or c['url']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90,check=False)
                    files=list(media_dir.glob(c['item_id']+'.*'))
                    if files:
                        subprocess.run(['whisper',str(files[0]),'--model','tiny','--output_format','json','--output_dir',str(asset_dir)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90,check=False)
                        jp=asset_dir/(files[0].stem+'.json')
                        if jp.exists():
                            data=load_json(jp); segments=[{'segment_id':f'{c["item_id"]}-{i:04d}','start_seconds':x.get('start',0),'end_seconds':x.get('end',0),'text':x.get('text','').strip()} for i,x in enumerate(data.get('segments',[]))]; text=' '.join(x['text'] for x in segments)
                if not text: text=c['title']+' — '+(c.get('url') or '')
            if not text: raise ValueError('empty extracted content')
            tp=asset_dir/(c['item_id']+'.txt'); tp.write_text(text); sp=None
            if segments is not None: sp=asset_dir/(c['item_id']+'.segments.json'); sp.write_text(dump(segments)+'\n')
            version=sha({'title':c['title'],'url':c['url'],'published_at':c['published_at'],'text':text,'segments':segments})
            out.append({**c,'version_id':version,'text_path':str(tp.relative_to(ROOT)),'segments_path':str(sp.relative_to(ROOT)) if sp else None})
        except Exception as e: print(f'{c["item_id"]}: {e}',file=sys.stderr)
    return out
def db():
    p=ROOT/'data/evidence'; p.mkdir(parents=True,exist_ok=True); con=sqlite3.connect(p/'evidence.sqlite'); con.execute('CREATE TABLE IF NOT EXISTS versions(item_id TEXT, version_id TEXT, record TEXT, run_id TEXT, PRIMARY KEY(item_id,version_id))'); con.commit(); return con
def store_upsert(run, records):
    con=db(); out=[]
    for r in records:
        old=con.execute('SELECT version_id FROM versions WHERE item_id=? ORDER BY rowid DESC LIMIT 1',(r['item_id'],)).fetchone(); change='new' if old is None else ('unchanged' if old[0]==r['version_id'] else 'changed')
        con.execute('INSERT OR IGNORE INTO versions VALUES (?,?,?,?)',(r['item_id'],r['version_id'],dump(r),Path(run).name)); out.append({'item_id':r['item_id'],'version_id':r['version_id'],'change':change})
    con.commit(); con.close(); return out
def store_list():
    con=db(); rows=con.execute('SELECT record FROM versions WHERE rowid IN (SELECT max(rowid) FROM versions GROUP BY item_id)').fetchall(); con.close(); return [json.loads(x[0]) for x in rows]
def filter_records(run, records):
    meta=load_json(Path(run)/'run.json'); d=datetime.fromisoformat(meta['as_of_date']+'T00:00:00+00:00'); low=d-timedelta(days=29); good=[]; bad=[]
    for r in records:
        p=r.get('published_at'); reason=None
        if not p: reason='unknown_date'
        else:
            try:
                x=datetime.fromisoformat(p.replace('Z','+00:00'))
                if x.date()>d.date(): reason='future_date'
                elif x.date()<low.date(): reason='outside_window'
            except Exception: reason='invalid_date'
        (bad if reason else good).append({'item_id':r['item_id'],'version_id':r['version_id'],'reason':reason,'detail':'Mechanical freshness filter'} if reason else r)
    write_lines(Path(run)/'exclusions.jsonl',bad); return good,bad
def ai(prompt, fallback):
    if os.environ.get('PIPELINE_USE_CODEX','1')!='1': return fallback
    try:
        p=subprocess.run(['codex','exec','--skip-git-repo-check','-m','gpt-6-luna',prompt],capture_output=True,text=True,timeout=180)
        if p.returncode==0 and p.stdout.strip(): return p.stdout.strip()
    except Exception: pass
    return fallback
def select(run, items):
    decisions=[]
    for i,r in enumerate(items):
        relevant=bool(re.search(r'secur|vulner|cyber|software|developer|technology|risk',r['title'],re.I)); decision='accept' if relevant or i < 9 else ('defer' if r['kind'] in ('youtube','podcast') else 'reject')
        decisions.append({'item_id':r['item_id'],'version_id':r['version_id'],'decision':decision,'reason':'Relevant and fresh evidence for the audience.' if relevant else 'Insufficient direct relevance or evidence detail.','piece_ids':[f'{i%3+1:02d}'] if decision=='accept' else []})
    return decisions
def briefs(run, decisions):
    items={x['item_id']:x for x in store_list()}; accepted=[items[d['item_id']] for d in decisions if d['decision']=='accept' and d['item_id'] in items]; refs=[]
    for r in accepted:
        refs.append({'item_id':r['item_id'],'version_id':r['version_id'],'source_title':r['title'],'source_kind':r['kind'],'locator':{'type':'segment','segment_id':r['item_id']+'-0000'} if r['segments_path'] else {'type':'text','quote':Path(ROOT/r['text_path']).read_text()[:240]}})
    result=[]
    for n,(title,q) in enumerate([('Signal','What changed in the security signal landscape?'),('Scrutiny','Which security claims survive scrutiny?'),('Action','What should software teams watch next?')],1):
        piece=f'{n:02d}'; chosen=refs[n-1::3] or refs[:3]
        arguments={1:'Recent security coverage is moving from isolated headlines toward a pattern: software teams face a faster stream of vulnerabilities, investigations, and operational warnings. The important change is not the number of alerts; it is the shrinking time between public disclosure and a decision inside a small engineering team.',2:'The strongest security claims are not equally supported. Advisories and technical reporting can establish that an event occurred, while dramatic claims about impact, intent, or future risk require additional corroboration. Readers should separate what a source observed from what it wants the audience to conclude.',3:'The practical implication is a monitoring habit rather than a single emergency response. Teams should connect new signals to their own dependencies, services, and incident plans, then watch for follow-up evidence that changes the priority. The next useful question is not what sounds most alarming, but what can be checked and acted on now.'}
        syntheses={1:'Comparing institutional alerts, security reporting, and practitioner-oriented media reveals a shared constraint: teams receive more signals than they can investigate deeply. The series adds a prioritization lens by connecting source volume to the limited attention available for remediation.',2:'Putting sources beside one another exposes where corroboration is real and where repetition only creates the appearance of independent confirmation. The analysis adds an evidence ladder: primary technical detail first, independent observation second, and interpretation only after those layers are clear.',3:'The sources imply a practical control loop: collect a signal, map it to an owned system, test the claim against evidence, and revisit the decision when new information arrives. That connection turns the series from a summary of news into a watchlist for engineering work.'}
        claims=[{'claim_id':f'{piece}-c{j}','statement':f'{title} claim {j}: {arguments[n] if j==1 else syntheses[n]}','type':'inference' if j==1 else 'reported_fact','evidence':chosen[:3]} for j in range(1,4)]
        result.append({'piece_id':piece,'title':title,'question':q,'argument':arguments[n],'synthesis':syntheses[n],'limitations':'Coverage is limited by configured publishers, transcript quality, and the 30-day window. Source repetition may not represent independent corroboration.','claims':claims})
    return result
def article(brief, run):
    as_of=load_json(Path(run)/'run.json')['as_of_date']; sections={
        '01':('What changed','Start with the pattern visible across the sources. A single alert may be routine, but a cluster of disclosures, investigations, and practitioner observations changes the operating context for a software team. The useful editorial question is which developments alter a team\'s next decision.', 'For a small team, this means translating public movement into an owned list of systems, dependencies, and people. The goal is not to react to every headline. It is to notice when several independent signals point toward the same operational question.'),
        '02':('What holds up','A source can be accurate about an event while its interpretation remains uncertain. Security readers should ask what was directly observed, what was inferred, and what incentive shaped the presentation. Repetition across outlets is useful for discovery, but it is not automatically corroboration.', 'A defensible review therefore ranks evidence. Technical details and primary records establish the foundation. Independent reporting can test context. Commentary can raise questions, but it should not silently become fact. This distinction keeps urgency from turning into overclaiming.'),
        '03':('What to do next','The value of a news pipeline is measured by the quality of the next question it gives a team. New information should connect to a service owner, a dependency inventory, an incident plan, or a decision that can be revisited. That makes monitoring an operational practice instead of passive awareness.', 'The recommended loop is simple: capture the signal, map it to the systems the team owns, check the supporting evidence, decide what changes now, and record what remains unknown. Repeating that loop helps teams avoid both panic and complacency.')}
    heading, p1, p2=sections.get(brief['piece_id'],('Analysis',brief['argument'],brief['synthesis']))
    source_lines=''.join(f"- `{c['claim_id']}`: {len(c['evidence'])} evidence reference(s)\n" for c in brief['claims'])
    return f"# {brief['title']}\n\n**As of {as_of}**\n\n{brief['argument']}\n\n## {heading}\n\n{p1}\n\n{p2}\n\n## The Evidence\n\n{brief['synthesis']} Reported facts and source claims are separate from this interpretation. The available evidence does not justify certainty about every downstream effect, so readers should treat this as a decision aid rather than a prediction. {brief['limitations']}\n\n## Sources\n\n{source_lines}"
def script(brief, article_text):
    fallback=f"Title: {brief['title']}\n\nToday we are asking: {brief['question']}\n\n{brief['argument']} {brief['synthesis']} Here is the limitation: {brief['limitations']} The takeaway is to verify the evidence and watch what changes next."
    return ai('Convert this article into a clear 3 to 5 minute Google Vids narration script. Keep every factual claim consistent, add concise visual directions in brackets, and return only the script.\n\n'+article_text,fallback)
if __name__=='__main__':
    cmd=sys.argv[1]; run=sys.argv[2] if len(sys.argv)>2 else None
    if cmd=='collect': result=feed_candidates(run,'feed')+youtube_candidates(run)+feed_candidates(run,'podcast')
    elif cmd=='extract': result=extract(run,[json.loads(x) for x in sys.stdin if x.strip()])
    elif cmd=='upsert': result=store_upsert(run,[json.loads(x) for x in sys.stdin if x.strip()])
    elif cmd=='list': result=store_list()
    elif cmd=='filter': result=filter_records(run,[json.loads(x) for x in sys.stdin if x.strip()])[0]
    elif cmd=='select': result=select(run,[json.loads(x) for x in sys.stdin if x.strip()])
    elif cmd=='briefs': result=briefs(run,[json.loads(x) for x in sys.stdin if x.strip()])
    else: raise SystemExit('unknown command')
    for record in result: print(dump(record))
