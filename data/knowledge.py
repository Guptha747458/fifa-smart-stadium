"""Simulated multilingual knowledge base for RAG + translation.

Provides stadium rules, emergency info, local customs, accessibility services,
and a phrasebook across 50+ languages for the multilingual assistant.
"""
import json
from pathlib import Path

LANGUAGES = [
    ("en", "English"), ("es", "Spanish"), ("fr", "French"), ("pt", "Portuguese"),
    ("de", "German"), ("it", "Italian"), ("ar", "Arabic"), ("zh", "Chinese"),
    ("ja", "Japanese"), ("ko", "Korean"), ("ru", "Russian"), ("hi", "Hindi"),
    ("bn", "Bengali"), ("ur", "Urdu"), ("tr", "Turkish"), ("fa", "Persian"),
    ("id", "Indonesian"), ("vi", "Vietnamese"), ("th", "Thai"), ("ms", "Malay"),
    ("nl", "Dutch"), ("pl", "Polish"), ("uk", "Ukrainian"), ("sv", "Swedish"),
    ("no", "Norwegian"), ("da", "Danish"), ("fi", "Finnish"), ("cs", "Czech"),
    ("el", "Greek"), ("he", "Hebrew"), ("ro", "Romanian"), ("hu", "Hungarian"),
    ("bg", "Bulgarian"), ("hr", "Croatian"), ("sr", "Serbian"), ("sk", "Slovak"),
    ("sl", "Slovenian"), ("lt", "Lithuanian"), ("lv", "Latvian"), ("et", "Estonian"),
    ("sw", "Swahili"), ("am", "Amharic"), ("yo", "Yoruba"), ("ig", "Igbo"),
    ("zu", "Zulu"), ("af", "Afrikaans"), ("xh", "Xhosa"), ("tn", "Tswana"),
    ("fil", "Filipino"), ("ta", "Tamil"), ("te", "Telugu"), ("ml", "Malayalam"),
    ("pa", "Punjabi"), ("ne", "Nepali"), ("si", "Sinhala"), ("my", "Burmese"),
    ("km", "Khmer"), ("lo", "Lao"), ("ka", "Georgian"), ("az", "Azerbaijani"),
]

# RAG documents: stadium operations knowledge
KNOWLEDGE_DOCS = [
    {
        "id": "rule-bag",
        "category": "stadium_rules",
        "title": "Prohibited Items",
        "text": "Bags larger than 14x14x6 inches are prohibited. No outside food or drinks. "
                "Clear bag policy enforced. No professional cameras, drones, or laser pointers. "
                "Only empty reusable bottles under 32oz allowed.",
    },
    {
        "id": "rule-entry",
        "category": "stadium_rules",
        "title": "Entry & Security",
        "text": "All fans must pass through metal detectors and show match ticket + valid ID. "
                "Gates open 3 hours before kickoff. Arrive early to avoid bottlenecks at GATE_A and GATE_B.",
    },
    {
        "id": "emerg-medical",
        "category": "emergency",
        "title": "Medical Emergency",
        "text": "In a medical emergency, locate the nearest First Aid station (marked green cross) "
                "or tell any steward. For life-threatening situations call the venue emergency line. "
                "Accessible medical assistance is available at all concourses.",
    },
    {
        "id": "emerg-evac",
        "category": "emergency",
        "title": "Evacuation",
        "text": "During evacuation follow stewards to the nearest Emergency Exit (EXIT_N / EXIT_S). "
                "Do not use elevators during fire evacuation; use ramps and accessible routes. "
                "Wheelchair users should proceed to marked refuge areas.",
    },
    {
        "id": "acc-services",
        "category": "accessibility",
        "title": "Accessibility Services",
        "text": "Wheelchair-accessible seating is in Section 340 (upper) via Elevator 1. "
                "Companion seating, assistive listening devices, and sensory bags available at Fan Info Desk. "
                "Step-free routes use RAMP_1 and ELEV_1. Live captioning and sign-language interpretation "
                "available on the official app.",
    },
    {
        "id": "transit-plan",
        "category": "transportation",
        "title": "Getting To/From Stadium",
        "text": "Transit Hub (north-west) connects to rail and bus. Shuttle Stop serves last-mile. "
                "East Parking has EV charging. Post-match, expect 45-60 min egress; use TRANSIT_HUB "
                "or staggered shuttle departures to avoid gridlock.",
    },
    {
        "id": "customs",
        "category": "local_customs",
        "title": "Local Customs & Etiquette",
        "text": "Tipping 15-20% at restaurants is customary. Public transit is card/contactless only. "
                "Be respectful of diverse fans; photography of others without consent is discouraged.",
    },
    {
        "id": "sustain",
        "category": "sustainability",
        "title": "Sustainability",
        "text": "Recycling and compost bins are paired at every food vendor. Bring a reusable bottle. "
                "Choose plant-based meal options to lower carbon footprint. Vendors track inventory to "
                "reduce food waste.",
    },
    {
        "id": "food-bev",
        "category": "food_beverage",
        "title": "Food & Beverage Offerings",
        "text": "Diverse food options including Halal, Kosher, Vegetarian, Vegan, Gluten-Free. Food Vendor #1 features Halal and Vegetarian specialities. Local delicacies at Food Vendor #2. Mobile ordering available in the app to skip queues. Sustainability-first sourcing.",
    },
    {
        "id": "ev-parking",
        "category": "transportation",
        "title": "Parking & EV Charging",
        "text": "East Parking has 40 EV charging spaces (Level 2). Parking must be pre-booked online. Shuttle service operates between Gate A and the Shuttle Stop. Carpooling gets a 20% discount on parking fees.",
    },
    {
        "id": "weather-info",
        "category": "weather",
        "title": "Weather Contingencies",
        "text": "In case of severe rain, lightning, or extreme heat, fans should seek shelter in the covered concourses. Event operations may stagger entrance timings. Bottled water distribution points will open automatically.",
    },
    {
        "id": "security-info",
        "category": "security",
        "title": "Security & Lost Items",
        "text": "Report lost items or suspicious activities to nearest steward. Main lost & found desk is at Fan Info Desk (North Concourse). Children safety wristbands are available free of charge at all gates.",
    },
    {
        "id": "volunteer-tips",
        "category": "volunteer_training",
        "title": "Volunteer Customer Service",
        "text": "Assist disabled fans proactively. Direct wheelchair users to elevator or ramp. Smile and use translation tools for international fans. Always know the nearest First Aid location.",
    },
    {
        "id": "social-tips",
        "category": "social_experience",
        "title": "Fan Social Zones & Photo Spots",
        "text": "Official Fan Zone is outside Gate A. Giant trophy photo op is located on the North Concourse. Tag your photos with #FIFA2026Genius for a chance to be featured on the stadium big screens.",
    },
    {
        "id": "sustain-game",
        "category": "sustainability",
        "title": "Green Fan Rewards",
        "text": "Gamify your green impact! Deposit plastic cups in smart bins to earn points. Redeem points for food discounts and exclusive merchandise. Carbon offset matches are available via the platform.",
    },
    {
        "id": "accessible-paths",
        "category": "accessibility",
        "title": "Accessible Routing Details",
        "text": "Ramps (RAMP_1) provide step-free access to North and West concourses. Elevator (ELEV_1) links North Concourse to Section 340 (wheelchair seating). Sensory room is located near Section 101.",
    },
]

# A small phrasebook for the translation demo (key phrases in several langs).
PHRASEBOOK = {
    "where_is_restroom": {
        "en": "Where is the nearest restroom?", "es": "¿Dónde está el baño más cercano?",
        "fr": "Où sont les toilettes les plus proches ?", "ar": "أين أقرب دورة مياه؟",
        "zh": "最近的洗手间在哪里？", "ja": "一番近いトイレはどこですか？",
        "pt": "Onde fica o banheiro mais próximo?", "de": "Wo ist die nächste Toilette?",
    },
    "help_medical": {
        "en": "I need medical help.", "es": "Necesito ayuda médica.", "fr": "J'ai besoin d'aide médicale.",
        "ar": "أحتاج إلى مساعدة طبية.", "zh": "我需要医疗帮助。", "ja": "医療の助けが必要です。",
        "pt": "Preciso de ajuda médica.", "de": "Ich brauche medizinische Hilfe.",
    },
    "exit_where": {
        "en": "Where is the nearest exit?", "es": "¿Dónde está la salida más cercana?",
        "fr": "Où est la sortie la plus proche ?", "ar": "أين أقرب مخرج؟",
        "zh": "最近的出口在哪里？", "ja": "一番近い出口はどこですか？",
        "pt": "Onde fica a saída mais próxima?", "de": "Wo ist der nächste Ausgang?",
    },
}


def export_json(path=None):
    out = {
        "languages": [{"code": c, "name": n} for c, n in LANGUAGES],
        "knowledge": KNOWLEDGE_DOCS,
        "phrasebook": PHRASEBOOK,
    }
    if path:
        Path(path).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    export_json(Path(__file__).parent / "knowledge.json")
    print("knowledge.json written")
