"""FX-011 claim provenance for the two pinned, model-free CLI demos."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from product.validate_input import validate_bytes

PRODUCT = Path(__file__).resolve().parents[1]

# Reviewed template language. New narrative requires explicit review even if
# a Markdown snapshot is regenerated alongside the renderer.
TEMPLATE = frozenset("""
# AI asistovaný návrh — vyžaduje kontrolu analytikom
**Syntetická ukážka — automaticky vytvorený pracovný prehľad**
Režim `SYNTHETIC_DEMO` · `report_generation_allowed = false`
## Identita a rozsah
Zdrojové polia používajú zápis JSON. Hodnota `null` označuje nedostupný údaj a `""` prázdny reťazec.
Profil validátora: `forenzx-analysis-result-0e4c7fae` · renderer: `0.1.1`
Pripnutá revízia profilu Hubu: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`
### Integrita a história podľa zdroja
## Upozornenia a obmedzenia zdroja
### Upozornenia
### Obmedzenia
## Zdrojové nálezy
## Časová os
## Diagnostika validátora
Diagnostické položky vytvoril validátor.
Štruktúra: `STRUCTURE_VALID`.
Rozsah je prijatý JSON. Autentickosť zdroja, pôvodné artefakty, podpisy, dôveryhodnosť časových pečiatok, úplnosť prenosu a kontext modelu: `NOT_VERIFIED`.
## AI vysvetlenie
AI vysvetlenie nebolo vytvorené.
""".strip().splitlines())


class BriefClaimTests(unittest.TestCase):
    def test_cli_claims_have_a_source_or_reviewed_template(self):
        contract = (PRODUCT.parent / "docs/PRODUCT_CONTRACT.md").read_text(encoding="utf-8")
        disclaimer, = (line for line in contract.splitlines() if line.startswith("> Tento dokument"))
        for scenario in ("completed-hit", "completed-no-ioc"):
            with self.subTest(scenario=scenario):
                raw = (PRODUCT / "fixtures" / (scenario + ".json")).read_bytes()
                data = json.loads(raw)
                output = subprocess.check_output(
                    [sys.executable, str(PRODUCT / "brief_cli.py"), scenario], timeout=10
                ).decode("utf-8")
                allowed = set(TEMPLATE)
                allowed.update((
                    disclaimer,
                    f"SHA-256 prijatých bajtov JSON: `{hashlib.sha256(raw).hexdigest()}`",
                    f"Počet nálezov v prijatom JSON: {len(data['findings'])}.",
                    f"Počet udalostí v prijatom JSON: {len(data['timeline'])}. "
                    "Zachované je poradie zdroja a pôvodný zápis času.",
                ))
                scope = "V skúmanom rozsahu sa nenašli známe IOC z použitého balíka."
                if data["summary_classification"] == "NO_KNOWN_IOC":
                    allowed.add(scope)
                    heading = "## Zdrojové nálezy\n"
                    self.assertIn(heading, output)
                    findings_intro = output.split(heading, 1)[1].split("\n#", 1)[0]
                    self.assertIn(scope, findings_intro.splitlines(),
                                  f"Missing scoped conclusion in finding summary: {findings_intro.strip()}")
                else:
                    self.assertNotIn(scope, output)
                if any(not f["raw_evidence_ref"] and not f["artifact_path"] for f in data["findings"]):
                    allowed.add("Referencia na pôvodný artefakt chýba.")
                if any(not e["timezone"] for e in data["timeline"]):
                    allowed.add("Zdroj neuvádza časovú zónu.")

                # Compare structured diagnostics to the independently invoked
                # validator. Its limitations have a different origin from findings.
                check = validate_bytes(raw, profile="forenzx-analysis-result-0e4c7fae",
                                       expected_job_id=data["job_id"], expected_case_id=data["case_id"],
                                       expected_evidence_id=data["evidence_id"])
                if not check["issues"]:
                    allowed.add("Validátor neuviedol žiadne diagnostické položky.")

                records = {"## Identita a rozsah": data,
                           "### Integrita a história podľa zdroja": data,
                           "Zdrojový záznam `/execution_record`": data["execution_record"]}
                findings = {}
                for i, finding in enumerate(data["findings"]):
                    findings[f"### Nález `/findings/{i}`"] = finding
                records.update(findings)
                for i, event in enumerate(data["timeline"]):
                    records[f"### Syntetická udalosť `/timeline/{i}`"] = event
                for i, event in enumerate(data["chain_of_custody"]):
                    records[f"Záznam `/chain_of_custody/{i}`"] = event
                for heading, key in (("### Upozornenia", "warnings"), ("### Obmedzenia", "limitations")):
                    records[heading] = {f"/{key}/{i}": v for i, v in enumerate(data[key])}

                context = None
                confidence = []
                for line in output.splitlines():
                    if not line:
                        continue
                    if line in records or line.startswith("#"):
                        context = line
                    if line.startswith("    "):
                        if context == "## Diagnostika validátora":
                            self.assertIn(json.loads(line), check["issues"])
                        else:
                            key, value = line.strip().split(" = ", 1)
                            record = records.get(context, {})
                            self.assertIn(key, record, line)
                            self.assertEqual(json.loads(value), record[key], line)
                            if key == "confidence":
                                confidence.append((context, json.loads(value)))
                    else:
                        self.assertTrue(line in allowed or line in records,
                                        f"Unsupported brief statement: {line}")
                self.assertCountEqual(confidence, [(h, f["confidence"]) for h, f in findings.items()])
