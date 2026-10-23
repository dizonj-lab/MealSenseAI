#!/usr/bin/env bash
# Downloads the verified pretrained MediaPipe models (Apache-2.0) used for food recognition.
set -euo pipefail
cd "$(dirname "$0")"
B=https://storage.googleapis.com/mediapipe-models
curl -fsSL -o efficientnet_lite0.tflite $B/image_classifier/efficientnet_lite0/float32/latest/efficientnet_lite0.tflite
curl -fsSL -o efficientdet_lite0.tflite $B/object_detector/efficientdet_lite0/float32/latest/efficientdet_lite0.tflite
ls -la *.tflite
