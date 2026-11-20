# Záznam overenia dashboardu v0.1

Dátum: 20. 11. 2026 (Europe/Bratislava).

## Rozsah

Tento záznam hodnotí pracovný dashboard a jeho ukladanie. Nie je validáciou budúceho ForenZX skillu, upstream forenzného enginu ani schválením Agensi.

Zdroj aplikácie nasadenej cez Sites: commit `ff8dda95fb47173b0adba355ce687a108f6388cb`. Tento GitHub import zachováva runtime zdroje; aktualizuje README o vytvorený repozitár a pridáva tento záznam.

## Automatické kontroly

- `npm test`: kontrola 18 úloh, 17 brán pred podaním a 23 zdrojov; následne **13/13 testov** správy stavu.
- Testy zahŕňajú skutočné vykonanie SQL v SQLite: zastaraná revízia, súbežné zmeny závislostí v oboch smeroch, izolácia používateľov, podmienená história a rollback pri chybe zápisu histórie.
- Kontrolované sú aj neplatné vstupy, podmienky dokončenia, pôvod požiadavky a limit tela.
- `npm run typecheck`: úspech bez chýb.
- ESLint API rout, stavového modulu, databázovej schémy a ich testu: úspech bez chýb.
- Produkčný build Vinext: úspech.

SQLite test sám nepreukazuje správanie vzdialenej služby; preto nasleduje kontrola nasadenia.

## Súkromné nasadenie a kontrola v prehliadači

- Sites potvrdil úspešné nasadenie a prístup iba vlastníka.
- URL: https://forenzx-analysis-brief-vorkei.erikbabcan.chatgpt.site/
- Overené načítanie 18 úloh, stav 3 hotové, 17 povinných brán, 23 zdrojových záznamov v dátach.
- Na už doloženej prípravnej úlohe FX-004 bol dočasne odškrtnutý bod. Pri stave „hotovo“ bolo uloženie nedostupné.
- Úloha bola dočasne uložená ako rozpracovaná s testovacou poznámkou.
- Po úplnom obnovení stránky sa zobrazil uložený checkbox, poznámka, stav a revízia 1.
- Pôvodné tri splnené kritériá, dôkaz a stav „hotovo“ boli obnovené. Dashboard opäť zobrazil 3/18 hotových úloh.
- Vyhľadanie `FX-012` správne zobrazilo jednu zodpovedajúcu úlohu.
- Export bol spustený cez rozhranie; obsah stiahnutého súboru nebol samostatne porovnávaný.
- Vizuálne skontrolované desktopové rozhranie. Samostatný test mobilného zariadenia zatiaľ nebol vykonaný.
- Lokálny náhľad bez identity správne zobrazil požiadavku na prihlásenie. Produkčná autentifikácia nebola vypnutá.

## Úložisko a zostávajúce hranice

Zmeny stavov patria do D1 a exportu. Nevytvárajú automatické Git commity. História je aplikačne iba dopĺňaná; netvrdíme nezmeniteľný WORM audit.

Dokončenie vyžaduje kritériá a textový dôkaz, ale aplikácia sama nepreveruje pravdivosť ľubovoľnej poznámky používateľa. Nové významy kritérií preto potrebujú nové ID úlohy alebo vedomé nové posúdenie.

ForenZX klient, referenčná sada, vernosť AI prehľadu, nezávislé odborné review a licencie zostávajú otvorenými úlohami produktového backlogu.

---

## Doplnenie 21. 11. 2026 — zmena katalógu a prvá kontrola vstupu

Tento dodatok nemení historický výsledok z 20. 11. 2026. Rozsah je rozšírený dashboard a samostatný lokálny validátor; celý MCP ani modelový workflow sa týmto neoveruje.

### Vykonané automatické kontroly

- `npm test`: **22/22 testov** správy stavu; katalóg **18 úloh, 17 brán, 30 zdrojov**.
- Nové SQL testy vykonávajú migráciu aj produkčné SQL v SQLite. Zahŕňajú prevod pôvodných stavov podľa nemennej definície, zachovanie dôkazov, neprenášanie odškrtnutia na nové kritériá, opätovné otvorenie hotových nadväzujúcich úloh a ochranu súbežnej novšej úpravy.
- Starý formulár musí pri zmene definície dostať konflikt; samotná aktuálna revízia nestačí.
- `npm run test:product`: **34/34 testov** lokálneho validátora vrátane samostatného CLI procesu, identity, chýb JSON, hraničných veľkostí, viditeľných obmedzení a nemennosti vstupu.
- `npm run typecheck`: úspech bez chýb.
- `git diff --check`: úspech bez chýb.

### Rozsah produktu

FX-005 zostáva rozpracovaná. Kontrola pripnutého profilu sa vzťahuje iba na dodaný extrahovaný JSON. Výstup vždy ponechá `report_generation_allowed: false`; úplnosť transportu, kontext modelu, autenticita a podpisy zostávajú `NOT_VERIFIED`. Technické limity parsera nie sú zmeranou kapacitou AI klienta. Podrobnosti a reprodukovateľné príkazy sú v [product/README.md](../product/README.md).

### Zachovanie existujúcej databázy

Migrácia `0001_thick_human_fly.sql` iba pridáva tri stĺpce. Pôvodné indexy checkboxov interpretuje nemenný snapshot v `lib/legacy-task-definitions.ts`. Zosúladenie katalógu zachová poznámky a pôvodnú históriu; zmenené definície dostanú záznam dôvodu. Nezmenené úlohy FX-001, FX-002 a FX-004 sa nemajú znovu otvárať.

Pred nasadením bol cez produkčné rozhranie stiahnutý a načítaný platný JSON export: 18 úloh a 2 historické udalosti. Následné porovnanie po nasadení sa zaznamená oddelene; samotný lokálny test nie je dôkazom úspešnej vzdialenej migrácie.

### Produkčné overenie po nasadení, 21. 11. 2026

- Zdroj nasadenej aplikácie: Sites commit `ed7c2cf92c3841b0b60c8f2d002c086cbe504714`. GitHub obsahuje rovnakú implementáciu a navyše tento následný záznam kontroly.
- Produkčný build prešiel. Sites vrátil úspešné súkromné nasadenie `appgdep_6b00d90f61d08191aeb6be6061e5c45f`.
- Živý dashboard po obnovení načítal 18 úloh a nové kritériá; počet hotových prípravných úloh zostal 3/18 a brán 3/17.
- Export stiahnutý po migrácii bol programovo porovnaný s exportom pred migráciou. Všetkých 18 pôvodných stavov, dôkazových poznámok a zoznamov checkboxov sa zhodovalo. Všetky pôvodné polia oboch historických udalostí zostali zachované.
- Revízie a časové značky nezmenených hotových úloh FX-001, FX-002 a FX-004 zostali bez zmeny.
- História po migrácii mala 11 udalostí: pôvodné 2 a 9 nových udalostí `catalog_changed`. Nové kritériá zostali neoznačené.
- Cez rozhranie bol do FX-005 zapísaný doložený lokálny pokrok: stav „Rozpracované“, 5/8 kritérií, poznámka s výsledkom 34 testov a zostávajúcimi hranicami.
- Po úplnom obnovení stránky sa zachovali stav, presné checkboxy `[0, 1, 2, 3, 7]`, poznámka a revízia 2. Ostatných 17 úloh sa nezmenilo.
- Posledný export má 18 úloh, 30 zdrojov a 12 udalostí. Všetkých 11 predchádzajúcich udalostí je zachovaných; pribudol jediný `user_update` pre FX-005.

Browser QA bolo zamerané na zmenené uloženie, migráciu a export. Tento krok nezavádza tvrdenie o vykonaní mobilného alebo celého MCP/modelového testu.

### Následná úprava poradia integračných krokov

Po rozšírení FX-005 by jej dokončenie implicitne vyžadovalo FX-007, kým FX-007 čakalo cez FX-006 späť na FX-005. Opravené závislosti: FX-006 vychádza z FX-001/002; dokončenie FX-005 závisí aj od FX-007. Kritériá ani doložený čiastkový pokrok sa nezmenili. Spresnenie syntetických scenárov a hraníc jednotlivých fáz je v dodatku k review.

Katalóg po úprave prešiel kontrolou referencií a acyklickosti: 18 úloh, 17 brán, 30 zdrojov. Produkčný build prešiel. Sites potvrdil úspešné súkromné nasadenie zdroja `56a32b14564676884959c0fc07e70a2c2813b3d2`, deployment `appgdep_6b00d9f683a08191b241ba73ab461f0b`. Táto následná zmena nemení implementáciu uloženia; browserové porovnanie exportov vyššie patrí k predchádzajúcej revízii katalógu a netvrdí sa ako druhé nové meranie.

## FX-006 — vykonanie bodu 4.1

V nadväzujúcom kroku 21. 11. 2026 vznikla referenčná sada a runner: **50/50 scenárov PASS**, **46/46 produktových testov PASS** (34 pôvodných + 12 nových). Katalóg očakávaní bol zafixovaný pred prvým vyhodnotením a výsledky si nevyžiadali jeho zmenu. Podrobný rozsah, mapovanie všetkých šiestich kritérií, príkazy a neotestované oblasti uvádza [záznam FX-006](FX006_REFERENCE_VERIFICATION.md).

Pred aktualizáciou pracovného stavu bol stiahnutý export s 18 úlohami a 14 historickými udalosťami. FX-006 mala stav `todo`, prázdne checkboxy a revíziu 2. Dokončenie tejto úlohy znamená pripravenú syntetickú sadu, nie úspech živého klienta alebo modelu.

Po nasadení zdroja `20a9ff5c9bb4bbc118dd6c20a671c33ce316216e` a uložení cez rozhranie bolo úplným obnovením a porovnaním exportu potvrdené: FX-006 `done`, 6/6 kritérií, revízia 3; ostatných 17 úloh nezmenených; všetkých 14 pôvodných udalostí zachovaných a jediná nová aktualizácia. Dashboard má 4/18 hotových úloh a ponúka FX-007 ako ďalší krok. Podrobnosti sú v zázname FX-006.
