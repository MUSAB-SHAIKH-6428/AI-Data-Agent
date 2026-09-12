import logging
import warnings
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Silence warnings and Google SDK AFC logs
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

load_dotenv()

def pick_llm(model_level: str):
    level = model_level.lower().strip()

    if level == "low":
        llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
    elif level == "medium":
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    elif level == "high":
        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0)
    else:
        raise ValueError(f"Unsupported Level: {model_level}")

    return llm

if __name__ == "__main__":
    llm_obj = pick_llm("low")
    res = llm_obj.invoke("Capital of India?")
    print(res.text)
