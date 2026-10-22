
import os
import json

from dotenv import load_dotenv
from openai import OpenAI

from .explain import explain_path

load_dotenv()


def explain_with_ai(hops):
    baseline = explain_path(hops)

    provider = os.getenv(
        "LLM_PROVIDER", "offline"
    ).lower()

    if provider == "offline":
        baseline["mode"] = "offline"
        return baseline

    try:
        if provider == "ollama":
            client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
                timeout=12.0
            )
            model = os.getenv(
                "OLLAMA_MODEL", "qwen2.5:7b"
            )

        elif provider == "cloud":
            key = os.getenv("LLM_API_KEY")
            model = os.getenv("LLM_MODEL")

            if not key or not model:
                raise ValueError(
                    "Missing LLM_API_KEY or LLM_MODEL"
                )

            client = OpenAI(
                api_key=key,
                base_url=os.getenv(
                    "LLM_BASE_URL"
                ) or None,
                timeout=12.0
            )
        else:
            raise ValueError("Unknown provider")

        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={
                "type": "json_object"
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cybersecurity analyst. "
                        "Rewrite ONLY the supplied explanations "
                        "in clear professional English. "
                        "Do not invent assets, techniques, "
                        "vulnerabilities or probabilities. "
                        "Return JSON with a 'steps' array. "
                        "Each step must have edge_id, "
                        "technique_id and text. "
                        "Keep IDs exactly unchanged. "
                        "Mention both IDs in every text."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps(baseline)
                }
            ]
        )

        content = json.loads(
            response.choices[0].message.content
        )

        ai_steps = content.get("steps")

        if not isinstance(ai_steps, list):
            raise ValueError("Invalid AI steps")

        if len(ai_steps) != len(baseline["steps"]):
            raise ValueError("Step count mismatch")

        for original, generated in zip(
            baseline["steps"], ai_steps
        ):
            edge = original["edge_id"]
            technique = original["technique_id"]

            if (
                generated.get("edge_id") != edge
                or generated.get("technique_id") != technique
                or not isinstance(
                    generated.get("text"), str
                )
                or edge not in generated["text"]
                or technique not in generated["text"]
            ):
                raise ValueError("AI response mismatch")

        baseline["steps"] = ai_steps
        baseline["mode"] = "ai"

    except Exception as exc:
        print("LLM FALLBACK REASON:", type(exc).__name__)
        baseline["mode"] = "offline_fallback"


    return baseline
