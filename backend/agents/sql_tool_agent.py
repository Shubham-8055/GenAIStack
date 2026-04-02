"""
SQL Tool Agent: Custom XML Loop Implementation
"""
import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase

class SQLToolAgent:
    def __init__(self, system_prompt: str, llm, db_uri: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.db_uri = db_uri
        
        sync_uri = db_uri.replace("+asyncpg", "") if db_uri else ""
        
        try:
            if sync_uri:
                self.db = SQLDatabase.from_uri(sync_uri)
                self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
                self.tools = {t.name: t for t in self.toolkit.get_tools()}
                print("[SQLToolAgent] Successfully connected and initialized Custom XML SQL agent.")
            else:
                self.tools = None
                print("[SQLToolAgent] No database URI provided.")
        except Exception as e:
            print(f"[SQLToolAgent] Init error: {e}")
            self.tools = None

    def execute(self, user_query: str, chat_history: list = None) -> str:
        if not self.tools:
            return "Error: Could not connect to the external database. Please check the DB connection string in Agent Settings."
        
        tool_descriptions = "\n".join([f"- {name}: {t.description}" for name, t in self.tools.items()])
        prompt = f"""{self.system_prompt}

You have access to the following tools to interact with the SQL database:
{tool_descriptions}

Whenever you need to use a tool, you MUST strictly output ONLY the following XML block:
<minimax:tool_call>
<invoke name="tool_name">
<parameter name="query">tool input here</parameter>
</invoke>
</minimax:tool_call>

You must use 'sql_db_list_tables' to see existing tables before querying.
Use 'sql_db_schema' to get the schema of specific tables (pass table names in query param).
Use 'sql_db_query' to execute SQL.

If you don't need a tool or you have your final answer, just output regular text (do not use XML).
"""

        messages = [SystemMessage(content=prompt)]
        if chat_history:
            for msg in chat_history[-4:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                     messages.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
        
        messages.append(HumanMessage(content=user_query))

        try:
            for step in range(6): # Max 6 steps
                response = self.llm.invoke(messages)
                content = response.content
                print(f"[SQLToolAgent] Step {step+1} LLM output: {content!r}")
                messages.append(AIMessage(content=content))
                
                if "<invoke name=" in content:
                    target_match = re.search(r'<invoke name="([^"]+)">', content)
                    param_match = re.search(r'<parameter name="([^"]+)">([^<]*)</parameter>', content)
                    
                    if target_match:
                        tool_name = target_match.group(1)
                        tool_input = param_match.group(2).strip() if param_match else ""
                        
                        if tool_name in self.tools:
                            tool = self.tools[tool_name]
                            print(f"[SQLToolAgent] Invoking {tool_name} with {tool_input!r}")
                            try:
                                if tool_name == "sql_db_list_tables":
                                    tool_res = str(tool.invoke(""))
                                else:
                                    tool_res = str(tool.invoke(tool_input))
                            except Exception as e:
                                tool_res = f"Error executing tool: {e}"
                        else:
                            tool_res = f"Tool {tool_name} not found."
                            
                        print(f"[SQLToolAgent] Tool Output (len={len(tool_res)})")
                        messages.append(HumanMessage(content=f"Tool Output:\n{tool_res}"))
                    else:
                        messages.append(HumanMessage(content="Error: Could not parse <invoke name> tag."))
                else:
                    return content # Final answer
            return "Agent stopped after too many internal query steps."
        except Exception as e:
            print(f"[SQLToolAgent] Execution error: {e}")
            return f"An error occurred while querying the database: {str(e)}"
