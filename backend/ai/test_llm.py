
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL")

if not key or key == "YOUR_API_KEY_HERE" or not model or model == "YOUR_MODEL_NAME":
    raise SystemExit("Configure LLM_API_KEY and LLM_MODEL in .env first")

client = OpenAI(
    api_key=key,
    base_url=os.getenv("LLM_BASE_URL") or None,
    timeout=15.0
)

response = client.chat.completions.create(
    model=model,
    temperature=0.2,
    response_format={"type": "json_object"},
    messages=[
        {
            "role": "system",
            "content": "Return a JSON object with status and message fields."
        },
        {
            "role": "user",
            "content": "Return status success and message ShadowTwin AI ready."
        }
    ]
)

data = json.loads(response.choices[0].message.content)

assert data["status"] == "success"
assert isinstance(data["message"], str)

print("REAL LLM JSON TEST SUCCESS")
print(json.dumps(data, indent=2))
