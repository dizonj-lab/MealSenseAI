#!/usr/bin/env bash
# NVIDIA Container Toolkit so Docker (Ollama) and training can use the RTX GPU.
#   sudo ./setup-gpu.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
if ! nvidia-smi >/dev/null 2>&1; then
  echo "NVIDIA driver not working. RTX 50-series needs driver 570+ (open kernel modules):"
  echo "  sudo ubuntu-drivers install --gpgpu   (or: sudo apt install nvidia-driver-570-open) && sudo reboot"
  exit 1
fi
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update -q && apt-get install -y -q nvidia-container-toolkit >/dev/null
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L && echo "GPU available to Docker"
