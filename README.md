# ForenZX · Release Board

[Otvoriť súkromný dashboard](https://forenzx-analysis-brief-vorkei.erikbabcan.chatgpt.site/) · [Repozitár](https://github.com/erikbabcan-commits/forenzx-analysis-brief)

Súkromný pracovný dashboard pre prípravu **ForenZX Analysis Brief**. Obsahuje 18 úloh, 17 brán pred podaním, závislosti, akceptačné kritériá, dôkazy dokončenia a odborné podklady. Dashboard nie je samotný forenzný skill.

## Priebežný stav k 21. 11. 2026

- Overený upstream commit: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`.
- Hotové sú FX-001, FX-002, FX-004 a FX-006: zdrojový základ, rozsah, metodika a syntetická referenčná sada.
- FX-005 je rozpracovaná: samostatný lokálny validátor a dva syntetické príklady, 34/34 testov. Úspech kontroly vstupu nepovoľuje generovanie prehľadu.
- FX-007 má vykonaný živý HTTP test: 13/13 kontrol PASS. Codex CLI 0.172.0-alpha.2 zablokoval štart vlastného úložiska pred MCP komunikáciou; úloha zostáva blokovaná s 2/4 doloženými kritériami. [Podrobný záznam](docs/FX007_LIVE_VERIFICATION.md).
- FX-006 je hotová ako syntetická referenčná sada: 50/50 scenárov a 46/46 produktových testov; [záznam overenia](docs/FX006_REFERENCE_VERIFICATION.md).
- Koordinačný cyklus FX-008/009: **53/53 pozorovaní autorizácie zodpovedá pripnutému Hubu; požiadavka iba na reportovanie má FAIL**. FX-008 je v živom dashboarde blokovaná 3/4, FX-009 rozpracovaná 0/8; [záznam uloženia](docs/verification/COORDINATION_DELIVERY.json). Rovnaké poverenie umožňuje čítanie aj zrušenie úlohy. [Review oprávnení](docs/reviews/FX008_AUTHORIZATION_REVIEW.md) a [reprodukcia](integration/fx008/README.md) odlišujú úspech testu od nesplnenej produktovej brány.
- [Mapa dát FX-009](docs/reviews/FX009_DATA_FLOW_REVIEW.md) dokladá chýbajúcu kontrolu pred vydaním výsledkov klientovi a neoverený modelový profil. [Nezávislý checklist FX-010](docs/reviews/FX010_INTEGRATION_PRECHECK.md) pripravuje review Codexovho rendereru; jeho odovzdanie pri kontrole nebolo na GitHube dostupné. Reálne vstupy zostávajú nepovolené.
- Ďalší krok: zopakovať pripravený test v funkčnej lokálnej inštalácii AI klienta a samostatne opraviť zistené moderné discovery/verziovanie upstreamu. Potom uzavrieť zostávajúce tri podmienky FX-005.
- Navrhovaná cena skillu: 19 USD jednorazovo.
- Z poskytnutej komunikácie nevyplýva externý termín odovzdania. Agensi uvádza odhad kontroly až od podania.

## Používanie

Vyhľadajte alebo filtrujte úlohu, otvorte detail, označte splnené kritériá, doplňte dôkaz a uložte stav. Dokončenie vyžaduje všetky kritériá, neprázdny dôkaz a hotové závislosti. Pri súbežnej úprave aplikácia odmietne prepísať novšiu revíziu.

Dokončenie je záznam pracovného rozhodnutia; aplikácia nevie overiť pravdivosť ľubovoľnej poznámky. Zelené percento nenahrádza odborné review.

Zmeny stavov sa ukladajú v D1 pre prihláseného vlastníka, vrátane histórie. Nie sú automaticky Git commitmi. Verziovaný katalóg úloh a dokumentácia žijú v zdrojovom repozitári. **Export JSON** obsahuje aktuálny snapshot a históriu na zálohu; import nie je implementovaný.

Do poznámok nevkladajte poverenia ani reálny dôkazový materiál. Tento board spravuje prácu na produkte, nie vyšetrovacie spisy.

## Dokumentácia

- [Doplnenia po kontrole šiestich pripomienok](docs/REVIEW_ADDENDUM_2026-11-21.md)
- [Prvá implementácia kontroly vstupu FX-005](product/README.md)
- [Syntetická referenčná sada FX-006](product/reference/README.md)
- [Vykonaný prompt pre FX-006](docs/prompts/FX006_REFERENCE_SUITE_PROMPT.md)
- [Vykonaný prompt pre bod 4.2 / FX-007](docs/prompts/FX007_LIVE_CLIENT_PROMPT.md)
- [Výsledky živého testu FX-007](docs/FX007_LIVE_VERIFICATION.md)
- [Oprávnenia FX-008: zdrojový a syntetický runtime review](docs/reviews/FX008_AUTHORIZATION_REVIEW.md)
- [Tok údajov a ukladanie FX-009](docs/reviews/FX009_DATA_FLOW_REVIEW.md)
- [FX-010: integračný checklist a návrh brány pre reálne vstupy](docs/reviews/FX010_INTEGRATION_PRECHECK.md)
- [Lokálne klonovanie, spustenie a testy](docs/LOCAL_SETUP.md)
- [Produktový kontrakt](docs/PRODUCT_CONTRACT.md)
- [Metodika a pracovný slovník](docs/METHODOLOGY.md)
- [Brány kvality](docs/QUALITY_GATES.md)
- [Register odborných zdrojov](docs/SOURCES.md)
- [Backlog](data/backlog.json)
- [Technické a obchodné zdroje](data/engineering-sources.json)

## Architektúra

Vinext / React, serverové API a Cloudflare D1. Prístup obmedzuje súkromné Sites zdieľanie; API navyše vyžaduje identitu poskytnutú autentifikačnou vrstvou. Kľúč používateľa izoluje stav. Nevytvára sa vlastná databáza hesiel.

`GET /api/tasks` vracia katalóg a stav, `PATCH /api/tasks/:id` ukladá revíziu, `GET /api/export` exportuje snapshot a históriu. Mutácie kontrolujú pôvod požiadavky.

## Vývoj

### Naklonovať, overiť a spustiť lokálne

Predpoklady: Git, Node **22.13+**, npm a Python **3.10+**. Použite Bash na Linuxe, macOS alebo vo WSL; prístup k súkromnému repozitáru musí mať váš Git alebo GitHub CLI.

```bash
gh repo clone erikbabcan-commits/forenzx-analysis-brief
cd forenzx-analysis-brief
bash scripts/local-bootstrap.sh
```

Bez GitHub CLI použite `git clone https://github.com/erikbabcan-commits/forenzx-analysis-brief.git` s vlastným Git credential helperom. Kompletný opatrný obal na klonovanie do nového adresára je [scripts/clone-and-test.sh](scripts/clone-and-test.sh).

Bootstrap nainštaluje závislosti, keď treba, spustí kontroly, vytvorí build, overí lokálne uloženie a export a otvorí lokálnu službu na **http://127.0.0.1:5173**. URL vypíše v termináli; prehliadač otvorte sami. `Ctrl+C` službu ukončí. Len kontroly bez trvalo bežiaceho dashboardu: `bash scripts/local-bootstrap.sh --check-only`. Obsadený port: `bash scripts/local-bootstrap.sh --port 5174` alebo `--port 0` pre automatický výber.

Lokálny režim používa označený syntetický účet a samostatnú lokálnu D1. **Aktuálne zmeny zo živého dashboardu sa doň automaticky neprenesú.** Produkčné prihlásenie ani hostovanú databázu nemení. [Úplný lokálny návod](docs/LOCAL_SETUP.md).

### Samostatné kontroly

Node 22.13+ a závislosti z lockfile. Inštalácia: `npm ci`. Typová kontrola: `npm run typecheck`. Overenie backlogu a stavu: `npm test`. Schému meniť cez `db/schema.ts` a `npm run db:generate`; vygenerované migrácie sa verziujú a spätne neupravujú.

Lokálny validátor produktového vstupu je samostatný Python 3.10+ skript bez externých závislostí. Jeho testy sa spúšťajú cez `npm run test:product` alebo `python3 -m unittest discover -s product/tests -v`. Úspech tejto sady je dôkazom lokálnych kontrol na syntetických vstupoch, nie úspešného MCP spojenia, bezpečného modelového kontextu ani hotového skillu.

Autorskú referenčnú sadu spustí `npm run test:reference`. Očakávania sú verziované v `product/reference/catalog.json`; veľké hraničné vstupy sa vytvárajú deterministicky. Samostatný príkaz `python3 product/run_reference_suite.py --materialize /tmp/forenzx-fx006-fixtures --report /tmp/forenzx-fx006-results.json` zachová aj vygenerované vstupy a report. Použite nové cesty; existujúce súbory sa štandardne neprepisujú. Tento beh overuje lokálny kontrakt a explicitne ponecháva živý klient aj LLM ako neotestované.

`npm run test:local` overí lokálnu bránu; `npm run local:check` vykoná celý lokálny bootstrap vrátane HTTP/D1 smoke testu. `npm run local` spustí už vytvorený build. Priame `npm run dev` nemá lokálnu syntetickú identitu; na funkčné lokálne odškrtávanie použite dodaný launcher.

Pre nasadenie používajte dodané Sites skripty. Produkčné tajomstvá nepatria do zdrojov.

### Bod 4.2 — živý MCP test

Prompt je v [docs/prompts/FX007_LIVE_CLIENT_PROMPT.md](docs/prompts/FX007_LIVE_CLIENT_PROMPT.md). Reprodukovateľný test skutočného upstream procesu je oddelený od offline referenčnej sady:

```bash
# Vyžaduje Python 3.11+; vytvorí vlastný venv a čistý pinned checkout.
bash scripts/fx007-mcp-check.sh

# Na skutočné overenie AI klienta treba aj nainštalovaný a prihlásený Codex CLI.
bash scripts/fx007-mcp-check.sh --with-codex --with-legacy-sdk
```

Prvý príkaz overuje priamo HTTP, autentifikáciu a čítanie syntetického výsledku. Druhý navyše spustí skutočný AI klient a samostatný diagnostický test staršieho SDK. Dostupnosť klienta, modelu a siete sa nesmie zameniť za úspech. Skript generuje iba dočasné testovacie poverenia; nepotrebuje vaše produkčné kľúče. Reporty ukladá do ignorovaného adresára `.fx007-runtime/runs/`. [Integračný návod](integration/fx007/README.md).

## Licencie a publikácia

Tento pracovný repozitár nevyriešil licenciu ForenZX servera ani distribučné podmienky skillu. Pred plateným vydaním musí vlastník rozhodnúť FX-003. Založenie súkromného dashboardu nepublikuje produkt na Agensi a nemení licenciu upstreamu.

GitHub repozitár: `erikbabcan-commits/forenzx-analysis-brief`, **private**. Vytvorený a overený 20. 11. 2026. Živý dashboard je na odkaze vyššie. [Záznam overenia dashboardu](docs/VERIFICATION.md).


## Zmeny katalógu

Zmena významu akceptačných kritérií nesmie zdediť starý stav „hotovo“. Definície úloh sú verziované. Zhodné kritériá zachovajú priradené checkboxy, nové kritériá zostanú nesplnené a dôkazy sa zachovajú. Zmenená dokončená úloha a jej dokončené závislé úlohy sa znovu otvoria na posúdenie so záznamom histórie. Nové samostatné úlohy dostanú nové ID. Klient musí pri ukladaní poslať aj aktuálny identifikátor definície, aby stará otvorená stránka nepotvrdila nové kritériá.

## Overenie z 22. novembra 2026

[Aktuálne výsledky, testované revízie a otvorené podmienky](docs/reviews/FX_AUDIT_2026-11-22.md).
