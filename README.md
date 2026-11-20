# ForenZX · Release Board

[Otvoriť súkromný dashboard](https://forenzx-analysis-brief-vorkei.erikbabcan.chatgpt.site/) · [Repozitár](https://github.com/erikbabcan-commits/forenzx-analysis-brief)

Súkromný pracovný dashboard pre prípravu **ForenZX Analysis Brief**. Obsahuje 18 úloh, 17 brán pred podaním, závislosti, akceptačné kritériá, dôkazy dokončenia a odborné podklady. Dashboard nie je samotný forenzný skill.

## Priebežný stav k 21. 11. 2026

- Overený upstream commit: `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`.
- Pripravený návrh rozsahu a metodiky. Tri prípravné úlohy sú hotové.
- FX-005 je rozpracovaná: samostatný lokálny validátor a dva syntetické príklady, 34/34 testov. Úspech kontroly vstupu nepovoľuje generovanie prehľadu.
- Reálny MCP klient, celkové produktové testy, nezávislé odborné review a licencia zostávajú otvorené.
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

Node 22.13+ a závislosti z lockfile. Inštalácia: `npm ci`. Typová kontrola: `npm run typecheck`. Overenie backlogu a stavu: `npm test`. Schému meniť cez `db/schema.ts` a `npm run db:generate`; vygenerované migrácie sa verziujú a spätne neupravujú.

Lokálny validátor produktového vstupu je samostatný Python 3.10+ skript bez externých závislostí. Jeho testy sa spúšťajú cez `npm run test:product` alebo `python3 -m unittest discover -s product/tests -v`. Úspech tejto sady je dôkazom lokálnych kontrol na syntetických vstupoch, nie úspešného MCP spojenia, bezpečného modelového kontextu ani hotového skillu.

Používajte dodané Sites skripty na build a nasadenie. Produkčné tajomstvá nepatria do zdrojov. Lokálny náhľad bez autentifikačných hlavičiek môže vrátiť 401; nejde o dôvod vypnúť kontrolu identity v produkcii.

## Licencie a publikácia

Tento pracovný repozitár nevyriešil licenciu ForenZX servera ani distribučné podmienky skillu. Pred plateným vydaním musí vlastník rozhodnúť FX-003. Založenie súkromného dashboardu nepublikuje produkt na Agensi a nemení licenciu upstreamu.

GitHub repozitár: `erikbabcan-commits/forenzx-analysis-brief`, **private**. Vytvorený a overený 20. 11. 2026. Živý dashboard je na odkaze vyššie. [Záznam overenia dashboardu](docs/VERIFICATION.md).


## Zmeny katalógu

Zmena významu akceptačných kritérií nesmie zdediť starý stav „hotovo“. Definície úloh sú verziované. Zhodné kritériá zachovajú priradené checkboxy, nové kritériá zostanú nesplnené a dôkazy sa zachovajú. Zmenená dokončená úloha a jej dokončené závislé úlohy sa znovu otvoria na posúdenie so záznamom histórie. Nové samostatné úlohy dostanú nové ID. Klient musí pri ukladaní poslať aj aktuálny identifikátor definície, aby stará otvorená stránka nepotvrdila nové kritériá.
