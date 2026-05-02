"""Eval metrics：precision / recall / f1 纯函数。"""
from __future__ import annotations

from typing import Iterable


def compute_precision_recall_f1(
    predicted: Iterable, groundtruth: Iterable,
) -> dict:
    p_set = set(predicted)
    g_set = set(groundtruth)
    tp = len(p_set & g_set)
    fp = len(p_set - g_set)
    fn = len(g_set - p_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
