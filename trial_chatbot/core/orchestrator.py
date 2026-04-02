"""
Orchestrator — Routes user queries to the appropriate agent.
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class MainOrchestrator:
    def __init__(self, system_prompt: str, rag_prompt: str, llm):
        self.llm = llm
        self.system_prompt = system_prompt
        self.rag_prompt = rag_prompt

    def route_request(self, messages: list) -> dict:
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
            return {"target": "error", "message": str(e)}

    def execute(self, user_query: str, chat_history: list = None) -> dict:
        chat_history = chat_history or []
        messages = [SystemMessage(content=self.system_prompt)]
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_query))
        command = self.route_request(messages)
        print(f"[Orchestrator] Route: {command.get('target')}")
        return command

    def synthesize_answer(self, query: str, context: str) -> str:
        messages = [
            SystemMessage(content=self.rag_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nUser Question: {query}"),
        ]
        return self.llm.invoke(messages).content
