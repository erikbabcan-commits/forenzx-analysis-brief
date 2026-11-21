# FX-008 — serverom vynútené oprávnenie iba na reportovanie

Pracuj v erikbabcan-commits/forenzx-mcp-hub a koordinačnom erikbabcan-commits/forenzx-analysis-brief. Najprv over pokyny AGENTS.md, vetvy, commity a pracovné zmeny. Zachovaj historické reporty FX-007 a 53-kontrolový baseline FX-008.

Implementuj samostatné neadmin reportovacie JWT: rola reporter, konkrétna organizácia a explicitné report_case_ids aj report_job_ids. Čítanie vyžaduje oba granty, uloženú väzbu job/case a zhodu organizácie jobu aj registrovaného prípadu. Samotná zhoda používateľa, organizácie alebo dostupnosť iného case nesmie stačiť.

Po normalizácii aliasov v spoločnom dispatcheri povoľ reporterovi iba status/results. Start/cancel odmietni pred parametrami, pack lookupom, vytvorením jobu, workerom, downloadom a mutáciou. Over canonical aj existujúce aliasy na /mcp a /mcp/jsonrpc; zmiešané reporter/admin roly nesmú obísť obmedzenie. Prázdne roly zamietni. SSE musí použiť rovnakú hranicu job/case. Discovery nie je náhrada autorizácie.

Zachovaj explicitné odlíšenie analytických API kľúčov: nejde o reportovacie poverenia ani tenant izoláciu. Lokálne stdio zostáva administratívne rozhranie pod OS oprávneniami, nie podporovaný reportovací transport. Popíš provisionovanie, krátku expiráciu JWT, chýbajúcu živú revokáciu a fail-closed obnovu case ACL po reštarte.

V syntetických testoch používaj novú dočasnú DB a úložiská pred importom Hubu. Over pozitívne čítania a presnú zhodu výsledku vrátane varovaní, záporné granty a organizácie, nemennosť DB aj taskov pri zamietnutí, chybný typ JWT grantov, SSE a aliasy. Nespúšťaj reálne prípady, engine ani model. Zopakuj FX-007 HTTP proti presnému opravenému commitu; novú akceptáciu Codex klienta tvrď iba po skutočnom úspešnom behu.

Odovzdaj draft PR, presné výsledky a reprodukčné príkazy. Produkciu nenasadzuj, FX-009 ani generovanie reálnych prehľadov tým neuzatváraj.

## Vykonanie 21. 11. 2026

- Hub draft PR: https://github.com/erikbabcan-commits/forenzx-mcp-hub/pull/29
- Zverejnený commit: 3b4effdb08cda68f733c56d995ccb54380729e8b.
- Úplné Hub testy: 297 PASS; z toho 77 nových reporter testov.
- FX-007 HTTP na zverejnenom commite: 13/13 PASS.
- Codex CLI 0.172.0-alpha.2: pokus zlyhal pri inicializácii app-servera s Read-only file system, pred MCP nástrojmi. Historické používateľské úspechy 0.170.0 sa tým nemenia.
- Nová politika je lokálne overená a čaká na review/merge; produkcia a FX-009 zostávajú neoverené.

Reprodukcia v Hube po checkoute presného commitu:

```bash
python scripts/check_reporter_authorization.py
```

Reprodukcia v koordinačnom repozitári s touto úpravou probe (závislosti musia byť nainštalované):

```bash
python integration/fx007/run_probe.py \
  --upstream ../forenzx-mcp-hub \
  --upstream-commit 3b4effdb08cda68f733c56d995ccb54380729e8b \
  --output /tmp/fx007-reporter-new-run
```

Pre opakovanie klienta v prostredí s funkčným Codex CLI pridaj `--with-codex` a použi nový výstupný adresár. FX-007 ostáva skúškou historického analytického klienta; reportovacie JWT pokrýva samostatná 77-testová sada. Nie je to dôkaz nového reportovacieho klienta od konca po koniec.
