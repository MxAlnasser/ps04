# Signal to Ship Pipeline

A repeatable intelligence pipeline for turning recent cybersecurity and software news into articles, Google Vids scripts, and narrated voiceovers.

This project is configured for engineering leads and technically literate product managers who need to understand which security developments deserve attention and what to do next.

## What It Does

The pipeline can:

- Collect recent written sources from RSS feeds.
- Collect recent YouTube videos with `yt-dlp`.
- Collect recent podcast episodes and audio locations.
- Retrieve written source content.
- Download media when needed.
- Use automatic captions when available.
- Optionally use local Whisper transcription when captions are unavailable.
- Preserve timestamped transcript segments for video and audio evidence.
- Apply the required 30-day publication window.
- Record exclusions such as stale, future, undated, or invalid material.
- Detect new, changed, unchanged, and duplicate evidence.
- Keep evidence versions in a SQLite-backed store.
- Apply the editorial policy to source selection.
- Record accepted, rejected, and deferred items.
- Create three distinct editorial briefs.
- Generate three connected article drafts.
- Generate three matching Google Vids or HeyGen scripts.
- Summarize scripts into short one-paragraph narration text.
- Generate voiceovers using the provided `voice.wav` reference.
- Produce readable source lists for RSS, YouTube, and podcasts.
- Preserve machine-readable artifacts for inspection and replay.
- Create a publication handoff package after human approval.

## Requirements

The project uses the tools already installed in this workspace:

- Bash
- Python 3
- `jq`
- `yt-dlp`
- `ffmpeg`
- Whisper
- Codex
- `gum`
- Chatterbox TTS dependencies used by `tts.py`

No additional Python package is required beyond the installed TTS environment.

The voice workflow also requires:

- `lib/tts.py`
- `assets/voice.wav`

`assets/voice.wav` is the reference voice used by Chatterbox.

## Basic Use

Run the pipeline from the repository root:

```bash
./run.sh
```

The command opens an interactive menu:

1. **Full package**: articles, Google Vids prompts, and voiceovers.
2. **Articles + Google Vids prompts**: skips voice generation.
3. **Articles only**: creates the written series without video deliverables.

The terminal prints progress as each stage runs. Every run has built-in timeouts so a blocked feed, media download, transcription, or model call cannot wait forever.

## Command Options

```bash
./run.sh --help
```

Shows the available commands.

```bash
./run.sh --full
```

Enables Whisper when a video or podcast has no usable automatic captions. This can take substantially longer than the normal run.

```bash
./run.sh --offline
```

Runs without Codex. This is useful for a fast local test or when the model service is unavailable.

```bash
./run.sh --voiceovers
```

Uses the existing Google Vids prompts in `output/google-vids/`, asks Codex to create one concise paragraph per prompt, and sends those short paragraphs to the voice model.

```bash
./run.sh --package runs/RUN_ID
```

Creates a publication package from a run that has passed review and has a matching human approval record. Packaging does not recollect sources or regenerate approved drafts.

## Interactive Output Choices

### Full Package

Creates:

- Three article files.
- Three full Google Vids prompts.
- Three short one-paragraph voiceover text files.
- Three WAV voiceovers using `voice.wav`.
- RSS, YouTube, and podcast source lists.
- Downloaded media associated with the current run.

### Articles and Prompts

Creates the three articles and the full Google Vids prompts, but skips voice synthesis.

### Articles Only

Creates only the article deliverables and source lists. This is useful when the written analysis needs review before creating videos.

## Human-Facing Output

All files intended for normal review are placed in one folder:

```text
output/
├── README.md
├── articles/
│   ├── article-01.md
│   ├── article-02.md
│   └── article-03.md
├── google-vids/
│   ├── video-prompt-01.md
│   ├── video-prompt-02.md
│   ├── video-prompt-03.md
│   ├── voiceover-text-01.txt
│   ├── voiceover-text-02.txt
│   └── voiceover-text-03.txt
├── voiceovers/
│   ├── video-prompt-01.wav
│   ├── video-prompt-02.wav
│   └── video-prompt-03.wav
├── sources/
│   ├── rss.md
│   ├── youtube.md
│   └── podcasts.md
└── media/
```

The generated `output/README.md` is a run-specific checklist. Start there when reviewing the latest output.

### Articles

Read the files in `output/articles/`. The three pieces have different editorial purposes:

1. **Signal**: what changed and why it matters.
2. **Scrutiny**: which claims are supported and where evidence is uncertain.
3. **Action**: what software teams should do and watch next.

### Google Vids Prompts

Copy the matching `video-prompt-01.md`, `video-prompt-02.md`, or `video-prompt-03.md` file into Google Vids or HeyGen. These are the fuller scripts with visual directions and production guidance.

### Voiceover Text

The `voiceover-text-*.txt` files are shorter than the full Google Vids prompts. Codex removes headings, visual directions, citations, and production notes, leaving one natural spoken paragraph for TTS.

### Voiceovers

The `output/voiceovers/` directory contains WAV files generated with the provided voice reference. These can be used as narration assets in the video-production workflow.

### Source Lists

The files in `output/sources/` list the titles and URLs collected in the latest run, separated by source type.

### Downloaded Media

The files in `output/media/` are named from their source titles where possible. Internal evidence IDs are not exposed in the human-facing folder.

## Internal Artifacts

The human-facing output is intentionally separate from the machine-readable pipeline data.

```text
runs/RUN_ID/
├── run.json
├── config/
├── prompts/
├── logs/
├── candidates/
├── candidates.jsonl
├── items.jsonl
├── changes.jsonl
├── corpus.jsonl
├── eligible.jsonl
├── exclusions.jsonl
├── decisions.jsonl
├── briefs.jsonl
├── articles.jsonl
├── articles/
├── video_scripts.jsonl
├── video_scripts/
├── review.json
├── approval.json
├── summary.json
└── package/
```

These files support grading, replay, debugging, source traceability, duplicate handling, and the required repeatability demonstration. They are not intended to be the normal review interface.

The `data/` directory contains retained evidence, downloaded source media, transcripts, and the persistent evidence index.

## Editorial Pipeline

The stages are intentionally separated:

1. `collectors/` discover RSS, YouTube, and podcast material.
2. `processing/` extracts content and applies freshness filtering.
3. `data/store.sh` owns persistent evidence and version history.
4. `editorial/` selects items and develops three briefs.
5. `content/` writes articles and video scripts.
6. `review/` checks references, files, coverage, and consistency.
7. `publishing/` prepares the human publication handoff.
8. `reporting/` summarizes counts, failures, tools, and remaining manual work.

The required Bash entry points remain independently runnable and preserve the architecture specified by the assignment.

## TTS Workflow

The reusable `lib/tts.py` module supports both direct use and pipeline use.

Direct use:

```bash
python3 lib/tts.py --text some-text.txt --voice assets/voice.wav --output some-output.wav
```

Pipeline use:

```bash
./run.sh --voiceovers
```

The pipeline loads the TTS model once, summarizes each full Google Vids prompt first, and then generates one WAV per short narration. Voice generation is time-bounded because local model inference can be slow.

## Timeouts and Progress

Progress messages appear in the terminal, for example:

```text
[collect] fetching RSS feeds
[extract] podcast: episode title
[series] writing article drafts
[voice] output/google-vids/voiceover-text-01.txt -> output/voiceovers/video-prompt-01.wav
```

The pipeline uses bounded operations for:

- RSS requests.
- YouTube collection.
- Podcast collection.
- Content extraction.
- The collection workflow.
- The editorial workflow.
- Voiceover generation.
- Manual test commands.

A failed source does not silently become successful empty coverage. Partial results are retained and reported.

## Configuration

Edit these files to change the publication:

- `config/project.json`: publication name, topic, audience, and central question.
- `config/sources.json`: RSS, YouTube, and podcast sources.
- `config/editorial_policy.md`: selection and credibility rules.
- `prompts/select_items.md`: selection instructions.
- `prompts/create_briefs.md`: brief-generation instructions.
- `prompts/write_articles.md`: article-generation instructions.
- `prompts/write_video_scripts.md`: video-script instructions.

The exact configuration and prompts used for every run are copied into that run's internal directory.

## Publication Workflow

After reviewing the output:

1. Fact-check `output/articles/`.
2. Paste each `output/google-vids/video-prompt-*.md` file into Google Vids or HeyGen.
3. Use the matching WAV from `output/voiceovers/` when appropriate.
4. Publish each article on Substack.
5. Publish each video on YouTube.
6. Add the article and source links to each video description.
7. Record the final links in `SUBMISSION.md`.
8. Record human approval in the appropriate run's `approval.json`.
9. Package the approved run with `./run.sh --package runs/RUN_ID`.

## Git Hygiene

Generated artifacts are excluded by `.gitignore`, including:

- `runs/`
- `output/`
- `data/evidence/`
- `data/media/`
- `data/assets/`
- `tmp/`
- Python caches.
- Generated root-level media files.
- Local environment files.

The source code, configuration, prompts, assignment documents, TTS implementation, and voice reference remain separate from generated run output.

## Troubleshooting

### The run appears stuck

Watch the stage messages. A stage is bounded by timeouts and will eventually report an error or continue with partial coverage. Use `./run.sh --offline` to check the local pipeline without Codex.

### Voice generation is too slow

Use `./run.sh` and choose the articles-plus-prompts option, then run `./run.sh --voiceovers` only when ready. The voice stage loads a local model and may take several minutes.

### A source is inaccessible

The run records the failure and continues with usable sources. Check `output/sources/` and the internal run receipts for incomplete coverage.

### Google Vids prompts are too long for TTS

Use the short `voiceover-text-*.txt` files or run `./run.sh --voiceovers`. The full prompts are intended for Google Vids; the short files are intended for narration.

### I need to inspect the complete pipeline

Open the latest run directory under `runs/`. The human-facing files are in `output/`, while the run directory contains the complete machine-readable evidence trail.
