"""End-to-end MCP check: starts mcp_server.py over stdio, calls every tool,
resource and prompt like a real MCP client would, and prints PASS/FAIL.

Usage:
    python check_mcp.py            # summary
    python check_mcp.py --verbose  # also print each response
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent

# (tool, arguments, check on the parsed result, which agent/component it exercises)
CASES = [
    ("analyze_return_patterns", {"category": "Electronics"},
     lambda r: r[0]["cause"] == "COMPATIBILITY" and r[0]["signal_strength"] == "High", "Pattern Analysis Agent"),
    ("get_pattern_details", {"category": "Electronics", "cause": "COMPATIBILITY"},
     lambda r: r["privacy_status"] == "Approved" and "explanation" in r, "Pattern Analysis Agent"),
    ("recommend_pre_purchase", {"cause": "COMPATIBILITY"},
     lambda r: [i["name"] for i in r][:1] == ["Compatibility checker"], "Pre-Purchase Agent"),
    ("recommend_post_purchase", {"cause": "COMPATIBILITY"},
     lambda r: all(i["requires_human_approval"] for i in r), "Post-Purchase Agent"),
    ("forecast_intervention_impact", {"cause": "COMPATIBILITY", "intervention_id": "compat_checker",
                                      "affected_returns": 100},
     lambda r: r["prevented_returns"] == {"low": 12, "expected": 20, "high": 25}, "Forecasting"),
    ("get_sanitized_order_context", {"example_order_id": "A-ORD-0001"},
     lambda r: r["found"] and set(r) == {"found", "product_category", "delivery_status", "exchange_available",
                                         "return_started"}, "Mock OMS"),
    ("create_support_intervention_draft", {"cause": "COMPATIBILITY", "action": "Recommend compatible replacement",
                                           "channel": "Customer support queue"},
     lambda r: r["status"] == "DRAFT" and r["requires_human_approval"], "Mock customer service"),
    ("get_privacy_audit_summary", {},
     lambda r: r["summary"]["approved"] > 0 and r["summary"]["suppressed"] > 0, "Privacy coordinator / audit"),
    ("classify_return_text", {"customer_comment": "wrong device model"},
     lambda r: r["cause"] == "COMPATIBILITY", "Classifier"),
    ("get_category_cause_matrix", {}, lambda r: any(x["signal_score"] == 3 for x in r), "Pattern Analysis Agent"),
    ("prioritize_interventions", {"cause": "DIMENSION_MISMATCH"},
     lambda r: r[0]["quadrant"] == "Quick win", "Pre/Post-Purchase Agents"),
    ("forecast_intervention_portfolio", {"cause": "COMPATIBILITY",
                                         "intervention_ids": ["compat_checker", "compatible_replacement"],
                                         "affected_returns": 100},
     lambda r: r["combined_prevented_returns"]["expected"] == 36, "Forecasting"),
    ("simulate_privacy_policy", {"min_retailers": 3},
     lambda r: r["approved_under_policy"] < r["approved_under_current_policy"], "Privacy coordinator"),
    ("search_knowledge_base", {"query": "exchange"}, lambda r: len(r) >= 1, "Returns Intelligence Agent"),
    ("list_support_drafts", {}, lambda r: len(r) >= 1 and r[0]["customer_contacted"] is False,
     "Mock customer service"),
    # Privacy guard: a single-retailer pattern must not be released.
    ("get_pattern_details", {"category": "Beauty", "cause": "OTHER"},
     lambda r: r["privacy_status"] == "Not released", "Privacy guard (blocked pattern)"),
    # Validation guard: looser policy must be rejected.
    ("simulate_privacy_policy", {"local_min_records": 2},
     lambda r: "error" in r, "Privacy guard (policy floor)"),
]

RESTRICTED = {"retailer_id", "retailer_token", "local_count", "total_count", "customer_comment", "return_id"}


def leaked_keys(obj) -> list[str]:
    """Restricted fields used as keys anywhere in the response (values like a list of field names are fine)."""
    if isinstance(obj, dict):
        return [k for k in obj if k in RESTRICTED] + [x for v in obj.values() for x in leaked_keys(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in leaked_keys(v)]
    return []


def parse(result) -> object:
    if result.structuredContent is not None:
        sc = result.structuredContent
        return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
    text = "".join(getattr(c, "text", "") for c in result.content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # FastMCP returns one content block per list item for list results.
        return [json.loads(c.text) for c in result.content]


async def main(verbose: bool) -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], cwd=str(ROOT))
    failures = 0
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            resources = [str(r.uri) for r in (await session.list_resources()).resources]
            prompts = [p.name for p in (await session.list_prompts()).prompts]
            print(f"Server exposes {len(tools)} tools, {len(resources)} resources, {len(prompts)} prompt(s)\n")

            tested = set()
            for name, args, check, component in CASES:
                tested.add(name)
                try:
                    data = parse(await session.call_tool(name, args))
                    leaked = leaked_keys(data)
                    ok = bool(check(data)) and not leaked
                    detail = f"restricted fields leaked: {leaked}" if leaked else ""
                except Exception as exc:  # report, keep going
                    ok, data, detail = False, None, f"{type(exc).__name__}: {exc}"
                failures += not ok
                print(f"{'PASS' if ok else 'FAIL'}  {name:<34} {component}  {detail}")
                if verbose:
                    print("      " + json.dumps(data)[:400])

            for uri in resources:
                text = (await session.read_resource(uri)).contents[0].text
                ok = bool(text.strip())
                failures += not ok
                print(f"{'PASS' if ok else 'FAIL'}  resource {uri}")
            for p in prompts:
                msg = (await session.get_prompt(p, {"category": "Electronics"})).messages[0].content.text
                ok = "analyze_return_patterns" in msg
                failures += not ok
                print(f"{'PASS' if ok else 'FAIL'}  prompt {p}")

            untested = tools - tested
            if untested:
                failures += len(untested)
                print(f"FAIL  untested tools: {sorted(untested)}")

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--verbose" in sys.argv)))
