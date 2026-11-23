# FX-008 — syntetické overenie autorizácie Hubu

Tento probe vykonáva reálnu HTTP autentifikáciu a ACL pripnutého Hubu cez `httpx.ASGITransport` v jednom procese. **Úspešná charakterizácia aktuálneho správania neznamená splnené oprávnenia iba na reportovanie.** Súhrn uvádza obidva výsledky samostatne.

## Reprodukcia

Predpoklady: čistý checkout `forenzx-mcp-hub` na commite `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`, izolovaný Python s upstream závislosťami a `httpx`. Aktuálne použité verzie sú v [výsledku](../../docs/verification/FX008_AUTHORIZATION_RESULTS.json); prostredie zodpovedá existujúcemu `scripts/requirements-fx007.txt`.

Z koreňa tohto repozitára:

```bash
/path/to/venv/bin/python -B integration/fx008/run_authorization_probe.py \
  --upstream /path/to/forenzx-mcp-hub \
  --output /path/to/new-FX008_AUTHORIZATION_RESULTS.json
```

Výstupný JSON musí byť nový. Existujúci dôkaz skript neprepíše. Návratový kód `0` znamená, že pozorovania zodpovedali explicitným očakávaniam aktuálneho zdroja. Pre produkt sa samostatne číta `summary.reporting_policy_gate`; doložený beh má **`FAIL`**. Návratový kód nie je release gate.

## Izolácia a hranica testu

- Čistota a presný commit upstreamu sa kontrolujú pred behom aj po ňom; report obsahuje SHA-256 kontrolovaných zdrojov a samotného probe.
- Produkčná konfigurácia, nová dočasná SQLite databáza, úložiská, prázdny adresár packov a čerstvé náhodné kľúče sa nastavia **pred importom Hubu**. Aktuálny adresár je nový dočasný adresár bez `.env`. Aj novovytvorený podpisový kľúč sa nachádza v dočasnom úložisku.
- `ASGITransport` neotvára sieťový server a nespúšťa lifespan. Automatické kontroly vzdialených serverov sú vypnuté. Nepoužije sa AI klient, model, Docker, download ani forenzný engine.
- Dočasné záznamy sa vytvárajú cez skutočný job manager. Ich výsledky vychádzajú výhradne z `product/fixtures/completed-hit.json`, s upravenými syntetickými identitami a zodpovedajúcim `execution_record`.
- Auth a ACL zostávajú pôvodné, bez dependency override. Registračné metódy ACL iba pripravia testovacie prípady. Identifikátor scenára `case_grant` znamená **prístup cez zhodu organizácie registrovaného prípadu**, nie explicitný grant konkrétnemu používateľovi. Scenár zámerne odlišuje organizáciu case od organizácie jobu, aby izoloval OR vetvu politiky. Report to identifikuje v `principal_definitions.case_grant`.
- `reporter_label` je iba podpísané testovacie JWT tvrdenie `roles=["reporter"]`. Hub takú rolu neimplementuje; skúška nepredstiera existujúci platný reportovací scope. Rovnaké rozlíšenie je priamo v `principal_definitions.reporter_label` výsledku.
- Pri `cancel` sa vykoná skutočná zmena `QUEUED → CANCELLED` na syntetickom jobe bez worker tasku. Pri odmietnutí sa porovná snímka tabuliek jobs/results a stav jobu.
- Pri `start` jediný sentinel nahradí `pack_registry.get_pack`. Tento bod je v pripnutom zdroji **po skutočnej kontrole case ACL, pred kontrolou packu, vytvorením jobu a background taskom**. Jeho dosiahnutie dokazuje prechod cez autorizáciu, nie úspešné spustenie analýzy.
- Report neukladá autorizáciu, tokeny, súkromné kľúče ani surové logy. Dočasná databáza, kľúče a adresáre sa po behu odstránia.

Žiadny admin kľúč sa neposiela v požiadavke; dočasný admin kľúč sa generuje iba preto, že ho vyžaduje produkčná konfigurácia Hubu.

## Čo vyhodnotenie znamená

| Pole | Význam |
| --- | --- |
| `baseline_match` | Očakávanie odvodené z konkrétneho aktuálneho zdroja súhlasilo s behom. |
| `reporting_policy_status: FAIL` | Existujúce poverenie dovolilo úkon, ktorý budúci reportovací tok musí zakázať. Neznamená to, že Hub deklaruje implementovaný reporter scope. |
| `REVIEW_REQUIRED` | Organizácia, vlastník alebo prístup cez case otvorili čítanie; presná užšia produktová politika ešte potrebuje kontrakt. |
| `NOT_TESTED` pri discovery | Viditeľnosť write nástroja nie je sama dôkaz možnosti ho spustiť ani technického zákazu. |
| `report_generation_allowed: false` | Tento audit nepovoľuje produkčné generovanie prehľadov. |

Úplný rozbor, zistenia a ďalšie akceptačné kritériá sú v [review FX-008](../../docs/reviews/FX008_AUTHORIZATION_REVIEW.md).

## Overenie z 22. novembra 2026

[Aktuálne výsledky, testované revízie a otvorené podmienky](../../docs/reviews/FX_AUDIT_2026-11-22.md).
