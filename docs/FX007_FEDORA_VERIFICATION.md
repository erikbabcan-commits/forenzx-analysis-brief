# Overenie FX-007 na OS Fedora — 22. 11. 2026

Stručný záznam o úspešnom vykonaní reálneho integračného behu FX-007 na lokálnej pracovnej stanici s OS Fedora.

## Identifikátory a parametre behu

| Parameter | Hodnota |
| :--- | :--- |
| **ID behu (Run ID)** | `20261122T010902Z-dee2c7c4` |
| **Dátum a čas (UTC)** | Začiatok: `2026-11-22T01:09:02.865286+00:00`<br/>Koniec: `2026-11-22T01:09:21.545706+00:00` |
| **Testovaný commit dashboardu** | `fb6b03f57297358381bf7b91ee7c811fc08146c6` (`main`) |
| **Testovaný upstream MCP commit** | `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f` (`erikbabcan-commits/forenzx-mcp-hub`) |
| **Klient AI** | `codex-cli 0.170.0` (prihlásený cez ChatGPT účet, bežiaci na Fedora Linux x86_64) |
| **Runtime prostredie** | Python `3.15.2`, Node.js `v22.23.1`, npm `10.9.8` |
| **Cesta k pôvodnému reportu** | `.fx007-runtime/runs/20261122T010902Z-dee2c7c4/report.json` |
| **SHA-256 pôvodného reportu** | `f0fb9cd12b53138ac21454067241da358bda47ea7b21c0dd924fecd5d43c4c4c` |

## Namerané výsledky kontrol

| Metrika / Kontrola | Výsledok | Poznámka |
| :--- | :--- | :--- |
| **Návratový kód (exit code)** | `0` | Celý integračný wrapper prebehol bez chýb |
| **HTTP kontroly servera** | **13/13 PASS** | Všetky negatívne aj pozitívne bezpečnostné a funkčné kontroly prešli |
| **`http_acceptance`** | `true` | ForenZX HTTP endpoint splnil akceptačné testy |
| **`requested_acceptance`** | `true` | Vyžiadaný rozsah `--with-codex --with-legacy-sdk` splnený |

## Spojenie cez AI klienta (Codex CLI) — Osobitné vyhodnotenie

* **Status:** `COMPLETED` (`exit_code: 0`, `timed_out: false`, `accepted: true`)
* **Spôsob overenia:** Codex CLI bol spustený v neinteraktívnom režime s dočasnou konfiguráciou (`--ephemeral`, `--ignore-user-config`, `sandbox: read-only`), povolenými nástrojmi `forenzx_analysis_status` a `forenzx_analysis_results` a autorizáciou cez premennú prostredia `FX007_SYNTHETIC_BEARER`.
* **Pozorovanie servera:** Server zaznamenal úspešné volania oboch povolených MCP nástrojov zo strany Codexu bez neznámych požiadaviek.
* **Zhoda výsledku:** `final_exact_match: true` — Codex načítal syntetickú úlohu `d3c5ef12-81eb-467f-b304-e278a6d57346` s presnou zhodou stavu (`COMPLETED`), klasifikácie (`HIT`), varovaní a obmedzení.

## Kompatibilita `mcp-python 1.29.0` (Legacy SDK) — Osobitné vyhodnotenie

* **Status:** `INCOMPATIBLE_OR_FAILED`
* **Klient:** `mcp-python 1.29.0`
* **Typ chyby:** `ExceptionGroup`
* **Presná chyba:** `RuntimeError: Unsupported protocol version from the server: 2026-07-28`
* **Pozorovanie:** Klient mcp-python 1.29.0 odmietol verziu protokolu 2026-07-28 oznámenú serverom.

## Stav backlogu

Stav položiek backlogu (napr. FX-007, FX-008, FX-009) sa v tomto commite nemení a zostáva na samostatné posúdenie podľa akceptačných kritérií a formálnych brán kvality (`docs/QUALITY_GATES.md`).
