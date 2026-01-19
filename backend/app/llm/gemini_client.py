from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

    llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.3
)