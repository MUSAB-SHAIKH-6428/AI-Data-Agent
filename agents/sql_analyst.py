import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from Model.Schema import AgentSchema

# -------------------------------------------AI AGENT CODE-------------------------------------------

def curate_ques(state: AgentSchema) -> AgentSchema:
    user_question = state.user_question

    llm = pick_llm("low")

    response = llm.invoke(f"Curate the following Question {user_question}")

    state.curated_ques = response
    return state

def prompt_query_context(state: AgentSchema) -> AgentSchema:
    curated_question = state.curate_ques




