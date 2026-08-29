"""
Trains (once, fast, CPU-only, seconds not minutes) and caches the two ML
models used by Defend:

- account_takeover_clf: GradientBoostingClassifier on engineered session
  features. Chosen over a GNN for the hackathon build -- see note below.
- generalist: IsolationForest anomaly detector trained across ALL attack
  types' feature space, used as the fallback + novelty sensor.

NOTE ON THE GNN SIMPLIFICATION: the original design called for a graph
neural network over the transaction network to catch mule-account chains.
PyTorch Geometric adds a multi-GB dependency chain and needs a labeled
graph dataset to train meaningfully -- neither is available/deployable on
free-tier compute in the hackathon's timeframe. We substitute engineered
graph-adjacent features (device_change, geo_velocity, tx_velocity --
proxies for "this session looks like it's part of a fast-moving takeover
chain") into a gradient-boosted tree, which trains in under a second and
deploys anywhere. Upgrade path documented in README: swap this module's
`predict_account_takeover()` for a PyG model with the same function
signature once you have a labeled transaction graph.
"""
import joblib
from pathlib import Path

from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.model_selection import train_test_split

from app.config import settings
from app.generate.tabular_generator import generate_mixed_dataset

_MODELS_DIR = Path(settings.models_dir)
_MODELS_DIR.mkdir(parents=True, exist_ok=True)
_ATO_MODEL_PATH = _MODELS_DIR / "account_takeover_clf.joblib"
_GENERALIST_MODEL_PATH = _MODELS_DIR / "generalist_iforest.joblib"

_FEATURE_COLS = ["hour_of_day", "device_change", "geo_velocity_kmh",
                  "tx_velocity_10min", "login_failed_attempts", "amount_inr"]


class ModelStore:
    def __init__(self):
        self.ato_model: GradientBoostingClassifier | None = None
        self.generalist_model: IsolationForest | None = None
        self.bootstrap_dataset = None
        self.last_training_metrics: dict = {}
        # Session-scoped only -- resets on server restart, not persisted
        # across deploys. Honest version tracking, not durable MLOps versioning.
        self._ato_train_count = 0
        self._generalist_train_count = 0
        self._load_or_train()

    def _load_or_train(self):
        self.bootstrap_dataset = generate_mixed_dataset()

        if _ATO_MODEL_PATH.exists():
            self.ato_model = joblib.load(_ATO_MODEL_PATH)
            self._eval_ato()
            # Loaded from a cache written by an earlier process/run --
            # still a real, functional model, not "untrained". Counts as
            # version 1 unless this process later retrains it explicitly.
            self._ato_train_count = max(self._ato_train_count, 1)
        else:
            self.ato_model = self._train_ato()
            joblib.dump(self.ato_model, _ATO_MODEL_PATH)

        if _GENERALIST_MODEL_PATH.exists():
            self.generalist_model = joblib.load(_GENERALIST_MODEL_PATH)
            self._eval_generalist()
            self._generalist_train_count = max(self._generalist_train_count, 1)
        else:
            self.generalist_model = self._train_generalist()
            joblib.dump(self.generalist_model, _GENERALIST_MODEL_PATH)

    def _train_ato(self) -> GradientBoostingClassifier:
        df = self.bootstrap_dataset.copy()
        df["is_ato"] = (df["attack_id"] == "account_takeover").astype(int)
        X = df[_FEATURE_COLS]
        y = df["is_ato"]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        clf = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=42)
        clf.fit(X_train, y_train)
        self._score_ato(clf, X_test, y_test)
        self._ato_train_count += 1
        return clf

    def _score_ato(self, clf, X_test, y_test):
        from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)[:, 1]
        tn, fp, fn, tp = confusion_matrix(y_test, preds, labels=[0, 1]).ravel()
        # False-positive rate on LEGITIMATE traffic specifically -- the
        # challenge brief explicitly says "keep false positives on
        # legitimate payments low," so this gets its own named metric
        # rather than being buried inside overall precision.
        fpr_on_legit = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        self.last_training_metrics["account_takeover"] = {
            "precision": round(float(precision_score(y_test, preds)), 3),
            "recall": round(float(recall_score(y_test, preds)), 3),
            "f1": round(float(f1_score(y_test, preds)), 3),
            "auc": round(float(roc_auc_score(y_test, probs)), 3),
            "false_positive_rate_on_legit": round(float(fpr_on_legit), 4),
        }

    def _eval_ato(self):
        """Recompute metrics for a model loaded from disk (no retrain)."""
        df = self.bootstrap_dataset.copy()
        df["is_ato"] = (df["attack_id"] == "account_takeover").astype(int)
        X = df[_FEATURE_COLS]
        y = df["is_ato"]
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        self._score_ato(self.ato_model, X_test, y_test)

    def _train_generalist(self) -> IsolationForest:
        df = self.bootstrap_dataset
        X = df[_FEATURE_COLS]
        model = IsolationForest(n_estimators=150, contamination=0.25, random_state=42)
        model.fit(X)
        self._score_generalist(model, X, df["label"].values)
        self._generalist_train_count += 1
        return model

    def _score_generalist(self, model, X, y_true):
        from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
        raw_preds = model.predict(X)  # -1 = anomaly, 1 = normal
        preds = (raw_preds == -1).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, preds, labels=[0, 1]).ravel()
        fpr_on_legit = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        self.last_training_metrics["generalist"] = {
            "precision": round(float(precision_score(y_true, preds)), 3),
            "recall": round(float(recall_score(y_true, preds)), 3),
            "f1": round(float(f1_score(y_true, preds)), 3),
            "false_positive_rate_on_legit": round(float(fpr_on_legit), 4),
        }

    def _eval_generalist(self):
        df = self.bootstrap_dataset
        X = df[_FEATURE_COLS]
        self._score_generalist(self.generalist_model, X, df["label"].values)

    def predict_account_takeover(self, features: dict) -> float:
        import pandas as pd
        row = pd.DataFrame([[features.get(c, 0) for c in _FEATURE_COLS]], columns=_FEATURE_COLS)
        return float(self.ato_model.predict_proba(row)[0][1])

    def predict_generalist(self, features: dict) -> tuple[float, bool]:
        import pandas as pd
        row = pd.DataFrame([[features.get(c, 0) for c in _FEATURE_COLS]], columns=_FEATURE_COLS)
        raw_score = self.generalist_model.decision_function(row)[0]  # lower = more anomalous
        is_anomaly = self.generalist_model.predict(row)[0] == -1
        # squash decision_function (~[-0.5, 0.5]) into a 0-1 risk score
        risk = float(max(0.0, min(1.0, 0.5 - raw_score)))
        return risk, bool(is_anomaly)

    def retrain_generalist(self):
        """Called by the feedback loop after new taxonomy entries are
        added, so the generalist's feature space stays current."""
        self.bootstrap_dataset = generate_mixed_dataset()
        self.generalist_model = self._train_generalist()
        joblib.dump(self.generalist_model, _GENERALIST_MODEL_PATH)

    def model_version(self, which: str) -> str:
        count = self._ato_train_count if which == "account_takeover" else self._generalist_train_count
        return f"session-v{count}" if count else "untrained"


model_store = ModelStore()
