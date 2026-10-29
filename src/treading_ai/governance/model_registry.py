"""Model Registry and Governance Engine for Treading-AI.

Provides immutable model versioning, artifact serialization, lineage tracking,
challenger registration, and audited rollback capability.
"""

from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
from pathlib import Path
import pickle
from typing import Any, Dict, List, Optional, Union

from treading_ai.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_DIR = PROJECT_ROOT / "models" / "registry"


@dataclass
class ModelMetadata:
    """Metadata describing a registered model version."""
    model_version: str
    model_class: str
    feature_names: List[str]
    hyperparameters: Dict[str, Any]
    created_at: str
    status: str  # 'INCUMBENT', 'CHALLENGER', 'REJECTED', 'ARCHIVED'
    promoted_at: Optional[str] = None
    promotion_reason: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    parent_version: Optional[str] = None
    hypothesis_tested: Optional[str] = None


class ModelRegistry:
    """Manages model artifacts, metadata, promotion gates, and rollback."""

    def __init__(self, registry_dir: Union[str, Path] = DEFAULT_REGISTRY_DIR):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.registry_dir / "registry_index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load registry index from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read registry index: %s. Creating new index.", e)
        return {}

    def _save_index(self) -> None:
        """Atomically persist registry index to disk."""
        temp_file = self.metadata_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)
        temp_file.replace(self.metadata_file)

    def register_model(
        self,
        model_version: str,
        model_obj: Any,
        model_class: str,
        feature_names: List[str],
        hyperparameters: Dict[str, Any],
        status: str = "CHALLENGER",
        performance_metrics: Optional[Dict[str, Any]] = None,
        parent_version: Optional[str] = None,
        hypothesis_tested: Optional[str] = None,
    ) -> ModelMetadata:
        """
        Register a new model artifact with immutable metadata.

        Returns:
            ModelMetadata instance.
        """
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        artifact_path = self.registry_dir / f"{model_version}.pkl"

        # Serialize model object
        with open(artifact_path, "wb") as f:
            pickle.dump(model_obj, f)

        meta = ModelMetadata(
            model_version=model_version,
            model_class=model_class,
            feature_names=feature_names,
            hyperparameters=hyperparameters,
            created_at=now_str,
            status=status,
            performance_metrics=performance_metrics or {},
            parent_version=parent_version,
            hypothesis_tested=hypothesis_tested,
        )

        self._index[model_version] = asdict(meta)
        self._save_index()
        logger.info("Registered model '%s' (status: %s)", model_version, status)
        return meta

    def get_model(self, model_version: str) -> Tuple[Any, ModelMetadata]:
        """Load model object and its metadata."""
        if model_version not in self._index:
            raise KeyError(f"Model '{model_version}' not registered in registry!")

        meta_dict = self._index[model_version]
        meta = ModelMetadata(**meta_dict)

        artifact_path = self.registry_dir / f"{model_version}.pkl"
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact file '{artifact_path}' missing!")

        with open(artifact_path, "rb") as f:
            model_obj = pickle.load(f)

        return model_obj, meta

    def get_incumbent(self) -> Optional[ModelMetadata]:
        """Find the currently active INCUMBENT model."""
        for version, meta_dict in self._index.items():
            if meta_dict.get("status") == "INCUMBENT":
                return ModelMetadata(**meta_dict)
        return None

    def promote_challenger(self, challenger_version: str, justification: str) -> ModelMetadata:
        """
        Promote a validated CHALLENGER to INCUMBENT.
        Archives the prior incumbent and writes audit justification.
        """
        if challenger_version not in self._index:
            raise KeyError(f"Challenger '{challenger_version}' not found in registry!")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Archive existing incumbent
        for ver, meta_dict in self._index.items():
            if meta_dict.get("status") == "INCUMBENT":
                meta_dict["status"] = "ARCHIVED"
                logger.info("Archived previous incumbent '%s'", ver)

        # Promote challenger
        chal_meta = self._index[challenger_version]
        chal_meta["status"] = "INCUMBENT"
        chal_meta["promoted_at"] = now_str
        chal_meta["promotion_reason"] = justification
        self._save_index()
        logger.info("Promoted challenger '%s' to INCUMBENT: %s", challenger_version, justification)
        return ModelMetadata(**chal_meta)

    def reject_challenger(self, challenger_version: str, rejection_reason: str) -> ModelMetadata:
        """Record rejection of a challenger model with specific failure reason."""
        if challenger_version not in self._index:
            raise KeyError(f"Challenger '{challenger_version}' not found in registry!")

        chal_meta = self._index[challenger_version]
        chal_meta["status"] = "REJECTED"
        chal_meta["promotion_reason"] = f"REJECTED: {rejection_reason}"
        self._save_index()
        logger.info("Rejected challenger '%s': %s", challenger_version, rejection_reason)
        return ModelMetadata(**chal_meta)

    def rollback(self, target_version: str, rollback_reason: str) -> ModelMetadata:
        """
        Roll back incumbent status to an earlier registered model version.
        """
        if target_version not in self._index:
            raise KeyError(f"Target rollback version '{target_version}' not in registry!")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Archive current incumbent
        for ver, meta_dict in self._index.items():
            if meta_dict.get("status") == "INCUMBENT":
                meta_dict["status"] = "ARCHIVED"
                logger.info("Archived current incumbent '%s' during rollback", ver)

        target_meta = self._index[target_version]
        target_meta["status"] = "INCUMBENT"
        target_meta["promoted_at"] = now_str
        target_meta["promotion_reason"] = f"ROLLBACK to {target_version}: {rollback_reason}"
        self._save_index()
        logger.warning("Rolled back incumbent to '%s': %s", target_version, rollback_reason)
        return ModelMetadata(**target_meta)

    def list_models(self) -> List[ModelMetadata]:
        """Return all registered models as a list of ModelMetadata."""
        return [ModelMetadata(**m) for m in self._index.values()]
