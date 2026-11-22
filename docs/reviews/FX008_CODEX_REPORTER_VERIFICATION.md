# FX-008: Overenie reálneho klienta Codex CLI s rolou reporter a dôkazom identity

**Dátum overenia:** 2026-11-22T02:54:01Z  
**Prostredie:** Fedora Linux (lokálne testovacie prostredie)  
**Klient:** `codex-cli 0.170.0` (prihlásený účet ChatGPT)  
**Release Board commit:** `7fa5ea573541d2e44b527b2662d1de9daf0bc4f9` (vetva `fix/fx008-reporter-evidence`)  
**ForenZX MCP Hub commit:** `3b4effdb08cda68f733c56d995ccb54380729e8b` ([Hub PR #29](https://github.com/erikbabcan-commits/forenzx-mcp-hub/pull/29))  
**ID behu:** `20261122T025347Z-72cc4984`  
**Report behu:** `/home/vorkei/Projekty/forenzx-analysis-brief-fedora/.fx008-runtime/runs/20261122T025347Z-72cc4984/report.json`  
**SHA-256 reportu:** `528d0edbb1ed8da523c263e7162ddbced4db2f4e560f7a90766fd2e543a43f98`  

---

## 1. Zhrnutie a verdikt

**Verdikt:** **PASS**  
*Skutočný klient codex-cli 0.170.0 s oprávnením reporter úspešne cez MCP prečítal stav aj výsledok syntetickej analýzy zo servera a vrátil presnú 6-poľovú odpoveď, pričom obe čítania preukázali v tej istej udalosti úspešnú odpoveď Hubu, správne job_id, očakávaný hash výsledku a väzbu na presne to syntetické reporter poverenie, ktoré beh vydal pre Codex.*

---

## 2. Rozlíšenie overenia: Čo overil Hub a čo porovnala sonda

Pre zaistenie rigoróznosti dôkazu identity dokumentácia striktne rozlišuje zodpovednosti medzi serverom a sondou:

### 2.1 Čo overil ForenZX MCP Hub (server)
- **Kryptografická autenticita a expirácia JWT:** Overenie podpisu voči kľúču inštancie (`JWT_SECRET_KEY`) a platnosti expiračného timestampu (`exp`).
- **Fail-closed autorizácia nástrojov:** Vynútenie obmedzení roly `reporter` v `core/acl.py` – povolené výhradne čítacie nástroje `forenzx_analysis_status` a `forenzx_analysis_results`. Akékoľvek zápisové či modifikačné nástroje (`forenzx_analysis_start`, `forenzx_analysis_cancel`) sú serverom odmietnuté s kódom `-32603` (pokryté 77/77 regresnými testami).
- **Viacúrovňové ACL pre prípad a úlohu:** Overenie väzby na deklarovanú organizáciu, oprávnenie prístupu k prípadu (`report_case_ids`) a úlohe (`report_job_ids`) prostredníctvom `case_access_provider`.

### 2.2 Čo porovnala testovacia sonda
- **In-memory väzba na vydané poverenie klienta:** Hub v odpovedi nevystavuje identifikátor tokenu; sonda preto v ASGI middleware (`Recorder`) priamo v pamäti (bez zápisu na disk, do logov či reportu) pomocou `hmac.compare_digest` porovnala prijatý Bearer token voči presne tomu syntetickému tokenu, ktorý tento konkrétny beh vydal pre klienta Codex. Do udalosti uložila výhradne boolean výsledok `caller_credential_matched: true`.
- **Korelačné pravidlo jednej udalosti:** Sonda v hodnotení `evaluate_codex_events` vyžadovala, aby pre každé z dvoch volaní nastali v **tej istej udalosti** súčasne všetky kritériá:
  1. HTTP status 200, bez chyby JSON-RPC (`rpc_error_code is None`, `has_result: true`, `tool_is_error: false`).
  2. Zhodné `job_id` pri požiadavke aj odpovedi (`requested_job_id == job_id` a `returned_job_id == job_id`).
  3. Zhoda kontrolného súčtu výsledku s očakávaným fixatúrnym hašom (`tool_result_sha256 == expected_hash`).
  4. Skutočná väzba na vydané poverenie (`caller_credential_matched: true`) a rolu `reporter` (`auth_role == "reporter"`).
- **Odvodenie akceptácie:** Hodnota `server_accepted_reporter: true` aj finálny `PASS` sú odvodené priamo z prítomnosti oboch týchto verifikovaných udalostí v prevádzkovom zázname.

---

## 3. Namerané výsledky

### 3.1 Výsledok väzby na poverenie pre jednotlivé nástroje
- **`forenzx_analysis_status`:**
  - `verified_event_present`: **ÁNO (Event 17)**
  - `caller_credential_matched`: **ÁNO** (prijatý token sa presne zhodoval s vydaným tokenom)
  - `auth_role`: **`reporter`**
  - `job_id`: zhodné s očakávaným syntetickým ID
  - `tool_result_sha256`: zhodné s očakávaným stavom
- **`forenzx_analysis_results`:**
  - `verified_event_present`: **ÁNO (Event 18)**
  - `caller_credential_matched`: **ÁNO** (prijatý token sa presne zhodoval s vydaným tokenom)
  - `auth_role`: **`reporter`**
  - `job_id`: zhodné s očakávaným syntetickým ID
  - `tool_result_sha256`: zhodné s očakávaným fixatúrnym výsledkom

### 3.2 Celkové správanie Codex CLI
- **Stav procesu:** `COMPLETED` (exit code: 0, timed_out: false).
- **Zistené roly na serveri:** `['reporter']`.
- **Neočakávané volania nástrojov:** Žiadne (`[]`).
- **Zhoda odpovede:** Úplná zhoda (100 %) v 6 požadovaných poliach (`job_id`, `state`, `classification`, `finding_count`, `warnings`, `limitations`).

### 3.3 HTTP a regresné testy
- **HTTP kontroly sondy:** 13 / 13 PASS
- **Hub bezpečnostná suita (PR #29):** 77 / 77 reporter testov PASS, 12 / 12 ACL testov PASS
- **Cielené testy vyhodnocovacej logiky (`test_probe.py`):** **10 / 10 PASS**
  - Úspech oboch čítaní s viazaným poverením: PASS
  - Odmietnutie pri chýbajúcej väzbe na jednom čítaní: PASS
  - Odmietnutie pri prítomnosti role reporter iba na chybovej udalosti: PASS
  - Zachovanie predvoleného správania pre rolu `analyst`: PASS
  - Odmietnutie pri neočakávaných volaniach: PASS
  - In-memory porovnanie v `Recorder` a nulový únik tajomstiev do logov/udalostí: PASS

---

## 4. Bezpečnostné mantinely a stav backlogu
- **Nulový únik tajomstiev:** Tokeny, podpisové kľúče ani ich odtlačky neboli zapísané do diskových logov, `traffic.jsonl` ani `report.json`.
- **Produkčné nasadenie:** Nevykonané (`production_deployment: NOT_PERFORMED`).
- **Generovanie reportov:** Ponechané zakázané (`report_generation_allowed: false`).
- **Zostávajúce podmienky:** Pre reálne uzatvorenie celej položky FX-008 a prechod do FX-009 naďalej zostáva vyriešiť živú správu a revokáciu poverení, perzistentnú obnovu ACL po reštarte a poskytovateľskú zmluvu dátového toku FX-009.
