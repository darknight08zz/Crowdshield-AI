"""
CROWDSHIELD PUBLIC ANNOUNCEMENT DRAFTING MODULE
================================================
Generates deterministic, ready-to-broadcast public announcements for venue PA systems
and citizen mobile alerts based on situation type, zone name, and recommended actions.
Supports English ('en') and Hindi ('hi') without live LLM latency.
"""

from typing import Dict, Any, Optional

ANNOUNCEMENT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "REVERSE_FLOW": "Attention visitors near {zone_name}: One-way pedestrian flow is in effect. Please move forward with the designated direction and do not turn back or walk against the crowd.",
        "SURGE": "Attention visitors in {zone_name}: High crowd density detected. Please remain calm, maintain steady forward movement toward open exit gates, and avoid stopping in pathways.",
        "STAGNATION": "Attention visitors in {zone_name}: Movement is temporarily bottlenecked ahead. Please follow security officer directions, refrain from pushing, and keep emergency lanes clear.",
        "DISPERSED_INCIDENT_CLUSTER": "Attention visitors in {zone_name}: Safety personnel are clearing an active incident area. Please yield space to emergency officers and follow directional signage.",
        "NORMAL": "Attention visitors in {zone_name}: Please maintain orderly movement, stay aware of your surroundings, and keep exit pathways clear. Thank you for your cooperation."
    },
    "hi": {
        "REVERSE_FLOW": "ध्यान दें {zone_name} के श्रद्धालु: एकतरफा पैदल मार्ग नियम लागू है। कृपया दिए गए दिशा-निर्देशों का पालन करें और भीड़ के विपरीत न चलें।",
        "SURGE": "ध्यान दें {zone_name} के श्रद्धालु: अत्यधिक भीड़ देखी गई है। कृपया शांत रहें और खुले निकास द्वारों की ओर निरंतर आगे बढ़ें।",
        "STAGNATION": "ध्यान दें {zone_name} के श्रद्धालु: आगे मार्ग में रुकावट है। कृपया सुरक्षा कर्मियों के निर्देशों का पालन करें और धक्का-मुक्की न करें।",
        "DISPERSED_INCIDENT_CLUSTER": "ध्यान दें {zone_name} के श्रद्धालु: सुरक्षा कर्मी स्थिति को संभाल रहे हैं। कृपया आपातकालीन टीम को स्थान दें।",
        "NORMAL": "ध्यान दें {zone_name} के श्रद्धालु: कृपया शांतिपूर्वक चलते रहें और निकास मार्ग खाली रखें। आपके सहयोग के लिए धन्यवाद।"
    }
}


def draft_announcement(
    situation_type: str,
    zone_name: str,
    recommended_action: str = "",
    language: str = "en"
) -> str:
    """
    Drafts ready-to-broadcast public announcement text.

    Args:
        situation_type: Behavior pattern or situation key ('REVERSE_FLOW', 'SURGE', 'STAGNATION', etc.)
        zone_name: Human-readable name of the affected zone/sector.
        recommended_action: Specific recommended action type or title (optional context modifier).
        language: Language code ('en' or 'hi'). Default is 'en'.

    Returns:
        str: Ready-to-broadcast formatted public advisory text.
    """
    lang = language.lower() if language and language.lower() in ANNOUNCEMENT_TEMPLATES else "en"
    situation_key = situation_type.upper() if situation_type else "NORMAL"

    templates = ANNOUNCEMENT_TEMPLATES.get(lang, ANNOUNCEMENT_TEMPLATES["en"])
    template = templates.get(situation_key, templates["NORMAL"])

    return template.format(zone_name=zone_name)
