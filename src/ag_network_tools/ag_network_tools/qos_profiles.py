"""Helpers for describing and constructing QoS profiles.

The YAML file is the human-readable source of truth, and this module turns it
into rclpy QoSProfile objects. When the YAML is unavailable, safe built-in
defaults keep the mock system runnable.
"""

from __future__ import annotations

from copy import deepcopy
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
    return mapping.get(str(name).lower(), ReliabilityPolicy.RELIABLE)


def _to_durability(name: str) -> DurabilityPolicy:
    mapping = {
        "volatile": DurabilityPolicy.VOLATILE,
        "transient_local": DurabilityPolicy.TRANSIENT_LOCAL,
    }
    return mapping.get(str(name).lower(), DurabilityPolicy.VOLATILE)


def _to_history(name: str) -> HistoryPolicy:
    mapping = {
        "keep_last": HistoryPolicy.KEEP_LAST,
        "keep_all": HistoryPolicy.KEEP_ALL,
    }
    return mapping.get(str(name).lower(), HistoryPolicy.KEEP_LAST)


def profile_from_dict(data: Dict[str, Any]) -> QoSProfile:
    """Construct a QoSProfile from a plain dictionary."""
    profile = QoSProfile(depth=int(data.get("depth", 10)))
    profile.reliability = _to_reliability(data.get("reliability", "reliable"))
    profile.durability = _to_durability(data.get("durability", "volatile"))
    profile.history = _to_history(data.get("history", "keep_last"))
    return profile


def resolve_qos_config_path(preferred_path: Optional[str] = None) -> Optional[Path]:
    """Return the best available QoS config path."""
    if preferred_path:
        candidate = Path(preferred_path).expanduser()
        if candidate.exists():
            return candidate

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


def load_qos_config(preferred_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load the YAML QoS mapping or fall back to built-in defaults."""
    path = resolve_qos_config_path(preferred_path)
    if path is None:
        return deepcopy(DEFAULT_QOS_CONFIG)

    with path.open("r", encoding="utf-8") as stream:
        parsed = yaml.safe_load(stream) or {}

    topics = parsed.get("topics")
    if not isinstance(topics, dict):
        return deepcopy(DEFAULT_QOS_CONFIG)

    merged = deepcopy(DEFAULT_QOS_CONFIG)
    for topic_name, profile in topics.items():
        if isinstance(profile, dict):
            merged["topics"][_normalize_topic_name(topic_name)] = profile
    return merged


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
