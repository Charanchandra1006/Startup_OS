#!/usr/bin/env python3
"""
Chief AI Startup OS — Action Type Coverage Checker
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 8.2 (CI safety gate)

Scans all agent_*.py files for action_type string literals and fails CI
if any action_type is missing from BOTH tier_classifier.py and denylist.json.

This prevents unclassified action types from slipping through — every action
that an agent can propose must have a known risk tier or be explicitly denied.

Usage: python scripts/check_action_type_coverage.py
Exit code 0 = all action types covered, 1 = gaps found.
"""

import os
import re
import sys
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def find_agent_action_types() -> set[str]:
    """Scan all agent_*.py files for action_type string literals."""
    action_types: set[str] = set()
    services_dir = os.path.join(REPO_ROOT, "services")
    
    for root, dirs, files in os.walk(services_dir):
        for f in files:
            if f.startswith("agent_") and f.endswith(".py"):
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                
                # Match action_type = "..." or "action_type": "..."
                patterns = [
                    r'action_type\s*[=:]\s*["\']([a-z_\.]+)["\']',
                    r'"action_type"\s*:\s*"([a-z_\.]+)"',
                    r"'action_type'\s*:\s*'([a-z_\.]+)'",
                ]
                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        action_types.add(match.group(1))
    
    return action_types


def find_classified_action_types() -> set[str]:
    """Extract action types known to tier_classifier.py."""
    classified: set[str] = set()
    
    classifier_path = os.path.join(
        REPO_ROOT, "packages", "shared-types", "python",
        "chief_types", "tier_classifier.py"
    )
    
    if os.path.exists(classifier_path):
        with open(classifier_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Match string literals that look like action types
        for match in re.finditer(r'["\']([a-z_\.]+)["\']', content):
            candidate = match.group(1)
            if "." in candidate or "_" in candidate:
                classified.add(candidate)
    
    return classified


def find_denied_action_types() -> set[str]:
    """Extract action types from denylist.json."""
    denied: set[str] = set()
    
    denylist_path = os.path.join(REPO_ROOT, "packages", "schemas", "denylist.json")
    
    if os.path.exists(denylist_path):
        with open(denylist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        static_data = data.get("_static_data", {})
        for entry in static_data.get("denied_action_types", []):
            denied.add(entry.get("action_type", ""))
    
    return denied


def main():
    print("=" * 60)
    print("Chief AI — Action Type Coverage Check")
    print("=" * 60)
    
    agent_actions = find_agent_action_types()
    classified = find_classified_action_types()
    denied = find_denied_action_types()
    
    covered = classified | denied
    
    print(f"\nAgent action types found:     {len(agent_actions)}")
    print(f"Classified action types:      {len(classified)}")
    print(f"Denied action types:          {len(denied)}")
    print(f"Total covered:                {len(covered)}")
    
    # Find gaps
    gaps = agent_actions - covered
    
    if gaps:
        print(f"\n❌ COVERAGE GAP: {len(gaps)} action type(s) not in tier_classifier or denylist:")
        for gap in sorted(gaps):
            print(f"   - {gap}")
        print(
            "\nEvery agent action_type must be classified in tier_classifier.py "
            "or listed in denylist.json. Add missing types to prevent "
            "unclassified actions from bypassing the safety model."
        )
        sys.exit(1)
    else:
        print("\n✅ All agent action types are covered by tier_classifier or denylist.")
        
        if agent_actions:
            print("\nCovered action types:")
            for at in sorted(agent_actions):
                source = "classified" if at in classified else "denied"
                print(f"   ✓ {at} ({source})")
        
        sys.exit(0)


if __name__ == "__main__":
    main()
