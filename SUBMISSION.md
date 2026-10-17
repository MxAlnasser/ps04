# Problem Set 4 Student Submission

Complete this document with your project details and links. Keep the course instructions in [README.md](README.md) and the required contracts in [ARCHITECTURE.md](ARCHITECTURE.md).

**Student:** To complete  
**GitHub repository:** Add repository link after publication

## Topic and Audience

- **Publication name:** Signal to Ship
- **Topic:** Recent software and cybersecurity developments
- **Audience and assumed knowledge:** Engineering leads and technically literate product managers at small software teams; readers understand basic software delivery but need help evaluating security signals.
- **Central question:** Which recent security signals deserve engineering attention, and what should teams do next?
- **Scope and exclusions:** Recent, evidence-backed changes affecting software delivery, dependencies, cloud systems, privacy, or incident response. Exclude undated, stale, duplicated, inaccessible, purely promotional, or technically empty material.
- **Reason for readers to return:** Each edition connects fresh advisories, technical reporting, video, and practitioner audio into a decision-oriented view of what changed, what holds up, and what to watch.

## Published Series

Replace each placeholder with the title or working link. Verify that course staff can open every publication.

| Piece | Title | Substack article | YouTube video |
| --- | --- | --- | --- |
| 1 | To complete | Add link | Add link |
| 2 | To complete | Add link | Add link |
| 3 | To complete | Add link | Add link |

**Separate technical demonstration video:** To record after the second live run

## Setup and Execution

The implementation uses Bash, Python 3.12 standard-library modules, `jq`, `yt-dlp`, `ffmpeg`, `whisper`, `codex`, and `gum`. No additional Python package is required. `PIPELINE_ALLOW_WHISPER=1` enables local transcription when automatic captions are unavailable; it is opt-in because transcription can be slow. `PIPELINE_USE_CODEX=1` is the default and converts reviewed articles into Google Vids-ready scripts through Codex. Set it to `0` for an offline deterministic fixture run. Reviewable outputs are refreshed in `output/`; machine-readable artifacts remain in `runs/RUN_ID/` and retained evidence remains in `data/`.

Populate `config/project.json`, `config/sources.json`, `config/editorial_policy.md`, and the four files in `prompts/`. Run `bash run.sh`; collector, extraction, workflow, and external-test timeouts prevent indefinite hangs.

After implementation, the required entry commands are:

```bash
bash run.sh
bash run.sh --package runs/RUN_ID
```

Replace `RUN_ID` with an actual run directory. For a bounded local check, use `PIPELINE_USE_CODEX=0 timeout 240 bash run.sh`. For a full media transcription attempt, use `PIPELINE_ALLOW_WHISPER=1 bash run.sh`. Disposable checks are kept under `tmp/`; interrupted runs remain under `runs/` with their partial artifacts.

## Architecture and Manual Handoffs

Add a diagram of your implemented pipeline and explain any additional components or helpers. Show where models are called and where evidence is stored.

Describe the human editorial review, Google Vids or HeyGen production, and Substack and YouTube publishing steps. Identify the files passed into each manual step and the resulting artifacts.

## Evidence and Runs

Link to the retained evidence, editorial decisions, briefs, content checks, and intermediate artifacts needed to inspect the complete workflow. Keep referenced text and transcript files accessible. Explain how to retrieve media omitted from the repository.

| Run | Actual date | Run artifacts and logs | Elapsed time | Approximate cost |
| --- | --- | --- | --- | --- |
| First live run | 2026-10-16 | `runs/20261016T160156Z-28902/` (interrupted extraction; failure evidence) | recorded in receipts | unknown |
| Second live run | 2026-10-16 | `runs/20261016T161145Z-22393/` | see `summary.json` | unknown |

Explain what changed between runs. Identify unknown or estimated costs. Provide the records demonstrating duplicate handling, the date-window checks, and collection failure or recovery. Label any fixture replay or simulated failure.

Trace one published claim to its brief, editorial decision, source version, and exact supporting passage or timestamp.

## Editorial Review

Link to the editorial policy and prompts used. Provide your review of at least three accepted and three rejected or deferred items, comparing the AI's reasons with your own judgment.

Show the policy before and after your revision, the affected stage outputs, and what changed. Record factual corrections, remaining limitations, and the evidence for your final publication approval.

## Reflection

The initial run showed that source reachability and transcript generation are operational risks, not invisible implementation details. The main limitation is that blocked feeds and missing captions reduce evidence quality; the next improvement is a second transcript-provider fallback and a pre-draft check for six independent publishers. The architecture keeps evidence storage behind `data/store.sh`, trading convenience for replayable versions and duplicate detection. Publication links and the technical demonstration remain manual completion steps.
