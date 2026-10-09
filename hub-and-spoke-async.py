# ------------------------------------------------------------------
# Azure AI Foundry Hub-and-Spoke Orchestration Pattern
#
# Technical demonstration of multi-agent orchestration using:
# - AIProjectClient and PromptAgentDefinition
# - Dynamic agent version creation
# - FunctionTool-based agent delegation
# - Agent-to-agent communication
# - Async conversation and response workflows
# - Function call routing and execution
# - Iterative reasoning with tool outputs
#
# Architecture:
#   Hub Agent -> Function Calls -> Spoke Agents
#
# The Hub coordinates execution, processes tool requests,
# invokes specialized agents, returns function_call_output
# objects, and continues reasoning until completion.
# ------------------------------------------------------------------
import os
import json
import asyncio
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (PromptAgentDefinition, FunctionTool,)

# ORCHESTRATION PATTERN: HUB AND SPOKE

load_dotenv()
endpoint = os.environ["PAYG_FOUNDRY_ENDPOINT"]
model = os.environ["PAYG_FOUNDRY_MODEL"]
hub_agent_name = "research-orchestrator-hub"
market_agent_name = "market-analysis-agent"
risk_agent_name = "risk-assessment-agent"

print(f"⭐ HUB & SPOKE ORCHESTRATION PATTERN ⭐")

#TEST MARKET DATA & QUERY
market_snapshot = {
    "equities": {
        "AAPL": {
            "price": 220.15,
            "change_pct": 1.4,
            "volume": 55000000
        },
        "MSFT": {
            "price": 465.80,
            "change_pct": -0.8,
            "volume": 28000000
        },
        "NVDA": {
            "price": 132.10,
            "change_pct": 4.7,
            "volume": 76000000
        }
    },
    "commodities": {
        "gold": {
            "price": 2435.50,
            "change_pct": -0.4
        },
        "oil": {
            "price": 82.15,
            "change_pct": 3.2
        }
    }
}
user_query = f"""
Analyze equities and commodities and provide investment risk assessment.

Market Data:
{json.dumps(market_snapshot, indent=2)}

Please:
1. Produce a market analysis.
2. Assess investment risk.
3. Provide an investment recommendation.
"""

#SPOKE AGENT TOOL IMPLEMENTATION
market_analysis_tool = {
    "type": "function",
    "function": {
        "name": "invoke_market_analysis_agent",
        "description": "Analyzes current market conditions for specified asset classes. Returns structured market report with price trends, volatility indicators, and sector performance.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Asset classes to analyze: equities, fixed_income, derivatives, commodities"
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["summary", "detailed"],
                    "description": "Level of analysis detail required"
                }
            },
            "required": ["asset_classes"]
        }
    }
}

# Define spoke invocation tools
market_tool = FunctionTool(
    name="invoke-market-analysis-agent",
    description="Analyzes market conditions for specified asset classes",
    parameters={
        "type": "object",
        "properties": {
            "asset_classes": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Asset classes to analyze"
            }
        },
        "required": ["asset_classes"]
    }
)
risk_tool = FunctionTool(
    name="invoke-risk-assessment-agent",
    description="Assesses investment risk based on market analysis results",
    parameters={
        "type": "object",
        "properties": {
            "market_data": {
                "type": "string",
                "description": "Market analysis results to evaluate"
            }
        },
        "required": ["market_data"]
    }
)
spoke_tools = [ market_tool, risk_tool ]

async def main() -> None:
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
    ):
        try:
            # SPOKE AGENTS (MARKET ANALYSIS AND RISK ASSESSMENT)
            market_agent_version = await project_client.agents.create_version(
                        agent_name=market_agent_name,
                        definition=PromptAgentDefinition(
                            model=model,
                            instructions="""You analyze equity market conditions and return structured market reports.
            1. Identify which asset classes are present in the market data and analyze them accordingly.
            2. Provide a structured market report including price trends, volatility indicators, and sector performance.
            3. Maximum length is 300 words or less, compact and concise.""",
                        ),
                    )
            print(f"🟢 market_agent_version version {market_agent_version.id} created")
            risk_agent_version = await project_client.agents.create_version(
                        agent_name=risk_agent_name,
                        definition=PromptAgentDefinition(
                            model=model,
                            instructions="""You assess investment risk based on market data and return risk scores.
            1. Evaluate the risk level for each asset class based on market analysis.
            2. Provide a structured risk assessment including risk scores and potential impact.
            3. Maximum length is 200 words or less, compact and concise.""",
                        ),
                    )
            print(f"🟢 risk_agent_version version {risk_agent_version.id} created")
            # HUB AGENT WITH SPOKE TOOLS
            hub_agent_version = await project_client.agents.create_version(
                agent_name=hub_agent_name,
                definition=PromptAgentDefinition(
                    model=model,
                    instructions="""You are an investment research orchestrator. Do not perform the analysis yourself. Use the tools.
            1. Always invoke invoke-market-analysis-agent first.
            2. After receiving the market analysis, invoke-risk-assessment-agent must also always be invoked.
            3. After receiving the risk assessment, only generate a BUY, SELL, or HOLD decision for each equity and commodity.""",
                    tools=spoke_tools,
                ),
            )
            print(f"🟢 hub_agent_version version {hub_agent_version.id} created")
            for tool in hub_agent_version.definition.tools:
                print(f"  🛠️  {tool.name}")            

            hub_client = project_client.get_openai_client(agent_name=hub_agent_name)
            market_client = project_client.get_openai_client(agent_name=market_agent_name)
            risk_client = project_client.get_openai_client(agent_name=risk_agent_name)         

            result = await orchestrate_hub(hub_client, market_client, risk_client, user_query)
            print("🎯 ***** FINAL RECOMENDATION ***** 🎯")
            print("\n", result, "\n")
        except Exception as e:
            print(f"❌ Error occurred: {e}")

async def orchestrate_hub(hub_client, market_client, risk_client, user_query: str):
    print("🟢 BEGIN orchestrate_hub()")

    conversation = await hub_client.conversations.create(
        items=[{"type": "message", "role": "user", "content": user_query}],
    )

    response = await hub_client.responses.create(conversation=conversation.id)

    while True:
        tool_calls = []

        for item in response.output:
            print(f"  ⚡ {item.type}")            

            if item.type == "function_call":
                tool_calls.append(item)
                print(f"  🧠 {getattr(item, 'name', None)}")

        # Finished reasoning
        if not tool_calls:            
            print("🟢 END orchestrate_hub()")
            return response.output_text

        # Execute requested spoke(s)
        tool_outputs = []

        for tool_call in tool_calls:
            print(f"    ✨ TOOL REQUESTED: {tool_call.name}")

            arguments = json.loads(tool_call.arguments)

            result = await invoke_spoke(market_client, risk_client, tool_call.name, arguments)

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": result
            })

        # Continue Hub reasoning
        response = await hub_client.responses.create(
            model=model,
            previous_response_id=response.id,
            input=tool_outputs
        )    

async def invoke_spoke(market_client, risk_client, spoke_name: str, parameters: dict) -> str:
    print(f"      🤖 invoking SPOKE: {spoke_name}")

    if spoke_name == "invoke-market-analysis-agent":

        market_conversation = await market_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": json.dumps(parameters)}]
        )
        market_response = await market_client.responses.create(
            conversation=market_conversation.id
        )
        print("        📊 MARKET ANALYSIS COMPLETE")
        #print(market_response.output_text)

        return market_response.output_text

    elif spoke_name == "invoke-risk-assessment-agent":

        risk_conversation = await risk_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": json.dumps(parameters)}]
        )

        risk_response = await risk_client.responses.create(
            conversation=risk_conversation.id
        )
        print("        🔎 RISK ANALYSIS COMPLETE")
        #print(risk_response.output_text)

        return risk_response.output_text

    raise Exception(f"❌ Unknown spoke: {spoke_name}")

if __name__ == "__main__":
    asyncio.run(main())
