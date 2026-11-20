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
