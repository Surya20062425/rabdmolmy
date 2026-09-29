#!/usr/bin/env python3
"""
ORCA — Agentic AI Marine Ecosystem Reasoning Platform
SIH 2026 #176 | ISRO | Disaster Management

Minimal working prototype (1-hour build):
- Natural-language query → intent classification
- Task decomposition into specialized agents (Ocean, Weather, Geospatial, Risk)
- Sample marine data (SST, chlorophyll, PFZ, weather, geofences)
- Spatial-temporal reasoning, safety assessment, geofencing
- Explainable evidence chain + recommendations
- Conversational CLI interface with regional-language support template

Real data APIs (Bhuvan, INCOIS, IMD, Open-Meteo, Marine Regions) plug in
behind the agent interfaces. This prototype uses sample data to demonstrate
the full agentic reasoning flow.
"""

import json, math, re, sys
from datetime import datetime, timedelta
from typing import Any

# ──────────────────────────────────────────────────────────────
# 1. SAMPLE MARINE DATA (production: replace with API calls)
# ──────────────────────────────────────────────────────────────

# Sea Surface Temperature grid (lat, lon, sst_celsius)
SST_DATA = [
    {"lat": 8.5, "lon": 76.5, "sst": 29.2, "chlorophyll": 0.8},
    {"lat": 8.5, "lon": 77.0, "sst": 28.9, "chlorophyll": 1.2},
    {"lat": 9.0, "lon": 76.5, "sst": 28.5, "chlorophyll": 2.1},
    {"lat": 9.0, "lon": 77.0, "sst": 28.1, "chlorophyll": 3.5},
    {"lat": 10.0, "lon": 76.0, "sst": 27.8, "chlorophyll": 1.8},
    {"lat": 10.0, "lon": 77.5, "sst": 27.2, "chlorophyll": 4.2},
    {"lat": 12.0, "lon": 80.0, "sst": 29.5, "chlorophyll": 0.6},
    {"lat": 12.5, "lon": 80.5, "sst": 29.1, "chlorophyll": 0.9},
    {"lat": 13.0, "lon": 81.0, "sst": 28.8, "chlorophyll": 1.5},
    {"lat": 14.0, "lon": 82.0, "sst": 28.3, "chlorophyll": 2.8},
    {"lat": 15.0, "lon": 83.0, "sst": 27.9, "chlorophyll": 3.9},
    {"lat": 16.0, "lon": 84.0, "sst": 27.1, "chlorophyll": 5.2},
    {"lat": 10.5, "lon": 76.2, "sst": 28.0, "chlorophyll": 2.5},
    {"lat": 10.8, "lon": 76.8, "sst": 27.5, "chlorophyll": 3.8},
    {"lat": 11.2, "lon": 77.2, "sst": 27.0, "chlorophyll": 4.8},
]

# Potential Fishing Zones (from INCOIS-style advisory)
PFZ_DATA = [
    {"lat": 10.5, "lon": 76.8, "day": "today", "productivity": "high",
     "species": "mackerel, sardine", "depth_m": 40, "distance_km": 25,
     "from_coast": "off Kerala coast"},
    {"lat": 12.5, "lon": 80.5, "day": "today", "productivity": "high",
     "species": "tuna, mackerel", "depth_m": 60, "distance_km": 40,
     "from_coast": "off Tamil Nadu coast"},
    {"lat": 14.0, "lon": 82.0, "day": "today", "productivity": "moderate",
     "species": "sardine", "depth_m": 35, "distance_km": 30,
     "from_coast": "off Andhra coast"},
    {"lat": 8.5, "lon": 76.5, "day": "today", "productivity": "moderate",
     "species": "mackerel", "depth_m": 25, "distance_km": 15,
     "from_coast": "off Kerala coast"},
]

# Weather forecast data (wind, waves, alerts)
WEATHER_DATA = [
    {"lat": 10.5, "lon": 76.8, "time": "morning", "wind_kt": 12,
     "wave_m": 1.2, "swell_m": 0.8, "gust_kt": 18, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.1},
    {"lat": 10.5, "lon": 76.8, "time": "afternoon", "wind_kt": 18,
     "wave_m": 1.8, "swell_m": 1.0, "gust_kt": 25, "lightning_risk": "moderate",
     "cyclone_alert": False, "tide_m": 0.9},
    {"lat": 10.5, "lon": 76.8, "time": "evening", "wind_kt": 15,
     "wave_m": 1.5, "swell_m": 0.9, "gust_kt": 22, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.3},
    {"lat": 11.5, "lon": 78.0, "time": "morning", "wind_kt": 8,
     "wave_m": 0.7, "swell_m": 0.4, "gust_kt": 12, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.2},
    {"lat": 11.5, "lon": 78.0, "time": "afternoon", "wind_kt": 12,
     "wave_m": 1.0, "swell_m": 0.6, "gust_kt": 18, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.0},
    {"lat": 11.5, "lon": 78.0, "time": "evening", "wind_kt": 10,
     "wave_m": 0.8, "swell_m": 0.5, "gust_kt": 15, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.4},
    {"lat": 12.5, "lon": 80.5, "time": "morning", "wind_kt": 22,
     "wave_m": 2.2, "swell_m": 1.2, "gust_kt": 30, "lightning_risk": "moderate",
     "cyclone_alert": False, "tide_m": 1.0},
    {"lat": 12.5, "lon": 80.5, "time": "afternoon", "wind_kt": 28,
     "wave_m": 2.8, "swell_m": 1.5, "gust_kt": 38, "lightning_risk": "high",
     "cyclone_alert": False, "tide_m": 0.8},
    {"lat": 14.0, "lon": 82.0, "time": "morning", "wind_kt": 10,
     "wave_m": 0.9, "swell_m": 0.5, "gust_kt": 15, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.2},
    {"lat": 8.5, "lon": 76.5, "time": "morning", "wind_kt": 8,
     "wave_m": 0.6, "swell_m": 0.3, "gust_kt": 12, "lightning_risk": "low",
     "cyclone_alert": False, "tide_m": 1.4},
]

# Geofence zones (EEZ boundary, MPAs, restricted waters, fishing closure zones)
GEOZONES = [
    {"name": "Indian EEZ - Arabian Sea", "type": "eez_boundary",
     "min_lat": 8.0, "max_lat": 24.0, "min_lon": 65.0, "max_lon": 89.0,
     "description": "India's Exclusive Economic Zone boundary"},
    {"name": "Indian EEZ - Bay of Bengal", "type": "eez_boundary",
     "min_lat": 4.0, "max_lat": 22.0, "min_lon": 80.0, "max_lon": 100.0,
     "description": "India's EEZ in Bay of Bengal"},
    {"name": "Gulf of Mannar Marine National Park", "type": "mpa",
     "min_lat": 8.5, "max_lat": 9.0, "min_lon": 77.5, "max_lon": 78.5,
     "description": "Marine protected area - fishing restricted"},
    {"name": "Bhitarkanika Wildlife Sanctuary", "type": "mpa",
     "min_lat": 20.0, "max_lat": 20.5, "min_lon": 86.5, "max_lon": 87.0,
     "description": "Marine protected area - turtle nesting ground"},
    {"name": "Gahirmatha Turtle Sanctuary", "type": "mpa",
     "min_lat": 20.0, "max_lat": 20.3, "min_lon": 86.8, "max_lon": 87.2,
     "description": "Turtle nesting ground - no fishing during breeding season"},
    {"name": "West Coast Fishing Closure (Monsoon)", "type": "seasonal_closure",
     "min_lat": 8.0, "max_lat": 14.0, "min_lon": 72.0, "max_lon": 78.0,
     "description": "Mandatory fishing ban period (June-July)"},
    {"name": "East Coast Fishing Closure (Monsoon)", "type": "seasonal_closure",
     "min_lat": 14.0, "max_lat": 22.0, "min_lon": 80.0, "max_lon": 86.0,
     "description": "Mandatory fishing ban period (April-May)"},
    {"name": "International Maritime Boundary - Sri Lanka", "type": "international_boundary",
     "min_lat": 6.0, "max_lat": 10.0, "min_lon": 76.5, "max_lon": 81.0,
     "description": "Approaching international boundary - caution advised"},
]

# Coastal reference points for human-friendly directions
COASTAL_POINTS = [
    {"name": "Kochi (Cochin)", "lat": 9.93, "lon": 76.26, "state": "Kerala"},
    {"name": "Thiruvananthapuram", "lat": 8.48, "lon": 76.94, "state": "Kerala"},
    {"name": "Kanyakumari", "lat": 8.09, "lon": 77.54, "state": "Tamil Nadu"},
    {"name": "Chennai", "lat": 13.08, "lon": 80.27, "state": "Tamil Nadu"},
    {"name": "Visakhapatnam", "lat": 17.68, "lon": 83.21, "state": "Andhra Pradesh"},
    {"name": "Kochchi (Andhra)", "lat": 15.50, "lon": 78.00, "state": "Andhra Pradesh"},
]


# ──────────────────────────────────────────────────────────────
# 2. GEOSPATIAL UTILITIES
# ──────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def point_in_zone(lat: float, lon: float, zone: dict) -> bool:
    """Check if a point lies within a geofence zone (bbox)."""
    return (zone["min_lat"] <= lat <= zone["max_lat"]
            and zone["min_lon"] <= lon <= zone["max_lon"])


def find_zones_for_point(lat: float, lon: float) -> list[dict]:
    """Return all geofence zones containing a point."""
    return [z for z in GEOZONES if point_in_zone(lat, lon, z)]


def nearest_point(target_lat: float, target_lon: float,
                  points: list[dict], lat_key="lat", lon_key="lon") -> tuple:
    """Find the nearest point from a list and return (point, distance_km)."""
    best = None
    best_dist = float("inf")
    for p in points:
        d = haversine_km(target_lat, target_lon, p[lat_key], p[lon_key])
        if d < best_dist:
            best_dist = d
            best = p
    return best, best_dist


# ──────────────────────────────────────────────────────────────
# 3. CONVERSATIONAL INTERFACE — LANGUAGE DETECTION
# ──────────────────────────────────────────────────────────────

# Indian regional language keyword patterns (minimal — production uses
# a proper language-ID model or LLM)
LANG_PATTERNS = {
    "tamil": ["பவள", "மீன்", "படக்", "கடல்", "வேளாண்மை", "வணிகம்",
              "பவளம்", "மீன்பிடி", "கடல்", "நிலம்", "வேளாண்மை"],
    "malayalam": ["മത്സ്യം", "പറക്കുക", "കടൽ", "പടയാളൻ", "മലയാളം",
                  "മീൻ", "കടൽ", "പടയാളൻ"],
    "telugu": ["మత్స్యం", "పడవ", "సముద్రం", "పల్లె", "తెలుగు",
               "మీను", "సముద్రం", "పడవ"],
    "kannada": ["ಮೀನು", "ಹಡಗು", "ಸಮುದ್ರ", "ಕನ್ನಡ", "ಮೀನುಗಾರಿಕೆ",
                 "ಸಮುದ್ರ", "ಹಡಗು"],
    "hindi": ["मत्स्य", "नाव", "समुद्र", "हिंदी", "मछली", "जल", "समुद्र",
              "नाव"],
    "marathi": ["मासे", "नाव", "समुद्र", "मराठी", "मासे", "सागर", "नाव"],
    "gujarati": ["મછલી", "નૌકા", "સમુદ્ર", "ગુજરાતી", "મત્સ્ય", "સમુદ્ર",
                 "નૌકા"],
    "bengali": ["মাছ", "জাহাজ", "সমুদ্র", "বাংলা", "মৎস্য", "সমুদ্র", "জাহাজ"],
    "odia": ["ମାଛ", "ଜାହାଜ", "ସାମୁଦ୍ରୟ", "ଓଡ଼ିଆ", "ମ୎ତ୍ସ୍ୟ", "ସମୁଦ୍ର",
              "ଜାହାଜ"],
}

DEFAULT_LANG = "english"
LANGUAGES_SUPPORTED = ["english", "tamil", "malayalam", "telugu", "kannada",
                       "hindi", "marathi", "gujarati", "bengali", "odia"]

LANG_RESPONSE_TEMPLATES = {
    "tamil": {
        "greeting": "வணக்கம்! நான் ஒரு சக்திவாய்ந்த கடல் அறிவாளர் ஆகும்.",
        "farewell": "நல்வாழ்த்துகள்! பாதுகாப்பான மீன்பிடி நண்பர் ஆகவும்.",
        "fallback": "தயவுசெய்து ஆங்கிலத்தில் கேட்கவும். (Please ask in English.)"
    },
    "malayalam": {
        "greeting": "സ്വാഗതം! ഞാന്‍ ഒരു കടല്‍ ബുദ്ധിമുട്ടുള്ള ഉപദേശകനാണ്.",
        "farewell": "നന്ദി! സുരക്ഷിതമായ മത്സ്യം പിടിക്കാന്‍ ആശംസക്കുന്നു.",
        "fallback": "ദയവായി ഇംഗ്ലീഷില്‍ ചോദിക്കുക. (Please ask in English.)"
    },
    "telugu": {
        "greeting": "స్వాగతం! నేను ఒక లక్షణీయమైన సముద్ర సలహాదారుడు.",
        "farewell": "ధన్యవాదాలు! సురక్షితమైన మత్స్య సలహాలతో.",
        "fallback": "దయచేసి ఆంగ్లంలో అడగండి. (Please ask in English.)"
    },
    "kannada": {
        "greeting": "ಸ್ವಾಗತ! ನಾನು ಒಬ್ಬ ಸಮುದ್ರ ಬುದ್ಧಿಮತ್ತೆಯ ಸಲಹೆಗಾರ.",
        "farewell": "ಧನ್ಯವಾದಗಳು! ಸುರಕ್ಷತೆಯ ಮೀನುಗಾರಿಕೆಗೆ ಶುಭಾಶಯಗಳು.",
        "fallback": "ದಯವಿರುವುದರೆ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕೇಳಿ. (Please ask in English.)"
    },
    "hindi": {
        "greeting": "स्वागत है! मैं एक समुद्री बुद्धिमान सलाहकार हूँ।",
        "farewell": "धन्यवाद! सुरक्षित मत्स्यपालन की कामना के साथ।",
        "fallback": "कृपया अंग्रेज़ी में पूछें। (Please ask in English.)"
    },
    "marathi": {
        "greeting": "स्वागत आहे! मी एक समुद्री बुद्धिमान सल्लाहकार आहे.",
        "farewell": "धन्यवाद! सुरक्षित मासेमारिगROUP्यासाठी शुभेच्छा.",
        "fallback": "कृपया इंग्रजीत विचाराॅ. (Please ask in English.)"
    },
    "gujarati": {
        "greeting": "સ્વાગત છે! હું એક સમુદ્રી બુદ્ધિશાળી સલાહકાર છું.",
        "farewell": "આભાર! સુરક્ષિત મછલી પકડવા માટે શુભકામનાઓ.",
        "fallback": "કૃપા કરીને અંગ્રેજીમાં પૂછો. (Please ask in English.)"
    },
    "bengali": {
        "greeting": "স্বাগতম! আমি একজন সামুদ্রিক বুদ্ধিমত্তার পরামর্শদাতা।",
        "farewell": "ধন্যবাদ! নিরাপদ মাছ ধরার শুভেচ্ছা।",
        "fallback": "অনুগ্রহ করে ইংরেজিতে জিজ্ঞাসা করুন। (Please ask in English.)"
    },
    "odia": {
        "greeting": "ସ୍ୱାଗତ! ମୁଁ ଏକ ସମୁଦ୍ରୀୟ ବୁଦ୍ଧିମତି ଉପଦେଶକ।",
        "farewell": "ଧନ୍ୟବାଦ! ସୁରକ୍ଷିତ ମାଛ ଧରିବା ପାଇଁ ଶୁଭେଚ୍ଛା।",
        "fallback": "ଦୟାକରି ଇଂରାଜୀରେ ପ୍ରଶ୍ନ କରନ୍ତୁ। (Please ask in English.)"
    },
}

LANG_NAME_DISPLAY = {
    "tamil": "தமிழ் (Tamil)",
    "malayalam": "മലയാളം (Malayalam)",
    "telugu": "తెలుగు (Telugu)",
    "kannada": "ಕನ್ನಡ (Kannada)",
    "hindi": "हिन्दी (Hindi)",
    "marathi": "मराठी (Marathi)",
    "gujarati": "ગુજરાતી (Gujarati)",
    "bengali": "বাংলা (Bengali)",
    "odia": "ଓଡ଼ିଆ (Odia)",
    "english": "English",
}


def detect_language(query: str) -> str:
    """Detect the language of a query using keyword matching.
    Returns the language code (e.g. 'tamil', 'hindi', 'english').
    """
    qlower = query.lower()
    scores = {}
    for lang, keywords in LANG_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in qlower)
        if score > 0:
            scores[lang] = score
    if scores:
        return max(scores, key=scores.get)
    return DEFAULT_LANG


def get_lang_greeting(lang: str) -> str:
    return LANG_RESPONSE_TEMPLATES.get(lang, LANG_RESPONSE_TEMPLATES["english"]).get(
        "greeting", "")


def get_lang_farewell(lang: str) -> str:
    return LANG_RESPONSE_TEMPLATES.get(lang, LANG_RESPONSE_TEMPLATES["english"]).get(
        "farewell", "")


def get_lang_fallback(lang: str) -> str:
    return LANG_RESPONSE_TEMPLATES.get(lang, LANG_RESPONSE_TEMPLATES["english"]).get(
        "fallback", "")


# ──────────────────────────────────────────────────────────────
# 4. INTENT CLASSIFICATION
# ──────────────────────────────────────────────────────────────

class QueryIntent:
    """Parsed user intent from a natural-language marine query."""

    def __init__(self, query: str, lang: str):
        self.raw = query
        self.lang = lang
        self.query_type = "unknown"
        self.location = None  # (lat, lon) or coastal reference
        self.time_window = "today"
        self.species_interest = None
        self.matched_keywords = []

    def __repr__(self):
        return (f"QueryIntent(type={self.query_type}, lang={self.lang}, "
                f"loc={self.location}, time={self.time_window})")


INTENT_RULES = [
    {
        "type": "pfz_query",
        "keywords": ["fishing zone", "pfz", "potential fishing", "fish",
                     "where fish", "catch", "fish location", "mackerel",
                     "sardine", "tuna", "where to fish"],
        "time_weight": ["today", "tomorrow"],
    },
    {
        "type": "safety_query",
        "keywords": ["safe", "safety", "venture", "go out", "danger",
                     "risk", " hazardous", "safe to", "can i go",
                     "weather", "storm", "unsafe"],
        "time_weight": ["tomorrow", "morning", "evening", "today"],
    },
    {
        "type": "conditions_query",
        "keywords": ["tide", "weather", "sea condition", "wave", "swell",
                     "wind", "current", "conditions", "sea state", "temperature"],
        "time_weight": ["today", "tomorrow", "morning", "afternoon", "evening"],
    },
    {
        "type": "alert_query",
        "keywords": ["alert", "warning", "cyclone", "lightning", "storm",
                     "tsunami", "danger", "hazard", "advisory", "alert in",
                     "warning in", "cyclone alert"],
        "time_weight": ["today", "tomorrow", "now", "this week"],
    },
    {
        "type": "chlorophyll_query",
        "keywords": ["chlorophyll", "chlorophyll concentration", "chla",
                     "productivity", "phytoplankton", "plankton",
                     "high chlorophyll", "fertile", "plankton bloom"],
        "time_weight": ["today", "this week", "currently"],
    },
    {
        "type": "sst_query",
        "keywords": ["sea surface temperature", "sst", "temperature",
                     "water temperature", "warm water", "cold water",
                     "temperature near"],
        "time_weight": ["today", "currently", "this week"],
    },
    {
        "type": "route_query",
        "keywords": ["route", "path", "safest route", "navigation",
                     "way", "optimal route", "safe route", "direction",
                     "how to reach", "navigation route", "voyage"],
        "time_weight": ["tomorrow", "today", "this voyage"],
    },
    {
        "type": "productivity_query",
        "keywords": ["productivity decline", "fish decline", "why less fish",
                     "fish decreased", "low catch", "why no fish",
                     "fish productivity", "declined", "reduced catch",
                     "less fish", "catch reduced"],
        "time_weight": ["recent", "last month", "this season", "why"],
    },
    {
        "type": "avoid_zones_query",
        "keywords": ["avoid", "restricted", "dangerous zone", "unsafe zone",
                     "should avoid", "not go", "stay away", "restricted area",
                     "no go", "prohibited", "avoid zone", "hazardous zone",
                     "dont go"],
        "time_weight": ["today", "tomorrow", "now"],
    },
]


def classify_intent(query: str) -> QueryIntent:
    """Classify a natural-language marine query into an intent."""
    qlower = query.lower()
    intent = QueryIntent(query, DEFAULT_LANG)
    best_type = None
    best_score = 0

    for rule in INTENT_RULES:
        score = sum(1 for kw in rule["keywords"] if kw in qlower)
        if score > best_score:
            best_score = score
            best_type = rule["type"]
        elif score == best_score and best_type is None:
            best_type = rule["type"]

    intent.query_type = best_type if best_type else "unknown"
    intent.matched_keywords = [kw for rule in INTENT_RULES
                               for kw in rule["keywords"] if kw in qlower][:5]

    # Time window extraction
    time_patterns = [
        (r"\btomorrow\b", "tomorrow"),
        (r"\bthis\s+morning\b", "morning"),
        (r"\bthis\s+afternoon\b", "afternoon"),
        (r"\bthis\s+evening\b", "evening"),
        (r"\btonight\b", "evening"),
        (r"\bthis\s+week\b", "this week"),
        (r"\btoday\b", "today"),
        (r"\bnow\b", "now"),
        (r"\brecent\b", "recent"),
        (r"\blast\s+month\b", "last month"),
        (r"\blast\s+season\b", "last season"),
    ]
    for pat, tw in time_patterns:
        if re.search(pat, qlower):
            intent.time_window = tw
            break

    # Species interest
    species_list = ["mackerel", "sardine", "tuna", "anchovy", "prawn",
                    "shrimp", "mussel", "clam", "crab", "lobster"]
    for sp in species_list:
        if sp in qlower:
            intent.species_interest = sp
            break

    # Location hints
    for cp in COASTAL_POINTS:
        if cp["name"].lower() in qlower:
            intent.location = (cp["lat"], cp["lon"], cp["name"])
            break

    # Coordinate extraction (lat, lon) pairs
    coord_match = re.search(r"(\d+\.?\d*)\s*[,°]\s*(\d+\.?\d*)", qlower)
    if coord_match:
        try:
            lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
            # Validate sensible coastal lat/lon range for India
            if 6 <= lat <= 24 and 68 <= lon <= 100:
                intent.location = (lat, lon, "specified coordinates")
        except ValueError:
            pass

    return intent


# ──────────────────────────────────────────────────────────────
# 5. AGENT DEFINITIONS
# ──────────────────────────────────────────────────────────────

class AgentResult:
    """Standardized result from any ORCA agent."""

    def __init__(self, agent_name: str, status: str, data: dict,
                 evidence: list[str], confidence: float = 0.8):
        self.agent_name = agent_name
        self.status = status  # "success", "partial", "failed"
        self.data = data
        self.evidence = evidence
        self.confidence = confidence

    def to_dict(self):
        return {
            "agent": self.agent_name,
            "status": self.status,
            "data": self.data,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
        }


# ─── 5a. OCEAN AGENT ────────────────────────────────────────
# Responsibilities: SST, chlorophyll, PFZ detection, productivity trends,
# cross-parameter correlation.

class OceanAgent:
    """Agent for oceanographic reasoning: SST, chlorophyll, PFZ, trends."""

    NAME = "ocean_agent"

    def analyze(self, intent: QueryIntent) -> AgentResult:
        evidence = []
        data = {}

        loc = intent.location
        if loc is None:
            loc = (10.5, 76.8)  # default: off Kochi coast

        lat, lon = loc[0], loc[1]

        # Nearest SST/chlorophyll point
        nearest_sst, sst_dist = nearest_point(lat, lon, SST_DATA)
        data["nearest_sst_point"] = {
            "lat": nearest_sst["lat"], "lon": nearest_sst["lon"],
            "sst_c": nearest_sst["sst"], "chlorophyll_mg_m3": nearest_sst["chlorophyll"],
            "distance_km": round(sst_dist, 1),
        }
        evidence.append(
            f"SST near query location: {nearest_sst['sst']}°C at "
            f"({nearest_sst['lat']}, {nearest_sst['lon']}), "
            f"chlorophyll: {nearest_sst['chlorophyll']} mg/m³"
        )

        # PFZ nearby
        nearest_pfz, p_fz_dist = nearest_point(lat, lon, PFZ_DATA)
        data["nearest_pfz"] = {
            "lat": nearest_pfz["lat"], "lon": nearest_pfz["lon"],
            "productivity": nearest_pfz["productivity"],
            "species": nearest_pfz["species"], "depth_m": nearest_pfz["depth_m"],
            "distance_km": round(p_fz_dist, 1),
            "from_coast": nearest_pfz["from_coast"],
        }
        evidence.append(
            f"Potential Fishing Zone: {nearest_pfz['productivity']} productivity "
            f"for {nearest_pfz['species']} at ({nearest_pfz['lat']}, "
            f"{nearest_pfz['lon']}), {nearest_pfz['distance_km']} km away, "
            f"depth {nearest_pfz['depth_m']}m"
        )

        # SST favourability (ideal range for pelagic fish: 26-30°C)
        sst_val = nearest_sst["sst"]
        sst_favorable = 26 <= sst_val <= 30
        data["sst_favorable"] = sst_favorable
        if sst_favorable:
            evidence.append(f"SST {sst_val}°C is in favourable range (26-30°C) for pelagic fish aggregation")
        else:
            evidence.append(f"SST {sst_val}°C is outside favourable range (26-30°C) — may affect fish aggregation")

        # Chlorophyll favourability (moderate-high: 1-5 mg/m³ indicates productivity)
        chl_val = nearest_sst["chlorophyll"]
        chl_favorable = 1.0 <= chl_val <= 5.0
        data["chlorophyll_favorable"] = chl_favorable
        if chl_favorable:
            evidence.append(f"Chlorophyll {chl_val} mg/m³ indicates productive waters (good for fish food chain)")
        else:
            evidence.append(f"Chlorophyll {chl_val} mg/m³ is {'low' if chl_val < 1 else 'very high'} — {'limited food availability' if chl_val < 1 else 'possible bloom / turbid conditions'}")

        # Cross-correlation: both favourable → high PFZ potential
        data["combined_potential"] = sst_favorable and chl_favorable
        if data["combined_potential"]:
            evidence.append("Both SST and chlorophyll favourable — high potential for fish aggregation (PFZ conditions met)")
        else:
            evidence.append("SST and/or chlorophyll not both favourable — PFZ potential reduced")

        # Productivity trend analysis
        data["trend_assessment"] = self._assess_trend(lat, lon)

        return AgentResult(self.NAME, "success", data, evidence, confidence=0.85)

    def _assess_trend(self, lat: float, lon: float) -> dict:
        """Assess productivity trend for a region (simulated)."""
        # In production: compare historical SST/chlorophyll time series
        base_sst = 28.0
        base_chl = 2.5

        # Simulate trend: if near known productive zone, positive trend
        near_pfz = any(haversine_km(lat, lon, p["lat"], p["lon"]) < 50
                      for p in PFZ_DATA)
        trend = "stable" if not near_pfz else "improving"
        reason = ("Near active PFZ zones with consistent conditions"
                  if near_pfz else "Away from major PFZ zones — stable but lower productivity")

        return {
            "trend": trend,
            "reason": reason,
            "base_sst_c": base_sst,
            "base_chl_mg_m3": base_chl,
        }


# ─── 5b. WEATHER AGENT ───────────────────────────────────────
# Responsibilities: wind, wave, swell, lightning, cyclone alerts, forecast.

class WeatherAgent:
    """Agent for weather and sea-state intelligence."""

    NAME = "weather_agent"

    def analyze(self, intent: QueryIntent) -> AgentResult:
        evidence = []
        data = {}

        loc = intent.location or (10.5, 76.8)
        lat, lon = loc[0], loc[1]
        time_key = intent.time_window

        # Find matching weather record
        weather_records = [w for w in WEATHER_DATA
                          if haversine_km(lat, lon, w["lat"], w["lon"]) < 50]

        if not weather_records:
            # Default to nearest weather station
            nearest_w, w_dist = nearest_point(lat, lon, WEATHER_DATA)
            weather_records = [nearest_w]
            evidence.append(f"Using nearest weather station at {w_dist:.0f} km")

        # Select forecast for time window
        time_map = {
            "morning": "morning", "afternoon": "afternoon",
            "evening": "evening", "now": "morning",
            "today": "morning", "tomorrow": "morning",
            "this week": "morning", "recent": "morning",
            "last month": "morning", "last season": "morning",
        }
        forecast_time = time_map.get(time_key, "morning")
        forecast = next((w for w in weather_records if w["time"] == forecast_time),
                        weather_records[0])

        data["forecast"] = {
            "time": forecast["time"],
            "wind_kt": forecast["wind_kt"],
            "wave_m": forecast["wave_m"],
            "swell_m": forecast["swell_m"],
            "gust_kt": forecast["gust_kt"],
            "lightning_risk": forecast["lightning_risk"],
            "cyclone_alert": forecast["cyclone_alert"],
            "tide_m": forecast["tide_m"],
            "location": f"({forecast['lat']}, {forecast['lon']})",
        }

        evidence.append(
            f"Weather forecast for {forecast['time']}: wind {forecast['wind_kt']} kt, "
            f"waves {forecast['wave_m']} m, swell {forecast['swell_m']} m, "
            f"gusts {forecast['gust_kt']} kt, lightning risk: {forecast['lightning_risk']}"
        )

        # Safety thresholds (per maritime standards)
        wind_safe = forecast["wind_kt"] <= 15
        wind_caution = 15 < forecast["wind_kt"] <= 25
        wind_danger = forecast["wind_kt"] > 25

        wave_safe = forecast["wave_m"] <= 1.5
        wave_caution = 1.5 < forecast["wave_m"] <= 2.5
        wave_danger = forecast["wave_m"] > 2.5

        data["wind_level"] = ("safe" if wind_safe else
                              "caution" if wind_caution else "danger")
        data["wave_level"] = ("safe" if wave_safe else
                              "caution" if wave_caution else "danger")

        tide_safe = forecast["tide_m"] <= 1.5
        tide_caution = 1.5 < forecast["tide_m"] <= 2.0
        tide_danger = forecast["tide_m"] > 2.0
        data["tide_level"] = ("safe" if tide_safe else
                              "caution" if tide_caution else "danger")

        if wind_danger:
            evidence.append(f"WARNING: Wind {forecast['wind_kt']} kt exceeds safe threshold (25 kt) — hazardous for small vessels")
        elif wind_caution:
            evidence.append(f"CAUTION: Wind {forecast['wind_kt']} kt — moderate, experienced operators only")

        if wave_danger:
            evidence.append(f"WARNING: Wave height {forecast['wave_m']} m exceeds safe threshold (2.5 m) — high risk for small fishing boats")
        elif wave_caution:
            evidence.append(f"CAUTION: Wave height {forecast['wave_m']} m — moderate sea state")

        if forecast["lightning_risk"] in ("high", "moderate"):
            evidence.append(f"Lightning risk: {forecast['lightning_risk']} — {'seek shelter immediately if lightning observed' if forecast['lightning_risk'] == 'high' else 'be prepared for lightning activity'}")

        if forecast["cyclone_alert"]:
            evidence.append("CYCLONE ALERT: Active cyclone warning in this region — DO NOT VENTURE OUT")

        # Tide info
        data["tide_level"] = (
            "safe" if forecast["tide_m"] <= 1.5 else
            "caution" if forecast["tide_m"] <= 2.0 else "danger"
        )
        data["tide_advisory"] = (
            "High tide — be aware of coastal inundation" if forecast["tide_m"] > 1.5
            else "Normal tide conditions"
        )
        if forecast["tide_m"] > 1.3:
            evidence.append(f"Tide height {forecast['tide_m']} m — {'above normal, watch for coastal surge' if forecast['tide_m'] > 1.5 else 'slightly elevated'}")

        # Overall weather safety
        danger_count = sum([wind_danger, wave_danger, forecast["cyclone_alert"],
                           forecast["lightning_risk"] == "high"])
        caution_count = sum([wind_caution, wave_caution,
                           forecast["lightning_risk"] == "moderate"])
        data["weather_risk_level"] = (
            "high" if danger_count > 0 else
            "moderate" if caution_count > 0 else "low"
        )

        return AgentResult(self.NAME, "success", data, evidence, confidence=0.9)


# ─── 5c. GEOSPATIAL AGENT ────────────────────────────────────
# Responsibilities: coordinate operations, distance, geofencing, route ops.

class GeospatialAgent:
    """Agent for geospatial reasoning: coordinates, geofencing, boundaries."""

    NAME = "geospatial_agent"

    def analyze(self, intent: QueryIntent) -> AgentResult:
        evidence = []
        data = {}

        loc = intent.location or (10.5, 76.8)
        lat, lon = loc[0], loc[1]

        # Geofence check
        zones = find_zones_for_point(lat, lon)
        data["geozones"] = zones
        data["zone_count"] = len(zones)

        if zones:
            zone_names = [z["name"] for z in zones]
            data["zone_names"] = zone_names
            for z in zones:
                evidence.append(
                    f"Location ({lat}, {lon}) is within: {z['name']} "
                    f"({z['type']}) — {z['description']}"
                )
        else:
            evidence.append(f"Location ({lat}, {lon}) is not within any restricted geofence zone")

        # EEZ boundary proximity check
        eez_zones = [z for z in GEOZONES if z["type"] == "eez_boundary"]
        eez_distance = None
        for ez in eez_zones:
            # Check distance to nearest edge of EEZ bbox
            edges = [
                (ez["min_lat"], ez["min_lon"]),
                (ez["min_lat"], ez["max_lon"]),
                (ez["max_lat"], ez["min_lon"]),
                (ez["max_lat"], ez["max_lon"]),
            ]
            min_edge_dist = min(haversine_km(lat, lon, e[0], e[1]) for e in edges)
            if eez_distance is None or min_edge_dist < eez_distance:
                eez_distance = min_edge_dist

        data["eez_boundary_distance_km"] = round(eez_distance, 1) if eez_distance else None
        data["in_eez"] = any(point_in_zone(lat, lon, ez) for ez in eez_zones)

        if eez_distance and eez_distance < 30:
            evidence.append(f"WARNING: Within {eez_distance:.0f} km of EEZ boundary — risk of crossing into international waters")
        elif eez_distance:
            evidence.append(f"Distance to EEZ boundary: {eez_distance:.0f} km — safe margin")

        # Distance to nearest coastal point (for human directions)
        nearest_coast, coast_dist = nearest_point(lat, lon, COASTAL_POINTS)
        data["nearest_coastal_point"] = {
            "name": nearest_coast["name"],
            "state": nearest_coast["state"],
            "lat": nearest_coast["lat"],
            "lon": nearest_coast["lon"],
            "distance_km": round(coast_dist, 1),
        }
        evidence.append(
            f"Nearest coastal reference: {nearest_coast['name']}, "
            f"{nearest_coast['state']} — {coast_dist:.0f} km away"
        )

        # International boundary proximity
        intl_zones = [z for z in GEOZONES if z["type"] == "international_boundary"]
        for iz in intl_zones:
            if point_in_zone(lat, lon, iz):
                evidence.append(f"WARNING: Near international maritime boundary with Sri Lanka — exercise caution")

        # Route safety helper: check if a straight-line path crosses zones
        if intent.query_type == "route_query" and intent.location:
            # For route queries, check the path from user to destination
            data["route_safety_note"] = (
                "Route analysis requires destination coordinates. "
                "Provide a destination to get a full route safety assessment."
            )

        return AgentResult(self.NAME, "success", data, evidence, confidence=0.95)


# ─── 5d. RISK ASSESSMENT AGENT ───────────────────────────────
# Fuses ocean + weather + geospatial into GO/CAUTION/NO-GO with evidence.

class RiskAgent:
    """Agent for safety risk synthesis combining all data sources."""

    NAME = "risk_agent"

    def assess(self, ocean: AgentResult, weather: AgentResult,
               geospatial: AgentResult, intent: QueryIntent) -> AgentResult:
        evidence = []
        decision = "GO"
        risk_level = "low"
        reasons = []

        # ── Weather risk ──
        weather_data = weather.data.get("forecast", {})
        wind_level = weather.data.get("wind_level", "safe")
        wave_level = weather.data.get("wave_level", "safe")
        weather_risk = weather.data.get("weather_risk_level", "low")

        if wind_level == "danger" or wave_level == "danger":
            decision = "NO-GO"
            risk_level = "high"
            reasons.append(f"Wind/wave conditions hazardous: wind={wind_level}, wave={wave_level}")
            evidence.append("SEA STATE HAZARD: Wind or wave conditions exceed safe thresholds for fishing vessels")
        elif wind_level == "caution" or wave_level == "caution":
            decision = "CAUTION"
            risk_level = "moderate"
            reasons.append(f"Wind/wave conditions require caution: wind={wind_level}, wave={wave_level}")
            evidence.append("MODERATE SEA STATE: Conditions are marginal — experienced operators only, stay near shore")

        if weather_data.get("cyclone_alert"):
            decision = "NO-GO"
            risk_level = "critical"
            reasons.append("Cyclone alert active")
            evidence.append("CYCLONE WARNING: Active cyclone alert — fishing operations should cease immediately")

        if weather_data.get("lightning_risk") == "high":
            decision = "NO-GO"
            reasons.append("High lightning risk")
            evidence.append("LIGHTNING HAZARD: High lightning risk — vessels at sea are vulnerable")

        # ── Geofencing risk ──
        zones = geospatial.data.get("geozones", [])
        zone_types = [z["type"] for z in zones]
        if "mpa" in zone_types:
            decision = "NO-GO" if intent.query_type in ("pfz_query", "route_query") else decision
            risk_level = "high" if decision == "NO-GO" else risk_level
            reasons.append("Location within Marine Protected Area — fishing restricted")
            evidence.append("GEOFENCING: Within MPA boundary — fishing activities restricted to protect marine ecosystem")
        if "seasonal_closure" in zone_types:
            decision = "NO-GO" if intent.query_type in ("pfz_query", "route_query") else decision
            reasons.append("Seasonal fishing closure in effect")
            evidence.append("SEASONAL BAN: Mandatory fishing closure in this region — compliance required by law")
        if "international_boundary" in zone_types:
            reasons.append("Near international maritime boundary")
            evidence.append("BORDER PROXIMITY: Near international boundary — risk of unwittingly crossing into foreign waters; coordinate with maritime authorities")

        eez_dist = geospatial.data.get("eez_boundary_distance_km")
        if eez_dist and eez_dist < 20:
            reasons.append(f"Within {eez_dist} km of EEZ boundary")
            evidence.append(f"EEZ BOUNDARY: Only {eez_dist} km from EEZ edge — maintain awareness of maritime boundary")

        # ── Ocean conditions ──
        ocean_data = ocean.data
        if not ocean_data.get("combined_potential", False):
            reasons.append("Ocean conditions not optimal for fishing (SST/chlorophyll not favourable)")
            evidence.append("OCEAN PRODUCTIVITY: SST and chlorophyll not both in favourable range — reduced fish aggregation expected")

        # ── Final decision synthesis ──
        if decision == "NO-GO" and risk_level != "critical":
            evidence.append("FINAL DECISION: NO-GO — one or more safety factors preclude safe fishing operations at this time")

        if decision == "CAUTION":
            evidence.append("FINAL DECISION: CAUTION — conditions are marginal; proceed only if experienced, stay near shore, monitor conditions")

        if decision == "GO":
            evidence.append("FINAL DECISION: GO — conditions appear favorable for safe fishing operations with standard precautions")

        data = {
            "decision": decision,
            "risk_level": risk_level,
            "reasons": reasons,
            "factors_considered": {
                "weather": {"wind_level": wind_level, "wave_level": wave_level,
                           "weather_risk": weather_risk},
                "geofencing": {"zones": zone_types, "eez_distance_km": eez_dist},
                "ocean": {"sst_favorable": ocean_data.get("sst_favorable"),
                          "chl_favorable": ocean_data.get("chlorophyll_favorable"),
                          "combined_potential": ocean_data.get("combined_potential")},
            },
        }

        confidence = min(ocean.confidence, weather.confidence, geospatial.confidence)
        return AgentResult(self.NAME, "success", data, evidence, confidence=confidence)


# ──────────────────────────────────────────────────────────────
# 6. RESPONSE ASSEMBLY
# ──────────────────────────────────────────────────────────────

class ResponseBuilder:
    """Assembles the final conversational response with evidence chain."""

    def __init__(self, lang: str):
        self.lang = lang

    def build(self, intent: QueryIntent, ocean: AgentResult,
              weather: AgentResult, geospatial: AgentResult,
              risk: AgentResult) -> dict:
        """Assemble a complete response."""
        decision = risk.data.get("decision", "UNKNOWN")
        risk_level = risk.data.get("risk_level", "unknown")

        # Determine primary recommendation text based on query type
        rec_text = self._recommendation_text(intent, decision, risk_level,
                                              ocean, weather, geospatial)

        # Evidence chain (explainability)
        evidence_chain = []
        evidence_chain.append(f"Query understood as: {intent.query_type.replace('_', ' ')}")
        evidence_chain.append(f"Language detected: {LANG_NAME_DISPLAY.get(self.lang, self.lang)}")
        if intent.location:
            loc_info = intent.location
            if len(loc_info) == 3:
                evidence_chain.append(f"User location: {loc_info[2]} ({loc_info[0]}, {loc_info[1]})")
            else:
                evidence_chain.append(f"User location: ({loc_info[0]}, {loc_info[1]})")

        # Add agent evidence
        for ev in ocean.evidence:
            evidence_chain.append(f"[Ocean Agent] {ev}")
        for ev in weather.evidence:
            evidence_chain.append(f"[Weather Agent] {ev}")
        for ev in geospatial.evidence:
            evidence_chain.append(f"[Geospatial Agent] {ev}")
        for ev in risk.evidence:
            evidence_chain.append(f"[Risk Agent] {ev}")

        # Alerts section
        alerts = []
        for ev in risk.evidence:
            if ev.startswith("WARNING") or ev.startswith("CYCLONE") or ev.startswith("LIGHTNING"):
                alerts.append(ev)
        for ev in weather.evidence:
            if ev.startswith("WARNING") or ev.startswith("CYCLONE"):
                alerts.append(ev)
        for ev in geospatial.evidence:
            if ev.startswith("WARNING"):
                alerts.append(ev)

        # Map data for geospatial visualization
        map_data = {
            "user_location": {"lat": intent.location[0] if intent.location else 10.5,
                              "lon": intent.location[1] if intent.location else 76.8},
            "pfz_points": [{"lat": p["lat"], "lon": p["lon"],
                           "label": f"PFZ: {p['productivity']} ({p['species']})"}
                          for p in PFZ_DATA],
            "weather_stations": [{"lat": w["lat"], "lon": w["lon"],
                                  "wind_kt": w["wind_kt"], "wave_m": w["wave_m"]}
                                 for w in WEATHER_DATA],
            "geozones": [{"name": z["name"], "type": z["type"],
                         "lat": (z["min_lat"] + z["max_lat"]) / 2,
                         "lon": (z["min_lon"] + z["max_lon"]) / 2,
                         "bbox": [[z["min_lon"], z["min_lat"]],
                                  [z["max_lon"], z["max_lat"]]],
                         "description": z["description"]}
                        for z in GEOZONES],
        }

        # Regional language response wrapper
        lang_note = ""
        if self.lang != "english":
            lang_note = (f"\n\n── Responding in {LANG_NAME_DISPLAY.get(self.lang, self.lang)} ──\n"
                        f"({get_lang_fallback(self.lang)})")

        response = {
            "query": intent.raw,
            "language": self.lang,
            "language_display": LANG_NAME_DISPLAY.get(self.lang, self.lang),
            "intent_type": intent.query_type,
            "time_window": intent.time_window,
            "recommendation": rec_text,
            "decision": decision,
            "risk_level": risk_level,
            "evidence_chain": evidence_chain,
            "alerts": alerts,
            "map_data": map_data,
            "agent_results": {
                "ocean": ocean.to_dict(),
                "weather": weather.to_dict(),
                "geospatial": geospatial.to_dict(),
                "risk": risk.to_dict(),
            },
            "regional_language_note": lang_note,
        }
        return response

    def _recommendation_text(self, intent, decision, risk_level,
                             ocean, weather, geospatial) -> str:
        """Generate natural-language recommendation based on query type."""
        qtype = intent.query_type
        decision_text = {
            "GO": "🟢 Conditions appear favourable — you may proceed with standard precautions.",
            "CAUTION": "🟡 CAUTION — conditions are marginal. Only experienced operators should venture out, and stay near shore.",
            "NO-GO": "🔴 NO-GO — one or more safety factors make venturing out hazardous right now.",
            "critical": "🔴 URGENT: Critical safety alert — do not venture out under any circumstances.",
        }

        if qtype == "pfz_query":
            p_fz = ocean.data.get("nearest_pfz", {})
            sst = ocean.data.get("nearest_sst_point", {})
            rec = (f"Nearest Potential Fishing Zone (PFZ): {p_fz.get('productivity', 'unknown')} "
                   f"productivity for {p_fz.get('species', 'various')} at "
                   f"({p_fz.get('lat')}, {p_fz.get('lon')}), {p_fz.get('distance_km')} km from your location. "
                   f"Depth: {p_fz.get('depth_m')}m. {decision_text.get(decision, '')} "
                   f"SST at your location: {sst.get('sst_c')}°C, "
                   f"chlorophyll: {sst.get('chlorophyll_mg_m3')} mg/m³. "
                   f"PFZ conditions {'met' if ocean.data.get('combined_potential') else 'not fully met'}.")

        elif qtype == "safety_query":
            w = weather.data.get("forecast", {})
            rec = (f"Safety assessment for {intent.time_window}: "
                   f"wind {w.get('wind_kt')} kt, waves {w.get('wave_m')} m, "
                   f"swell {w.get('swell_m')} m, lightning risk: {w.get('lightning_risk')}. "
                   f"Cyclone alert: {'ACTIVE — DO NOT VENTURE' if w.get('cyclone_alert') else 'None'}. "
                   f"{decision_text.get(decision, '')}")

        elif qtype == "conditions_query":
            w = weather.data.get("forecast", {})
            sst = ocean.data.get("nearest_sst_point", {})
            rec = (f"Conditions near your location: "
                   f"Wind {w.get('wind_kt')} kt ({w.get('wind_level')}), "
                   f"Waves {w.get('wave_m')} m ({w.get('wave_level')}), "
                   f"Swell {w.get('swell_m')} m, "
                   f"Tide {w.get('tide_m')} m ({w.get('tide_level', 'N/A')}), "
                   f"Lightning risk: {w.get('lightning_risk')}. "
                   f"SST: {sst.get('sst_c')}°C. {decision_text.get(decision, '')}")

        elif qtype == "alert_query":
            alerts = []
            w = weather.data.get("forecast", {})
            if w.get("cyclone_alert"):
                alerts.append("CYCLONE ALERT ACTIVE — stay ashore, follow IMD advisories")
            if w.get("lightning_risk") == "high":
                alerts.append("High lightning risk — avoid open sea")
            if w.get("lightning_risk") == "moderate":
                alerts.append("Moderate lightning risk — be prepared")
            if w.get("wind_kt") > 25:
                alerts.append(f"High wind warning: {w.get('wind_kt')} kt")
            if w.get("wave_m") > 2.5:
                alerts.append(f"High wave warning: {w.get('wave_m')} m")
            zone_alerts = []
            for z in geospatial.data.get("geozones", []):
                if z["type"] in ("mpa", "seasonal_closure"):
                    zone_alerts.append(f"{z['name']}: {z['description']}")
            if zone_alerts:
                alerts.append(f"Restricted zones nearby: {'; '.join(zone_alerts)}")
            if not alerts:
                alerts.append("No active alerts for your area at this time")
            rec = "Current alerts:\n" + "\n".join(f"  • {a}" for a in alerts) + \
                  f"\n\nOverall risk: {risk_level}. {decision_text.get(decision, '')}"

        elif qtype == "chlorophyll_query":
            sst = ocean.data.get("nearest_sst_point", {})
            rec = (f"Chlorophyll concentration near you: {sst.get('chlorophyll_mg_m3')} mg/m³ "
                   f"at ({sst.get('lat')}, {sst.get('lon')}). "
                   f"{'This indicates productive waters with good phytoplankton — food for fish.' if sst.get('chlorophyll_favorable') else 'Chlorophyll level is outside optimal range.'} "
                   f"SST: {sst.get('sst_c')}°C ({'favourable' if sst.get('sst_favorable') else 'outside favourable range'}). "
                   f"Combined potential: {'HIGH — good PFZ conditions' if ocean.data.get('combined_potential') else 'reduced'}. "
                   f"{decision_text.get(decision, '')}")

        elif qtype == "sst_query":
            sst = ocean.data.get("nearest_sst_point", {})
            rec = (f"Sea Surface Temperature near you: {sst.get('sst_c')}°C "
                   f"at ({sst.get('lat')}, {sst.get('lon')}). "
                   f"{'Favourable range (26-30°C) for pelagic fish.' if sst.get('sst_favorable') else 'Outside favourable range — may affect fish distribution.'} "
                   f"Chlorophyll: {sst.get('chlorophyll_mg_m3')} mg/m³. "
                   f"{decision_text.get(decision, '')}")

        elif qtype == "route_query":
            coast = geospatial.data.get("nearest_coastal_point", {})
            zones = geospatial.data.get("geozones", [])
            rec = (f"Route planning from your location. "
                   f"Nearest coastal reference: {coast.get('name')}, "
                   f"{coast.get('state')} — {coast.get('distance_km')} km. "
                   f"Restricted zones along potential route: "
                   f"{', '.join(z['name'] for z in zones) if zones else 'None identified'}. "
                   f"{'WARNING: Check geofencing for your complete route before departure.' if zones else ''} "
                   f"{decision_text.get(decision, '')} "
                   f"Provide a destination for detailed route safety analysis.")

        elif qtype == "productivity_query":
            trend = ocean.data.get("trend_assessment", {})
            rec = (f"Productivity assessment for your region: "
                   f"Trend: {trend.get('trend', 'unknown')} — {trend.get('reason', '')}. "
                   f"Base SST: {trend.get('base_sst_c')}°C, base chlorophyll: {trend.get('base_chl_mg_m3')} mg/m³. "
                   f"{'Fish productivity likely stable or improving.' if trend.get('trend') in ('improving', 'stable') else 'Productivity may be below average.'} "
                   f"Possible factors: seasonal patterns, monsoon cycles, ocean currents, fishing pressure, habitat changes. "
                   f"{decision_text.get(decision, '')}")

        elif qtype == "avoid_zones_query":
            zones = geospatial.data.get("geozones", [])
            rec = "Zones to avoid based on current conditions:\n"
            hazard_zones = [z for z in zones if z["type"] in (
                "mpa", "seasonal_closure", "international_boundary")]
            if hazard_zones:
                for z in hazard_zones:
                    rec += f"  • {z['name']} ({z['type']}) — {z['description']}\n"
            else:
                rec += "  No restricted zones identified near your location.\n"
            w = weather.data.get("forecast", {})
            if w.get("wave_m", 0) > 2.0:
                rec += f"  • Hazardous sea area: waves {w.get('wave_m')} m — avoid open sea\n"
            if w.get("wind_kt", 0) > 20:
                rec += f"  • High wind area: wind {w.get('wind_kt')} kt — avoid departure\n"
            rec += f"\nOverall recommendation: {decision_text.get(decision, '')}"

        else:
            rec = (f"I understand you're asking about {qtype.replace('_', ' ')}. "
                   f"Here's what I can tell you: "
                   f"SST near you: {ocean.data.get('nearest_sst_point', {}).get('sst_c', 'N/A')}°C, "
                   f"nearest PFZ: {ocean.data.get('nearest_pfz', {}).get('productivity', 'N/A')} "
                   f"at {ocean.data.get('nearest_pfz', {}).get('distance_km', 'N/A')} km, "
                   f"wind: {weather.data.get('forecast', {}).get('wind_kt', 'N/A')} kt, "
                   f"waves: {weather.data.get('forecast', {}).get('wave_m', 'N/A')} m. "
                   f"Safety decision: {decision}. {decision_text.get(decision, '')}")

        return rec


# ──────────────────────────────────────────────────────────────
# 7. ORCHESTRATOR — decomposes query, routes to agents, synthesizes
# ──────────────────────────────────────────────────────────────

class ORCAOrchestrator:
    """
    Main orchestrator: interprets user intent, decomposes into tasks,
    routes to specialized agents, and synthesizes a response.
    """

    def __init__(self):
        self.ocean_agent = OceanAgent()
        self.weather_agent = WeatherAgent()
        self.geospatial_agent = GeospatialAgent()
        self.risk_agent = RiskAgent()
        self.response_builder = None

    def process(self, query: str) -> dict:
        """Full processing pipeline: query → response."""
        # Step 1: Language detection
        lang = detect_language(query)

        # Step 2: Intent classification
        intent = classify_intent(query)
        intent.lang = lang  # attach detected language

        # Step 3: Agent orchestration (parallel where possible)
        ocean_result = self.ocean_agent.analyze(intent)
        weather_result = self.weather_agent.analyze(intent)
        geospatial_result = self.geospatial_agent.analyze(intent)

        # Step 4: Risk synthesis (depends on all three)
        risk_result = self.risk_agent.assess(ocean_result, weather_result,
                                              geospatial_result, intent)

        # Step 5: Response assembly
        self.response_builder = ResponseBuilder(lang)
        response = self.response_builder.build(intent, ocean_result,
                                               weather_result, geospatial_result,
                                               risk_result)

        return response

    def interactive_session(self):
        """Run an interactive conversational session."""
        print("\n" + "=" * 60)
        print("  ORCA — Marine EcOsystem Reasoning with Collaborative Agents")
        print("  SIH 2026 #176 | ISRO | Disaster Management")
        print("=" * 60)
        print(f"\nSupported languages: {', '.join(LANG_NAME_DISPLAY.values())}")
        print("Try: 'Where is the nearest PFZ today?' or 'Is it safe to venture tomorrow?'")
        print("Type 'quit' or 'exit' to end.\n")

        lang = "english"
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not query:
                continue

            if query.lower() in ("quit", "exit", "bye", "q"):
                lang_note = get_lang_farewell(lang) if lang != "english" else "Goodbye! Stay safe at sea."
                print(f"\nORCA: {lang_note}")
                break

            # Detect language (can change mid-conversation)
            new_lang = detect_language(query)
            if new_lang != lang:
                lang = new_lang
                greet = get_lang_greeting(lang)
                if greet:
                    print(f"\nORCA: {greet}")
                    if lang != "english":
                        print(f"ORCA: {get_lang_fallback(lang)}")

            # Process query
            response = self.process(query)

            # Print response
            print(f"\nORCA [{response['language_display']}]: ")
            print(f"  Query type: {response['intent_type'].replace('_', ' ')}")
            print(f"  Time window: {response['time_window']}")
            print(f"\n  {response['recommendation']}")

            if response["alerts"]:
                print("\n  🔴 ALERTS:")
                for alert in response["alerts"]:
                    print(f"    • {alert}")

            print(f"\n  Safety decision: {response['decision']} ({response['risk_level']})")
            print(f"\n  Evidence chain ({len(response['evidence_chain'])} steps):")
            for i, ev in enumerate(response["evidence_chain"], 1):
                print(f"    {i}. {ev}")

            print(f"\n  Map data ready: user at ({response['map_data']['user_location']['lat']}, "
                  f"{response['map_data']['user_location']['lon']}), "
                  f"{len(response['map_data']['pfz_points'])} PFZ points, "
                  f"{len(response['map_data']['geozones'])} geozones marked.")
            print(response.get("regional_language_note", ""))


# ──────────────────────────────────────────────────────────────
# 8. DEMO — run sample queries to show the full pipeline
# ──────────────────────────────────────────────────────────────

def run_demo():
    """Run a set of demo queries showing the full agentic pipeline."""
    orchestrator = ORCAOrchestrator()

    demo_queries = [
        # 1. PFZ query
        "Where is the nearest potential fishing zone today near Kochi?",
        # 2. Safety query (no location → default, but weather is safe)
        "Is it safe to venture into the sea tomorrow morning near Chennai?",
        # 3. Conditions query
        "What are the tide, weather, and sea conditions near my fishing location?",
        # 4. Alert query
        "Are there any lightning or cyclone alerts in my area?",
        # 5. Chlorophyll + SST query
        "Which regions show high chlorophyll concentration and favourable sea surface temperature?",
        # 6. Route query
        "What is the safest route for a fishing vessel considering weather and sea-state conditions?",
        # 7. Productivity decline query
        "Why has fish productivity declined in a particular coastal region?",
        # 8. Avoid zones query
        "Which fishing zones should be avoided due to hazardous marine conditions or geofencing restrictions?",
    ]

    print("\n" + "=" * 60)
    print("  ORCA DEMO — 8 Example Queries from Problem Statement")
    print("=" * 60)

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'─' * 60}")
        print(f"  DEMO {i}: {query}")
        print(f"{'─' * 60}")

        response = orchestrator.process(query)

        print(f"\n  ORCA [{response['language_display']}]:")
        print(f"  Recommendation: {response['recommendation']}")

        if response["alerts"]:
            print("\n  ALERTS:")
            for a in response["alerts"]:
                print(f"    • {a}")

        print(f"\n  Decision: {response['decision']} | Risk: {response['risk_level']}")
        print(f"\n  Evidence ({len(response['evidence_chain'])} steps):")
        for j, ev in enumerate(response["evidence_chain"], 1):
            print(f"    {j}. {ev}")

        print(f"\n  Supporting data: PFZ points={len(response['map_data']['pfz_points'])}, "
              f"weather stations={len(response['map_data']['weather_stations'])}, "
              f"geozones={len(response['map_data']['geozones'])}")

    print(f"\n{'=' * 60}")
    print("  DEMO COMPLETE — 8/8 queries processed successfully")
    print(f"{'=' * 60}")


# ──────────────────────────────────────────────────────────────
# 9. ENTRY POINT
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        ORCAOrchestrator().interactive_session()
