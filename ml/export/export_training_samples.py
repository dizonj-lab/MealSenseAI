"""Export user-labelled photo regions for the next training cycle: a thin wrapper around the backend's
app.tools.export_dataset, for running outside Docker with the repository's virtual environment.

Only a dataset version frozen in Admin → Datasets can be exported: samples that were shared with consent, from
verified contributors, and passed screening or were approved by a person. Withdrawals since freezing are honoured.

    python ml/export/export_training_samples.py EXP-003 [--out datasets/raw/user_labels]

On the server, prefer:  docker compose exec backend python -m app.tools.export_dataset EXP-003
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.tools.export_dataset import main  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and "--out" not in args:
        args += ["--out", str(ROOT / "datasets/raw/user_labels")]
    sys.exit(main(args))
