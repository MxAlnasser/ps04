#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
source=ROOT/'assets/voice.wav'
prompt_dir=ROOT/'output/google-vids'
target=ROOT/'output/voiceovers'
short_dir=ROOT/'output/google-vids'
target.mkdir(parents=True, exist_ok=True)
if not source.exists():
    raise SystemExit('assets/voice.wav is missing')
prompts=sorted(prompt_dir.glob('video-prompt-*.md'))
if not prompts:
    raise SystemExit('No Google Vids prompts found in output/google-vids')
from lib.tts import generate
short_prompts=[]
for prompt in prompts:
    short_text=short_dir/(prompt.stem.replace('video-prompt-', 'voiceover-text-')+'.txt')
    if os.environ.get('PIPELINE_USE_CODEX','1') == '1':
        instruction=('Summarize the following Google Vids script into exactly one natural spoken paragraph '
                     'for voice narration. Keep the central argument, key evidence, uncertainty, and takeaway. '
                     'Remove headings, visual directions, citations, and production notes. Return only the paragraph.\n\n'
                     + prompt.read_text(encoding='utf-8'))
        result=subprocess.run(['codex','exec','--skip-git-repo-check','-m','gpt-6-luna',instruction],capture_output=True,text=True,timeout=180)
        text=result.stdout.strip() if result.returncode == 0 else ''
    else:
        text=' '.join(line.strip() for line in prompt.read_text(encoding='utf-8').splitlines() if line.strip() and not line.startswith('#') and not line.startswith('['))
    if not text:
        raise SystemExit(f'Could not create a short narration for {prompt.name}')
    short_text.write_text(text+'\n', encoding='utf-8')
    short_prompts.append((prompt, short_text))

from chatterbox.tts import ChatterboxTTS
model=ChatterboxTTS.from_pretrained(device='cpu')
for prompt, short_text in short_prompts:
    output=target/(prompt.stem+'.wav')
    print(f'[voice] {short_text.relative_to(ROOT)} -> {output.relative_to(ROOT)}', file=sys.stderr, flush=True)
    generate(str(short_text), str(source), str(output), model=model)