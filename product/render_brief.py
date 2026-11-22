"""Deterministic Markdown for the two bundled FX-010 synthetic scenarios."""
import json
from pathlib import Path
import unicodedata

if __package__:
    from . import validate_input as validator
else:
    import validate_input as validator

VERSION = "0.1.1"
DEMO_PROFILE = "forenzx-analysis-result-0e4c7fae"
PRODUCT = Path(__file__).resolve().parent
SCENARIOS = ("completed-hit", "completed-no-ioc")
DISCLAIMER = (
    "Tento dokument je AI asistovaný pracovný návrh prehľadu z poskytnutých výsledkov ForenZX. "
    "Pred odborným použitím musí analytik overiť údaje, odkazy a závery oproti zdrojovým výsledkom "
    "a relevantným podkladom. Dokument sám osebe nepreukazuje úplnosť vyšetrovania ani prípustnosť dôkazov."
)


class BriefError(ValueError):
    """A fixed diagnostic safe for the CLI."""


def _literal(value):
    """One reversible JSON value on a single indented Markdown code line."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return "".join(
        json.dumps(ch, ensure_ascii=True)[1:-1]
        if unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} else ch
        for ch in encoded
    )


def _fields(lines, record, fields):
    for key in fields:
        lines.append(f"    {key} = {_literal(record.get(key))}")


def _source_list(lines, title, key, items):
    lines.extend(["", f"### {title}", ""])
    for index, value in enumerate(items):
        lines.append(f"    /{key}/{index} = {_literal(value)}")
    if not items:
        lines.append("Zdroj obsahuje prázdny zoznam.")


def _markdown(data, check):
    lines = [
        "# AI asistovaný návrh — vyžaduje kontrolu analytikom", "",
        "**Syntetická ukážka — automaticky vytvorený pracovný prehľad**", "",
        "Režim `SYNTHETIC_DEMO` · `report_generation_allowed = false`", "",
        "> " + DISCLAIMER, "", "## Identita a rozsah", "",
        f"SHA-256 prijatých bajtov JSON: `{check['input']['sha256']}`",
        f"Profil validátora: `{check['profile']}` · renderer: `{VERSION}`",
        f"Pripnutá revízia profilu Hubu: `{check['upstream_commit']}`", "",
        "Zdrojové polia používajú zápis JSON. "
        "Hodnota `null` označuje nedostupný údaj a `\"\"` prázdny reťazec.", "",
    ]
    _fields(lines, data, ("job_id", "case_id", "evidence_id", "pack_id", "pack_version",
                          "status", "summary_classification", "started_at", "completed_at"))
    lines.extend(["", "### Integrita a história podľa zdroja", ""])
    _fields(lines, data, ("input_integrity",))
    for i, item in enumerate(data["chain_of_custody"]):
        lines.extend(["", f"Záznam `/chain_of_custody/{i}`", ""])
        _fields(lines, item, ("action", "actor", "timestamp", "sha256_before", "sha256_after"))
    lines.extend(["", "Zdrojový záznam `/execution_record`", ""])
    _fields(lines, data.get("execution_record") or {}, ("record_version", "input_root_sha256",
                                                        "ioc_bundle_version", "ioc_bundle_sha256"))
    lines.extend(["", "## Upozornenia a obmedzenia zdroja"])
    _source_list(lines, "Upozornenia", "warnings", data["warnings"])
    _source_list(lines, "Obmedzenia", "limitations", data["limitations"])

    lines.extend(["", "## Zdrojové nálezy", "", f"Počet nálezov v prijatom JSON: {len(data['findings'])}."])
    if data["summary_classification"] == "NO_KNOWN_IOC":
        lines.extend(["", "V skúmanom rozsahu sa nenašli známe IOC z použitého balíka."])
    for i, item in enumerate(data["findings"]):
        lines.extend(["", f"### Nález `/findings/{i}`", ""])
        _fields(lines, item, ("id", "classification", "severity", "confidence", "ioc_type", "ioc_name",
                              "description", "timestamp", "artifact_path", "artifact_hash",
                              "raw_evidence_ref", "is_ai_assisted"))
        if not item.get("raw_evidence_ref") and not item.get("artifact_path"):
            lines.extend(["", "Referencia na pôvodný artefakt chýba."])
    lines.extend(["", "## Časová os", "", f"Počet udalostí v prijatom JSON: {len(data['timeline'])}. "
                  "Zachované je poradie zdroja a pôvodný zápis času."])
    for i, event in enumerate(data["timeline"]):
        lines.extend(["", f"### Syntetická udalosť `/timeline/{i}`", ""])
        _fields(lines, event, ("timestamp", "original_timestamp", "timezone", "normalization_notes",
                               "event_type", "source_tool", "description", "relevance_score"))
        if not event.get("timezone"):
            lines.extend(["", "Zdroj neuvádza časovú zónu."])
    lines.extend(["", "## Diagnostika validátora", "", "Diagnostické položky vytvoril validátor.",
                  f"Štruktúra: `{check['status']}`.", ""])
    if check["issues"]:
        for issue in check["issues"]:
            lines.append("    " + _literal(issue))
    else:
        lines.append("Validátor neuviedol žiadne diagnostické položky.")
    lines.extend(["", "Rozsah je prijatý JSON. Autentickosť zdroja, pôvodné artefakty, podpisy, "
                  "dôveryhodnosť časových pečiatok, úplnosť prenosu a kontext modelu: `NOT_VERIFIED`.",
                  "", "## AI vysvetlenie", "", "AI vysvetlenie nebolo vytvorené.", ""])
    return "\n".join(lines).encode("utf-8")


def render_demo(scenario: str, snapshot: bytes) -> bytes:
    """Validate the captured bytes against the release manifest before formatting."""
    if type(snapshot) is not bytes:
        raise BriefError("IMMUTABLE_BYTES_REQUIRED")
    if scenario not in SCENARIOS:
        raise BriefError("UNKNOWN_SCENARIO")
    manifest = json.loads((PRODUCT / "brief_reference/manifest.json").read_bytes())
    pin = manifest[scenario]
    check = validator.validate_bytes(snapshot, profile=DEMO_PROFILE,
                                     expected_job_id=pin["job_id"], expected_case_id=pin["case_id"],
                                     expected_evidence_id=pin["evidence_id"])
    if check["passed"] is not True or check["status"] != "STRUCTURE_VALID":
        raise BriefError("INPUT_REJECTED")
    if check["report_generation_allowed"] is not False:
        raise BriefError("UNEXPECTED_VALIDATOR_POLICY")
    if check["input"]["sha256"] != pin["sha256"]:
        raise BriefError("FIXTURE_HASH_MISMATCH")
    return _markdown(json.loads(snapshot), check)
