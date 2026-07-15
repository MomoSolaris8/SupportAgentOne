import base64
import json
import os
from dataclasses import asdict, dataclass, field

from openai import OpenAI


VISION_PROMPT = """Analyze the uploaded image for an insurance support workflow.

Return only valid JSON with this exact shape:
{
  "ocr_text": "visible or extracted text, preserving important wording; empty string if none",
  "visible_objects": ["visible objects, documents, vehicles, damage, UI elements"],
  "dates": ["visible dates"],
  "amounts": ["visible monetary amounts or quantities"],
  "names": ["visible names, organizations, products, places"],
  "insurance_relevant_facts": ["operational facts relevant for insurance support"],
  "limitations": "uncertainties, unreadable areas, or missing image analysis limits"
}

Use German for descriptions. Do not decide coverage, liability, fraud, claim validity,
claim amount, or final regulation."""


@dataclass(frozen=True)
class ImageAnalysis:
    ocr_text: str = ""
    visible_objects: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    amounts: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    insurance_relevant_facts: list[str] = field(default_factory=list)
    limitations: str = ""

    def summary(self, filename: str) -> str:
        parts: list[str] = []
        if self.ocr_text:
            parts.append(f"Extrahierter Text: {self.ocr_text}")
        if self.visible_objects:
            parts.append("Sichtbare Objekte/Inhalte: " + "; ".join(self.visible_objects))
        if self.dates:
            parts.append("Datumsangaben: " + "; ".join(self.dates))
        if self.amounts:
            parts.append("Betraege/Mengen: " + "; ".join(self.amounts))
        if self.names:
            parts.append("Namen/Organisationen/Orte: " + "; ".join(self.names))
        if self.insurance_relevant_facts:
            parts.append("Versicherungsrelevante Beobachtungen: " + "; ".join(self.insurance_relevant_facts))
        if self.limitations:
            parts.append(f"Einschraenkungen: {self.limitations}")
        if not parts:
            return f"Bild '{filename}' wurde analysiert, aber es wurden keine verwertbaren sichtbaren Inhalte erkannt."
        return " | ".join(parts)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _analysis_from_json(content: str) -> ImageAnalysis:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return ImageAnalysis(
            insurance_relevant_facts=[content.strip()] if content.strip() else [],
            limitations="Das Vision-Modell hat keine gueltige JSON-Struktur geliefert.",
        )
    if not isinstance(parsed, dict):
        return ImageAnalysis(limitations="Das Vision-Modell hat keine JSON-Objektstruktur geliefert.")
    return ImageAnalysis(
        ocr_text=str(parsed.get("ocr_text") or "").strip(),
        visible_objects=_as_string_list(parsed.get("visible_objects")),
        dates=_as_string_list(parsed.get("dates")),
        amounts=_as_string_list(parsed.get("amounts")),
        names=_as_string_list(parsed.get("names")),
        insurance_relevant_facts=_as_string_list(parsed.get("insurance_relevant_facts")),
        limitations=str(parsed.get("limitations") or "").strip(),
    )


def analyze_image(image_bytes: bytes, content_type: str, filename: str) -> ImageAnalysis:
    model = os.environ.get("VISION_MODEL")
    api_key = os.environ.get("EMBEDDING_API_KEY")
    base_url = os.environ.get("EMBEDDING_BASE_URL")
    if not model or not api_key or not base_url:
        return ImageAnalysis(
            limitations=(
                f"Bild '{filename}' wurde hochgeladen ({content_type}). "
                "Es ist kein Vision-Modell konfiguriert; der Inhalt wurde nicht automatisch analysiert."
            )
        )

    data_url = f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=0,
    )
    return _analysis_from_json(response.choices[0].message.content or "")


def summarize_image(image_bytes: bytes, content_type: str, filename: str) -> str:
    return analyze_image(image_bytes, content_type, filename).summary(filename)
