#!/usr/bin/env python3
import hashlib, json, os, re, shutil, sys
from pathlib import Path
from pipeline import ROOT, load_json, dump, lines, write_lines, now, article, script

def write_content(run):
    briefs=lines(Path(run)/'briefs.jsonl'); ad=Path(run)/'articles'; vd=Path(run)/'video_scripts'; ad.mkdir(exist_ok=True); vd.mkdir(exist_ok=True); am=[]; vm=[]
    for b in briefs:
        p=ad/(b['piece_id']+'.md'); p.write_text(article(b,run)); claims=[x['claim_id'] for x in b['claims']]; am.append({'piece_id':b['piece_id'],'path':str(p.relative_to(ROOT)),'claim_ids':claims})
        sp=vd/(b['piece_id']+'.md'); sp.write_text(script(b,p.read_text())); vm.append({'piece_id':b['piece_id'],'path':str(sp.relative_to(ROOT)),'claim_ids':claims})
    write_lines(Path(run)/'articles.jsonl',am); write_lines(Path(run)/'video_scripts.jsonl',vm)
def review(run):
    briefs=lines(Path(run)/'briefs.jsonl'); am=lines(Path(run)/'articles.jsonl'); vm=lines(Path(run)/'video_scripts.jsonl'); issues=[]
    if len(briefs)!=3: issues.append({'artifact':'briefs.jsonl','severity':'error','message':'Expected exactly three briefs.'})
    for p in ('01','02','03'):
        if not (Path(run)/'articles'/f'{p}.md').exists(): issues.append({'artifact':f'articles/{p}.md','severity':'error','message':'Missing article.'})
        if not (Path(run)/'video_scripts'/f'{p}.md').exists(): issues.append({'artifact':f'video_scripts/{p}.md','severity':'error','message':'Missing video script.'})
    for b in briefs:
        if len(b.get('claims',[]))<3: issues.append({'artifact':f'brief {b.get("piece_id")}','severity':'error','message':'Fewer than three claims.'})
    payload=b''.join(p.read_bytes() for p in (Path(run)/'briefs.jsonl',Path(run)/'articles.jsonl',Path(run)/'video_scripts.jsonl') if p.exists())
    rid=hashlib.sha256(payload).hexdigest()
    return {'review_id':rid,'passed':not any(x['severity']=='error' for x in issues),'issues':issues}
def summary(run):
    def count(name): return len(lines(Path(run)/name)) if Path(run,name).exists() else None
    changes=lines(Path(run)/'changes.jsonl'); dec=lines(Path(run)/'decisions.jsonl'); logs=list((Path(run)/'logs').glob('*.json'))
    bad=[x for x in logs if json.loads(x.read_text()).get('status') in ('failed','incomplete')]
    review=None
    if Path(run,'review.json').exists():
        try: review=load_json(Path(run)/'review.json')
        except json.JSONDecodeError: review=None
    status='ready_for_production' if Path(run,'approval.json').exists() and review and review.get('passed') else ('awaiting_review' if review else 'failed')
    return {'run_id':Path(run).name,'status':status,'counts':{'discovered':count('candidates.jsonl'),'extracted':count('items.jsonl'),'new':sum(x['change']=='new' for x in changes),'changed':sum(x['change']=='changed' for x in changes),'unchanged':sum(x['change']=='unchanged' for x in changes),'eligible':count('eligible.jsonl'),'excluded':count('exclusions.jsonl'),'accepted':sum(x['decision']=='accept' for x in dec),'rejected':sum(x['decision']=='reject' for x in dec),'deferred':sum(x['decision']=='defer' for x in dec),'articles':count('articles.jsonl'),'video_scripts':count('video_scripts.jsonl')},'failed_stages':len(bad),'manual_actions':['human review','Google Vids or HeyGen production','Substack publication','YouTube publication'],'tools':['python3','yt-dlp','ffmpeg','whisper','codex'],'cost_usd':None,'notes':'Counts are based on saved JSONL artifacts; incomplete collection is retained in stage receipts.'}
def handoff(run):
    run=Path(run); s=summary(run); c=s['counts']; media=list((ROOT/'data/media').glob('*')); out=ROOT/'output'
    if out.exists():
        for child in out.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    (out/'articles').mkdir(parents=True); (out/'google-vids').mkdir(); (out/'sources').mkdir(); (out/'media').mkdir()
    mode=os.environ.get('OUTPUT_MODE','full')
    for p in ('01','02','03'):
        shutil.copyfile(run/'articles'/(p+'.md'), out/'articles'/(f'article-{p}.md'))
        if mode in ('full','prompts','voiceovers'):
            shutil.copyfile(run/'video_scripts'/(p+'.md'), out/'google-vids'/(f'video-prompt-{p}.md'))
    for label, filename in [('rss','feeds.jsonl'),('youtube','youtube.jsonl'),('podcasts','podcasts.jsonl')]:
        records=lines(run/'candidates'/filename); (out/'sources'/(label+'.md')).write_text('\n'.join([f'# {label.title()} sources', '']+[f'- {x.get("title", "Untitled")}\n  {x.get("url", "no URL")}' for x in records])+'\n')
    item_titles={x['item_id']:x for x in lines(run/'items.jsonl')}
    media_ids=set(item_titles)
    used=set()
    for item in media:
        if item.is_file():
            record=next((x for key,x in item_titles.items() if item.name.startswith(key+'.')), None)
            if not record or item.stem not in media_ids: continue
            title=record.get('title','source-media') if record else item.stem
            label=re.sub(r'[^A-Za-z0-9]+','-',title).strip('-').lower()[:70] if title else 'source-media'
            label=label or 'source-media'; candidate=f'{label}{item.suffix.lower()}'; number=2
            while candidate in used:
                candidate=f'{label}-{number}{item.suffix.lower()}'; number+=1
            used.add(candidate); shutil.copy2(item, out/'media'/candidate)
    lines_out=[f'# Signal to Ship: Run {run.name}', '', f"Status: **{s['status']}**", '', '## Open these files', '', 'These are the only files you need for the normal review.', '', '### Articles', '']
    for p in ('01','02','03'):
        lines_out.append(f'- `output/articles/article-{p}.md`')
    if mode in ('full','prompts','voiceovers'):
        lines_out += ['', '### Google Vids prompts', '', 'Copy each matching prompt into Google Vids or HeyGen.', '']
        for p in ('01','02','03'):
            lines_out.append(f'- `output/google-vids/video-prompt-{p}.md`')
    if mode in ('full','voiceovers'):
        lines_out += ['', '### Short voiceover text', '', 'These one-paragraph files are the text sent to your voice model.', '']
        for p in ('01','02','03'):
            lines_out.append(f'- `output/google-vids/voiceover-text-{p}.txt`')
        lines_out += ['', '### Generated voice audio', '', '- Open `output/voiceovers/` for the WAV narration files.']
    lines_out += ['', '### Source lists', '', '- `output/sources/rss.md`', '- `output/sources/youtube.md`', '- `output/sources/podcasts.md`', '', '### Downloaded media', '', '- Open `output/media/` for downloaded podcast and video audio.', '', '## Quick Run Summary', '']
    lines_out += [f"- Discovered: {c['discovered']}", f"- Fresh and eligible: {c['eligible']}", f"- Accepted for the series: {c['accepted']}", f"- Excluded by date or validity checks: {c['excluded']}", f"- Articles: {c['articles']}", f"- Video prompts: {c['video_scripts']}", '', '## What To Do Next', '', '1. Read and fact-check the three article files.', '2. Paste each matching video prompt into Google Vids or HeyGen.', '3. Add the article and source links to each video description.', '4. Publish the articles on Substack and the videos on YouTube.']
    report=out/'README.md'; report.write_text('\n'.join(lines_out)+'\n'); (ROOT/'latest-run.txt').write_text(str(run.relative_to(ROOT))+'\n'); return report
def package(run):
    review=load_json(Path(run)/'review.json'); approval=load_json(Path(run)/'approval.json');
    if not review.get('passed') or approval.get('decision')!='approve' or approval.get('review_id')!=review.get('review_id'): raise SystemExit('package requires passing review and matching approval')
    out=Path(run)/'package'; out.mkdir(exist_ok=True); manifest=[]
    for p in ('01','02','03'):
        for kind,folder in [('article','articles'),('video_script','video_scripts')]:
            src=Path(run)/folder/(p+'.md'); dst=out/(folder+'-'+p+'.md'); shutil.copyfile(src,dst); manifest.append({'piece_id':p,'kind':kind,'path':str(dst.relative_to(ROOT))})
    (out/'manual_handoffs.md').write_text('# Manual handoffs\n\nPaste each video script into Google Vids or HeyGen, review the rendered video, publish articles in Substack, then publish videos in YouTube with article and source links in each description.\n')
    links=Path(out)/'publication_links.json'
    if not links.exists(): write_lines(links,[{'piece_id':p,'substack_url':None,'youtube_url':None} for p in ('01','02','03')])
    (out/'manifest.json').write_text(dump({'assets':manifest})+'\n'); return {'assets':manifest}
if __name__=='__main__':
    cmd,run=sys.argv[1:3]
    if cmd=='content': write_content(run)
    elif cmd=='review': print(dump(review(run)))
    elif cmd=='summary': print(dump(summary(run)))
    elif cmd=='handoff': print(handoff(run))
    elif cmd=='package': print(dump(package(run)))
