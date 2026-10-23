# ------------------------------------------------------------------
# Azure AI Foundry Branching Chain Orchestration Pattern
#
# Technical demonstration of conditional workflow orchestration using:
# - FoundryChatClient and Agent Framework messaging
# - Async prompt execution with get_response()
# - LLM-driven classification and decision routing
# - Dynamic branch selection based on AI analysis
# - Specialized valuation workflows per company profile
# - Structured JSON generation and parsing
# - Conditional execution with business-rule routing
# - Result aggregation and workflow convergence
#
# Architecture:
#
#           Company Metrics
#                  |
#          Classification Stage
#                  |
#                  v
#       Company Profile Analysis
#                  |
#          +-------+-------+
#          |       |       |
#          |       |       |
#          v       v       v
#      Growth   Mature   Asset
#      Driven   Earnings Heavy
#          |       |       |
#          |       |       |
#      DCF      Multiple  Asset-Based
#   Valuation  Valuation Valuation
#          |       |       |
#          +-------+-------+
#                  |
#            Aggregation
#                  |
#          Final Valuation
#
# The workflow begins with an AI-powered classification
# stage that evaluates company financial characteristics
# and determines the most appropriate analytical path.
# Rather than executing every valuation methodology,
# the orchestration engine dynamically selects the
# branch that best matches the company's profile.
#
# Growth-oriented companies are routed to discounted
# cash flow analysis, mature businesses are routed
# to comparable multiples analysis, and asset-heavy
# organizations can be routed to asset-based valuation
# models. This pattern reduces unnecessary computation,
# improves analytical relevance, and demonstrates
# intelligent AI-driven workflow routing where a
# single LLM decision determines downstream execution.
#
# The result is a scalable decision-tree architecture
# that combines classification, conditional branching,
# specialized analysis, and final result convergence
# into a unified orchestration workflow.
# ------------------------------------------------------------------


from agent_framework.foundry import FoundryChatClient
from agent_framework import Message
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import asyncio
import json
import os

load_dotenv()
endpoint = os.environ["PAYG_FOUNDRY_ENDPOINT"]
model = os.environ["PAYG_FOUNDRY_MODEL"]

chat_client = FoundryChatClient(
    project_endpoint=endpoint,
    model=model,
    credential=DefaultAzureCredential(),
)

print(f"⭐ BRANCHING CHAIN PATTERN ⭐")

company_metrics = {
    "revenue_millions": 250,
    "revenue_growth_3yr": 0.85,
    "operating_margin": -0.12,
    "debt_to_equity": 0.3
}

async def analyze_company_classification(company_metrics):
    """Step 1: Classify company financial profile"""
    try:
        classification_prompt = f"""
    Analyze these company financial metrics and classify the company's profile:
    {json.dumps(company_metrics, indent=2)}

    Classify into one of: GROWTH_DRIVEN, MATURE_EARNINGS, ASSET_HEAVY
    Return JSON with: {{"classification": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
    """
        response = await chat_client.get_response(
            messages=[
                Message(role="user", contents=[classification_prompt])
            ]
        )

        print(f"🔍 Classification response:\n{json.dumps(json.loads(str(response)), indent=2)}")

        return json.loads(str(response))
    
    except Exception as e:
        raise RuntimeError(f"❌ Error analyzing company classification: {e}")
    
async def valuation_dcf_branch(company_metrics, classification):
    """Branch 1: Discounted cash flow for growth companies"""
    try:
        dcf_prompt = f"""
    Company classification: {classification['reasoning']}
    Company financial metrics: {json.dumps(company_metrics, indent=2)}

    Generate a 5-year discounted cash flow analysis. Include:
    - Revenue growth projections
    - Terminal value calculation
    - Risk-adjusted discount rate
    - Intrinsic value estimate

    Return structured JSON with all calculation components.
    """
        response = await chat_client.get_response(
            messages=[Message(role="user", contents=[dcf_prompt])]
        )

        print(f"🔍 DCF response:\n{json.dumps(json.loads(str(response)), indent=2)}")

        return json.loads(str(response))
    
    except Exception as e:
        raise RuntimeError(f"❌ Error performing DCF valuation: {e}")

async def valuation_multiples_branch(company_metrics, classification):
    """Branch 2: Comparable multiples for mature companies"""
    try:
        multiples_prompt = f"""
    Company classification: {classification['reasoning']}
    Company financial metrics: {json.dumps(company_metrics, indent=2)}

    Perform a comparable company analysis using:
    - P/E ratio vs. industry median
    - EV/EBITDA comparison
    - Price-to-book assessment

    Return JSON with valuation range and peer comparison data.
    """
        response = await chat_client.get_response(
            messages=[Message(role="user", contents=[multiples_prompt])]
        )

        print(f"🔍 Multiples response:\n{json.dumps(json.loads(str(response)), indent=2)}")

        return json.loads(str(response))
    
    except Exception as e:
        raise RuntimeError(f"❌Error performing multiples valuation: {e}")

async def main():
    """Execute branching chain based on company classification"""
    try:
        # Step 1: Classification (always executed)
        print(f"🤖 run analyze_company_classification...")
        classification = await analyze_company_classification(company_metrics)
        print(f"🎯 classification result: {classification['classification']} 🎯")
        
        # Step 2: Branch based on classification
        if classification['classification'] == 'GROWTH_DRIVEN':
            print(f"🤖 run valuation_dcf_branch...")
            valuation_result = await valuation_dcf_branch(company_metrics, classification)
            print(f"🎯 valuation_dcf_branch result: {valuation_result} 🎯")
        elif classification['classification'] == 'MATURE_EARNINGS':
            print(f"🤖 run valuation_multiples_branch...")
            valuation_result = await valuation_multiples_branch(company_metrics, classification)
            print(f"🎯 valuation_multiples_branch result: {valuation_result} 🎯")
        else:
            # Asset-heavy branch would go here
            raise NotImplementedError("❌ Asset-heavy valuation not shown")

        # Step 3: Aggregate results (same for all branches)
        valuation_result['classification'] = classification
        print(valuation_result)
    except Exception as e:
        raise RuntimeError(f"❌ Error executing branching chain: {e}")

if __name__ == "__main__":
    asyncio.run(main())
