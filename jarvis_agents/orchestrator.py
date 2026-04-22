"""
Jarvis AI Assistant — Orchestrator Agent (The Brain)
Uses a Python-based router instead of SDK handoffs for Groq compatibility.
The orchestrator classifies intent, then we route to the right specialist.
"""

import os
import re
from agents import Agent, Runner
from providers.llm_provider import get_model
from jarvis_agents.dev_agent import create_dev_agent
from jarvis_agents.seo_agent import create_seo_agent
from jarvis_agents.debug_agent import create_debug_agent
from jarvis_agents.file_agent import create_file_agent

# Disable SDK tracing (we're not using OpenAI's API)
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

ORCHESTRATOR_INSTRUCTIONS = """
You are Jarvis — an intelligent AI assistant inspired by Iron Man's JARVIS.
You are polite, professional, slightly witty, and extremely competent.

## Your Role
You are the central brain. For each user message, do TWO things:
1. Determine which specialist should handle it (or handle it yourself)
2. Respond to the user

## ROUTING RULES — Start EVERY response with a route tag:

[ROUTE:SELF] — For general conversation, questions, advice, planning, jokes
[ROUTE:DEV] — For coding, WordPress, Elementor, scripting, HTML/CSS/JS, development
[ROUTE:SEO] — For Amazon listings, product SEO, keyword optimization
[ROUTE:DEBUG] — For troubleshooting, diagnostics, "is this site down?", error analysis
[ROUTE:FILES] — For opening apps, browsing files, finding documents, system info,
                AND seeing the screen / what's on display / what app is open

## After the route tag, write your response naturally.

## Examples
User: "Hello!" → [ROUTE:SELF] Good evening, sir. How may I assist you today?
User: "Fix my WordPress CSS" → [ROUTE:DEV] I'll take a look at that CSS issue for you.
User: "Create a listing for a yoga mat" → [ROUTE:SEO] I'll craft an optimized Amazon listing for that yoga mat.
User: "Is my site down?" → [ROUTE:DEBUG] Let me check that for you right away.
User: "Open Chrome" → [ROUTE:FILES] Opening Chrome for you now.
User: "What's on my screen?" → [ROUTE:FILES] Let me take a look at your screen.
User: "What am I doing?" → [ROUTE:FILES] Let me check what you're working on.
User: "What do I have open?" → [ROUTE:FILES] Let me see what apps you have running.

## Rules — CRITICAL
1. Keep responses brief but conversational (1-3 sentences). Talk back naturally like a real assistant.
2. Address the user as "sir" occasionally.
3. Be direct and avoid filler words, but maintain your helpful Jarvis persona.
4. Never say "I'm just an AI" — you are Jarvis.
5. ALWAYS include the [ROUTE:X] tag at the start of your response.
6. If the user speaks Urdu, reply in Urdu smoothly.
7. NEVER list options unless asked. Just perform the action and confirm conversationally.
"""


class JarvisOrchestrator:
    """
    Routes user requests to specialist agents based on intent classification.
    Uses the orchestrator LLM to classify, then delegates to the right agent.
    """

    def __init__(self):
        # Create classifier (lightweight, just determines routing)
        self.classifier = Agent(
            name="jarvis_classifier",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            model=get_model(),
        )

        # Create specialist agents
        self.specialists = {
            "DEV": create_dev_agent(),
            "SEO": create_seo_agent(),
            "DEBUG": create_debug_agent(),
            "FILES": create_file_agent(),
        }

        # Route pattern
        self._route_pattern = re.compile(r'\[ROUTE:(\w+)\]')

    async def process(self, user_input: str, history: list[dict] | None = None) -> tuple[str, str]:
        """
        Process a user message: classify intent → route to specialist.

        Args:
            user_input: The user's message.
            history: Recent conversation messages for context.

        Returns:
            Tuple of (response_text, agent_name).
        """
        # Build context-aware input
        enhanced_input = self._build_context(user_input, history)

        # Step 1: Classify intent
        classify_result = await Runner.run(self.classifier, enhanced_input)
        full_response = classify_result.final_output

        # Step 2: Extract route
        route_match = self._route_pattern.search(full_response)

        if not route_match or route_match.group(1) == "SELF":
            # Orchestrator handles it directly — strip the route tag
            response = self._strip_route_tag(full_response)
            return response, "Jarvis"

        route = route_match.group(1)
        agent = self.specialists.get(route)

        if not agent:
            # Unknown route, handle directly
            response = self._strip_route_tag(full_response)
            return response, "Jarvis"

        # Step 3: Delegate to specialist agent
        try:
            specialist_result = await Runner.run(agent, enhanced_input)
            return specialist_result.final_output, agent.name
        except Exception as e:
            # If specialist fails, return the classifier's own response
            response = self._strip_route_tag(full_response)
            return f"{response}\n\n(Note: specialist agent encountered an issue: {str(e)[:100]})", "Jarvis"

    def _build_context(self, user_input: str, history: list[dict] | None) -> str:
        """Build a context-aware prompt including recent conversation history."""
        if not history:
            return user_input

        # Include last 4 messages for context (summarized inline to avoid breaking Groq tool parsing)
        recent = history[-4:]
        context_lines = []
        for msg in recent:
            role = "I previously said" if msg["role"] == "user" else "You previously replied"
            content = msg["content"][:100]
            context_lines.append(f'({role}: "{content}")')

        context = " ".join(context_lines)
        return f"{user_input}\n\n[Context: {context}]"

    def _strip_route_tag(self, text: str) -> str:
        """Remove the [ROUTE:X] tag from the response."""
        return self._route_pattern.sub('', text).strip()


def create_orchestrator() -> JarvisOrchestrator:
    """Create the Jarvis orchestrator with Python-based routing."""
    return JarvisOrchestrator()
