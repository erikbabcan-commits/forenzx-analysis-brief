# Technické review FX-010 · renderer 0.1.1

Rozsah tvorí režim `SYNTHETIC_DEMO` s dvoma pripnutými vstupmi. PR #6 vychádza z auditnej vetvy na `5c922ac0a67a66504cb1557e833b7458d3d4df32`. Diff verzie 0.1.0 mal 11 súborov. Pri začatí review GitHub evidoval súhrn reprodukcie z Fedory a komentár o vynechanom automatickom review. Formálne ani riadkové review vtedy GitHub neevidoval.

## Fedorský dôkaz

Fedora testovala `0d2a394f69fb593f3fa301645010d23f7981cf28` s rendererom 0.1.0. Jej záznam uvádza 63 produktových testov, 50 referenčných scenárov, 22 testov stavu, 9 testov launchera a úspešnú kontrolu buildu a D1. Commit `5200590b46fd1740de7b0a5231ca4a494033f27a` pridal jediný súbor. V Codex Work sme z GitHubu načítali jeho presné bajty a overili ich voči Git blobu aj odtlačku oznámenému z Fedory.

| Dôkaz | Hodnota |
| --- | --- |
| Veľkosť pôvodného JSON | 2 396 B |
| Git blob | `4a510650f02da0310b2606b5d473dc30da8f48e8` |
| SHA-256 pôvodného JSON | `c923107412abe9878d0f7de5d06242a0c3b5f7168e467f0d69980ce63f5e3b4e` |

[Pôvodný report z Fedory](https://github.com/erikbabcan-commits/forenzx-analysis-brief/blob/5200590b46fd1740de7b0a5231ca4a494033f27a/docs/verification/FX010_FEDORA_VERIFICATION.json) · [Odtlačok oznámený z Fedory](https://github.com/erikbabcan-commits/forenzx-analysis-brief/pull/6#issuecomment-7082780518)

## Dve opravy po fedorskom behu

| Miesto vo verzii 0.1.0 | Pozorovaný dopad | Regresný test vo verzii 0.1.1 |
| --- | --- | --- |
| [brief_cli.py, riadok 41](https://github.com/erikbabcan-commits/forenzx-analysis-brief/blob/0d2a394f69fb593f3fa301645010d23f7981cf28/product/brief_cli.py#L41) | Pri zavretom čítacom konci rúry Python pri ukončení opakoval neúspešný zápis. Výsledkom bol kód 120 a druhá diagnostika. | `test_closed_stdout_returns_documented_error_once` spúšťa CLI so zavretým čítacím koncom. Zápis končí kódom 2 a jednou stručnou správou. |
| [render_brief.py, riadok 58](https://github.com/erikbabcan-commits/forenzx-analysis-brief/blob/0d2a394f69fb593f3fa301645010d23f7981cf28/product/render_brief.py#L58) | Brief pripisoval všetky odsadené hodnoty zdroju. V príklade NO_KNOWN_IOC však štyri odsadené položky vypočítal validátor. | `test_validator_items_have_their_own_provenance` rozlíši zdrojovú časť od diagnostiky vrátane pôvodu položky `TIMEZONE_UNSPECIFIED`. |

## Kontroly v Codex Work

Nasledujúce verdikty platia pre lokálne CLI v Linuxe s Pythonom 3.12.14. Označenia R01–R18 pochádzajú z [integračného checklistu](FX010_INTEGRATION_PRECHECK.md).

| ID | Verdikt | Dôkaz |
| --- | --- | --- |
| R01 | PASS | Obe CLI ukážky volajú ten istý renderer. Obe prešli v samostatných procesoch so zákazom socketov a podprocesov cez audit hook. |
| R02 | PASS | Pôvodný validátor má rovnaký Git blob. Povolenie musí byť presná logická hodnota false. Regresia odmietla true, 0 aj null. |
| R03 | PASS | Dve povolené ID. CLI odmietlo externú cestu, URL, pomlčku ako zdroj, zmenenú fixture, symbolický odkaz a FIFO. |
| R04 | PASS | Test zamenil súbor po validácii. Výstup sa zhodoval s pôvodnou bajtovou snímkou. |
| R05 | PASS | Samostatné zámeny job, case a evidence ID voči manifestu skončili chybou. |
| R06 | PASS | Obe ukážky prešli nezávislými obsahovými očakávaniami aj bajtovým porovnaním. |
| R07 | PASS | Porovnanie všetkých položiek podľa indexu pokrýva poradie, duplicity aj posledné varovanie. |
| R08 | PASS | Obidva nálezy majú ukazovateľ do JSON. HIT zachováva cestu a riadok 1, negatívny príklad uvádza chýbajúcu referenciu. |
| R09 | PASS | Negatívna interpretácia je viazaná na skúmaný rozsah. Syntetická zmena HIT na prázdne nálezy neprešla kontrolou odtlačku. Konflikt medzi negatívnou klasifikáciou a pozitívnym nálezom odmietol validátor. |
| R10 | PASS | Offset aj čas bez zóny zostali v pôvodnom zápise. Rozporné časy boli odmietnuté. |
| R11 | PASS po oprave | Samostatné sekcie pre zdroj, diagnostiku s uvedeným pôvodom a explicitné oznámenie, že AI vysvetlenie nebolo vytvorené. |
| R12 | PASS pre vykreslenie | Pandoc 3.1.11.1 s čítačkou GFM spracoval syntetické varovanie s odkazom, obrázkom, HTML, novým riadkom a smerovou značkou ako jeden blok kódu. Dekódovanie JSON obnovilo pôvodnú hodnotu. |
| R13 | PASS po oprave | Chyba a nadlimitný vstup nevytvorili cieľový súbor. Pri dvoch zápisoch na jednu cestu skončili procesy kódmi 0 a 2 a zostal jediný úplný súbor. Samostatný test pokrýva zatvorený stdout. |
| R14 | PASS | Samostatné procesy pri dvoch nastaveniach časovej zóny vyrobili presné referenčné bajty. |
| R15 | PASS | Vypočítaný odtlačok patrí vstupným bajtom JSON. Zdrojový pôvod, pôvodné artefakty, podpisy, dôveryhodné časy a úplnosť prenosu majú označenie `NOT_VERIFIED`. |
| R16 | PASS | V oddelenej kópii vynechanie posledného varovania skončilo očakávaným kódom 1 a zlyhaním dvoch podprípadov. |
| R17 | PASS pre checkout | Test kopíruje potrebné moduly a fixtures do nového adresára a spúšťa skutočné Python CLI mimo projektu. Doručenie cez Agensi je `NOT_TESTED`. |
| R18 | PASS pre odovzdanie vo Work | Verzie, testy, odtlačky aj rozsah sú nižšie. Nová nezávislá reprodukcia verzie 0.1.1 na Fedore je `NOT_TESTED`. |

| Markdown | 0.1.0 · Fedora | 0.1.1 · Codex Work |
| --- | --- | --- |
| completed-hit | `1ee78a92081d07ca3a1e75cafb897abdfebfc8b2055d0085c2fa80876003f665` | `4b81f94ba9fb43c753921c4aa0cd47e614b139a39450f12c1fa79694460e2a89` |
| completed-no-ioc | `f01a27663ed118d3e2d33c7047cbac09a58caa4f35e74b9bea7d678390cec978` | `5429135bdebd665ec87ef7c0796d97c76168a64a8f4b2ec91c669f1453685705` |

Obe nové ukážky prešli `cmp` proti referenciám 0.1.1. Produktové testy prešli v počte 65/65, referenčná sada FX-006 v počte 50/50. Bootstrap s Node.js 24.22.3 a npm 11.19.1 dokončil 22/22 testov stavu, 9/9 testov launchera, typecheck, build a HTTP kontrolu s reštartom dočasnej D1. Návratový kód bol 0.

```bash
python3 -m unittest product.tests.test_brief_cli.DemoCLITests.test_closed_stdout_returns_documented_error_once
python3 -m unittest product.tests.test_render_brief.RendererTests.test_validator_items_have_their_own_provenance
python3 -m unittest discover -s product/tests -v
python3 product/run_reference_suite.py
bash scripts/local-bootstrap.sh --check-only --port 0
```

Pre oba príklady sa dá použiť [fedorský postup](../handoffs/FX010_CODEX_HANDOFF.md). Overenie reálneho prípadu, modelu a produkčného toku zostáva otvorené. `report_generation_allowed` má hodnotu `false`.
