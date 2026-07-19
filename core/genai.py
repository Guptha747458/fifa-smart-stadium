"""GenAI Core: LLM orchestration + multilingual translation + RAG retriever.

This module is the "brain" of StadiumGenius AI. It is designed to use a real LLM
when an API key is present, but ships with a deterministic, explainable simulated
GenAI fallback so the solution runs fully offline at the hackathon without keys.

Real LLM hook: set GEMINI_API_KEY or OPENAI_API_KEY and we attempt a chat call.
Otherwise we use a rule-based "simulated GenAI" that mirrors RAG + translation.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from data.knowledge import KNOWLEDGE_DOCS, LANGUAGES, PHRASEBOOK

LANG_NAMES = {c: n for c, n in LANGUAGES}


@dataclass
class GenAIConfig:
    mode: str = "auto"  # auto | real | simulated
    provider: str = "openai"  # openai | gemini
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"


def load_config() -> GenAIConfig:
    # Try to load .env file if it exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")
        except Exception as e:
            print(f"Error loading .env file: {e}")

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    
    if gemini_key:
        return GenAIConfig(
            mode="real",
            provider="gemini",
            model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com",
        )
    elif openai_key:
        return GenAIConfig(
            mode="real",
            provider="openai",
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=openai_key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    else:
        return GenAIConfig(
            mode="simulated",
            provider="openai",
            model="gpt-4o-mini",
            api_key="",
            base_url="",
        )


# ---------------------------------------------------------------------------
# RAG retriever (keyword + token overlap scoring)
# ---------------------------------------------------------------------------
def _tokenize(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(query: str, top_k: int = 3):
    q = _tokenize(query)
    scored = []
    for doc in KNOWLEDGE_DOCS:
        text = doc["text"] + " " + doc["title"] + " " + doc["category"]
        d = _tokenize(text)
        overlap = len(q & d)
        if overlap:
            scored.append((overlap, doc))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:top_k]]


# ---------------------------------------------------------------------------
# Simulated multilingual translation
# We map known phrases; for unknown text we produce a clearly-labeled
# transliteration-style stub so the UI demonstrates the 50+ language flow.
# ---------------------------------------------------------------------------
def translate(text: str, target_lang: str, source_lang: str = "en", cfg: GenAIConfig = None) -> dict:
    if target_lang not in LANG_NAMES:
        return {"ok": False, "error": f"Unsupported language: {target_lang}"}
    # exact phrasebook match (any direction via reverse lookup)
    for key, langs in PHRASEBOOK.items():
        for src, val in langs.items():
            if text.strip().lower() == val.lower():
                out = langs.get(target_lang, langs["en"])
                return {"ok": True, "source": src, "target": target_lang,
                        "text": out, "method": "phrasebook"}
                        
    # Try using real LLM if configured
    cfg = cfg or load_config()
    if cfg.mode == "real":
        system_prompt = (
            f"You are a professional translator. Translate the user's input text from "
            f"{LANG_NAMES.get(source_lang, source_lang)} to {LANG_NAMES[target_lang]}. "
            "Output ONLY the translated text, with no extra explanations or markdown wrapper."
        )
        try:
            translated_text = _real_chat(system_prompt, text, cfg)
            if not translated_text.startswith("[StadiumGenius AI"):
                return {
                    "ok": True,
                    "source": source_lang,
                    "target": target_lang,
                    "text": translated_text,
                    "method": "real"
                }
        except Exception as e:
            print(f"Real translation failed, falling back: {e}")

    # fallback: simulated. Real deployment would call an NMT model.
    name = LANG_NAMES[target_lang]
    if target_lang == "en":
        return {"ok": True, "source": source_lang, "target": "en",
                "text": text, "method": "simulated-passthrough"}
    return {
        "ok": True, "source": source_lang, "target": target_lang,
        "text": f"[{name}] {text}",  # clearly-marked simulated translation
        "method": "simulated",
    }


# ---------------------------------------------------------------------------
# LLM chat (RAG-grounded). Real call when configured, else simulated answer.
# ---------------------------------------------------------------------------
def _real_chat(system: str, user: str, cfg: GenAIConfig) -> str:
    try:
        import urllib.request
        if cfg.provider == "gemini":
            payload = json.dumps({
                "system_instruction": {
                    "parts": [{"text": system}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                }
            }).encode()
            url = f"{cfg.base_url.rstrip('/')}/v1beta/models/{cfg.model}:generateContent?key={cfg.api_key}"
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            payload = json.dumps({
                "model": cfg.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
            }).encode()
            req = urllib.request.Request(
                cfg.base_url.rstrip("/") + "/chat/completions", data=payload,
                headers={"Authorization": f"Bearer {cfg.api_key}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:  # fall back to simulated on any failure
        print(f"GenAI Error ({cfg.provider}): {e}")
        return _simulated_answer(system, user)


def _simulated_answer(system: str, user: str) -> str:
    docs = retrieve(user, top_k=3)
    if not docs:
        return ("I'm StadiumGenius AI. I can help with navigation, accessibility, "
                "emergencies, transit, and stadium rules. Could you rephrase?")
    primary = docs[0]
    resp = f"[StadiumGenius AI · grounded in {primary['category']}]\n{primary['text']}"
    if len(docs) > 1:
        resp += "\n\nRelated: " + "; ".join(d["title"] for d in docs[1:])
    return resp


def chat(user_message: str, language: str = "en", cfg: GenAIConfig = None) -> dict:
    cfg = cfg or load_config()
    # Retrieve RAG context, then respond in the user's language.
    docs = retrieve(user_message, top_k=3)
    context = "\n".join(f"- {d['title']}: {d['text']}" for d in docs)
    system = (
        "You are StadiumGenius AI, an assistant for FIFA World Cup 2026 fans, "
        "staff and volunteers. Answer ONLY using the provided context. "
        "Be concise, friendly, and accessibility-aware. "
        "Respond in the user's language.\n\nContext:\n" + context
    )
    if cfg.mode == "real":
        answer = _real_chat(system, user_message, cfg)
    else:
        answer = _simulated_answer(system, user_message)
    # Translate answer to requested language if not English.
    if language != "en":
        tr = translate(answer, language, "en")
        answer = tr.get("text", answer)
    return {
        "answer": answer,
        "language": language,
        "sources": [d["id"] for d in docs],
        "mode": cfg.mode,
    }


def recommend_fan_experience(phase: str, preferences: list = None, language: str = "en", cfg: GenAIConfig = None) -> dict:
    cfg = cfg or load_config()
    preferences = preferences or []
    pref_str = ", ".join(preferences) if preferences else "any interest"
    user_query = f"Recommend stadium activities and food options for a fan during {phase} who likes {pref_str}."
    
    docs = retrieve(user_query, top_k=3)
    context = "\n".join(f"- {d['title']}: {d['text']}" for d in docs)
    
    system = (
        "You are StadiumGenius AI. Recommend the best fan experience, food, or activities "
        "given the current match phase and user preferences. Use the context provided. "
        "Be concise, friendly, and structured. Respond in the requested language."
    )
    
    if cfg.mode == "real":
        answer = _real_chat(system, f"Phase: {phase}. Preferences: {pref_str}. Context:\n{context}", cfg)
    else:
        # Simulated responses
        food_recs = "Visit Food Vendor #1 (North Concourse) for delicious Halal/Veg options, or Food Vendor #2 (East Concourse) for local cuisines."
        custom_rec = "Check out the official FIFA Fan Zone outside Gate A for live music and activities."
        if phase == "pre_gates" or phase == "pre_peak":
            custom_rec = "Gates are opening! Beat the queues at GATE_A/B and get a picture with the giant World Cup Trophy at the North Concourse."
        elif phase == "halftime":
            custom_rec = "Halftime show starts now! Grab a quick snack via mobile ordering to avoid the 15-minute rush."
        elif phase == "end_peak" or phase == "egress":
            custom_rec = "Don't rush out! Enjoy post-match interviews on the big screens or shop for exclusive souvenirs at the Fan Info Desk."
            
        answer = f"[StadiumGenius AI Recommendations]\n\n🏟️ **Activity**: {custom_rec}\n\n🍔 **Food/Drink**: {food_recs}\n\n🌱 **Green Tip**: Deposit your cups in smart bins to earn Green Points!"
        
    if language != "en":
        tr = translate(answer, language, "en")
        answer = tr.get("text", answer)
        
    return {
        "ok": True,
        "recommendation": answer,
        "mode": cfg.mode
    }


def generate_incident_response(incident: dict, cfg: GenAIConfig = None) -> dict:
    cfg = cfg or load_config()
    kind = incident.get("kind", "incident")
    node = incident.get("node", "Unknown Location")
    severity = incident.get("severity", "medium")
    
    query = f"Emergency response protocol for {kind} incident at {node} with {severity} severity."
    docs = retrieve(query, top_k=2)
    context = "\n".join(f"- {d['title']}: {d['text']}" for d in docs)
    
    system = (
        "You are StadiumGenius AI, an expert dashboard responder for stadium safety operations. "
        "Recommend immediate operational steps, staff allocations, and announcements to broadcast "
        "for the logged incident. Be extremely precise, professional, and clear."
    )
    
    user_prompt = f"Incident Details:\n- Kind: {kind}\n- Node: {node}\n- Severity: {severity}\n\nContext:\n{context}"
    
    if cfg.mode == "real":
        answer = _real_chat(system, user_prompt, cfg)
    else:
        # High quality simulated emergency protocols
        if kind == "medical":
            answer = (
                f"🚨 **[URGENT RESPONSE: MEDICAL]**\n"
                f"1. **Staff Allocation**: Dispatch nearest medical responders to **{node}** immediately.\n"
                f"2. **Wayfinding**: Instruct stewards at GATE_A / North Concourse to clear the path for emergency personnel.\n"
                f"3. **Broadcast**: Send local alert to adjacent fans: 'Medical assistance is on the way. Please keep corridors clear.'\n"
                f"4. **Action**: Prep First Aid Station (green cross) for incoming patient."
            )
        elif kind == "crowd_surge":
            answer = (
                f"⚠️ **[URGENT RESPONSE: CROWD SURGE]**\n"
                f"1. **Flow Control**: Deploy 6 stewards to **{node}** to initiate entry throttling immediately.\n"
                f"2. **Dynamic Re-routing**: Update app routing to divert incoming fans to alternative zones.\n"
                f"3. **Broadcast**: Activate calming audio guidance: 'For your safety, please proceed slowly. Adjacent concourses are fully open.'\n"
                f"4. **Action**: Open emergency relief gates and disable any opposing physical flow."
            )
        elif kind == "security":
            answer = (
                f"🛡️ **[RESPONSE: SECURITY PROTOCOL]**\n"
                f"1. **Dispatch**: Alert safety stewards and venue security to investigate **{node}**.\n"
                f"2. **CCTV**: Direct command center camera feed to focus on the area.\n"
                f"3. **Guidance**: Instruct staff to maintain clear paths and report updates to central operations."
            )
        else:
            answer = (
                f"📋 **[RESPONSE: OPERATIONAL PROTOCOL]**\n"
                f"1. **Staff**: Send nearby volunteers to **{node}** to assist fans.\n"
                f"2. **Information**: Broadcast updates on local stadium screens and mobile app notifications.\n"
                f"3. **Incident Log**: Maintain active logging and standby for coordinator instructions."
            )
            
    return {
        "ok": True,
        "response_steps": answer,
        "mode": cfg.mode
    }


if __name__ == "__main__":
    print(json.dumps(chat("where can I charge my EV and park?"), indent=2))
    print(json.dumps(translate("Where is the nearest exit?", "ar"), indent=2))

