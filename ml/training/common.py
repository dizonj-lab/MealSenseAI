"""Shared helpers for the dataset and training pipeline."""
import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path = ROOT / "ml/training/config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def resolve(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def norm_label(raw: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", raw.strip().lower())).strip("_")


def sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def dataset_dir(cfg: dict) -> Path:
    d = cfg["dataset"]
    return resolve(d["output_dir"]) / f"{d['name']}-v{d['version']}"
