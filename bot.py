import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd

# Load the dataset
df = pd.read_csv("updated_data.csv")
load_dotenv()
TELE_TOKEN=os.getenv("TELEGRAM_API_KEY")
GROQ_API_KEY=os.getenv("GROQ_API_KEY")

os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "sevabot_project")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am SevaBot, your assistant for finding government schemes in India. Please tell me about your query or the issue you are facing, and I will try to find relevant government schemes for you.")
    return "QUERY"

def llm_setup(user_detail: str):
    prompt=ChatPromptTemplate.from_messages([
        ("system", f"You are a helpful assistant that provides information "
        "about the Government Schemes provided by central and state government "
        "to the citizens of India. You will be given the detail about  the user"
        "you have to provide the relevant information about the government schemes that are related to the details provided by the user. You should provide the name of the scheme, a brief description, and a link to the official website of the scheme if available. If there are multiple schemes related to the query, "
        "you should provide information about all of them."
        f"Use this dataset as your knowledge base: {df.to_string()}"
        " If there are no schemes related "
        "to the query, you should respond with Any with any 3-4 relevant government schemes found in the dataset that are related to the user request. Always provide the information in a clear and concise manner."),

    ])
    llm=ChatGroq(model_name="openai/gpt-oss-20b", groq_api_key=GROQ_API_KEY, temperature=0.2)
    return prompt | llm | StrOutputParser()
    


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):


    response=llm_setup(user_detail=update.message.text).invoke({}).strip()
    await update.message.reply_text(response)

def main():
    app=Application.builder().token(TELE_TOKEN).build()
    conv_handler=ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            "QUERY": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    print("SevaBot is running...")
    app.run_polling()

if __name__ == "__main__": 
    main()