import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import sql_analyst
from utils.llm_pick import pick_llm
from utils.elt_tools import ELTTools
from Model.Schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst


llm = pick_llm("medium")                                                                                                                   
llm_router = llm.with_structured_output(RouterSchema)                                                                                      
                                                             
# ---------------------------- DATA AGENT GRAPH ---------------------------- #                                                             
                                                                                                                                            
def router_node(state: DataAgentSchema):                                                                                                   
    message = state.messages[-1].content                                                                                                   
    route_response_dict = llm_router.invoke(message).model_dump()                                                                          
    state.route_response = route_response_dict['answer']                                                                                   
    return state                                                                                                                           
                                                                                                                                            
                                                                                                                                            
def etl_node(state: DataAgentSchema):                                                                                                      
    message = state.messages[-1].content                                                                                                   
    response = etl_analyst.invoke(                                                                                                         
        {"messages": [HumanMessage(content=str(message))]}                                                                                 
    )                                                                                                                                      
    # final AI message from the sub-agent response by extraction                                                                            
    final_msg = response["messages"][-1]                                                                                                   
    state.messages = state.messages + [final_msg]                                                                                          
    return state                                                                                                                           
                                                                                                                                            
                                                                                                                                            
def sql_node(state: DataAgentSchema):                                                                                                      
    message = state.messages[-1].content                                                                                                   
    input_schema = {                                                                                                                       
        "messages": [],                                                                                                                    
        "user_question": str(message),                                                                                                     
        "curated_ques": "",                                                                                                                
        "prompt_query_context": "",                                                                                                        
        "generated_sql_query": "",                                                                                                         
        "is_safe": "No",                                                                                                                   
        "comments": "",                                                                                                                    
        "sql_query_execution_result": "",                                                                                                  
        "final_answer": ""                                                                                                                 
    }                                                                                                                                      
                                                                                                                                            
    response = sql_analyst.invoke(input_schema)                                                                                            
    state.messages = state.messages + [AIMessage(content=response['final_answer'])]                                                        
    return state                                                                                                                           
                                                                                                                                            
                                                                                                                                            
data_agent_graph = StateGraph(DataAgentSchema)                                                                                             


data_agent_graph.add_node("router_node", router_node)                                                                                      
data_agent_graph.add_node("etl_node", etl_node)                                                                                            
data_agent_graph.add_node("sql_node", sql_node)                                                                                            


data_agent_graph.add_edge(START, "router_node")                                                                                            
                                                                                                                                            
                                                                                                                                            
def route_edge(state: DataAgentSchema) -> str:                                                                                             
    if state.route_response == "sql":                                                                                                      
        return "sql_node"                                                                                                                  
    elif state.route_response == "etl":                                                                                                    
        return "etl_node"                                                                                                                  
    else:                                                                                                                                  
        raise ValueError(f"Invalid route response: {state.route_response}")                                                                
                                                                                                                                            
                                                                                                                                            
data_agent_graph.add_conditional_edges(                                                                                                    
    "router_node",                                                                                                                         
    route_edge,                                                                                                                            
    {                                                                                                                                      
        "sql_node": "sql_node",                                                                                                            
        "etl_node": "etl_node"                                                                                                             
    }                                                                                                                                      
)                                                                                                                                          
                                                                                                                                            
data_agent_graph.add_edge("sql_node", END)                                                                                                 
data_agent_graph.add_edge("etl_node", END)                                                                                                 
                                                                                                                                            
data_agent = data_agent_graph.compile()                                                                                                    
                                                                                                                                            
                                                                                                                                            
if __name__ == "__main__":       

    # Test case 1 

    response = data_agent.invoke({                                                                                                             
    "messages": [HumanMessage(content="What are the top 3 most used payment methods in our database?")],                                   
    "route_response": ""})                                                                                                                                         
    print("Route:", response["route_response"])                                                                                                
    print("Answer:", response["messages"][-1].content)         

    # Test case 2

    response = data_agent.invoke({                                                                                                             
        "messages": [HumanMessage(content="Delete all cancelled rides from the rides table")],                                                 
        "route_response": ""})                                                                                                                                         
    print("Route:", response["route_response"])                                                                                                
    print("Answer:", response["messages"][-1].content)                                                                                    
                                                            