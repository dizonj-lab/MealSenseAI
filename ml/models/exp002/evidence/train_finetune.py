import csv
import hashlib
import json
import os
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import precision_recall_fscore_support
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm


ROOT = Path.home() / "development/mealsenseai"
EXPERIMENT = "EXP-002_FineTuning"
EVIDENCE = ROOT / "evidence" / EXPERIMENT
EVIDENCE.mkdir(parents=True, exist_ok=True)

MANIFEST = ROOT / "datasets/training_manifest_clean.csv"
SOURCE_CHECKPOINT = ROOT / "evidence/EXP-001_UnifiedFood/best_model.pth"

CONFIG = {
    "experiment": EXPERIMENT,
    "model": "efficientnet_b0",
    "initial_checkpoint": str(SOURCE_CHECKPOINT),
    "classes": 320,
    "epochs": 5,
    "batch_size": 32,
    "backbone_learning_rate": 1e-5,
    "classifier_learning_rate": 5e-5,
    "weight_decay": 1e-4,
    "seed": 42,
    "image_size": 224,
    "num_workers": 8,
    "training_strategy": "partial_backbone_finetuning",
    "unfrozen_feature_blocks": 3,
    "augmentation": {
        "rotation": 20,
        "horizontal_flip": 0.5,
        "crop_scale": [0.8, 1.0],
        "brightness": 0.2,
        "contrast": 0.2,
        "saturation": 0.2,
        "hue": 0.05,
    },
}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class FoodDataset(Dataset):
    def __init__(self, dataframe, transform, path_column, label_column):
        self.paths = dataframe[path_column].astype(str).tolist()
        self.labels = dataframe[label_column].astype(int).tolist()
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        path = Path(self.paths[index])
        if not path.is_absolute():
            path = ROOT / path

        with Image.open(path) as img:
            image = img.convert("RGB")

        return self.transform(image), self.labels[index]


def detect_column(df, candidates, purpose):
    for name in candidates:
        if name in df.columns:
            return name
    raise ValueError(
        f"Cannot identify {purpose} column. "
        f"Available columns: {list(df.columns)}"
    )


def load_manifest():
    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    df = pd.read_csv(MANIFEST)

    path_column = detect_column(
        df,
        ["filepath", "file_path", "image_path", "path"],
        "image path",
    )
    label_column = detect_column(
        df,
        ["class_id", "label_id", "canonical_id", "label_index"],
        "numeric class label",
    )
    split_column = detect_column(
        df,
        ["split", "dataset_split"],
        "split",
    )

    df[split_column] = df[split_column].astype(str).str.lower()

    train_df = df[df[split_column] == "train"].copy()
    val_df = df[df[split_column].isin(["val", "validation"])].copy()

    if train_df.empty or val_df.empty:
        raise ValueError(
            "Training or validation split is empty. "
            f"Split values: {df[split_column].value_counts().to_dict()}"
        )

    all_labels = df[label_column].astype(int)
    unique_labels = sorted(all_labels.unique().tolist())

    if unique_labels != list(range(CONFIG["classes"])):
        raise ValueError(
            "Class IDs must be contiguous integers from 0 to 319. "
            f"Found {len(unique_labels)} classes, "
            f"minimum={min(unique_labels)}, maximum={max(unique_labels)}."
        )

    return train_df, val_df, path_column, label_column


def build_transforms():
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )

    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(
            224,
            scale=(0.8, 1.0),
            ratio=(0.9, 1.1),
        ),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(20),
        transforms.ColorJitter(
            brightness=0.2,
            contrast=0.2,
            saturation=0.2,
            hue=0.05,
        ),
        transforms.ToTensor(),
        normalize,
    ])

    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ])

    return train_transform, val_transform


def load_source_state_dict():
    if not SOURCE_CHECKPOINT.exists():
        raise FileNotFoundError(
            f"EXP-001 checkpoint not found: {SOURCE_CHECKPOINT}"
        )

    checkpoint = torch.load(
        SOURCE_CHECKPOINT,
        map_location="cpu",
        weights_only=True,
    )

    if not isinstance(checkpoint, dict):
        raise TypeError("Checkpoint must contain a state dictionary.")

    if "model_state_dict" in checkpoint:
        return checkpoint["model_state_dict"]

    if "state_dict" in checkpoint:
        return checkpoint["state_dict"]

    return checkpoint


def build_model(device):
    print("Loading EXP-001 EfficientNet-B0 checkpoint...", flush=True)

    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(
        in_features,
        CONFIG["classes"],
    )

    state_dict = load_source_state_dict()
    model.load_state_dict(state_dict, strict=True)

    # Freeze the entire feature extractor.
    for parameter in model.features.parameters():
        parameter.requires_grad = False

    # Fine-tune only the final three feature blocks.
    feature_blocks = list(model.features.children())

    for block in feature_blocks[-CONFIG["unfrozen_feature_blocks"]:]:
        for parameter in block.parameters():
            parameter.requires_grad = True

    # Keep the classification head trainable.
    for parameter in model.classifier.parameters():
        parameter.requires_grad = True

    model = model.to(device)

    backbone_parameters = [
        p for p in model.features.parameters() if p.requires_grad
    ]

    optimizer = torch.optim.AdamW(
        [
            {
                "params": backbone_parameters,
                "lr": CONFIG["backbone_learning_rate"],
            },
            {
                "params": model.classifier.parameters(),
                "lr": CONFIG["classifier_learning_rate"],
            },
        ],
        weight_decay=CONFIG["weight_decay"],
    )

    trainable = sum(
        p.numel() for p in model.parameters() if p.requires_grad
    )
    total = sum(p.numel() for p in model.parameters())

    print(
        f"Trainable parameters: {trainable:,} / {total:,}",
        flush=True,
    )

    return model, optimizer


def set_training_mode(model):
    model.train()

    # Frozen feature blocks must not update BatchNorm statistics.
    feature_blocks = list(model.features.children())
    frozen_blocks = feature_blocks[:-CONFIG["unfrozen_feature_blocks"]]

    for block in frozen_blocks:
        block.eval()


def run_training_epoch(model, loader, optimizer, criterion, device, epoch):
    set_training_mode(model)

    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    progress = tqdm(
        loader,
        desc=f"Epoch {epoch}/{CONFIG['epochs']}",
        dynamic_ncols=True,
    )

    for images, labels in progress:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        outputs = model(images)
        loss = criterion(outputs, labels)

        loss.backward()
        optimizer.step()

        batch_size = labels.size(0)
        total_samples += batch_size
        total_loss += loss.item() * batch_size
        total_correct += (
            outputs.argmax(dim=1) == labels
        ).sum().item()

        progress.set_postfix(
            loss=f"{total_loss / total_samples:.4f}",
            acc=f"{total_correct / total_samples:.4f}",
        )

    return (
        total_loss / total_samples,
        total_correct / total_samples,
        total_samples,
    )


@torch.inference_mode()
def run_validation(model, loader, criterion, device):
    model.eval()

    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    predictions = []
    targets = []

    for images, labels in tqdm(
        loader,
        desc="Validation",
        dynamic_ncols=True,
    ):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        outputs = model(images)
        loss = criterion(outputs, labels)

        batch_size = labels.size(0)
        total_samples += batch_size
        total_loss += loss.item() * batch_size
        total_correct += (
            outputs.argmax(dim=1) == labels
        ).sum().item()

        predictions.extend(
            outputs.argmax(dim=1).cpu().tolist()
        )
        targets.extend(labels.cpu().tolist())

    precision, recall, f1, _ = precision_recall_fscore_support(
        targets,
        predictions,
        labels=list(range(CONFIG["classes"])),
        average="macro",
        zero_division=0,
    )

    return {
        "val_loss": total_loss / total_samples,
        "val_accuracy": total_correct / total_samples,
        "val_precision_macro": float(precision),
        "val_recall_macro": float(recall),
        "val_f1_macro": float(f1),
        "validation_samples": total_samples,
    }


def save_checkpoint(model, epoch, metric):
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "epoch": epoch,
            "validation_macro_f1": metric,
            "model_name": CONFIG["model"],
            "num_classes": CONFIG["classes"],
            "source_experiment": "EXP-001_UnifiedFood",
        },
        EVIDENCE / "best_model.pth",
    )


def main():
    seed_everything(CONFIG["seed"])

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is unavailable. EXP-002 requires the NVIDIA GPU."
        )

    device = torch.device("cuda")
    torch.backends.cudnn.benchmark = True

    CONFIG["device"] = torch.cuda.get_device_name(0)
    save_json(EVIDENCE / "config.json", CONFIG)

    environment = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": __import__("torchvision").__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "gpu_total_memory_gb": round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3,
            3,
        ),
        "source_checkpoint_sha256": sha256_file(SOURCE_CHECKPOINT),
        "training_manifest_sha256": sha256_file(MANIFEST),
    }
    save_json(EVIDENCE / "environment.json", environment)

    train_df, val_df, path_column, label_column = load_manifest()

    train_transform, val_transform = build_transforms()

    train_dataset = FoodDataset(
        train_df,
        train_transform,
        path_column,
        label_column,
    )
    val_dataset = FoodDataset(
        val_df,
        val_transform,
        path_column,
        label_column,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        num_workers=CONFIG["num_workers"],
        pin_memory=True,
        persistent_workers=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        num_workers=CONFIG["num_workers"],
        pin_memory=True,
        persistent_workers=True,
    )

    model, optimizer = build_model(device)
    criterion = nn.CrossEntropyLoss()

    print(
        f"Training images: {len(train_dataset):,}\n"
        f"Validation images: {len(val_dataset):,}\n"
        f"GPU: {CONFIG['device']}",
        flush=True,
    )

    history = []
    best_f1 = -1.0
    start = time.perf_counter()

    for epoch in range(1, CONFIG["epochs"] + 1):
        epoch_start = time.perf_counter()
        torch.cuda.reset_peak_memory_stats()

        train_loss, train_accuracy, train_samples = run_training_epoch(
            model,
            train_loader,
            optimizer,
            criterion,
            device,
            epoch,
        )

        validation = run_validation(
            model,
            val_loader,
            criterion,
            device,
        )

        torch.cuda.synchronize()
        epoch_seconds = time.perf_counter() - epoch_start

        result = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_accuracy,
            **validation,
            "epoch_seconds": epoch_seconds,
            "train_images_per_second": train_samples / epoch_seconds,
            "peak_gpu_memory_gb": (
                torch.cuda.max_memory_allocated() / 1024**3
            ),
        }

        history.append(result)

        pd.DataFrame(history).to_csv(
            EVIDENCE / "training_history.csv",
            index=False,
        )

        print(json.dumps(result, indent=2), flush=True)

        if result["val_f1_macro"] > best_f1:
            best_f1 = result["val_f1_macro"]
            save_checkpoint(model, epoch, best_f1)
            print("Best model checkpoint saved.", flush=True)

    total_seconds = time.perf_counter() - start

    summary = {
        "experiment": EXPERIMENT,
        "source_experiment": "EXP-001_UnifiedFood",
        "total_training_seconds": total_seconds,
        "best_validation_macro_f1": best_f1,
        "best_epoch": max(
            history,
            key=lambda row: row["val_f1_macro"],
        )["epoch"],
        "epochs_completed": len(history),
        "training_images": len(train_dataset),
        "validation_images": len(val_dataset),
    }

    save_json(EVIDENCE / "summary.json", summary)

    print("\nTRAINING COMPLETED", flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
