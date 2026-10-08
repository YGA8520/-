#!/usr/bin/env python3
"""Second-opinion transcription of study recordings with an ivrit.ai Whisper model (faster-whisper).

Resumable: a recording counts as done only when its .json exists, so after a Colab disconnect just run it again.
Writes, per recording, <stem>.txt (one "[HH:MM:SS.mmm] text" line per segment) and <stem>.json (segments with confidence),
plus run_log.txt (one TSV line per recording) and errors.log in the output folder.
"""
import argparse, json, os, re, sys, time

AUDIO_EXT = {'.mp3', '.m4a', '.wav', '.aac', '.ogg', '.opus', '.flac', '.wma', '.mp4', '.amr', '.3gp', '.webm'}
DEFAULT_MODEL = 'ivrit-ai/whisper-large-v3-turbo-ct2'
VOCAB_PROMPT = 'שיעור בגמרא, מסכת שבת. מלאכת בונה, סותר, מכה בפטיש, אין בנין וסתירה בכלים. רש"י, תוספות, רמב"ם, רבא ואביי.'


def natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def stamp(sec):
    ms = int(round(sec * 1000))
    return '%02d:%02d:%02d.%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def find_audio(root):
    found = []
    for d, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in AUDIO_EXT:
                found.append(os.path.join(d, f))
    return sorted(found, key=lambda p: natural_key(os.path.relpath(p, root)))


def max_repeat(texts):
    """Longest run of identical consecutive segments - the usual signature of a Whisper hallucination loop."""
    best = run = 1 if texts else 0
    for a, b in zip(texts, texts[1:]):
        run = run + 1 if a.strip() == b.strip() else 1
        best = max(best, run)
    return best


def is_done(out_json, clip_seconds):
    """Done = the .json exists and was made with the same clip setting (so a short test never masquerades as a full run)."""
    if not os.path.exists(out_json):
        return False
    try:
        with open(out_json, encoding='utf-8') as f:
            return json.load(f).get('clip_seconds', 0) == clip_seconds
    except Exception:
        return False


def pick_device(requested):
    try:
        import ctranslate2
        has_cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        has_cuda = False
    if requested == 'auto':
        requested = 'cuda' if has_cuda else 'cpu'
    if requested == 'cpu':
        print('WARNING: no GPU - on CPU this is far too slow for tens of hours of audio. '
              'In Colab: Runtime > Change runtime type > T4 GPU.', flush=True)
    return requested, ('float16' if requested == 'cuda' else 'int8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', required=True, help='folder with the audio files (searched recursively)')
    ap.add_argument('--output', required=True, help='folder for the transcripts (created if missing)')
    ap.add_argument('--model', default=DEFAULT_MODEL, help='faster-whisper model name or path')
    ap.add_argument('--device', default='auto', choices=['auto', 'cuda', 'cpu'])
    ap.add_argument('--prompt', action='store_true', help='bias the model with a short Torah vocabulary prompt')
    ap.add_argument('--limit', type=int, default=0, help='only the first N recordings (0 = all)')
    ap.add_argument('--clip-seconds', type=int, default=0, help='only the first N seconds of each recording (for tests)')
    ap.add_argument('--beam-size', type=int, default=5)
    args = ap.parse_args()

    from faster_whisper import WhisperModel
    os.makedirs(args.output, exist_ok=True)
    files = find_audio(args.input)
    if not files:
        sys.exit('no audio files found under %s' % args.input)
    if args.limit:
        files = files[:args.limit]

    device, compute = pick_device(args.device)
    print('model %s | device %s/%s | %d recordings | prompt %s' % (args.model, device, compute, len(files), args.prompt), flush=True)
    model = WhisperModel(args.model, device=device, compute_type=compute)

    run_log = os.path.join(args.output, 'run_log.txt')
    if not os.path.exists(run_log):
        with open(run_log, 'w', encoding='utf-8') as f:
            f.write('stem\taudio_sec\telapsed_sec\tspeed_x\tsegments\tmax_repeat\tlow_conf_segments\tavg_logprob\tstatus\n')

    t_start, done_audio, todo = time.time(), 0.0, 0
    for i, path in enumerate(files, 1):
        stem = os.path.splitext(os.path.basename(path))[0]
        out_json = os.path.join(args.output, stem + '.json')
        if is_done(out_json, args.clip_seconds):
            print('[%d/%d] %s - already done, skipping' % (i, len(files), stem), flush=True)
            continue
        todo += 1
        t0 = time.time()
        try:
            kw = dict(language='he', beam_size=args.beam_size, vad_filter=True,
                      vad_parameters=dict(min_silence_duration_ms=500),
                      condition_on_previous_text=False)  # prevents one bad segment from poisoning the rest
            if args.prompt:
                kw['initial_prompt'] = VOCAB_PROMPT
            if args.clip_seconds:
                kw['clip_timestamps'] = '0,%d' % args.clip_seconds
            seg_iter, info = model.transcribe(path, **kw)
            segs = []
            for s in seg_iter:  # lazy generator: the real work happens here
                segs.append(dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip(),
                                 avg_logprob=round(s.avg_logprob, 3), no_speech_prob=round(s.no_speech_prob, 3),
                                 compression_ratio=round(s.compression_ratio, 2)))
                if len(segs) % 50 == 0:
                    print('    %s: %s transcribed' % (stem, stamp(s.end)), flush=True)
            elapsed = time.time() - t0
            audio_sec = args.clip_seconds and min(args.clip_seconds, info.duration) or info.duration
            rep = max_repeat([s['text'] for s in segs])
            low = sum(1 for s in segs if s['avg_logprob'] < -1.0 or s['compression_ratio'] > 2.4)
            lp = sum(s['avg_logprob'] for s in segs) / len(segs) if segs else 0.0
            status = 'ok' if rep < 5 else 'REPEAT-LOOP?'
            if not segs:
                status = 'EMPTY'
            tmp_txt = os.path.join(args.output, stem + '.txt.tmp')
            with open(tmp_txt, 'w', encoding='utf-8') as f:
                for s in segs:
                    f.write('[%s] %s\n' % (stamp(s['start']), s['text']))
            os.replace(tmp_txt, os.path.join(args.output, stem + '.txt'))
            tmp_json = out_json + '.tmp'
            with open(tmp_json, 'w', encoding='utf-8') as f:  # written last: its existence marks the recording as done
                json.dump(dict(file=os.path.basename(path), model=args.model, duration=round(info.duration, 1),
                               prompt=args.prompt, clip_seconds=args.clip_seconds, segments=segs), f, ensure_ascii=False)
            os.replace(tmp_json, out_json)
            speed = audio_sec / elapsed if elapsed else 0
            done_audio += audio_sec
            remain = len(files) - i
            avg_elapsed = (time.time() - t_start) / todo
            print('[%d/%d] %s | %.0f min audio in %.0f s (%.1fx) | %d segments (%d low-confidence) | %s | ETA ~%.0f min'
                  % (i, len(files), stem, audio_sec / 60, elapsed, speed, len(segs), low, status, avg_elapsed * remain / 60), flush=True)
            with open(run_log, 'a', encoding='utf-8') as f:
                f.write('%s\t%.0f\t%.0f\t%.1f\t%d\t%d\t%d\t%.3f\t%s\n' % (stem, audio_sec, elapsed, speed, len(segs), rep, low, lp, status))
        except Exception as e:  # keep going: one broken file must not stop an overnight run
            print('[%d/%d] %s - ERROR: %r' % (i, len(files), stem, e), flush=True)
            with open(os.path.join(args.output, 'errors.log'), 'a', encoding='utf-8') as f:
                f.write('%s\t%r\n' % (path, e))
            with open(run_log, 'a', encoding='utf-8') as f:
                f.write('%s\t\t\t\t\t\t\t\tERROR\n' % stem)

    print('finished: %d new recordings, %.1f hours of audio, %.0f min wall time'
          % (todo, done_audio / 3600, (time.time() - t_start) / 60), flush=True)


if __name__ == '__main__':
    main()
