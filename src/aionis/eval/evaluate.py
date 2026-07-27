"""Cross-validation runner: OOS predictions + per-model metrics.

Runs purged, embargoed walk-forward CV. This is an EXPANDING window: the earliest
block has no training history and is never tested, but every other row lands in
exactly one test fold. The OOS predictions are a clean out-of-sample series used
for the with-vs-without comparison and the Diebold-Mariano test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aionis.eval.cv import purged_walk_forward_splits
from aionis.eval.metrics import directional_accuracy, mae, mse, up_baseline
from aionis.features.design_matrix import DesignMatrix


@dataclass
class CVResult:
    oos: pd.DataFrame  # one row per OOS sample: y_true, group, <model_name>...
    metrics: pd.DataFrame  # index=model_name, columns=[DA, up_baseline, MAE, MSE, n]

    def losses(self, model_name: str) -> np.ndarray:
        """Squared-error losses for a model over its OOS predictions."""
        err = self.oos[model_name].to_numpy(float) - self.oos["y_true"].to_numpy(float)
        return err * err


def cross_validate(
    dm: DesignMatrix,
    models: dict[str, callable],
    n_splits: int = 5,
    embargo: pd.Timedelta | None = None,
    horizon: int = 1,
) -> CVResult:
    if embargo is None:
        embargo = pd.Timedelta(days=max(1, horizon))

    splits = purged_walk_forward_splits(
        dm.prediction_times, dm.evaluation_times, n_splits=n_splits, embargo=embargo
    )

    # Collect OOS predictions keyed by global row position (each row in one fold).
    oos_preds: dict[int, dict] = {}
    for split in splits:
        Xtr, ytr = dm.X.iloc[split.train_idx], dm.y.iloc[split.train_idx]
        Xte = dm.X.iloc[split.test_idx]
        for name, fn in models.items():
            preds = fn(Xtr, ytr, Xte)
            for j, row_pos in enumerate(split.test_idx):
                slot = oos_preds.setdefault(int(row_pos), {})
                slot["y_true"] = float(dm.y.iloc[row_pos])
                slot["group"] = dm.groups.iloc[row_pos]
                slot["event_id"] = dm.metadata.iloc[row_pos]["event_id"]
                slot["symbol"] = dm.metadata.iloc[row_pos]["symbol"]
                slot["prediction_time"] = dm.metadata.iloc[row_pos]["prediction_time"]
                slot["evaluation_time"] = dm.metadata.iloc[row_pos]["evaluation_time"]
                slot[name] = float(preds[j])

    rows = [oos_preds[k] for k in sorted(oos_preds)]
    oos = pd.DataFrame(rows).reset_index(drop=True)

    metric_rows = []
    y_true = oos["y_true"].to_numpy(float)
    for name in models:
        pred = oos[name].to_numpy(float)
        metric_rows.append(
            {
                "model": name,
                "DA": directional_accuracy(y_true, pred),
                "up_baseline": up_baseline(y_true),
                "MAE": mae(y_true, pred),
                "MSE": mse(y_true, pred),
                "n": len(y_true),
            }
        )
    metrics = pd.DataFrame(metric_rows).set_index("model")
    return CVResult(oos=oos, metrics=metrics)
