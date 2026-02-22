import os
from google import genai
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("LLM_API_KEY")

if not api_key:
    raise ValueError("LLM_API_KEY not set")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Say hello in one sentence.",
)

print("LLM Response:")
print(response.text)
