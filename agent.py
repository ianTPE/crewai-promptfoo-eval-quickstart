"""
CrewAI Support Ticket Triage Agent — promptfoo provider

A minimal CrewAI crew that triages support tickets into structured JSON:
  { category, priority, rationale, next_action, tools_used }

Used as a Python provider for promptfoo evaluation.
"""

import os
import re

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool


# ---------------------------------------------------------------------------
# LLM setup — reads OPENAI_API_KEY from environment.
# Override the model with CREWAI_MODEL if needed (e.g. openai/gpt-4o).
# ---------------------------------------------------------------------------
llm = LLM(
    model=os.getenv("CREWAI_MODEL", "openai/gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY", ""),
    temperature=0.2,
)


# ---------------------------------------------------------------------------
# Tool — dummy knowledge base search for evaluation demonstration
# ---------------------------------------------------------------------------
@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base for similar tickets or known issues.
    Use this before triaging to find relevant context."""
    # Dummy implementation — replace with a real search in production
    return (
        f"Found 2 articles matching '{query}': "
        "[1] Billing FAQ — covers double-charge and refund policies. "
        "[2] Security Incident Runbook — steps for data-exposure reports."
    )

def build_crew(ticket: str) -> Crew:
    """Create a fresh crew for one promptfoo test case."""
    triage_agent = Agent(
        role="Support Ticket Triage Specialist",
        goal="Classify incoming support tickets by category, priority, and next action so the right team can respond quickly.",
        backstory=(
            "You are an experienced support operations analyst. "
            "You ALWAYS search the knowledge base before triaging a ticket. "
            "You read ticket descriptions, search for relevant context, "
            "and produce a concise, structured triage decision. "
            "You always respond in valid JSON with exactly five keys: "
            "category, priority, rationale, next_action, tools_used."
        ),
        tools=[search_knowledge_base],
        llm=llm,
        verbose=False,
    )

    triage_task = Task(
        description=(
            "Triage the following support ticket.\n\n"
            f"Ticket:\n{ticket}\n\n"
            "Step 1: Search the knowledge base for relevant context about this ticket.\n"
            "Step 2: Based on the search results and the ticket description, produce a triage decision.\n\n"
            "Respond with ONLY a JSON object containing these five keys:\n"
            '- "category": one of [billing, technical, account, feature_request, security]\n'
            '- "priority": one of [critical, high, medium, low]\n'
            '- "rationale": a one-sentence explanation of why you chose this category and priority\n'
            '- "next_action": a one-sentence description of what should happen next\n'
            '- "tools_used": an array of tool names you actually used, e.g. ["search_knowledge_base"]\n\n'
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        ),
        expected_output="A JSON object with keys: category, priority, rationale, next_action, tools_used",
        agent=triage_agent,
    )

    return Crew(
        agents=[triage_agent],
        tasks=[triage_task],
        verbose=False,
    )


def extract_json(output_text: str) -> str:
    """Return raw JSON when possible so promptfoo assertions can parse it."""
    match = re.search(r"\{[\s\S]*\}", output_text)
    return match.group() if match else output_text


# ---------------------------------------------------------------------------
# promptfoo provider entry point
# ---------------------------------------------------------------------------
def call_api(prompt: str, options: dict, context: dict) -> dict:
    """promptfoo Python provider interface.

    promptfoo calls this function for each test case.
    The `prompt` argument contains the rendered template (the ticket text).
    """
    triage_crew = build_crew(prompt)
    result = triage_crew.kickoff()

    # CrewAI returns a CrewOutput; extract the raw text
    output_text = result.raw if hasattr(result, "raw") else str(result)

    return {"output": extract_json(output_text)}
