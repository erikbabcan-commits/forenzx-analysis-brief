# FX-006 — záznam dokončenia referenčnej sady

Dátum: **21. 11. 2026, Europe/Bratislava**.

Verdikt: **PASS — pripravená a lokálne overená syntetická referenčná sada.** Všetkých šesť kritérií FX-006 má nižšie uvedený podklad. Živý klient, oprávnenia, model a finálny brief zostávajú samostatné otvorené úlohy.

## Čo sa vykonalo

[Zadanie](prompts/FX006_REFERENCE_SUITE_PROMPT.md) bolo prispôsobené projektu a vykonané. Autorský [katalóg](../product/reference/catalog.json) obsahuje 50 scenárov s presnými očakávaniami. Builder pripraví ich vstupy bez volania validátora; runner porovná skutočný výsledok s vopred zapísaným očakávaním.

Katalóg bol zafixovaný pred prvým vyhodnotením a pri hodnotení sa nemenil. SHA-256: `0e356122ecc01a51797703bd81939593b3b16c298bd84d689956229a9118cda4`.

Deterministicky vytvorený manifest: `71dde804e9dd40191a574c898786cdae3d49f74bdb4973a053bd37c899847f4a`. Päťdesiat vstupov má spolu 995 632 bajtov. Materiál je vytvorený synteticky od nuly.

## Výsledky

| Kontrola | Výsledok | Rozsah dôkazu |
| --- | --- | --- |
| Referenčné scenáre | **50/50 PASS** | Skutočný lokálny výsledok zodpovedá autorským očakávaniam. |
| Platné štruktúry v sade | **10** | Môžu obsahovať viditeľné obmedzenia; nepovoľujú generovanie prehľadu. |
| Očakávane odmietnuté vstupy | **40** | Odmietnutie je úspešným výsledkom príslušného negatívneho scenára. |
| Pôvodné testy validátora | **34/34 PASS** | Pôvodné testy a implementácia validátora zostali zachované. |
| Nové testy runnera | **12/12 PASS** | Úplnosť sady, integrita vstupov, správnosť porovnávania a reprodukovateľnosť. |
| Celý `npm run test:product` | **46/46 PASS** | Predchádzajúce dve testové skupiny spolu; nejde o ďalších 46 nezávislých scenárov. |

Strojový výsledok je v [FX006_REFERENCE_RESULTS.json](verification/FX006_REFERENCE_RESULTS.json). Obsahuje identitu katalógu a manifestu, hash zdroja validátora aj runnera, výsledok každého prípadu a explicitné oblasti `NOT_TESTED`.

## Mapovanie na šesť podmienok FX-006

| Kritérium | Prípady a podklad |
| --- | --- |
| Dokončené/nedokončené stavy, chýbajúca úloha, prístup | FX006-001–013; všetkých osem nedokončených stavov, status/message a dva odlišné kontrakty JSON-RPC chýb. |
| Referencie, časová zóna a rozporná identita | FX006-014–019; chýbajúca referencia, neznáma zóna, job/case/evidence a execution record. |
| Negatívny IOC a vložené pokyny | FX006-002, FX006-020; presný vstupný text, viditeľné obmedzenia a referencie. Odolnosť modelu zostáva netestovaná. |
| Očakávania pred vyhodnotením | Nemenný hash katalógu zafixovaný pred prvým spustením; výsledky sa nekopírujú do očakávaní. |
| Hranice, poškodený JSON, typy a enumy | FX006-021–032, FX006-043–045; bajty 262143/262144/262145 a agregované položky 999/1000/1001. |
| Verzie, povinné sekcie a posledný warning | FX006-033–042; samostatné chýbajúce sekcie, explicitný profil a presný posledný marker z 512 warnings. |

Ďalšie rozpory pokrývajú FX006-046–050: custody metadáta, negatívny súhrn pri pozitívnom náleze, časové poradie, exit code a neznáme pole.

## Overenie samotného hodnotenia

Runner naviaže celý dodaný manifest na nový deterministický výstup autorského katalógu. Testy preukázali odmietnutie skrátenej sady, zmeneného očakávania, nahradeného vstupu aj vtedy, keď niekto prepísal jeho deklarovaný hash. Nesprávny ukazovateľ sa nesmie potichu preskočiť.

Kontrolovaný mutant zmení skutočný výsledok validátora vrátane typu `true` oproti `1` a povolenia generovania. Porovnávanie musí vydať FAIL a CLI kód 1. Poškodená sada má samostatný kód 2; úspech kód 0. Overené sú aj cesty mimo sady, symlinky, reprodukovateľnosť, beh z cudzieho adresára a ochrana existujúceho reportu pred prepísaním.

Report nekopíruje text vložených pokynov ani posledného upozornenia. Výsledky a chyby sú uvedené pomocou ID prípadov a kontrolovaných kódov.

## Reprodukcia

Z koreňa repozitára s Python 3.10+:

```bash
python3 product/run_reference_suite.py
python3 -m unittest discover -s product/tests -v
```

Zachovanie vstupov a nového reportu:

```bash
python3 product/run_reference_suite.py \
  --materialize /tmp/forenzx-fx006-fixtures \
  --report /tmp/forenzx-fx006-results.json
```

Cieľ pre fixtures musí byť nový alebo prázdny; existujúci report sa štandardne neprepisuje. Na nové vyhodnotenie už materializovanej sady možno použiť `--manifest /tmp/forenzx-fx006-fixtures/manifest.json`.

## Hranice a ďalší krok

Všetky úspešné preflight výsledky stále obsahujú `report_generation_allowed: false`. Bajtové hranice sú limity lokálneho parsera. Hash prijatého súboru nepreukazuje pôvod ani podpis.

Chýbajúca úloha a odmietnutý prístup sú pripravené syntetické odpovede. Aktuálny validátor ich odmieta ako nepodporovaný obal; správne rozbalenie a správanie skutočného klienta sa otestujú vo FX-007/008. Vložený pokyn je testovací text; jeho prítomnosť vo vstupe nie je úspešným testom odolnosti LLM.

Ďalší krok je **FX-007 — reálny klient na tejto syntetickej sade**. FX-005 zostáva rozpracovaná 5/8 a odborné review vo FX-016 zostáva otvorené. Interné technické review tejto sady nenahrádza nezávislého odborného forenzného hodnotiteľa.

## Zápis do pracovného dashboardu

Produkčný build prešiel a Sites potvrdil súkromné nasadenie zdroja `20a9ff5c9bb4bbc118dd6c20a671c33ce316216e` (deployment `appgdep_6b00dce3caec8191946eebd8886d4f89`). GitHub obsahuje rovnakú implementáciu a tento následný záznam kontroly.

FX-006 bola cez rozhranie uložená ako hotová so všetkými šiestimi kritériami a konkrétnym dôkazom. Po úplnom obnovení stránky export potvrdil `done`, checkboxy `[0,1,2,3,4,5]`, presné znenie poznámky a revíziu 3. Ostatných 17 úloh zostalo zhodných s exportom pred zmenou. Všetkých 14 starších udalostí sa zachovalo; pribudla jediná udalosť aktualizácie FX-006.

Dashboard zobrazuje **4/18 hotových úloh, 4/17 splnených brán** a ako najbližší odblokovaný krok FX-007. Uloženie pracovného stavu neuzatvára žiadnu ďalšiu produktovú úlohu.
