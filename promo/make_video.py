#!/usr/bin/env python3
"""Assemble the Q-Mol 60s vertical promo (YouTube Short).

Pipeline (runs on a machine with network + full ffmpeg, i.e. CI):
  1. ElevenLabs TTS (with word/char timestamps) -> narration.mp3 + timings
  2. Derive per-scene durations from the narration timings (scene changes land
     on sentence boundaries)
  3. Render each scene still into a ken-burns video clip (libx264, 1080x1920)
  4. Concat clips -> silent visual track
  5. Synthesize a soft ambient music bed
  6. Mix voiceover + music
  7. Mux -> promo/out/qmol_short.mp4 (HD, H.264, faststart)

Requires env ELEVENLABS_API_KEY. Optional: ELEVENLABS_VOICE_ID,
ELEVENLABS_MODEL_ID, FFMPEG (path to ffmpeg binary).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"

API_KEY = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
# If unset, we auto-pick an available voice from the account (see resolve_voice).
VOICE_ID = (os.environ.get("ELEVENLABS_VOICE_ID") or "").strip()
# NB: "or" (not a get() default) — CI passes the env var as empty when the
# secret is absent, and an empty model_id is rejected by the API.
MODEL_ID = (os.environ.get("ELEVENLABS_MODEL_ID") or "").strip() or "eleven_multilingual_v2"
# Preferred premium voices, tried in order if present on the account.
PREFERRED_VOICES = ["Rachel", "Sarah", "Brian", "Adam", "Antoni", "Bella",
                    "Charlie", "Daniel", "George", "Bill", "Jessica", "Laura"]

FPS = 30
W, H = 1080, 1920
MIN_SCENE = 2.0
TAIL = 1.4  # extra hold on the final CTA scene

NARRATION = os.path.join(HERE, "narration.txt")
MP3 = os.path.join(OUT, "narration.mp3")


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def read_segments():
    with open(NARRATION, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def resolve_voice(client):
    """Return a usable voice_id: env override, else pick from the account."""
    if VOICE_ID:
        print("Using voice from env:", VOICE_ID, flush=True)
        return VOICE_ID
    try:
        voices = list(client.voices.get_all().voices)
    except Exception as e:  # noqa: BLE001
        print("voices list error:", e, file=sys.stderr)
        voices = []
    if voices:
        names = [(v.name or "") for v in voices]
        print("Account voices:", ", ".join(names), flush=True)
        # Prefer a known narrator voice; account voice names often carry
        # suffixes like "Roger - Laid-Back, Casual" so match on the first word.
        for pref in PREFERRED_VOICES:
            for v in voices:
                first = (v.name or "").split(" ")[0].strip(" -,")
                if first.lower() == pref.lower():
                    print(f"Using voice: {v.name} ({v.voice_id})", flush=True)
                    return v.voice_id
        v = voices[0]
        print(f"Using first available voice: {v.name} ({v.voice_id})",
              flush=True)
        return v.voice_id
    return "21m00Tcm4TlvDq8ikWAM"  # last-resort classic default


def tts(text):
    if not API_KEY:
        print("ERROR: ELEVENLABS_API_KEY is not set.", file=sys.stderr)
        sys.exit(78)  # EX_CONFIG -> handled as a clean skip by the workflow
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=API_KEY)
    vid = resolve_voice(client)
    print(f"Synthesizing with voice_id={vid} model={MODEL_ID}", flush=True)
    try:
        audio = client.text_to_speech.convert(
            voice_id=vid,
            text=text,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        with open(MP3, "wb") as f:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
    except Exception as e:  # noqa: BLE001
        print("ElevenLabs TTS failed:", repr(e),
              "status:", getattr(e, "status_code", "?"),
              "body:", getattr(e, "body", "?"), file=sys.stderr)
        sys.exit(1)
    size = os.path.getsize(MP3)
    print(f"narration.mp3 written ({size} bytes)", flush=True)
    if size < 10_000:
        print("ERROR: narration suspiciously small — aborting.",
              file=sys.stderr)
        sys.exit(1)
    return None  # proportional scene timing (per-character) is used


def probe_duration(path):
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ])
    return float(out.strip())


def scene_durations(segments, align):
    """Return a list of per-scene durations that sum to the narration length."""
    total = probe_duration(MP3)
    n = len(segments)
    starts = None
    if align:
        st = align.get("character_start_times_seconds")
        if st:
            joined = " ".join(segments)
            m = len(st)
            seg_start = []
            pos = 0
            for seg in segments:
                seg_start.append(st[min(pos, m - 1)])
                pos += len(seg) + 1  # +1 for the joining space
            seg_start[0] = 0.0
            starts = seg_start
    if not starts:
        # Fallback: split proportionally to characters
        lens = [len(s) for s in segments]
        tot = sum(lens)
        acc, starts = 0.0, []
        for L in lens:
            starts.append(acc)
            acc += total * (L / tot)
    # durations from consecutive starts; last extends to end + tail
    durs = []
    for i in range(n):
        end = starts[i + 1] if i + 1 < n else (total + TAIL)
        durs.append(max(MIN_SCENE, end - starts[i]))
    return durs


def make_clip(scene_png, duration, out_mp4):
    frames = max(2, round(duration * FPS))
    fade_out_st = max(0.0, frames / FPS - 0.35)
    vf = (
        f"zoompan=z='min(zoom+0.0007,1.12)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        f"fade=t=in:st=0:d=0.35,"
        f"fade=t=out:st={fade_out_st:.3f}:d=0.35,format=yuv420p"
    )
    run([
        FFMPEG, "-y", "-loop", "1", "-framerate", str(FPS), "-i", scene_png,
        "-filter_complex", vf, "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", out_mp4,
    ])
    return frames


def main():
    segments = read_segments()
    scenes = sorted(
        os.path.join(FRAMES, f) for f in os.listdir(FRAMES)
        if f.startswith("scene_") and f.endswith(".png")
    )
    if len(scenes) != len(segments):
        print(f"WARN: {len(scenes)} scenes vs {len(segments)} narration lines")
    text = " ".join(segments)
    print("Requesting narration from ElevenLabs...", flush=True)
    align = tts(text)
    durs = scene_durations(segments, align)
    print("Scene durations:", [round(d, 2) for d in durs], flush=True)

    clips = []
    total_frames = 0
    for i, scene in enumerate(scenes):
        d = durs[i] if i < len(durs) else MIN_SCENE
        out_mp4 = os.path.join(OUT, f"clip_{i:02d}.mp4")
        total_frames += make_clip(scene, d, out_mp4)
        clips.append(out_mp4)

    total_dur = total_frames / FPS
    print("Total video duration:", round(total_dur, 2), "s", flush=True)

    # concat
    listfile = os.path.join(OUT, "clips.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    visual = os.path.join(OUT, "visual.mp4")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
         "-c", "copy", visual])

    # ambient music bed (A-minor-ish pad), low volume
    music = os.path.join(OUT, "music.wav")
    T = total_dur
    run([
        FFMPEG, "-y",
        "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={T}",
        "-f", "lavfi", "-i", f"sine=frequency=277.18:sample_rate=44100:duration={T}",
        "-f", "lavfi", "-i", f"sine=frequency=329.63:sample_rate=44100:duration={T}",
        "-filter_complex",
        "[0][1][2]amix=inputs=3:normalize=0,tremolo=f=0.15:d=0.4,"
        f"lowpass=f=700,volume=0.05,afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={max(0.0, T - 2):.3f}:d=2[a]",
        "-map", "[a]", "-c:a", "pcm_s16le", music,
    ])

    # mix voiceover + music
    mix = os.path.join(OUT, "mix.m4a")
    run([
        FFMPEG, "-y", "-i", MP3, "-i", music, "-filter_complex",
        "[0:a]volume=1.1,aresample=44100[v];[1:a]volume=1.0[m];"
        "[v][m]amix=inputs=2:duration=longest:dropout_transition=0,"
        "alimiter=limit=0.95[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", mix,
    ])

    # final mux
    final = os.path.join(OUT, "qmol_short.mp4")
    run([
        FFMPEG, "-y", "-i", visual, "-i", mix,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", final,
    ])
    print("DONE ->", final, flush=True)
    print("size:", round(os.path.getsize(final) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
