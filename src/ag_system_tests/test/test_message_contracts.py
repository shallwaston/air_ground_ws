"""Message contract tests for the custom ag_interfaces package."""

from ag_interfaces.msg import DelayProbe
from ag_interfaces.msg import Heartbeat
from ag_interfaces.msg import MapTile
from ag_interfaces.msg import TargetInfo


def test_map_tile_fields_exist() -> None:
    fields = MapTile.get_fields_and_field_types()
    expected = {
        "header",
        "resolution",
        "width",
        "height",
        "origin",
        "elevation",
        "traversability",
        "source_stamp",
        "seq",
    }
    assert expected.issubset(fields.keys())


def test_target_info_fields_exist() -> None:
    fields = TargetInfo.get_fields_and_field_types()
    expected = {"header", "target_id", "pose", "confidence"}
    assert expected.issubset(fields.keys())


def test_heartbeat_fields_exist() -> None:
    fields = Heartbeat.get_fields_and_field_types()
    expected = {"header", "node_name", "role", "status", "detail"}
    assert expected.issubset(fields.keys())


def test_delay_probe_fields_exist() -> None:
    fields = DelayProbe.get_fields_and_field_types()
    expected = {"header", "seq", "source_stamp", "payload_bytes"}
    assert expected.issubset(fields.keys())
