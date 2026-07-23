from typing import Literal

from pydantic import BaseModel

from supportagent.claims.schemas import Claim, ClaimDocument, ProductLine


RequirementLevel = Literal["required", "optional", "conditional"]


class DocumentRequirement(BaseModel):
    document_type: str
    level: RequirementLevel
    product_line: ProductLine | Literal["all"]
    claim_type: str
    condition: str | None = None
    source_id: str
    source_title: str
    evidence_excerpt: str


GENERAL_SOURCE = "Schadenmeldung - Prozessablauf und benoetigte Unterlagen"
GENERAL_SOURCE_ID = "seed-9440feb5ebc8"
BUILDING_SOURCE = "Wohngebaeudeversicherung - Produktbeschreibung"
BUILDING_SOURCE_ID = "seed-f7b78becfa04"
VEHICLE_SOURCE = "Kfz-Schaden - Ablauf, Selbstbeteiligung und Unterlagen"
VEHICLE_SOURCE_ID = "seed-ccdc2746bb35"


DOCUMENT_REQUIREMENTS: list[DocumentRequirement] = [
    DocumentRequirement(
        document_type="claim_form",
        level="required",
        product_line="all",
        claim_type="all",
        source_id=GENERAL_SOURCE_ID,
        source_title=GENERAL_SOURCE,
        evidence_excerpt="Ausgefuelltes Schadenformular mit Schilderung des Schadenablaufs",
    ),
    DocumentRequirement(
        document_type="damage_photo",
        level="required",
        product_line="all",
        claim_type="all",
        source_id=GENERAL_SOURCE_ID,
        source_title=GENERAL_SOURCE,
        evidence_excerpt="Fotos des Schadens bzw. der beschaedigten Gegenstaende",
    ),
    DocumentRequirement(
        document_type="purchase_receipt",
        level="conditional",
        product_line="all",
        claim_type="all",
        condition="Damaged or stolen items require proof of purchase when available.",
        source_id=GENERAL_SOURCE_ID,
        source_title=GENERAL_SOURCE,
        evidence_excerpt="Kaufbelege oder Rechnungen fuer beschaedigte oder gestohlene Gegenstaende",
    ),
    DocumentRequirement(
        document_type="police_report",
        level="conditional",
        product_line="all",
        claim_type="all",
        condition="Required for burglary, theft, or vandalism.",
        source_id=GENERAL_SOURCE_ID,
        source_title=GENERAL_SOURCE,
        evidence_excerpt="Polizeibericht bei Einbruch, Diebstahl oder Vandalismus",
    ),
    DocumentRequirement(
        document_type="repair_estimate",
        level="optional",
        product_line="all",
        claim_type="all",
        condition="Provide when available; it is not a universal blocking requirement.",
        source_id=GENERAL_SOURCE_ID,
        source_title=GENERAL_SOURCE,
        evidence_excerpt="Kostenvoranschlag oder Reparaturrechnung eines Fachbetriebs, sofern vorhanden",
    ),
    DocumentRequirement(
        document_type="damage_cause_report",
        level="required",
        product_line="residential_building",
        claim_type="water_damage",
        source_id=BUILDING_SOURCE_ID,
        source_title=BUILDING_SOURCE,
        evidence_excerpt="Ein kurzer Bericht zur Schadenursache ist fuer die Bearbeitung erforderlich.",
    ),
    DocumentRequirement(
        document_type="repair_invoice",
        level="required",
        product_line="residential_building",
        claim_type="water_damage",
        source_id=BUILDING_SOURCE_ID,
        source_title=BUILDING_SOURCE,
        evidence_excerpt="Die Rechnung des Handwerksbetriebs ist fuer die Bearbeitung erforderlich.",
    ),
    DocumentRequirement(
        document_type="accident_report",
        level="required",
        product_line="vehicle",
        claim_type="vehicle_damage",
        source_id=VEHICLE_SOURCE_ID,
        source_title=VEHICLE_SOURCE,
        evidence_excerpt="Europaeischer Unfallbericht oder eigene Schadenschilderung",
    ),
    DocumentRequirement(
        document_type="repair_assessment",
        level="required",
        product_line="vehicle",
        claim_type="vehicle_damage",
        source_id=VEHICLE_SOURCE_ID,
        source_title=VEHICLE_SOURCE,
        evidence_excerpt="Kostenvoranschlag oder Gutachten einer Werkstatt bzw. eines Sachverstaendigen",
    ),
    DocumentRequirement(
        document_type="police_report",
        level="conditional",
        product_line="vehicle",
        claim_type="vehicle_damage",
        condition="Required for personal injury, hit-and-run, or suspected alcohol involvement.",
        source_id=VEHICLE_SOURCE_ID,
        source_title=VEHICLE_SOURCE,
        evidence_excerpt="Polizeiprotokoll bei Personenschaeden, Fahrerflucht oder Verdacht auf Alkoholeinfluss",
    ),
]


def normalize_document_type(value: str) -> str:
    return value.strip().casefold().replace("-", "_").replace(" ", "_")


def requirements_for_claim(claim: Claim) -> list[DocumentRequirement]:
    claim_type = normalize_document_type(claim.claim_type)
    return [
        requirement
        for requirement in DOCUMENT_REQUIREMENTS
        if requirement.product_line in {"all", claim.product_line}
        and requirement.claim_type in {"all", claim_type}
    ]


def requirements_by_level(claim: Claim, level: RequirementLevel) -> list[DocumentRequirement]:
    return [requirement for requirement in requirements_for_claim(claim) if requirement.level == level]


def required_documents_for_claim(claim: Claim) -> list[str]:
    return sorted({requirement.document_type for requirement in requirements_by_level(claim, "required")})


def optional_documents_for_claim(claim: Claim) -> list[str]:
    return sorted({requirement.document_type for requirement in requirements_by_level(claim, "optional")})


def conditional_documents_for_claim(claim: Claim) -> list[str]:
    return sorted({requirement.document_type for requirement in requirements_by_level(claim, "conditional")})


def completed_document_types(documents: list[ClaimDocument]) -> list[str]:
    return sorted(
        {
            normalize_document_type(document.document_type)
            for document in documents
            if document.extraction_status.upper() == "COMPLETED"
        }
    )


def missing_documents_for_claim(claim: Claim, documents: list[ClaimDocument]) -> list[str]:
    present = set(completed_document_types(documents))
    return sorted(set(required_documents_for_claim(claim)) - present)
