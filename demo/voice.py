"""Narration for the demo: speak the lines, then build the finished video.

    python3 voice.py speak     # clips/NN.wav + clips/durations.json, before recording
    python3 voice.py build     # demo.webm + scenes.json + clips → <output>.mp4 and .srt (narration.json "output")
    python3 voice.py           # both (for a recording made without clips)
    python3 voice.py samples   # one sample line in several Kokoro voices, to choose from
    python3 voice.py mine      # your own recordings (recordings/01.m4a …) instead of a synthetic voice
    python3 voice.py script    # RECORDING-SCRIPT.md: the lines to read, numbered as the files they go in
    python3 voice.py splice    # your camera takes + the recorded demo, in script order → <output>-final.mp4

NARRATION=narration-full.json picks the 12-minute presentation instead of the 5-minute tour.

Voices, best first:
  kokoro     Kokoro-82M, an open neural voice that runs locally (used on Buddy, in a container).
             VOICE=af_sarah (default), af_heart, af_bella, am_michael, bf_emma, bm_george …
  say        macOS system voices; the "Premium" ones are free downloads in System Settings →
             Accessibility → Spoken Content → Manage Voices. VOICE="Ava (Premium)".
  espeak-ng  robotic; only for checking timing.
ENGINE=kokoro|say|espeak forces one.

Building is what makes it seamless. The recording waits for real models, so
some scenes hold still longer than their line; those stretches are sped up
(at most 3×) until each scene lasts about as long as its narration, and every
line starts right after the one before. Underneath sits a generated music
bed (music.py) that dips whenever the voice speaks. Needs ffmpeg and
numpy.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path.cwd()
SRC = Path(__file__).resolve().parent
CLIPS = HERE / "clips"
LEAD = 0.35          # a scene's line begins this long after the scene does
TAIL = 0.45          # and the scene runs this long after the line ends
GAP = 0.3            # the least silence between two lines
MAX_SPEEDUP = 3.0
MUSIC_DB = -19       # the bed under the voice, before ducking (a little more present than CEREBRO's)
MAC_VOICES = ["Ava (Premium)", "Zoe (Premium)", "Ava (Enhanced)", "Zoe (Enhanced)",
              "Evan (Enhanced)", "Samantha (Enhanced)", "Samantha"]


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def duration(path: Path) -> float:
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)))


def script() -> dict:
    name = os.environ.get("NARRATION", "narration.json")
    path = HERE / name if (HERE / name).exists() else SRC / name
    return json.loads(path.read_text())


def lines() -> list[dict]:
    return script()["scenes"]


# --- Speaking ----------------------------------------------------------------------------------

def spoken_text(text: str, kind: str) -> str:
    """How the voice should say a word, where the spelling misleads it (narration.json "pronounce":
    word → [Kokoro markup with phonemes, plain respelling for the other voices]). Subtitles keep
    the written spelling."""
    for word, (phonemes, plain) in script().get("pronounce", {}).items():
        text = re.sub(rf"\b{re.escape(word)}\b", phonemes if kind == "kokoro" else plain, text)
    return text


def engine() -> str:
    wanted = os.environ.get("ENGINE")
    if wanted:
        return wanted
    try:
        import kokoro  # noqa: F401
        return "kokoro"
    except ImportError:
        pass
    if shutil.which("say"):
        return "say"
    if shutil.which("espeak-ng"):
        return "espeak"
    sys.exit("No voice available: install kokoro, run on a Mac, or install espeak-ng.")


def mac_voice() -> str:
    if os.environ.get("VOICE"):
        return os.environ["VOICE"]
    listed = [m.group(1).strip() for m in (re.match(r"^(.+?)\s{2,}[a-z]{2}_[A-Z]{2}", line)
                                            for line in run("say", "-v", "?").splitlines()) if m]
    return next((v for v in MAC_VOICES if v in listed), "Samantha")


def speak() -> None:
    kind = engine()
    CLIPS.mkdir(exist_ok=True)
    durations = {}
    if kind == "kokoro":
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline

        voice = os.environ.get("VOICE", "af_sarah")
        pipeline = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
        speed = float(os.environ.get("SPEED", "0.92"))  # a little slower than default reads warmer
    else:
        voice = mac_voice() if kind == "say" else os.environ.get("VOICE", "en-us")
    print(f"voice: {voice} ({kind})")
    for i, line in enumerate(lines()):
        out = CLIPS / f"{i:02}.wav"
        words = spoken_text(line["text"], kind)
        if kind == "kokoro":
            parts = [np.asarray(audio) for _, _, audio in pipeline(words, voice=voice, speed=speed)]
            sf.write(out.with_suffix(".raw.wav"), np.concatenate(parts), 24000)
            run("ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".raw.wav")), "-ar", "48000", "-ac", "1", str(out))
            out.with_suffix(".raw.wav").unlink()
        elif kind == "say":
            aiff = out.with_suffix(".aiff")
            run("say", "-v", voice, "-r", os.environ.get("RATE", "180"), "-o", str(aiff), words)
            run("ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "48000", "-ac", "1", str(out))
            aiff.unlink()
        else:
            raw = out.with_suffix(".raw.wav")
            run("espeak-ng", "-v", voice, "-s", os.environ.get("RATE", "165"), "-w", str(raw), words)
            run("ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ar", "48000", "-ac", "1", str(out))
            raw.unlink()
        durations[line["id"]] = round(duration(out), 2)
        print(f"  {line['id']:10} {durations[line['id']]:5.1f}s")
    (CLIPS / "durations.json").write_text(json.dumps({"voice": voice, "engine": kind, "seconds": durations}, indent=1))
    print(f"total speech {sum(durations.values()):.0f}s")


# --- Your own voice -------------------------------------------------------------------------------

AUDIO = (".wav", ".m4a", ".mp3", ".aac", ".caf", ".ogg", ".opus", ".webm", ".flac", ".aiff", ".mp4", ".mov", ".m4v", ".mkv")


def recordings() -> tuple[Path, dict[int, tuple[int, Path]]]:
    """Your files by the line they start on: 07.m4a covers line 7; a camera take 01-05.mp4 covers lines 1 to 5."""
    folder = Path(os.environ.get("RECORDINGS", HERE / "recordings"))
    files: dict[int, tuple[int, Path]] = {}
    for f in sorted(folder.iterdir()) if folder.exists() else []:
        m = re.match(r"^(\d+)(?:\s*-\s*(\d+))?", f.name)
        if m and f.suffix.lower() in AUDIO:
            first = int(m.group(1))
            files.setdefault(first, (int(m.group(2) or first), f))
    return folder, files


def narrated(line: dict) -> bool:
    """Lines whose audio the kit lays over the screen recording: all of them, or only the "screen" lines
    when the script marks some lines as the presenter on camera."""
    return line.get("mode", "screen") != "camera"


def mine() -> None:
    """Use the presenter's own recordings: one file per line, named by its number (01.m4a, 02 hook.wav …).
    Each is cleaned the same way: rumble below 80 Hz cut, silence trimmed at both ends, loudness evened out
    (-18 LUFS), 48 kHz mono. The video is then timed to these lines exactly as to a synthetic voice."""
    folder, found = recordings()
    files = {n: f for n, (_, f) in found.items()}
    want = lines()
    missing = [f"{i + 1:02} {line['id']}" for i, line in enumerate(want) if narrated(line) and i + 1 not in files]
    if missing:
        sys.exit(f"No recording in {folder} for: " + ", ".join(missing) + "\n(name each file by its line number, e.g. 01.m4a)")
    CLIPS.mkdir(exist_ok=True)
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12"
    durations = {}
    for i, line in enumerate(want):
        if not narrated(line):
            continue
        out = CLIPS / f"{i:02}.wav"
        run("ffmpeg", "-y", "-loglevel", "error", "-i", str(files[i + 1]), "-vn", "-af",
            f"highpass=f=80,{trim},areverse,{trim},areverse,loudnorm=I=-18:TP=-2:LRA=11",
            "-ar", "48000", "-ac", "1", str(out))
        durations[line["id"]] = round(duration(out), 2)
        words = len(line["text"].split())
        print(f"  {i + 1:02} {line['id']:10} {durations[line['id']]:5.1f}s  ({words / durations[line['id']] * 60:.0f} words/min)")
    (CLIPS / "durations.json").write_text(json.dumps({"voice": "own recordings", "engine": "own", "seconds": durations}, indent=1))
    print(f"total speech {sum(durations.values()) / 60:.1f} min")


def recording_script() -> None:
    """A printable script: each line with the file name it goes in and a target length at a calm pace."""
    s = script()
    out = [f"# Recording script: {s.get('output', 'demo')}", "",
           "Record each line as its own file, named by its number: `01.m4a`, `02.m4a` … (any common audio format).",
           "Quiet room, same distance from the mic, half a second of silence before and after. Redo a line rather",
           "than editing it. Camera lines may be one take for several lines, named by the range: `01-05.mp4`.",
           "Voice-only lines time the demo, so read them at the pace you want the screen to move.", ""]
    total = 0
    part = None
    for i, line in enumerate(s["scenes"]):
        if line.get("part") != part:
            part = line.get("part")
            out += [f"## {part}", ""] if part else []
        secs = len(line["text"].split()) / 2.3
        total += secs
        how = "on camera (video + audio)" if line.get("mode") == "camera" else "voice only (over the app demo)"
        ext = "mp4" if line.get("mode") == "camera" else "m4a"
        out += [f"**{i + 1:02} · {line.get('title', line['id'])}** — {how}, file `{i + 1:02}.{ext}`, about {secs:.0f} s", "",
                line["text"], ""]
    out.append(f"About {total / 60:.0f} minutes of speech at 138 words a minute.")
    (HERE / "RECORDING-SCRIPT.md").write_text("\n".join(out) + "\n")
    print(f"script: {HERE / 'RECORDING-SCRIPT.md'}")


SAMPLE_VOICES = ["af_heart", "af_bella", "af_nicole", "af_sarah", "am_michael", "am_fenrir",
                 "am_puck", "bf_emma", "bm_george", "bm_fable"]


def samples() -> None:
    """The opening line in several Kokoro voices, to choose from by ear."""
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    out = HERE / "voice-samples"
    out.mkdir(exist_ok=True)
    speed = float(os.environ.get("SPEED", "0.92"))
    pipelines = {}
    for voice in os.environ.get("VOICES", " ".join(SAMPLE_VOICES)).split():
        pipe = pipelines.setdefault(voice[0], KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M"))
        sample = " ".join(s["text"] for s in lines()[:1])
        audio = np.concatenate([np.asarray(a) for _, _, a in pipe(spoken_text(sample, "kokoro"), voice=voice, speed=speed)])
        wav = out / f"{voice}.wav"
        sf.write(wav, audio, 24000)
        run("ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(wav.with_suffix(".mp3")))
        wav.unlink()
        print(f"  {voice}: {wav.with_suffix('.mp3')}")


# --- Building ----------------------------------------------------------------------------------

def stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def cues(text: str, start: float, length: float) -> list[tuple[float, float, str]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]
    words = [len(s.split()) for s in sentences]
    t, out = start, []
    for sentence, n in zip(sentences, words, strict=True):
        span = length * n / sum(words)
        out.append((t, t + span, sentence))
        t += span
    return out


def build() -> None:
    if not (CLIPS / "durations.json").exists():
        speak()
    spoken = json.loads((CLIPS / "durations.json").read_text())["seconds"]
    text = {s["id"]: s["text"] for s in lines()}
    order = [s["id"] for s in lines()]
    video = HERE / "demo.webm"
    timing = json.loads((HERE / "scenes.json").read_text())["scenes"]
    total = duration(video)

    # 1. Each scene's stretch of video, sped up where it holds still too long.
    segments, starts, t = [], [], 0.0
    for i, scene in enumerate(timing):
        a = scene["start"] if i else 0.0
        b = timing[i + 1]["start"] if i + 1 < len(timing) else total
        length = b - a
        want = LEAD + spoken[scene["id"]] + TAIL
        speed = min(MAX_SPEEDUP, length / want) if length > want else 1.0
        segments.append((a, b, speed))
        starts.append(t)
        t += length / speed
    final = t

    # Each stretch rendered on its own and then joined: one filter graph cutting
    # eleven pieces from a 1080p stream buffers enough frames to run out of memory.
    parts = HERE / "parts"
    parts.mkdir(exist_ok=True)
    listing = []
    for k, (a, b, speed) in enumerate(segments):
        part = parts / f"{k:02}.mp4"
        run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(video),
            "-vf", f"setpts=(PTS-STARTPTS)/{speed:.4f},fps=30", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(part))
        listing.append(f"file '{part.name}'")
    (parts / "list.txt").write_text("\n".join(listing) + "\n")
    joined = parts / "joined.mp4"
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(parts / "list.txt"),
        "-c", "copy", str(joined))
    filters = []

    # 2. Each line where its scene starts, but never on top of the line before.
    placed, subtitles, cursor = [], [], 0.0
    for k, scene in enumerate(timing):
        sid = scene["id"]
        at = max(starts[k] + LEAD, cursor + GAP)
        placed.append((CLIPS / f"{order.index(sid):02}.wav", at))
        subtitles += cues(text[sid], at, spoken[sid])
        cursor = at + spoken[sid]
        print(f"  {sid:10} scene {starts[k]:6.1f}s  voice {at:6.1f}s  speed ×{segments[k][2]:.2f}")
    final = max(final, cursor + 1.0)
    landed = [{"id": scene["id"], "video": round(starts[k], 3), "voice": round(placed[k][1], 3),
               "voice_end": round(placed[k][1] + spoken[scene["id"]], 3)} for k, scene in enumerate(timing)]
    (HERE / "built.json").write_text(json.dumps({"final": round(final, 3), "scenes": landed}, indent=1))

    # 3. Music under it all, ducked by the voice.
    sys.path.insert(0, str(SRC))
    import music

    bed = HERE / "music.wav"
    music.write(str(bed), music.bed(final + 1))

    inputs = ["-i", str(joined), "-i", str(bed)]
    for clip, _ in placed:
        inputs += ["-i", str(clip)]
    voice_chain = []
    for n, (_, at) in enumerate(placed):
        ms = int(at * 1000)
        voice_chain.append(f"[{n + 2}:a]adelay={ms}|{ms},aformat=channel_layouts=stereo[c{n}]")
    filters += voice_chain
    filters.append("".join(f"[c{n}]" for n in range(len(placed))) +
                   f"amix=inputs={len(placed)}:normalize=0,apad,atrim=0:{final:.3f},"
                   "loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voice][key]")
    filters.append(f"[1:a]atrim=0:{final:.3f},volume={MUSIC_DB}dB,aformat=channel_layouts=stereo[bed]")
    filters.append("[bed][key]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600:makeup=1[ducked]")
    filters.append("[voice][ducked]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]")

    name = script().get("output", "demo")
    srt = HERE / f"{name}.srt"
    if os.environ.get("SUBTITLES", "1") == "0":   # you did not read the lines word for word
        subtitles = []
    srt.write_text("\n".join(f"{k}\n{stamp(a)} --> {stamp(b)}\n{line}\n" for k, (a, b, line) in enumerate(subtitles, 1)))
    out = HERE / f"{name}.mp4"
    subs = ["-i", str(srt)] if subtitles else []
    sub_map = ["-map", f"{len(placed) + 2}:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng"] if subtitles else []
    run("ffmpeg", "-y", "-loglevel", "error", *inputs, *subs, "-filter_complex", ";".join(filters),
        "-map", "0:v", "-map", "[aout]", *sub_map,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{final:.3f}", "-movflags", "+faststart", str(out))
    bed.unlink()
    shutil.rmtree(parts, ignore_errors=True)
    print(f"\nvideo: {out}  ({duration(out):.0f}s, from {total:.0f}s recorded)\nsubtitles: {srt}")


# --- Splicing your camera takes with the demo --------------------------------------------------

FRAME = ("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
         "fps=30,format=yuv420p")


def normalise(src: Path, out: Path, start: float | None = None, end: float | None = None, fade: float = 0.0) -> None:
    """One piece of the final cut: 1080p, 30 fps, 48 kHz stereo at -16 LUFS, so the pieces join without a jump."""
    cut = (["-ss", f"{start:.3f}"] if start is not None else []) + (["-to", f"{end:.3f}"] if end is not None else [])
    length = (end - (start or 0)) if end is not None else duration(src)
    af = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo"
    if fade:
        af += f",afade=t=in:d={fade},afade=t=out:st={max(0.0, length - fade):.3f}:d={fade}"
    # The audio is padded to the picture's length: pieces joined end to end must each be exactly as long in sound
    # as in picture, or every later camera take would drift out of lip sync.
    af += ",apad"
    run("ffmpeg", "-y", "-loglevel", "error", *cut, "-i", str(src), "-vf", FRAME, "-af", af, "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out))


def splice() -> None:
    """The final cut: in script order, each run of camera lines is your own take, and each run of screen lines is
    its stretch of the recorded demo (built.json says where each scene landed). The demo stretches are also kept
    as separate files, for splicing in your own editor instead."""
    name = script().get("output", "demo")
    demo = HERE / f"{name}.mp4"
    built = json.loads((HERE / "built.json").read_text())
    where = {s["id"]: s for s in built["scenes"]}
    order = [s["id"] for s in built["scenes"]]
    folder, files = recordings()
    want = lines()
    runs, i = [], 0   # [(mode, first line, last line)], 1-based
    while i < len(want):
        mode = "camera" if want[i].get("mode") == "camera" else "screen"
        j = i
        while j + 1 < len(want) and ("camera" if want[j + 1].get("mode") == "camera" else "screen") == mode:
            j += 1
        runs.append((mode, i + 1, j + 1))
        i = j + 1
    pieces_dir = HERE / "pieces"
    pieces_dir.mkdir(exist_ok=True)
    pieces, n_screen = [], 0
    for mode, a, b in runs:
        if mode == "camera":
            line = a
            while line <= b:
                if line not in files:
                    sys.exit(f"No camera take in {folder} starting at line {line:02} ({want[line - 1]['id']}); "
                             f"name it {line:02}.mp4, or {line:02}-{b:02}.mp4 for one take of lines {line}-{b}")
                last, src = files[line]
                if not run("ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=index", "-of", "csv=p=0", str(src)).strip():
                    sys.exit(f"{src.name} has no video; camera lines need a video take")
                out = pieces_dir / f"{len(pieces):02}-camera-{line:02}.mp4"
                normalise(src, out)
                pieces.append(out)
                print(f"  camera {line:02}{'-' + format(last, '02') if last != line else ''}  {src.name}  {duration(out):.1f}s")
                line = last + 1
        else:
            ids = [want[k - 1]["id"] for k in range(a, b + 1)]
            first, last = where[ids[0]], where[ids[-1]]
            nxt = order.index(ids[-1]) + 1
            start = 0.0 if order.index(ids[0]) == 0 else first["video"]
            end = max(where[order[nxt]]["video"], last["voice_end"] + TAIL) if nxt < len(order) else None
            n_screen += 1
            out = pieces_dir / f"{len(pieces):02}-screen-{n_screen}.mp4"
            normalise(demo, out, start, end, fade=0.35)
            keep = HERE / f"{name}-demo-{n_screen}.mp4"
            shutil.copy(out, keep)
            pieces.append(out)
            print(f"  screen {a:02}-{b:02}  demo {start:.1f}–{end if end is not None else built['final']:.1f}s  → {keep.name}")
    (pieces_dir / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in pieces))
    final = HERE / f"{name}-final.mp4"
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(pieces_dir / "list.txt"),
        "-c", "copy", "-movflags", "+faststart", str(final))
    shutil.rmtree(pieces_dir, ignore_errors=True)
    print(f"\nfinal cut: {final}  ({duration(final) / 60:.1f} min)")


if __name__ == "__main__":
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found. On a Mac: brew install ffmpeg")
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step == "samples":
        samples()
        sys.exit()
    if step == "script":
        recording_script()
        sys.exit()
    if step == "mine":
        mine()
        sys.exit()
    if step == "splice":
        splice()
        sys.exit()
    if step in ("speak", "all"):
        speak()
    if step in ("build", "all"):
        build()
