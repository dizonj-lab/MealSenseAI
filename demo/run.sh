#!/usr/bin/env bash
# Make the MealSenseAI demo video on Buddy, start to finish.
#
#   ./demo/run.sh            demo stack + photos + Wei Ming's week, voice, recording, finished MP4
#   ./demo/run.sh record     record and build again (stack already up; voice reused)
#   ./demo/run.sh voice      remake the voice (after editing narration.json), then record and build
#   ./demo/run.sh samples    the opening line in ten voices, to pick one by ear
#   ./demo/run.sh down       stop the demo stack (its data is kept)
#
# The 12-minute presentation (narration-full.json), with you on camera and your own voice over the demo:
#   NARRATION=narration-full.json ./demo/run.sh script         RECORDING-SCRIPT.md: what to record, file by file
#   NARRATION=narration-full.json ./demo/run.sh                a full preview first, every line in the Kokoro voice
#   NARRATION=narration-full.json RECORDINGS=~/mealsense-recordings ./demo/run.sh mine
#
# The final presentation (narration-final.json): every line is a video take of you; "camera" lines play full screen,
# "pip" lines put you in a corner over the demo, the evaluation figures and the system design:
#   NARRATION=narration-final.json ./demo/run.sh script         RECORDING-SCRIPT-MealSenseAI-final-presentation.md
#   NARRATION=narration-final.json RECORDINGS=~/mealsense-final ./demo/run.sh mine
#        your voice over the demo, then your camera takes spliced in → ~/mealsense-demo-<time>/…-final.mp4
#
#   VOICE=am_michael ./demo/run.sh voice     another Kokoro voice (af_sarah is the default)
#
# Everything runs in the Compose project "mealsense-demo" and in throwaway
# containers, on the images the live MealSenseAI was built from. The live app,
# its database and photos are not touched. The result is
# ~/mealsense-demo-<time>/MealSenseAI-demo.mp4 (+ .srt and the photo credits).
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
COMPOSE=(docker compose -f docker-compose.demo.yml)
# DEMO_SLM=1: use the live stack's Ollama (Qwen 2.5) so the settings scene shows the installed model and the
# advisor words its answers with it. Needs the live project "mealsenseai" running with its "slm" profile.
[ "${DEMO_SLM:-0}" = 1 ] && COMPOSE+=(-f docker-compose.demo-slm.yml)
PORT="${DEMO_WEB_PORT:-8380}"
BASE="http://127.0.0.1:$PORT"
PLAYWRIGHT="${PLAYWRIGHT_VERSION:-1.63.0}"
THEME="${THEME:-light}"
VOICE="${VOICE:-af_sarah}"
NARRATION="${NARRATION:-narration.json}"
OUTPUT="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('output','demo'))" "$NARRATION")"
BACKEND_IMAGE="${MEALSENSE_BACKEND_IMAGE:-mealsenseai/backend:local}"
STEP="${1:-all}"

case "$STEP" in
  down)
    "${COMPOSE[@]}" down
    echo "Stopped. Its data is kept; to delete the demo's own database and photos as well:"
    echo "  docker volume rm mealsense-demo_pgdata mealsense-demo_uploads"
    exit 0 ;;
  script)
    NARRATION="$NARRATION" python3 voice.py script
    exit 0 ;;
  all|record|voice|samples|mine) ;;
  *) echo "usage: $0 [all|record|voice|samples|script|mine|down]"; exit 1 ;;
esac

# The voice image is the same as CEREBRO's demo; reuse it if CEREBRO's was built here.
voice_image() {
  docker image inspect mealsense-demo-voice >/dev/null 2>&1 && return
  if docker image inspect cerebro-demo-voice >/dev/null 2>&1; then
    docker tag cerebro-demo-voice mealsense-demo-voice
  else
    echo "==> Building the voice image (Kokoro, once; a few minutes)"
    docker build -q -t mealsense-demo-voice -f voice.Dockerfile . >/dev/null
  fi
}
MODELS_VOLUME=mealsense-demo-models
docker volume inspect cerebro-demo-models >/dev/null 2>&1 && MODELS_VOLUME=cerebro-demo-models  # Kokoro, already downloaded
in_voice() {  # run voice.py in the voice container, in folder $1; what it writes is handed back to you, not left to root
  docker run --rm -v "$1:/work" -v "$HERE:/demo:ro" -v "$MODELS_VOLUME:/root/.cache" \
    -e VOICE="$VOICE" -e ENGINE=kokoro -e NARRATION="$NARRATION" -e SUBTITLES="${SUBTITLES:-1}" \
    -e RECORDINGS=/work/recordings -w /work mealsense-demo-voice \
    sh -c 'python /demo/voice.py "$1"; rc=$?; chown -R "$2" /work; exit $rc' _ "$2" "$(id -u):$(id -g)"
}
wipe() {  # remove a folder, even one an earlier container left owned by root
  rm -rf "$1" 2>/dev/null && return
  voice_image
  docker run --rm -v "$(dirname "$1"):/parent" mealsense-demo-voice rm -rf "/parent/$(basename "$1")"
}

if [ "$STEP" = samples ]; then
  voice_image
  mkdir -p "$HOME/mealsense-voice-samples"
  docker run --rm -v "$HOME/mealsense-voice-samples:/work" -v "$HERE:/demo:ro" -v "$MODELS_VOLUME:/root/.cache" \
    -w /work mealsense-demo-voice python /demo/voice.py samples
  echo "==> Samples in ~/mealsense-voice-samples/voice-samples/. Listen, then: VOICE=<name> ./demo/run.sh"
  exit 0
fi

SCENES_MODE=all
if [ "$STEP" = mine ]; then
  # Your recordings: the voice-only lines time and narrate the demo; the camera takes are spliced in at the end.
  [ -n "${RECORDINGS:-}" ] && [ -d "$RECORDINGS" ] || { echo "Set RECORDINGS to the folder with your files (01-05.mp4, 06.m4a …)"; exit 1; }
  wipe "$HERE/recordings" && mkdir -p "$HERE/recordings" && cp "$RECORDINGS"/* "$HERE/recordings/"
  voice_image
  echo "==> Your recordings: cleaning and measuring the voice-only lines"
  wipe "$HERE/clips"
  in_voice "$HERE" mine
  SCENES_MODE=screen
fi

if [ "$STEP" = all ] || [ "$STEP" = mine ]; then
  for image in "$BACKEND_IMAGE" "${MEALSENSE_FRONTEND_IMAGE:-mealsenseai/frontend:local}"; do
    docker image inspect "$image" >/dev/null 2>&1 || {
      echo "Image $image not found. Build the live app first (cd ~/MealSenseAI && docker compose build),"
      echo "or set MEALSENSE_BACKEND_IMAGE / MEALSENSE_FRONTEND_IMAGE."; exit 1; }
  done

  echo "==> Starting the demo stack (project mealsense-demo, $BASE)"
  "${COMPOSE[@]}" up -d --wait

  echo "==> Choosing the meal photos (free-licence Singapore dishes from Wikimedia Commons, checked by the model)"
  mkdir -p "$HERE/photos"
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$HERE:/demo" "$BACKEND_IMAGE" \
    python /demo/photos.py /demo/photos
  [ -f "$HERE/photos/chicken_rice.jpg" ] || {
    echo "No recognisable chicken rice photo was found; the lunch scene needs one."
    echo "Put a free-licence photo at demo/photos/chicken_rice.jpg (and its credit in photos/CREDITS.md), then: ./demo/run.sh"
    exit 1; }

  echo "==> Loading Wei Ming's week of meals (each analysed by the model)"
  python3 seed.py "$BASE" "$HERE/photos"
  echo "==> Giving the demo account the admin role (for the model-settings scene)"
  "${COMPOSE[@]}" exec -T backend python -m app.tools.admin grant weiming@mealsense.example
fi

# 1. The voice first, so every scene can be timed to its line.
if [ "$STEP" != record ] && [ "$STEP" != mine ] || [ ! -f "$HERE/clips/durations.json" ]; then
  voice_image
  echo "==> Speaking the narration ($VOICE)"
  wipe "$HERE/clips"
  in_voice "$HERE" speak
fi

# 2. The recording, in Playwright's own container (its browser, fonts and codecs).
echo "==> Recording the tour (5 to 12 minutes)"
wipe "$HERE/out"
docker run --rm --network host --ipc=host -v "$HERE:/demo" -v "$HERE/../docs/report/charts:/docs/report/charts:ro" -w /demo \
  -e BASE="$BASE" -e OUT=/demo/out -e THEME="$THEME" -e PHOTOS=/demo/photos -e NARRATION="$NARRATION" -e SCENES_MODE="$SCENES_MODE" \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  bash -c "npm install --no-save --silent playwright@$PLAYWRIGHT >/dev/null && node record.mjs; chown -R $(id -u):$(id -g) /demo/out /demo/node_modules 2>/dev/null || true"

# 3. Assembly: idle stretches tightened, voice, music, subtitles.
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$HOME/mealsense-demo-$STAMP"
mkdir -p "$DEST"
cp -r "$HERE/out/demo.webm" "$HERE/out/scenes.json" "$HERE/$NARRATION" "$HERE/clips" \
  "$HERE/voice.py" "$HERE/music.py" "$HERE/voice_mac.sh" "$DEST/"
cp "$HERE/photos/CREDITS.md" "$DEST/PHOTO-CREDITS.md" 2>/dev/null || true
voice_image
echo "==> Building the video"
if [ "$STEP" = mine ]; then
  cp -r "$HERE/recordings" "$DEST/"
  SUBTITLES=0 in_voice "$DEST" build    # you may not read word for word: no subtitles from the script
  echo "==> Splicing your camera takes with the demo"
  in_voice "$DEST" splice
  echo
  echo "==> Done: $DEST/$OUTPUT-final.mp4"
  echo "    The demo stretches alone, for your own editor: $DEST/$OUTPUT-demo-*.mp4"
else
  in_voice "$DEST" build
  echo
  echo "==> Done: $DEST/$OUTPUT.mp4"
fi
echo "    Photo credits (for the description): $DEST/PHOTO-CREDITS.md"
echo "    On your Mac:  scp 'admin@<buddy>:$DEST/MealSenseAI-demo.mp4' ~/Downloads/"
