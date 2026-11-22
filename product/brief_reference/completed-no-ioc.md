# AI asistovaný návrh — vyžaduje kontrolu analytikom

**Syntetická ukážka — automaticky vytvorený pracovný prehľad**

Režim `SYNTHETIC_DEMO` · `report_generation_allowed = false`

> Tento dokument je AI asistovaný pracovný návrh prehľadu z poskytnutých výsledkov ForenZX. Pred odborným použitím musí analytik overiť údaje, odkazy a závery oproti zdrojovým výsledkom a relevantným podkladom. Dokument sám osebe nepreukazuje úplnosť vyšetrovania ani prípustnosť dôkazov.

## Identita a rozsah

SHA-256 prijatých bajtov JSON: `feacf239b2667363425309f334966e6b0db64d992ab923bf067fee0a38a36aa6`
Profil validátora: `forenzx-analysis-result-0e4c7fae` · renderer: `0.1.0`
Pripnutá revízia profilu Hubu: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`

Hodnoty v odsadených blokoch pochádzajú zo zdroja. Hodnota `null` označuje nedostupný údaj a `""` prázdny reťazec.

    job_id = "demo-job-no-ioc"
    case_id = "demo-case"
    evidence_id = "demo-evidence"
    pack_id = "synthetic-triage"
    pack_version = "0.0.0"
    status = "COMPLETED"
    summary_classification = "NO_KNOWN_IOC"
    started_at = "2026-01-01T12:00:00+00:00"
    completed_at = "2026-01-01T12:00:02+00:00"

### Integrita a história podľa zdroja

    input_integrity = {"status": "DEMO_METADATA_NOT_VERIFIED", "synthetic": true}

Záznam `/chain_of_custody/0`

    action = "SYNTHETIC_COPY"
    actor = "synthetic-analyst"
    timestamp = "2026-01-01T12:00:00+00:00"
    sha256_before = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    sha256_after = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

Zdrojový záznam `/execution_record`

    record_version = "2"
    input_root_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ioc_bundle_version = "synthetic-0"
    ioc_bundle_sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

## Upozornenia a obmedzenia zdroja

### Upozornenia

    /warnings/0 = "SYNTHETIC DEMO: all identifiers, events and hash metadata are fictional; no live server or original artifact was examined."
    /warnings/1 = "The source fixture has no artifact reference for the negative finding."

### Obmedzenia

    /limitations/0 = "SYNTHETIC DEMO ONLY."
    /limitations/1 = "The fictional indicator set and examined subset are limited; absence of a match does not establish a safe device."
    /limitations/2 = "The event timezone is unknown."

## Zdrojové nálezy

Počet nálezov v prijatom JSON: 1.

V skúmanom rozsahu sa nenašli známe IOC z použitého balíka.

### Nález `/findings/0`

    id = "demo-finding-negative"
    classification = "NO_KNOWN_IOC"
    severity = "INFO"
    confidence = "LOW"
    ioc_type = "synthetic-indicator-set"
    ioc_name = null
    description = "Synthetic example: no known indicator match within the fictional examined subset. This is not a clean-device conclusion."
    timestamp = "2026-01-01T11:59:00"
    artifact_path = ""
    artifact_hash = null
    raw_evidence_ref = null
    is_ai_assisted = false

Referencia na pôvodný artefakt chýba.

## Časová os

Počet udalostí v prijatom JSON: 1. Zachované je poradie zdroja a pôvodný zápis času.

### Syntetická udalosť `/timeline/0`

    timestamp = "2026-01-01T11:59:00"
    original_timestamp = "2026-01-01T11:59:00"
    timezone = null
    normalization_notes = "Source offset is unknown. No UTC conversion was performed."
    event_type = "SYNTHETIC_EVENT"
    source_tool = "synthetic-fixture"
    description = "Fictional event for validator testing."
    relevance_score = 0.5

Zdroj neuvádza časovú zónu.

## Diagnostika validátora

Štruktúra: `STRUCTURE_VALID`.

    {"code": "NEGATIVE_IOC_SCOPE", "message": "No known IOC match is limited to the source examination and indicators; it does not establish a safe device.", "path": "/summary_classification", "severity": "limitation"}
    {"code": "MISSING_ARTIFACT_REFERENCE", "message": "No nonempty artifact path or raw reference was supplied; no reference was invented.", "path": "/findings/0", "severity": "limitation"}
    {"code": "TIMEZONE_UNSPECIFIED", "message": "Timestamp has no offset; no timezone or UTC value was inferred.", "path": "/findings/0/timestamp", "severity": "limitation"}
    {"code": "TIMEZONE_UNSPECIFIED", "message": "Timestamp has no offset; no timezone or UTC value was inferred.", "path": "/timeline/0/timestamp", "severity": "limitation"}

Rozsah je prijatý JSON. Autentickosť zdroja, pôvodné artefakty, podpisy, dôveryhodnosť časových pečiatok, úplnosť prenosu a kontext modelu: `NOT_VERIFIED`.

## AI vysvetlenie

AI vysvetlenie nebolo vytvorené.
