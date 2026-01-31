#!/usr/bin/env python3
"""
Run the Agatha pipeline and display results.

Note: Suppress Python 3.9 deprecation warnings from Google libraries.
Proper fix is to upgrade to Python 3.10+.

Usage:
    # With fixture data:
    python run_pipeline.py

    # With custom JSON file:
    python run_pipeline.py --input my_ads.json

    # With BigQuery (WhisperingHomes, last 30 days):
    python run_pipeline.py --bigquery

    # With BigQuery (custom tenant and days):
    python run_pipeline.py --bigquery --tenant wh --days 77

    # Output to JSON file:
    python run_pipeline.py --output results.json
"""

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*MCP requires.*")

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from controllers.agatha_controller import AgathaController
from helpers.tools import get_fixture_with_expected, get_ad_data


def load_input_data(input_file: str = None) -> dict:
    """Load ad data from file or use fixture."""
    if input_file:
        with open(input_file, 'r') as f:
            data = json.load(f)
        # Ensure required structure
        if "account_avg_roas" not in data:
            raise ValueError("Input JSON must have 'account_avg_roas' field")
        if "ads" not in data:
            raise ValueError("Input JSON must have 'ads' array")
        return data
    else:
        # Use fixture
        return get_fixture_with_expected()


async def load_bigquery_data(tenant: str, days: int) -> dict:
    """Load ad data from BigQuery."""
    print(f"Fetching data from BigQuery (tenant={tenant}, days={days})...")
    data = await get_ad_data(tenant=tenant, days=days, use_fixture=False)
    print(f"Retrieved {len(data.get('ads', []))} ads from BigQuery")
    return data


def print_analysis(analysis: dict):
    """Pretty print analysis results."""
    print("\n" + "=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    print(f"Account Avg ROAS: {analysis['account_avg_roas']:.2f}")
    print(f"Total Ads: {analysis['total_ads']}")
    print(f"Summary: {analysis['summary']}")
    print("-" * 70)

    for result in analysis['results']:
        status = "✓" if result['classification'] in ['GOOD', 'OK'] else "⚠" if result['classification'] == 'WARNING' else "✗" if result['classification'] == 'BAD' else "⏳"
        print(f"\n{status} {result['ad_name']}")
        print(f"   Classification: {result['classification']} | Confidence: {result['confidence']}")
        print(f"   Action: {result['recommended_action']}")
        metrics = result.get('metrics', {})
        print(f"   Spend: ${metrics.get('spend', 0):,.0f} | ROAS: {metrics.get('roas', 0):.2f} | Days: {metrics.get('days_active', 0)}")

        # Show chain of thought
        cot = result.get('chain_of_thought', {})
        if cot:
            comparison = cot.get('comparison', {})
            logic = cot.get('classification_logic', {})
            print(f"   ROAS Ratio: {comparison.get('roas_ratio', 'N/A')}")
            print(f"   Logic: {logic.get('reason', 'N/A')}")

        # Full explanation
        if 'user_explanation' in result:
            print(f"   Explanation: {result['user_explanation']}")


def print_recommendations(recommendations: dict):
    """Pretty print recommendations."""
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print(f"Total: {recommendations['total_recommendations']}")
    print(f"Actionable: {recommendations['actionable_count']}")
    print(f"Total Spend Change: ${recommendations['total_spend_change']:,.0f}")
    print(f"Expected Revenue Impact: ${recommendations['total_expected_revenue']:,.0f}")
    print("-" * 70)

    for rec in recommendations['recommendations']:
        action = rec['action']
        icon = "📈" if action == "SCALE" else "📉" if action == "REDUCE" else "⏸️" if action == "PAUSE" else "👀" if action in ["MONITOR", "REVIEW"] else "⏳"
        print(f"\n{icon} [{action}] {rec['ad_name']}")
        print(f"   Current: ${rec['current_spend']:,.0f} → Proposed: ${rec['proposed_new_spend']:,.0f} ({rec['change_percentage']:+d}%)")
        if 'expected_impact' in rec:
            impact = rec['expected_impact']
            print(f"   Expected: {impact.get('calculation', 'N/A')}")
        if 'rationale' in rec:
            print(f"   Rationale: {rec['rationale']}")


def print_execution(execution: dict):
    """Pretty print execution results."""
    print("\n" + "=" * 70)
    print("EXECUTION RESULTS" + (" (MOCK MODE)" if execution.get('mock_mode') else ""))
    print("=" * 70)
    print(f"Timestamp: {execution.get('timestamp')}")
    summary = execution.get('summary', {})
    if isinstance(summary, dict):
        print(f"Executed: {summary.get('total_executed', 0)} actions")
        print(f"Net Spend Change: ${summary.get('net_spend_change', 0):,.0f}")
    else:
        print(f"Summary: {summary}")
    print("-" * 70)

    for item in execution.get('executed', []):
        status = item.get('status', 'UNKNOWN')
        action = item.get('action_taken', item.get('action', 'UNKNOWN'))
        print(f"\n   [{status}] {action} - {item['ad_name']}")
        if 'message' in item:
            print(f"   {item['message']}")


async def run_pipeline(
    input_file: str = None,
    output_file: str = None,
    use_bigquery: bool = False,
    tenant: str = "wh",
    days: int = 30,
    limit: int = 10
):
    """Run the full pipeline."""
    # Load data
    print("Loading data...")
    if use_bigquery:
        data = await load_bigquery_data(tenant, days)
    else:
        data = load_input_data(input_file)

    # Strip _expected fields for processing and apply limit
    ads = []
    for ad in data['ads'][:limit]:  # Apply limit here
        clean_ad = {k: v for k, v in ad.items() if not k.startswith('_')}
        ads.append(clean_ad)

    print(f"Loaded {len(ads)} ads with account avg ROAS: {data['account_avg_roas']}")

    # Run pipeline
    controller = AgathaController()
    result = await controller.run_full_pipeline(
        account_avg_roas=data['account_avg_roas'],
        ads=ads,
        mock_mode=True
    )

    # Display results
    print_analysis(result['analysis'])
    print_recommendations(result['recommendations'])
    print_execution(result['execution'])

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✓ Results saved to {output_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description='Run the Agatha ad optimization pipeline')
    parser.add_argument('--input', '-i', help='Input JSON file with ad data (default: use fixture)')
    parser.add_argument('--output', '-o', help='Output JSON file for results')
    parser.add_argument('--bigquery', action='store_true', help='Use BigQuery instead of fixture')
    parser.add_argument('--tenant', default='wh', choices=['tl', 'wh'],
                        help='Tenant: tl=ThirdLove, wh=WhisperingHomes (default: wh)')
    parser.add_argument('--days', type=int, default=30, help='Days of data to query (default: 30)')
    parser.add_argument('--limit', type=int, default=10, help='Max number of ads to analyze (default: 10)')
    args = parser.parse_args()

    if args.bigquery and args.input:
        parser.error("Cannot use both --bigquery and --input")

    result = asyncio.run(run_pipeline(
        input_file=args.input,
        output_file=args.output,
        use_bigquery=args.bigquery,
        tenant=args.tenant,
        days=args.days,
        limit=args.limit
    ))


if __name__ == "__main__":
    main()
