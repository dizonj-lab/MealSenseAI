#!/usr/bin/env bash
# Make the MealSenseAI demo video on Buddy, start to finish.
#
#   ./demo/run.sh            demo stack + photos + Wei Ming's week, voice, recording, finished MP4
#   ./demo/run.sh record     record and build again (stack already up; voice reused)
#   ./demo/run.sh voice      remake the voice (after editing narration.json), then record and build
#   ./demo/run.sh samples    the opening line in ten voices, to pick one by ear
#   ./demo/run.sh down       stop the demo stack (its data is kept)
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
PORT="${DEMO_WEB_PORT:-8380}"
BASE="http://127.0.0.1:$PORT"
PLAYWRIGHT="${PLAYWRIGHT_VERSION:-1.63.0}"
THEME="${THEME:-light}"
VOICE="${VOICE:-af_sarah}"
BACKEND_IMAGE="${MEALSENSE_BACKEND_IMAGE:-mealsenseai/backend:local}"
STEP="${1:-all}"

case "$STEP" in
  down)
    "${COMPOSE[@]}" down
    echo "Stopped. Its data is kept; to delete the demo's own database and photos as well:"
    echo "  docker volume rm mealsense-demo_pgdata mealsense-demo_uploads"
    exit 0 ;;
  all|record|voice|samples) ;;
  *) echo "usage: $0 [all|record|voice|samples|down]"; exit 1 ;;
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
in_voice() {  # run voice.py in the voice container, in folder $1
  docker run --rm -v "$1:/work" -v "$HERE:/demo:ro" -v "$MODELS_VOLUME:/root/.cache" \
    -e VOICE="$VOICE" -e ENGINE=kokoro -w /work mealsense-demo-voice python /demo/voice.py "$2"
}

if [ "$STEP" = samples ]; then
  voice_image
  mkdir -p "$HOME/mealsense-voice-samples"
  docker run --rm -v "$HOME/mealsense-voice-samples:/work" -v "$HERE:/demo:ro" -v "$MODELS_VOLUME:/root/.cache" \
    -w /work mealsense-demo-voice python /demo/voice.py samples
  echo "==> Samples in ~/mealsense-voice-samples/voice-samples/. Listen, then: VOICE=<name> ./demo/run.sh"
  exit 0
fi

if [ "$STEP" = all ]; then
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
fi

# 1. The voice first, so every scene can be timed to its line.
if [ "$STEP" != record ] || [ ! -f "$HERE/clips/durations.json" ]; then
  voice_image
  echo "==> Speaking the narration ($VOICE)"
  rm -rf "$HERE/clips"
  in_voice "$HERE" speak
fi

# 2. The recording, in Playwright's own container (its browser, fonts and codecs).
echo "==> Recording the tour (about five minutes)"
rm -rf "$HERE/out"
docker run --rm --network host --ipc=host -v "$HERE:/demo" -w /demo \
  -e BASE="$BASE" -e OUT=/demo/out -e THEME="$THEME" -e PHOTOS=/demo/photos \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  bash -c "npm install --no-save --silent playwright@$PLAYWRIGHT >/dev/null && node record.mjs; chown -R $(id -u):$(id -g) /demo/out /demo/node_modules 2>/dev/null || true"

# 3. Assembly: idle stretches tightened, voice, music, subtitles.
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$HOME/mealsense-demo-$STAMP"
mkdir -p "$DEST"
cp -r "$HERE/out/demo.webm" "$HERE/out/scenes.json" "$HERE/narration.json" "$HERE/clips" \
  "$HERE/voice.py" "$HERE/music.py" "$HERE/voice_mac.sh" "$DEST/"
cp "$HERE/photos/CREDITS.md" "$DEST/PHOTO-CREDITS.md" 2>/dev/null || true
voice_image
echo "==> Building the video"
in_voice "$DEST" build
echo
echo "==> Done: $DEST/MealSenseAI-demo.mp4"
echo "    Photo credits (for the description): $DEST/PHOTO-CREDITS.md"
echo "    On your Mac:  scp 'admin@<buddy>:$DEST/MealSenseAI-demo.mp4' ~/Downloads/"
