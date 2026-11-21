import json, re, time
from groq import Groq

MODEL = "openai/gpt-oss-120b"


def get_client(api_key):
    return Groq(api_key=api_key)


def _is_rate(e):
    return "429" in str(e) or "rate" in str(e).lower()


def _call(client, messages, json_mode, temperature=0.1):
    base = dict(model=MODEL, messages=messages, temperature=temperature, max_completion_tokens=4096)
    first = {"reasoning_effort": "low"}
    if json_mode:
        first["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(3):
        for extra in (first, {}):  # fall back to plain call if an option is rejected
            try:
                r = client.chat.completions.create(**base, **extra)
                return r.choices[0].message.content or ""
            except Exception as e:
                last = e
                if _is_rate(e):
                    time.sleep(3 * (attempt + 1))
                    break
        else:
            break
    raise last


def parse_json(text):
    text = re.sub(r"```(?:json)?", "", text)
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1])


def chat_json(client, system, user):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for _ in range(2):
        try:
            return parse_json(_call(client, msgs, True))
        except (json.JSONDecodeError, ValueError):
            continue
    raise RuntimeError("The model did not return valid JSON. Please try again.")


def chat_text(client, system, user):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return _call(client, msgs, False, temperature=0.3).strip()
