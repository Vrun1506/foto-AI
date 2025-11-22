from dotenv import load_dotenv
from pyagentspec.llms import OpenAiConfig
from pyagentspec.agent import Agent
from wayflowcore.agentspec import AgentSpecLoader # I am using this for execution of the user's request. The agent will output the response.

load_dotenv()

# 1. Define Configuration
llm_config = OpenAiConfig(
    name="GPT-5.1 Model",
    model_id="gpt-5.1",
)

system_instructions = """
You are a helpful tutor bot. Answer the user's questions clearly and concisely.
"""

agent_spec = Agent(
    name="Tutor Agent",
    system_prompt=system_instructions,
    llm_config=llm_config
)

# 3. Load the Spec into the Runtime
loader = AgentSpecLoader()
runtime_agent = loader.load_component(agent_spec)

# 4. Execution
conversation = runtime_agent.start_conversation()

user_question = "What is an LLM?"
print(f"User: {user_question}")
conversation.append_user_message(user_question)

conversation.execute()

response = conversation.get_last_message()
print(f"Agent: {response.content}")