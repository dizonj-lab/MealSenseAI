# Admin area

The admin area (menu → **Admin**, admins only) holds everything needed to learn safely from users' photos and to change
the app's behaviour without a code change. Every admin route is checked on the server; every change is written to the
audit log.

| Tab | What it is for |
|---|---|
| Training data review | Samples waiting for a person: flagged by the checks, or picked for the random audit. Accept or reject, singly or in bulk. |
| Contributors | Who shared what: trust level, share of each food, samples this week. Verify an email by hand, suspend or reactivate. |
| Dataset versions | Freeze the eligible samples into a named version (e.g. `EXP-003`), see its lineage, roll back one contributor, export. |
| Models & updates | The live model, the model updates location (upload a package), and the model gate: checks, shadow mode, promote, roll back. |
| Model settings | Recognition thresholds, the local language model, the training-data checks and the gate's tolerances. |
| Prompts | The local model's prompts, versioned. |
| Audit log | Every admin action, setting and prompt change, and every consent change. |

## First-time setup (on Buddy)

```bash
cd ~/development/mealsenseai-mvp && git pull
docker compose up -d --build frontend backend          # runs migration 0007
docker compose exec backend python -m app.tools.admin grant joel.dizon@live.com
docker compose exec backend python -m app.tools.admin list
```

The role is granted only by this server command, never through the API or by email address alone, so nobody can make
themselves an admin by signing up with an admin's address. Revoke with `... app.tools.admin revoke <email>`; it takes
effect on the next request. Granting also marks that email as verified.

Optional second lock: put `/admin` and `/api/v1/admin` behind Cloudflare Access (free for small teams), allowing only
your own email. Requests then need both your Cloudflare login and the admin role.

Email verification links need SMTP (`SMTP_HOST` etc. in `.env`, the same settings as the contact form) and
`PUBLIC_URL=https://mealsense.xtangent.ai`. Without SMTP, verify an address by hand in **Contributors → Verify**.

## How a photo becomes training data

1. A user names, corrects or confirms a food from a photo → a sample is recorded (it also powers their personal memory).
2. It is **shared** only while the user's training consent is on. Switching consent off withdraws all their samples
   from every future dataset version and export.
3. It is **screened** when recorded, and again in a batch (Run all checks again, and before freezing):

   | Check | Effect |
   |---|---|
   | Same photo and label as the person's own earlier sample | rejected |
   | Photo missing | rejected |
   | Implausible label: the model was sure (≥ 60%) and the new label is not in its top three | flagged |
   | Carbohydrate safety: relabels a ≥ 15 g/100 g food to under half its carbohydrate | flagged |
   | Same photo from another account; near-identical crops with one label from 3+ accounts (a possible planted trigger) | flagged |
   | No food seen (whole photo, model below 15%) | flagged |
   | New account (under 72 h) | flagged |
   | One contributor over 5% of a food's examples (foods with 20+) | flagged |
   | More than 60 samples in 7 days | flagged |
   | Outlier: far from the average of its food | flagged |
   | Only confirmed the model's own guess | noted; weighted 0.5 in exports |

   A clean sample may still be picked for the random audit (5%). All numbers are in **Model settings → Training data checks**.
4. **Eligible** for a dataset version: shared, from a verified and active contributor, and approved by a person or
   passed (and not awaiting audit).
5. **Freeze** a version in Dataset versions. It never changes; the manifest lists its sample ids, counts, contributors
   (pseudonyms) and the settings in force. The base datasets (Food-101, FoodSG-233) are fixed and kept separate.
6. **Export** on the server, then train on the GPU machine:

   ```bash
   docker compose exec backend python -m app.tools.export_dataset EXP-003
   docker compose cp backend:/data/exports/EXP-003 datasets/raw/user_labels
   ```

   Anything withdrawn or deleted since freezing is left out and counted in `summary.json`.

## Releasing a new model (the gate)

1. Train (ml/training) with the exported version, and export the model to ONNX with its `class_mapping.json` and
   `model_card.json` (as in `ml/models/exp002/`).
2. Evaluate it against the live model on the **fixed gate test set**, a folder per class built once from a training
   run's held-out split, never containing user data:

   ```bash
   python ml/evaluation/gate_report.py --candidate path/to/EXP-003 --test-dir datasets/gate_test \
       --name EXP-003 --dataset-version EXP-003
   ```

   This writes `report.json` into the candidate folder: overall top-1 and the safety groups (rice, noodles, sweet
   drinks; `ml/evaluation/safety_classes.json`) for both models, and the test set's SHA-256. The test set must include
   classes from all three groups: a group the report does not measure fails the gate.
3. **Upload** the four files in Models & updates. The package must load and be self-consistent before it is accepted;
   it is stored in the model updates location (`/data/models/<name>/`, inside the photo volume).
4. The **gate** checks: overall accuracy no lower than the live model (tolerance 0.2 points), each safety group no lower
   (tolerance 0), and the same test set as every earlier candidate. Tolerances are in Model settings.
5. **Shadow mode**: the candidate classifies every food beside the live model, unseen by users; agreement and the most
   common disagreements are counted.
6. **Promote** (needs a passed gate, 200 foods compared and 90% agreement): the candidate becomes the live model at once,
   with no rebuild, and stays live across restarts. **Use the built-in model** rolls back immediately.

## Settings and prompts

Settings take effect within ten seconds for every user and need no restart. Each shows its default and range; Reset
returns to the default.

Prompts shape the local model's wording only. Every Meal Advisor reply is still checked: each number must come from the
user's data or the food table, no new foods may appear, unsafe advice is blocked, and otherwise the rule engine's own
answer is shown. Saving creates a new version; any version, or the built-in default, can be made active again.
