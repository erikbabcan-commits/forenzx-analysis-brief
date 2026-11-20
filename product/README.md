# ForenZX Analysis Brief — prvý deterministický preflight

Stav: **implementovaný a lokálne otestovaný základ FX-005**. Dátum: 21. 11. 2026, Europe/Bratislava. Nejde o hotový skill, forenzný prehľad ani schválený Agensi balík.

`validate_input.py` preverí jeden **už extrahovaný JSON výsledok `AnalysisResult`**. Nepoužíva sieť, MCP klienta, model ani cudzie Python závislosti. Vstup otvára iba na čítanie a nemení ho. Výstupom je diagnostický JSON s počtami, JSON ukazovateľmi a explicitnými hranicami overenia; samotné texty nálezov, zdrojové cesty, upozornenia, identifikátory prípadu ani obsah neznámych polí do diagnostiky nekopíruje.

## Podklad a kompatibilita

- Upstream: [`core/models/forensic.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/models/forensic.py).
- MCP implementácia: [`core/server.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/server.py).
- Pripnutý commit: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`.
- Náš profil prijímaného vstupu: `forenzx-analysis-result-0e4c7fae`.
- Verzia validátora: `0.1.0`.

Identifikátor profilu patrí **nášmu validátoru**. Netvrdí, že upstream vkladá do odpovede `schema_version` alebo `forenzx_version`; preskúmaný `AnalysisResult` také polia nemá. `pack_version` označuje analytický balík a `execution_record.record_version` záznam vykonania. Ich význam sa nezamieňa s verziou celej schémy výsledku.

Upstream nástroj serializuje `AnalysisResult` cez `model_dump(mode="json")` a MCP obsluha ho zabalí do textového výsledku. **Tento validátor zatiaľ obal nerozbaľuje.** Odmietne JSON-RPC, MCP `content` aj `structuredContent`. Chybové odpovede, stavové hlásenia a extrakciu správnej odpovede má otestovať budúci adaptér spolu s reálnym klientom. Výber profilu je explicitná konfigurácia používateľa; sám osebe neoveruje, aký server skutočne vytvoril dodaný súbor.

## Rýchle spustenie na syntetických dátach

Požiadavka: Python 3.10 alebo novší. Z koreňa repozitára:

```bash
python3 product/validate_input.py \
  --input product/fixtures/completed-hit.json \
  --profile forenzx-analysis-result-0e4c7fae \
  --expected-job-id demo-job-hit \
  --expected-case-id demo-case \
  --expected-evidence-id demo-evidence
```

Druhý príklad ukazuje negatívny IOC výsledok, chýbajúcu referenciu a neurčené časové pásmo:

```bash
python3 product/validate_input.py \
  --input product/fixtures/completed-no-ioc.json \
  --profile forenzx-analysis-result-0e4c7fae \
  --expected-job-id demo-job-no-ioc \
  --expected-case-id demo-case \
  --expected-evidence-id demo-evidence
```

Oba príklady sú **vytvorené synteticky od nuly**. Názvy, udalosti, identity a hashové metadáta sú fiktívne. Prázdne podpisové polia nepredstavujú overený podpis. Počítač nepotrebuje ForenZX server ani model; ide o skúšku vstupnej kontroly, nie o demo AI generovania. Čas do výsledku v celom Agensi klientovi nebol meraný.

Voliteľné `--input -` číta z binárneho stdin. Skript možno skopírovať do dočasného adresára a spustiť odkiaľkoľvek; profil a validačné pravidlá obsahuje priamo. Cestu k vstupu zadáva volajúci explicitne. Skript nehľadá vedľajšie súbory balíka. Reálne poverenia ani obsah dôkazov nevkladajte do argumentov; očakávané identifikátory majú prísť z nezávisle určenej úlohy, nie byť automaticky prebraté z práve kontrolovaného výsledku.

## Ako čítať výsledok

| Pole alebo návratový kód | Význam |
| --- | --- |
| `status: STRUCTURE_VALID`, `passed: true`, exit `0` | Dodané bajty prešli týmto lokálnym profilom a kontrolami konzistencie. Viditeľné obmedzenia môžu zostať. |
| `status: REJECTED`, `passed: false`, exit `2` | Vstup, identita, stav alebo konfigurácia neprešli. Nevytvárať úspešný prehľad nálezov. |
| `report_generation_allowed: false` | Táto fáza sama nikdy nepovoľuje vydanie AI prehľadu. Chýbajú nadväzujúce kontroly transportu, modelu a produktu. |
| `coverage.scope: RECEIVED_JSON_ONLY` | Počty a ukazovatele opisujú iba prijatý JSON. |
| `upstream_total: UNKNOWN` | Nevieme, koľko položiek bolo pred prípadným skrátením alebo exportom. Nevyrábame pomer „X z Y“. |
| `transport_completeness`, `model_context: NOT_VERIFIED` | Overenie kompletnej MCP odpovede a kontextu klienta ešte neprebehlo. |
| `input.sha256` | SHA-256 presných prijatých bajtov. Je to identifikácia tohto vstupu, bez tvrdenia o jeho autenticite alebo integrite originálnych artefaktov. |
| `verification.*: NOT_VERIFIED` | Validátor neoveruje podpis, pôvod výsledku ani pôvodné artefakty. |

`complete_byte_read: true` znamená, že lokálny vstup neprekročil bajtový limit a bol celý načítaný do parsera. Nedokazuje, že export obsahoval všetky pôvodné dáta. Pri prekročení limitu CLI prečíta najviac limit + 1 bajt; `bytes_read` preto nie je tvrdením o celkovej veľkosti súboru a hash zostáva `null`.

`--help` používa bežný textový výstup pomoci. Diagnostika chýb CLI a vstupu má JSON formát a nevracia pôvodnú cestu či obsah chybných argumentov. Počet diagnostických položiek je obmedzený na 100; `diagnostics_limited` upozorní na skrátený zoznam. Celkový stav zostane odmietnutý aj vtedy, keď neskoršia chyba už do zoznamu vojsť nemohla.

## Kontrakt kontrol

Validátor nepreberá tolerantné prevody typov z Pydantic. Očakáva explicitný JSON z dohodnutého serializovaného výsledku:

- Žiadne duplicitné JSON kľúče, `NaN`, nekonečné čísla, neplatné UTF-8, osamotené Unicode surrogate ani nedokončené JSON dokumenty.
- Všetky polia profilovaných objektov musia byť prítomné, vrátane polí, ktoré upstream model interne predvolí. Vynechané `warnings`, `limitations`, `findings`, `timeline` alebo `chain_of_custody` sa nesmú doplniť prázdnym zoznamom.
- Nové polia v koreňovom výsledku, nálezoch, časovej osi, custody záznamoch a execution record sa odmietnu. Opaque slovníky `input_integrity`, `raw_evidence_ref` a `details` majú iba kontrolu typu a všeobecných JSON limitov; ich vnútorný význam sa neoveruje.
- `job_id`, `case_id` a `evidence_id` sa porovnávajú s nezávisle dodanými očakávaniami. Prípad, dôkaz, pack/verzia a pôvodné začiatky/ukončenia v execution record musia zodpovedať nadradenému výsledku.
- Prijíma sa iba `COMPLETED`. Všetky ostatné známe stavy sa odmietnu. Zachová sa aj upstream pravidlo, že `FAILED` a `SECURITY_BLOCKED` musia používať klasifikáciu `ERROR`.
- Typy, známe enum hodnoty, boolean `is_ai_assisted: false`, jedinečnosť ID nálezov, číselné rozsahy a hashové formáty sa kontrolujú bez domýšľania.
- Záporné trvanie, nenulový exit code a rozporné poradie začiatku/konca pri oboch explicitných offsetoch vyžadujú odmietnutie. Toto sú dodatočné hranice nášho reporting profilu; nie tvrdenie, že každá taká hodnota porušuje všetky upstream modely.
- `NO_KNOWN_IOC` ostáva obmedzeným negatívnym výsledkom. Rozpor s prítomným `HIT`, `SUSPICIOUS` alebo `ERROR` nálezom sa odmietne. Validátor nerobí všeobecnú sémantickú validáciu všetkých odborných tvrdení.
- Chýbajúca referencia k artefaktu je viditeľné obmedzenie s ukazovateľom na nález. Prítomná cesta alebo `raw_evidence_ref` sa nikdy automaticky neoznačuje za skutočne existujúci a preskúmaný artefakt.
- Časy sa nemenia ani neprepočítavajú. Nerozpoznaný formát a chýbajúci offset sú viditeľné obmedzenia. Bez explicitných offsetov sa poradie neodvodzuje. Nevykonáva sa overenie presnosti hodín či zdrojovej časovej zóny.
- Custody metadáta s rozdielnymi hashmi sa odmietnu, ak zdroj nemá explicitnú akciu `INTEGRITY_BREACH_DETECTED`; taká akcia zostáva viditeľným obmedzením. Zhoda hashových reťazcov nie je nezávislé overenie dôkazu.

Ukazovatele na warnings/limitations zachovávajú poradie a počty ich položiek. **Tento program zatiaľ nevytvára výsledný prehľad a nekopíruje doň celý text sekcií.** Zachovanie textov v budúcom prehľade musí mať ďalší test zdroj → hotový výstup.

## Limity tejto implementácie

| Parameter | Predvolená hodnota | Dovolená konfiguračná horná hranica |
| --- | ---: | ---: |
| `--max-bytes` | 262 144 | 4 194 304 |
| `--max-records` | 1 000 | 100 000 |
| `--max-depth` | 32 | 64 |
| `--max-nodes` | 20 000 | 250 000 |

Všetky hodnoty sú **predbežné technické limity lokálneho parsera**, overené hraničnými testami. Nie sú zmeraným kontextovým limitom žiadneho LLM, klienta, MCP transportu ani požiadavkou NIST/SWGDE. Zvýšenie limitu nepovoľuje automaticky väčší vstup do modelu.

`max-records` je súčet položiek piatich sekcií: nálezy + časová os + upozornenia + obmedzenia + custody záznamy. `max-depth` počíta koreňový JSON objekt ako úroveň 1. `max-nodes` počíta JSON hodnoty vrátane objektov a polí; názvy vlastností sa nepočítajú osobitne. Bajtový limit sa kontroluje pred parsovaním, stromové limity po syntaktickom parsovaní. Samotný Python parser môže veľmi hlboký dokument odmietnuť skôr; aj táto chyba sa uzavrie bezpečnou diagnostikou.

## Testy a výsledok tohto kroku

```bash
python3 -m unittest discover -s product/tests -v
```

Overené 21. 11. 2026: **34/34 automatických testov**. Sada zahŕňa obidva syntetické prípady, stavy úloh, chýbajúce/nové polia, nesúlad identít, neplatné vnorené hodnoty a enumy, limity, skrátený JSON, duplicitné kľúče, neplatné čísla/Unicode, upozornenie na konci veľkého vstupu, chýbajúce referencie a nepreukázaný čas.

Testy spustili aj skutočný CLI proces zo samostatnej kópie skriptu v dočasnom adresári. Overili nemennosť vstupného súboru, čítanie najviac limit + 1 bajt, JSON pri chybách, neuvádzanie citlivých sentinelových hodnôt a neblokujúce odmietnutie FIFO na POSIX systéme. Nevykonávali sieťové ani modelové volania.

## Čo zostáva otvorené pred dokončením FX-005 a balíka

Nadväzujúca [referenčná sada FX-006](reference/README.md) rozširuje dva príklady na verziovaný katalóg scenárov s nezávislými očakávaniami. Spúšťa sa cez `python3 product/run_reference_suite.py`. Príkaz `unittest discover` teraz zahŕňa aj testy jej hodnotiaceho mechanizmu; uvedených 34 testov opisuje pôvodnú sadu validátora.

1. Podporovaný MCP klient a adaptér, ktorý správne získa a extrahuje úplnú odpoveď **pred** odovzdaním modelu. Lokálny súbor môže byť už skrátený; tento validátor to bez ďalšieho dôkazu nezistí.
2. Dôveryhodné potvrdenie serverovej verzie/kontraktu a transportnej úplnosti. Počty položiek v prijatom JSON samy nepreukazujú úplnosť predchádzajúceho exportu.
3. Zmeraný rozpočet kontextu konkrétneho modelu a klienta vrátane pokynov, nástrojov, histórie a rezervy výstupu. Limity v tomto programe nie sú jeho náhradou.
4. Prepojenie kontrolovaného preflightu na oprávnenia a tok dát, vrátane odmietnutia nepodporovaného prostredia. Text `SKILL.md` sám nevynucuje, kedy klient odovzdá dáta modelu.
5. Šablóna prehľadu, presné prenesenie upozornení/obmedzení a následné porovnanie faktov a referencií. V tomto kroku nevznikol žiadny AI brief.
6. Posúdenie distribúcie v Agensi vrátane veľkosti a čitateľnosti skriptu, aktuálnych pravidiel doručovania a skutočného toku ukážky. Pracovný validátor nie je hotový predajný ZIP.

Platený produkt, podpora konkrétneho modelu, kryptografické overenie ani nezávislé odborné posúdenie sa týmto krokom nevyhlasujú za dokončené.
