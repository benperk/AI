# ------------------------------------------------------------------
# Azure AI Foundry Fan-In / Fan-Out Orchestration Pattern
#
# Technical demonstration of parallel multi-agent orchestration using:
# - AIProjectClient and PromptAgentDefinition
# - Dynamic agent version creation
# - Async agent provisioning with asyncio.gather()
# - Fan-out execution across specialized AI agents
# - Fan-in synchronization of distributed agent results
# - Concurrent conversation and response workflows
# - Minimum-quorum reliability validation
# - Final aggregation and recommendation generation
#
# Architecture:
#          Market Data
#                |
#             Fan-Out
#                |
#    +-----------+-----------+
#    |           |           |
# Market      Risk      Sentiment
#  Agent      Agent       Agent
#    |           |           |
#    +-----------+-----------+
#                |
#             Fan-In
#                |
#      Final Synthesis Model
#
# Specialized agents execute independently in parallel,
# analyze different aspects of the same dataset, return
# domain-specific insights, and synchronize results into
# a consolidated recommendation. The workflow uses
# concurrent execution, quorum validation, and result
# aggregation to improve scalability, resiliency, and
# overall analytical coverage.
# ------------------------------------------------------------------
import os
import json
import asyncio
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (PromptAgentDefinition,)

# ORCHESTRATION PATTERN: FAN IN / FAN OUT
# Parallel agent spawning and synchronization

load_dotenv()
endpoint = os.environ["PAYG_FOUNDRY_ENDPOINT"]
model = os.environ["PAYG_FOUNDRY_MODEL"]
market_agent_name = "market-analysis-agent"
risk_agent_name = "risk-assessment-agent"
sentiment_agent_name = "sentiment-analysis-agent"

print(f"⭐ FAN IN & FAN OUT ORCHESTRATION PATTERN ⭐")

#TEST MARKET DATA & QUERY
market_snapshot = {
    "equities": {
        "AAPL": {
            "price": 220.15,
            "change_pct": 1.4,
            "volume": 55000000,
            "avg_volume": 48000000,
            "market_cap": 3.3e12,
            "sector": "Technology",
            "beta": 1.15,
            "volatility_30d": 0.22,
            "pe_ratio": 31.5,
            "forward_pe": 28.1,
            "revenue_growth_pct": 6.8,
            "news_sentiment": 0.72,
            "social_sentiment": 0.65,
            "analyst_rating": "Buy"
        },
        "MSFT": {
            "price": 465.80,
            "change_pct": -0.8,
            "volume": 28000000,
            "avg_volume": 31000000,
            "market_cap": 3.4e12,
            "sector": "Technology",
            "beta": 0.95,
            "volatility_30d": 0.18,
            "pe_ratio": 37.2,
            "forward_pe": 33.5,
            "revenue_growth_pct": 14.5,
            "news_sentiment": 0.58,
            "social_sentiment": 0.49,
            "analyst_rating": "Buy"
        },
        "NVDA": {
            "price": 132.10,
            "change_pct": 4.7,
            "volume": 76000000,
            "avg_volume": 54000000,
            "market_cap": 3.2e12,
            "sector": "Technology",
            "beta": 1.68,
            "volatility_30d": 0.42,
            "pe_ratio": 65.4,
            "forward_pe": 42.3,
            "revenue_growth_pct": 82.1,
            "news_sentiment": 0.91,
            "social_sentiment": 0.88,
            "analyst_rating": "Strong Buy"
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
    },

    "indices": {
        "SP500": {
            "level": 6200,
            "change_pct": 0.8
        },
        "NASDAQ": {
            "level": 20500,
            "change_pct": 1.5
        },
        "DOW": {
            "level": 44750,
            "change_pct": 0.2
        }
    },

    "sectors": {
        "Technology": {
            "change_pct": 2.3
        },
        "Energy": {
            "change_pct": 4.1
        },
        "Healthcare": {
            "change_pct": -1.2
        },
        "Financials": {
            "change_pct": 0.7
        }
    },

    "rates": {
        "fed_funds_rate": 5.25,
        "treasury_10y": 4.35,
        "treasury_2y": 4.72
    },

    "fx": {
        "DXY": {
            "level": 104.2,
            "change_pct": -0.3
        }
    },

    "market_sentiment": {
        "vix": 15.4,
        "fear_greed_index": 68,
        "overall_sentiment": "Bullish"
    }
}
user_query = f"""
Analyze equities and commodities and provide insights.

Market Data:
{json.dumps(market_snapshot, indent=2)}

Please:
1. Produce a market analysis.
2. Assess investment risk.
4. Determine sentiment.
3. Provide an investment recommendation.
"""
market_payload = json.dumps(market_snapshot)

async def main() -> None:
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        try:
            # FAN IN / FAN OUT AGENTS (MARKET ANALYSIS, SENTIMENT ANALYSIS, AND RISK ASSESSMENT)

            market_version_task = asyncio.create_task(
                project_client.agents.create_version(
                    agent_name=market_agent_name,
                    definition=PromptAgentDefinition(
                        model=model,
                        instructions="""You analyze equity market conditions and return structured market reports.
            1. Identify which asset classes are present in the market data and analyze them accordingly.
            2. Provide a structured market report including price trends, volatility indicators, and sector performance.
            3. Maximum length is 50 words or less, compact and concise.""",
                    ),
                )
            )
            risk_version_task = asyncio.create_task(
                project_client.agents.create_version(
                    agent_name=risk_agent_name,
                    definition=PromptAgentDefinition(
                        model=model,
                        instructions="""You assess investment risk based on market data and return risk scores.
            1. Evaluate the risk level for each asset class based on market analysis.
            2. Provide a structured risk assessment including risk scores and potential impact.
            3. Maximum length is 50 words or less, compact and concise.""",
                    ),
                )
            )
            sentiment_version_task = asyncio.create_task(
                project_client.agents.create_version(agent_name=sentiment_agent_name,
                    definition=PromptAgentDefinition(
                        model=model,
                        instructions="""You assess market sentiment for various asset classes based on market data and news.
            1. Evaluate the sentiment for each asset class as positive, negative, or neutral.
            2. Provide a structured sentiment analysis including key drivers and potential impact.
            3. Maximum length is 50 words or less, compact and concise.""",
                    ),
                )
            )

            market_agent_version, risk_agent_version, sentiment_agent_version = (
                await asyncio.gather(market_version_task, risk_version_task, sentiment_version_task))

            print(f"🟢 market_agent_version version {market_agent_version.id} created")
            print(f"🟢 risk_agent_version version {risk_agent_version.id} created")
            print(f"🟢 sentiment_agent_version version {sentiment_agent_version.id} created")         
            
            market_client = project_client.get_openai_client(agent_name=market_agent_name)
            risk_client = project_client.get_openai_client(agent_name=risk_agent_name)
            sentiment_client = project_client.get_openai_client(agent_name=sentiment_agent_name)     
    
            agent_results = await fan_in_fan_out_agent_analysis(
                market_client, risk_client, sentiment_client)

            print("🟢 BEGIN SYNCRONIZATION")
            synchronization_prompt = f"""
                Market Analysis
                {agent_results["market-analysis-agent"].output_text}

                Risk Assessment
                {agent_results["risk-assessment-agent"].output_text}

                Sentiment Analysis
                {agent_results["sentiment-analysis-agent"].output_text}

                Provide a 200 word final recommendation in markdown format.
                """
            #print(f"🎯 Synchronization Prompt: {synchronization_prompt} 🎯")
            final_response = await openai_client.chat.completions.create(
                model=model,
                messages=[ {"role": "user", "content": synchronization_prompt}],)
            
            print("🎯 ***** FINAL RECOMENDATION ***** 🎯")
            print("\n", final_response.choices[0].message.content, "\n")
        except Exception as e:
            print(f"❌ Error occurred: {e}")

async def fan_in_fan_out_agent_analysis(market_client, risk_client, sentiment_client):
    print("🟢 BEGIN: FAN-IN / FAN-OUT ANALYSIS")

    try:

        market_conv_task = asyncio.create_task(market_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": json.dumps(market_payload)}])
        )
        risk_conv_task = asyncio.create_task(risk_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": json.dumps(market_payload)}])
        )
        sentiment_conv_task = asyncio.create_task(sentiment_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": json.dumps(market_payload)}])
        )

        market_conversation, risk_conversation, sentiment_conversation = (
            await asyncio.gather(market_conv_task, risk_conv_task, sentiment_conv_task))

        market_task = asyncio.create_task(
            spawn_agent(market_client, market_agent_name, market_conversation))
        risk_task = asyncio.create_task(
            spawn_agent(risk_client, risk_agent_name, risk_conversation))
        sentiment_task = asyncio.create_task(
            spawn_agent(sentiment_client, sentiment_agent_name, sentiment_conversation))  

        results = await asyncio.gather(market_task, risk_task, sentiment_task, return_exceptions=True)

        # Apply minimum-quorum policy
        # Fail: need at least 2 of 3 agents to succeed
        agent_results = {}

        for result in results:
            if not isinstance(result, Exception):
                agent_results[result["agent"]] = result["result"]

        if len(agent_results) < 2:
            raise Exception("Minimum quorum not met: at least 2 of 3 agents must succeed.")
        
        print("🟢 END FAN-IN / FAN-OUT ANALYSIS")

        return agent_results

    except Exception as e:
        print(f"❌ Error occurred in fan_in_fan_out_agent_analysis: {e}")

async def spawn_agent(client, agent_name, conversation):
    try:
        print(f"🤖 spawning (fan-out) '{agent_name}'")

        response = await asyncio.wait_for(
            client.responses.create(conversation=conversation.id), timeout=30)

        print(f"🤖 deallocating (fan-in) '{agent_name}'")

        return { "agent": agent_name, "result": response }

    except Exception as e:
        print(f"❌ Error occurred in spawn_agent '{agent_name}': {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
