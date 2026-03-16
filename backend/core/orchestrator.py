"""
Orchestrator — Config-driven LLM router.
Decides which agent to call based on user input.
Accepts prompt and LLM instance from project config.
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class MainOrchestrator:
    def __init__(self, system_prompt: str, rag_prompt: str, llm):
        """
        Args:
            system_prompt: The orchestrator routing prompt (from DB config).
            rag_prompt: The RAG synthesis prompt (from DB config).
            llm: A ChatOpenAI instance (created via llm_provider).
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self.rag_prompt = rag_prompt
        print("[Orchestrator] Initialized (config-driven).")

    def route_request(self, messages: list) -> dict:
        """Decide which agent should handle the request."""
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Extract valid JSON block to bypass <think> tags or markdown
            cleaned = content.strip()
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx+1]
                
            print(f"[Orchestrator] RAW LLM OUTPUT (Cleaned): {cleaned!r}")
            return json.loads(cleaned)
        except Exception as e:
            print(f"[Orchestrator] Routing error: {e}")
            return {"target": "error", "message": str(e)}

    def execute(self, user_query: str, chat_history: list = None) -> dict:
        """
        Route the user query and return the routing decision.
        Does NOT call sub-agents — that's the agent_engine's job.

        Returns:
            dict: {"target": "rag_agent"|"direct_response", "parameters": {...}}
        """
        chat_history = chat_history or []

        # Build messages
        messages = [SystemMessage(content=self.system_prompt)]
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_query))

        # Get routing decision
        command = self.route_request(messages)
        print(f"[Orchestrator] Route: {command.get('target', 'unknown')}")
        return command

    def synthesize_answer(self, query: str, context: str) -> str:
        """
        Synthesize a natural language answer from RAG context.
        Uses the rag_prompt (synthesis prompt) from config.
        """
        messages = [
            SystemMessage(content=self.rag_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nUser Question: {query}"),
        ]
        response = self.llm.invoke(messages)
        return response.content
