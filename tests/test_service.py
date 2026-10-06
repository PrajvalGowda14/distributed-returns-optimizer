import ast
from pathlib import Path

import pytest

from src.privacy import find_restricted_fields
from src.service import DataUnavailableError, ReturnsOptimizationService

ROOT = Path(__file__).resolve().parent.parent


def test_three_nodes(service):
    nodes = service.get_system_status()["nodes"]
    assert len(nodes) == 3 and all(n["connected"] for n in nodes)


def test_analysis_returns_list_with_compatibility(service):
    patterns = service.analyze_patterns()
    assert isinstance(patterns, list) and patterns
    assert any(p["category"] == "Electronics" and p["cause"] == "COMPATIBILITY" for p in patterns)
    assert service.analyze_patterns(signal="High")[0]["cause"] == "COMPATIBILITY"


def test_audit_events_exist(service):
    s = service.get_privacy_audit()["summary"]
    assert s["approved"] > 0 and s["suppressed"] > 0


def test_collective_results_contain_no_restricted_fields(service):
    outputs = [service.get_system_status(), service.analyze_patterns(),
               service.get_pattern_details("Electronics", "COMPATIBILITY"),
               service.build_intervention_plan("Electronics", "COMPATIBILITY", "compat_checker"),
               service.get_privacy_audit()]
    assert find_restricted_fields(outputs) == []


def test_recommendations_for_demo(service):
    assert [i["name"] for i in service.get_pre_purchase_recommendations("COMPATIBILITY")] == [
        "Compatibility checker", "Device-model confirmation", "Supported-model list"]
    post = service.get_post_purchase_recommendations("COMPATIBILITY")
    assert [i["name"] for i in post] == ["Recommend compatible replacement", "Offer one-click exchange",
                                         "Route to technical support"]
    assert all(i["requires_human_approval"] and i["status"] == "DRAFT" for i in post)


def test_plan_requires_approved_pattern(service):
    plan = service.build_intervention_plan("Electronics", "COMPATIBILITY", "compatible_replacement")
    assert plan["requires_human_approval"] is True and plan["success_metric"]
    with pytest.raises(ValueError):
        service.build_intervention_plan("Beauty", "OTHER", "manual_review")


def test_unapproved_pattern_details_not_released(service):
    assert service.get_pattern_details("Beauty", "OTHER")["privacy_status"] == "Not released"


def test_missing_data_handled(tmp_path):
    svc = ReturnsOptimizationService(data_dir=tmp_path)
    assert svc.data_available is False
    assert svc.get_system_status()["approved_patterns"] == 0
    with pytest.raises(DataUnavailableError):
        svc.analyze_patterns()


def test_ui_and_mcp_do_not_read_csvs():
    for name in ("app.py", "mcp_server.py", "src/privacy/coordinator.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        for forbidden in ("read_csv", "import csv", "DATA_DIR", "retailer_a", "returns.csv", "orders.csv"):
            assert forbidden not in src, f"{name} references {forbidden}"


def test_mcp_tools_match_catalog(service):
    tree = ast.parse((ROOT / "mcp_server.py").read_text(encoding="utf-8"))
    tools = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)
             and any("tool" in ast.unparse(d) for d in n.decorator_list)}
    assert tools == {t["name"] for t in service.get_mcp_tool_summary()}
    assert len(tools) >= 8
