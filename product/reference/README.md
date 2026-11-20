# FX-006 — syntetická referenčná sada v1

**50 vopred definovaných scenárov** pre lokálnu kontrolu prijatého ForenZX výsledku a prípravu následných integračných testov. Celá sada je syntetická. Žiadny prípad neobsahuje reálny spis, poverenie, osobný údaj ani skutočný dôkazový materiál.

Sada pripravuje vstupy a presné očakávania. Sama nepreukazuje fungovanie servera, autentifikácie, MCP adaptéra, modelu, finálneho briefu ani podpisov.

## Zdrojový kontrakt a pôvod očakávaní

- Pripnutý upstream commit: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`.
- [Model výsledku](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/models/forensic.py) a [obsluha nástrojov](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/server.py).
- Profil vstupu: `forenzx-analysis-result-0e4c7fae`. Je to identifikátor nášho profilu; upstream tým nedostáva vymyslené `schema_version`.
- Autorský zdroj: [catalog.json](catalog.json). Každý prípad má ID, recept, očakávanú identitu, technické limity, presný výsledný stav, presnú množinu diagnostických kódov a podľa potreby ďalšie kontroly cez JSON Pointer.
- Katalóg bol vytvorený **pred prvým vyhodnotením**. Jeho očakávania nevznikli kopírovaním výstupu validátora.
- Zafixovaný SHA-256 katalógu pred hodnotením: `0e356122ecc01a51797703bd81939593b3b16c298bd84d689956229a9118cda4`.

Prípadné nezhody sa majú vyšetriť podľa kontraktu. Očakávanie sa nesmie automaticky prepísať na pozorovaný výsledok len preto, aby test prešiel. Vecná oprava katalógu potrebuje samostatný dôvod a novú zaznamenanú identitu.

## Súbory a vytvorenie vstupov

`build_fixtures.py` používa iba štandardnú knižnicu Pythonu. Načíta dva už existujúce syntetické základy z `../fixtures/`, overí ich SHA-256 uvedené v katalógu a vykoná obmedzené deklaratívne úpravy. Neimportuje validátor, nespúšťa model, sieť, shell ani príkazy z obsahu artefaktov.

```bash
python3 product/reference/build_fixtures.py \
  --output /tmp/forenzx-fx006-reference
```

Cieľový adresár musí byť nový alebo prázdny a nesmie byť symlink. Existujúcu sadu skript neprepisuje. Vznikne `manifest.json` a 50 vstupov v `files/`; veľké hraničné súbory sa preto nemusia uchovávať v zdrojovom repozitári.

Manifest obsahuje pre každý vstup počet bajtov a SHA-256. Relatívne cesty sú vytvorené výhradne z kontrolovaných ID prípadov. Očakávania sa prenášajú z katalógu bez odvodenia z výsledku testu.

Overenie samotného generátora: dve materializácie vytvorili identické manifesty aj vstupné bajty; kontrolované boli všetky vstupné assertions a odmietnutie prepisu neprázdneho cieľa. Spolu vzniká **995 632 bajtov vstupov**. SHA-256 manifestu pri tomto katalógu a generátore je `71dde804e9dd40191a574c898786cdae3d49f74bdb4973a053bd37c899847f4a`. Tento údaj nie je výsledkom validácie 50 scenárov.

## Matica pokrytia

| Prípady | Účel | Očakávanie lokálneho preflightu |
| --- | --- | --- |
| FX006-001–002 | Dokončený HIT a `NO_KNOWN_IOC` s referenčnými obmedzeniami | Platná štruktúra; zachované počty a viditeľné obmedzenia. |
| FX006-003–010 | Všetkých 8 nedokončených stavov: QUEUED, VALIDATING, RUNNING, PARSING, VERIFYING, FAILED, CANCELLED, SECURITY_BLOCKED | `ANALYSIS_NOT_COMPLETED`; žiadne povolenie prehľadu. |
| FX006-011–013 | Status/message, chýbajúca úloha, odmietnutý prístup | Status sa nesmie zameniť za výsledok; JSON-RPC chyby sú odmietnuté ako obal. |
| FX006-014–019 | Chýbajúca referencia, neznáma zóna, tri nezávislé identity, execution record iného prípadu | Presná viditeľná limitácia alebo chyba identity. |
| FX006-020 | Škodlivé pokyny v texte syntetického artefaktu | Text je dátom; štruktúra môže prejsť. Správanie modelu zostáva netestované. |
| FX006-021–026 | Bajty a agregované počty pod limitom, na limite a nad limitom | Presná hranica deklarovaného lokálneho profilu; nad limitom odmietnutie. |
| FX006-027–036 | Skrátený JSON, duplicita, nesprávne typy, nové enumy a verzie | Presné príslušné chybové kódy. |
| FX006-037–041 | Osobitne chýbajú warnings, limitations, findings, timeline, custody | `MISSING_FIELD`; sekcia sa nenahradí prázdnym zoznamom. |
| FX006-042 | Posledné upozornenie zo sady 512 warnings | Presný vstupný marker, počet 512 a posledný pointer `/warnings/511`. |
| FX006-043–045 | NaN, neplatné UTF-8 a osamotený Unicode surrogate | Odmietnutie neplatných dát. |
| FX006-046–050 | Custody rozpor, negatívny súhrn pri HIT, opačné časy, nenulový exit code, nové pole | Viditeľná chyba bez domýšľania opravenej hodnoty. |

## Presné hranice scenárov

Predvolený testovací profil má **262 144 bajtov, 1 000 agregovaných položiek, hĺbku 32 a 20 000 JSON uzlov**. Sú to predbežné technické limity už existujúceho validátora. Sada ich nepovažuje za odmeranú veľkosť kontextu LLM.

Bajtové scenáre majú presne **262 143 / 262 144 / 262 145 bajtov**. Veľkosť sa doplní platným JSON whitespace; táto trojica skúma bajtovú hranicu, nie schopnosť modelu spracovať dlhý obsah. Samostatný obsahový scenár FX006-042 má 512 rôznych upozornení s markerom na konci.

Počet položiek **999 / 1 000 / 1 001** je súčtom piatich sekcií: findings, timeline, warnings, limitations a chain_of_custody. Nie je to tvrdenie o počte nálezov ani o úplnosti pôvodného exportu. Po zmeraní klienta vo FX-005 sa relevantné parametrické hranice musia overiť znovu.

`expected_identity` je samostatne zapísané očakávanie testu. Pri troch rozporových prípadoch sa zámerne líši od identity vo vstupnom súbore; runner ho nesmie prepísať hodnotou z práve testovaného JSON.

## Čo lokálny úspech znamená

Každý prípad zachováva zákaz vyhlásiť prehľad za pripravený iba na základe preflightu: `report_generation_allowed: false`. Úplnosť transportu, kontext modelu, autenticita, originálne artefakty a podpisy zostávajú neoverené.

`expected.assertions` kontrolujú konkrétne hodnoty v diagnostickom výstupe. `input_assertions` kontrolujú, že generátor skutočne pripravil príslušný obsah — napríklad presný injection text alebo posledný warning. Prítomnosť takéhoto textu vo vstupe nepreukazuje jeho bezpečné spracovanie modelom ani zachovanie vo finálnom briefe.

JSON-RPC fixtures FX006-012 a FX006-013 majú rozdielny význam pre budúci adaptér, hoci ich dnešný validátor zhodne odmieta kódom `UNSUPPORTED_WRAPPER`:

- **Chýbajúca úloha:** vrátiť zrozumiteľnú nedostupnosť výsledku a overiť správne ID; nehľadať náhradný spis.
- **Odmietnutý prístup:** zastaviť spracovanie a vyriešiť oprávnenie; neobchádzať ho admin kľúčom alebo iným endpointom.

Syntetický text odmietnutia nie je tvrdením o presnom produkčnom chybovom hlásení či úspechu autentifikačného testu. Skutočný klient, jeho rozbalenie odpovedí a oprávnenia zostávajú vo FX-007/008.

Každý `future_workflow.validation_status` je **`NOT_TESTED`**. Obsah `expected_behavior` je požiadavka pripravená na ďalšiu fázu, nie dosiahnutý výsledok. Týka sa to najmä odolnosti voči vloženým pokynom, zachovania textov vo finálnom prehľade, vyjednania MCP, ochrany dát a modelových limitov.
