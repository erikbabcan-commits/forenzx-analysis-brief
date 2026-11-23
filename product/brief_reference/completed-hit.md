# AI asistovaný návrh — vyžaduje kontrolu analytikom

**Syntetická ukážka — automaticky vytvorený pracovný prehľad**

Režim `SYNTHETIC_DEMO` · `report_generation_allowed = false`

> Tento dokument je AI asistovaný pracovný návrh prehľadu z poskytnutých výsledkov ForenZX. Pred odborným použitím musí analytik overiť údaje, odkazy a závery oproti zdrojovým výsledkom a relevantným podkladom. Dokument sám osebe nepreukazuje úplnosť vyšetrovania ani prípustnosť dôkazov.

## Identita a rozsah

SHA-256 prijatých bajtov JSON: `461a511f6ca015ef1552b86fd1442e37e65288b0323987d4421adf6086a6c192`
Profil validátora: `forenzx-analysis-result-0e4c7fae` · renderer: `0.1.1`
Pripnutá revízia profilu Hubu: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`

Zdrojové polia používajú zápis JSON. Hodnota `null` označuje nedostupný údaj a `""` prázdny reťazec.

    job_id = "demo-job-hit"
    case_id = "demo-case"
    evidence_id = "demo-evidence"
    pack_id = "synthetic-triage"
    pack_version = "0.0.0"
    status = "COMPLETED"
    summary_classification = "HIT"
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

### Obmedzenia

    /limitations/0 = "This fixture demonstrates structure only and provides no evidence about a real device."

## Zdrojové nálezy

Počet nálezov v prijatom JSON: 1.

### Nález `/findings/0`

    id = "demo-finding-001"
    classification = "HIT"
    severity = "MEDIUM"
    confidence = "HIGH"
    ioc_type = "synthetic-domain"
    ioc_name = "SYNTHETIC-IOC-001"
    description = "Synthetic training fixture: an example event matched a fictional indicator. No real evidence was examined."
    timestamp = "2026-01-01T11:59:00+00:00"
    artifact_path = "synthetic/events.jsonl"
    artifact_hash = null
    raw_evidence_ref = {"line": 1, "path": "synthetic/events.jsonl"}
    is_ai_assisted = false

## Časová os

Počet udalostí v prijatom JSON: 1. Zachované je poradie zdroja a pôvodný zápis času.

### Syntetická udalosť `/timeline/0`

    timestamp = "2026-01-01T11:59:00+00:00"
    original_timestamp = "2026-01-01T11:59:00+00:00"
    timezone = "UTC"
    normalization_notes = null
    event_type = "SYNTHETIC_EVENT"
    source_tool = "synthetic-fixture"
    description = "Fictional event for validator testing."
    relevance_score = 0.5

## Diagnostika validátora

Diagnostické položky vytvoril validátor.
Štruktúra: `STRUCTURE_VALID`.

Validátor neuviedol žiadne diagnostické položky.

Rozsah je prijatý JSON. Autentickosť zdroja, pôvodné artefakty, podpisy, dôveryhodnosť časových pečiatok, úplnosť prenosu a kontext modelu: `NOT_VERIFIED`.

## AI vysvetlenie

AI vysvetlenie nebolo vytvorené.
