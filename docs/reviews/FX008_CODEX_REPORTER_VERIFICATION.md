# FX-008: Overenie reálneho klienta Codex CLI s rolou reporter

**Dátum overenia:** 2026-11-22T02:29:20Z  
**Prostredie:** Fedora Linux (lokálne testovacie prostredie)  
**Klient:** `codex-cli 0.170.0` (prihlásený účet ChatGPT)  
**Release Board commit:** `7fa5ea573541d2e44b527b2662d1de9daf0bc4f9` (vetva `fix/fx008-reporter-evidence`)  
**ForenZX MCP Hub commit:** `3b4effdb08cda68f733c56d995ccb54380729e8b` ([Hub PR #29](https://github.com/erikbabcan-commits/forenzx-mcp-hub/pull/29))  
**ID behu:** `20261122T022905Z-d145bb21`  
**Report behu:** `/home/vorkei/Projekty/forenzx-analysis-brief-fedora/.fx008-runtime/runs/20261122T022905Z-d145bb21/report.json`  
**SHA-256 reportu:** `6190472ce537830d15b822f258889e44ec063d35cd390609cba67f971815f062`  

---

## 1. Zhrnutie a verdikt

**Verdikt:** **PASS**  
*Skutočný klient codex-cli 0.170.0 s oprávnením reporter úspešne cez MCP prečítal stav aj výsledok syntetickej analýzy zo servera a vrátil presnú 6-poľovú odpoveď bez neočakávaných volaní.*

Všetky HTTP kontroly integrity, fail-closed ACL aj oba čítacie nástroje cez prihlásený Codex CLI prebehli bez zlyhania na syntetickej úlohe.

---

## 2. Namerané výsledky

### 2.1 HTTP kontroly sondy (13 / 13 PASS)
- `missing_auth_rejected`: PASS (HTTP 401)
- `invalid_jwt_rejected`: PASS (HTTP 401)
- `expired_jwt_rejected`: PASS (HTTP 401)
- `dev_bypass_rejected_in_production`: PASS (HTTP 401)
- `api_key_discovery`: PASS (HTTP 200)
- `jwt_tool_discovery`: PASS (HTTP 200)
- `unsupported_protocol_rejected`: PASS (HTTP 400)
- `completed_status`: PASS (HTTP 200, stav COMPLETED)
- `exact_result_roundtrip`: PASS (HTTP 200, presná zhoda výsledku)
- `warnings_and_limitations_preserved`: PASS
- `cross_organization_denied`: PASS (RPC kód -32603)
- `missing_job_rejected`: PASS (RPC kód -32602)
- `retrieved_input_passes_structural_validator`: PASS (validačný skript uspel)

### 2.2 Hub bezpečnostná a regresná suita
- `tests/security/test_reporter.py` (vrátane `scripts/check_reporter_authorization.py`): **77 / 77 PASS**
- `tests/security/test_acl.py`: **12 / 12 PASS**

### 2.3 Správanie Codex CLI
- **Stav procesu:** `COMPLETED` (návratový kód 0, timeout: false).
- **Použité poverenie:** Syntetický JWT s deklarovanou rolou `roles: ["reporter"]`, príslušným `organization`, `report_case_ids` a `report_job_ids`.
- **Rola pozorovaná serverom:** `reporter` (potvrdené v prevádzkovom logu ASGI).
- **Vykonané MCP volania:**
  - `forenzx_analysis_status` pre syntetické `job_id` (úspech, HTTP 200).
  - `forenzx_analysis_results` pre rovnaké `job_id` (úspech, HTTP 200).
- **Neočakávané volania nástrojov:** Žiadne (`[]`).
- **Zhoda odpovede:** Úplná zhoda (100 %) v 6 požadovaných poliach: `job_id`, `state`, `classification`, `finding_count`, `warnings` a `limitations`.

---

## 3. Bezpečnostné mantinely a stav backlogu

1. **Syntetické testovacie dáta:** Skúška prebehla výhradne na syntetických dátach v izolovanom procese loopback servera (127.0.0.1) s dočasnou SQLite databázou. Žiadne skutočné dáta ani produkčný systém neboli dotknuté.
2. **Zachovanie predvoleného správania:** Historické správanie sondy FX-007 s predvolenou rolou `analyst` zostalo zachované; voľba `--codex-role reporter` rozširuje sondu len na vyžiadanie.
3. **Poverenia a tajomstvá:** Tokeny a kľúče boli generované dynamicky, neboli vypísané do protokolu a sú v záznamoch redigované.
4. **Stav backlogu:** `report_generation_allowed` zostáva `false`. Úspešný integračný test je technickým dôkazom fungovania opravy Hubu v PR #29 a schopnosti klienta Codex fungovať pod rolou `reporter`, no pre uzavretie celej položky FX-008 a prechod do FX-009 zostávajú otvorené systémové podmienky:
   - Riešenie perzistencie a dynamického prideľovania/revokácie živých reporter oprávnení (live credential provisioning and revocation).
   - Perzistentná obnova case ACL po reštarte servera.
   - Posúdenie zmluvy poskytovateľa dátového toku a pre-model validácie (FX-009).
