"""Helpers for describing and constructing QoS profiles.

The YAML file is the human-readable source of truth, and this module turns it
into rclpy QoSProfile objects. When the YAML is unavailable, safe built-in
defaults keep the mock system runnable.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy

from ag_network_tools import topic_names


DEFAULT_QOS_CONFIG: Dict[str, Dict[str, Any]] = {
    "topics": {
        topic_names.UAV_MAP_TILE_TOPIC: {
            "reliability": "reliable",
            "durability": "transient_local",
            "history": "keep_last",
            "depth": 5,
        },
        topic_names.UAV_TARGET_TOPIC: {
            "reliability": "reliable",
            "durability": "transient_local",
            "history": "keep_last",
            "depth": 10,
        },
        topic_names.UAV_ODOM_TOPIC: {
            "reliability": "best_effort",
            "durability": "volatile",
            "history": "keep_last",
            "depth": 20,
        },
        topic_names.TF_TOPIC: {
            "reliability": "best_effort",
            "durability": "volatile",
            "history": "keep_last",
            "depth": 50,
        },
        topic_names.TF_STATIC_TOPIC: {
            "reliability": "reliable",
            "durability": "transient_local",
            "history": "keep_last",
            "depth": 1,
        },
        topic_names.DELAY_PROBE_TOPIC: {
            "reliability": "reliable",
            "durability": "volatile",
            "history": "keep_last",
            "depth": 20,
        },
        topic_names.DELAY_REPORT_TOPIC: {
            "reliability": "reliable",
            "durability": "volatile",
            "history": "keep_last",
            "depth": 20,
        },
        topic_names.HEARTBEAT_TOPIC: {
            "reliability": "reliable",
            "durability": "volatile",
            "history": "keep_last",
            "depth": 20,
        },
    }
}


def _normalize_topic_name(topic_name: str) -> str:
    if topic_name.startswith("/"):
        return topic_name
    return f"/{topic_name}"


def _to_reliability(name: str) -> ReliabilityPolicy:
    mapping = {
        "reliable": ReliabilityPolicy.RELIABLE,
        "best_effort": ReliabilityPolicy.BEST_EFFORT,
    }
    try:
        return mapping[str(name).lower()]
    except KeyError as exc:
        raise ValueError(f'Unknown QoS reliability: {name!r}') from exc


def _to_durability(name: str) -> DurabilityPolicy:
    mapping = {
        "volatile": DurabilityPolicy.VOLATILE,
        "transient_local": DurabilityPolicy.TRANSIENT_LOCAL,
    }
    try:
        return mapping[str(name).lower()]
    except KeyError as exc:
        raise ValueError(f'Unknown QoS durability: {name!r}') from exc


def _to_history(name: str) -> HistoryPolicy:
    mapping = {
        "keep_last": HistoryPolicy.KEEP_LAST,
        "keep_all": HistoryPolicy.KEEP_ALL,
    }
    try:
        return mapping[str(name).lower()]
    except KeyError as exc:
        raise ValueError(f'Unknown QoS history: {name!r}') from exc


def profile_from_dict(data: Dict[str, Any]) -> QoSProfile:
    """Construct a QoSProfile from a plain dictionary."""
    depth = data.get('depth', 10)
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ValueError('QoS depth must be an integer')
    history = _to_history(data.get('history', 'keep_last'))
    if depth < 0 or (history == HistoryPolicy.KEEP_LAST and depth == 0):
        raise ValueError('QoS depth must be positive for keep_last and nonnegative for keep_all')
    return QoSProfile(
        depth=depth, history=history,
        reliability=_to_reliability(data.get('reliability', 'reliable')),
        durability=_to_durability(data.get('durability', 'volatile')))


def resolve_qos_config_path(preferred_path: Optional[str] = None) -> Optional[Path]:
    """Return the best available QoS config path."""
    preferred_path = preferred_path or os.environ.get('AG_QOS_CONFIG_PATH')
    if preferred_path:
        candidate = Path(preferred_path).expanduser()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f'QoS config not found: {candidate}')

    try:
        share_dir = Path(get_package_share_directory("ag_bringup"))
        candidate = share_dir / "config" / "qos_profiles.yaml"
        if candidate.exists():
            return candidate
    except PackageNotFoundError:
        pass

    local_candidate = Path.cwd() / "config" / "qos" / "qos_profiles.yaml"
    if local_candidate.exists():
        return local_candidate

    return None


@lru_cache(maxsize=16)
def _load_qos_config(path: Path, mtime_ns: int, size: int) -> Dict[str, Dict[str, Any]]:
    """Cache parsed settings, invalidating on path/mtime/size changes."""
    with path.open("r", encoding="utf-8") as stream:
        parsed = yaml.safe_load(stream)
    if parsed is None:
        return deepcopy(DEFAULT_QOS_CONFIG)
    if not isinstance(parsed, dict):
        raise ValueError(f'QoS config must be a mapping: {path}')

    topics = parsed.get("topics", {})
    if not isinstance(topics, dict):
        raise ValueError(f'QoS topics must be a mapping: {path}')

    merged = deepcopy(DEFAULT_QOS_CONFIG)
    for topic_name, profile in topics.items():
        if not isinstance(topic_name, str) or not isinstance(profile, dict):
            raise ValueError(f'Invalid QoS topic entry: {topic_name!r} in {path}')
        normalized = _normalize_topic_name(topic_name)
        settings = merged['topics'].setdefault(normalized, {})
        settings.update(profile)
        profile_from_dict(settings)  # Fail before creating incompatible endpoints.
    return merged


def load_qos_config(preferred_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load settings, returning a private copy so callers cannot corrupt the cache."""
    path = resolve_qos_config_path(preferred_path)
    if path is None:
        return deepcopy(DEFAULT_QOS_CONFIG)
    path = path.resolve()
    stat = path.stat()
    return deepcopy(_load_qos_config(path, stat.st_mtime_ns, stat.st_size))


def get_qos_profile_for_topic(topic_name: str, preferred_path: Optional[str] = None) -> QoSProfile:
    """Return a QoSProfile for a topic, using defaults when the topic is unknown."""
    config = load_qos_config(preferred_path)
    normalized = _normalize_topic_name(topic_name)
    topic_config = config["topics"].get(normalized, DEFAULT_QOS_CONFIG["topics"][topic_names.HEARTBEAT_TOPIC])
    return profile_from_dict(topic_config)


def describe_qos_for_topic(topic_name: str, preferred_path: Optional[str] = None) -> str:
    """Return a human-friendly description string for a topic QoS policy."""
    config = load_qos_config(preferred_path)
    normalized = _normalize_topic_name(topic_name)
    topic_config = config["topics"].get(normalized)
    if topic_config is None:
        return f"{normalized}: using fallback QoS profile"
    return (
        f"{normalized}: reliability={topic_config.get('reliability', 'reliable')}, "
        f"durability={topic_config.get('durability', 'volatile')}, "
        f"history={topic_config.get('history', 'keep_last')}, "
        f"depth={topic_config.get('depth', 10)}"
    )


def get_all_topic_configs(preferred_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Return all known topic QoS configurations."""
    return load_qos_config(preferred_path)["topics"]
