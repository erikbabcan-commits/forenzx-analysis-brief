# FX-010 — nezávislé integračné podmienky pred odovzdaním rendereru

Dátum: **21. 11. 2026, Europe/Bratislava**. Vlastník: hlavný technický koordinátor.

**Verdikt tohto kroku: PASS pre prípravu review; implementácia FX-010 je NOT_TESTED.** Dokument je nezávislé zadanie akceptácie, nie schválenie rendereru, produkčného toku ani vydania. Nezavádza druhý renderer a nemení existujúce povolenia.

## 1. Z čoho vychádza kontrola

| Podklad | Overený stav pri obnove |
| --- | --- |
| Produktový repozitár | `erikbabcan-commits/forenzx-analysis-brief`, private; `main` = `fb6b03f57297358381bf7b91ee7c811fc08146c6`, tree `b7f8d40cf003f4a0b2610348e45574cde77232c9`. |
| Upstream Hub | Čistý lokálny checkout `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`. Tento pin zostáva podkladom; netvrdíme, že je najnovším upstreamom. |
| Koordinačná vetva | `chore/fx008-fx009-coordination`; oddelený checkout obnovený na presný produktový commit. |
| Codexovo odovzdanie | Pri úvodnej kontrole vzdialených vetiev bola dostupná iba `main`. Na nej chýbajú `docs/FX010_IMPLEMENTATION.md`, `docs/verification/FX010_RESULTS.json` a `docs/handoffs/FX010_CODEX_HANDOFF.md`. Lokálna práca v inom prostredí z toho nie je vylúčená. |
| Live dashboard | Načítaných 18 aktuálnych stavov a 16 udalostí pred zmenami tohto cyklu. FX-005 `in_progress` 5/8; FX-007 `blocked` 2/4; FX-008, FX-009 a FX-010 `todo`. Git seed sa nepoužil ako náhrada živého stavu. |
| Produktový základ | [Kontrakt](../PRODUCT_CONTRACT.md), [metodika](../METHODOLOGY.md), [brány](../QUALITY_GATES.md), [validátor](../../product/README.md), [FX-006](../FX006_REFERENCE_VERIFICATION.md), [FX-007](../FX007_LIVE_VERIFICATION.md). |

Historických 50 referenčných scenárov, 46 produktových testov a 13 HTTP kontrol sa v tomto dokumente nevyhlasuje za nový beh. Pri odovzdaní sa overí konkrétny commit a vykonajú iba skúšky potrebné na dotknuté brány.

## 2. Rozdelenie vlastníctva a integrácia

Codex vlastní spoločný renderer, syntetické CLI demo, jeho manifest, nezávislé očakávania, regresné testy a FX010 implementation/results/handoff. Koordinátor vlastní tento checklist, review FX-008/009, integračné požiadavky a záznam stavu. Úpravy rendereru sa začnú až po zrejmom odovzdaní vlastníctva alebo sa vrátia Codexu s presnou reprodukciou.

Po doručení odovzdania:

1. Zaznamenať skutočnú vetvu, commit, rodiča a čistotu pracovnej kópie. Prečítať diff a kód; názov reportu sám nie je dôkaz.
2. V oddelenom pracovnom priestore reprodukovať relevantné skúšky a oba CLI príklady. Uchovať verzie, príkazy, návratové kódy, hashe vstupov a výstupov.
3. Každému kritériu nižšie priradiť `PASS`, `FAIL`, `BLOCKED` alebo `NOT_TESTED` s konkrétnym dôkazom. Neprítomnosť implementácie je `NOT_TESTED`, nie úspech.
4. Kritický nedostatok vrátiť s jedným minimálnym syntetickým príkladom a očakávaním. Test ani pôvodný kontrakt neupravovať iba preto, aby kontrola vyšla.
5. Overený commit integrovať do pracovnej integračnej vetvy so zachovaním histórie a používateľových zmien. Úspešné demo samo neuzatvorí celé FX-010 s nesplnenými závislosťami.

## 3. Nezávislý checklist rendereru a CLI

Nasledujúce očakávania vznikli pred sprístupnením Codexovho rendereru. Pri review sa doplní stĺpec dôkazu, nie spätne zmäkčí požadované správanie.

| ID | Požadované správanie | Konkrétna kontrola pri odovzdaní | Stav teraz |
| --- | --- | --- | --- |
| R01 | Jeden spoločný deterministický renderer, bez sieťových volaní, modelu a spúšťania analýz. | Čítanie kódu, rozhrania a importov; CLI je tenký volajúci. Nevzniknú dve nezávislé implementácie faktického výstupu. | NOT_TESTED |
| R02 | Existujúci validačný kontrakt sa zachová. `report_generation_allowed` ostáva `false`. | Diff validátora a pôvodných očakávaní; regresné testy musia zachytiť zmenu príznaku aj jeho typu. `STRUCTURE_VALID` nie je produkčný súhlas. | NOT_TESTED |
| R03 | CLI prijme iba explicitne povolené syntetické fixtures. | Manifest s nezávislými identitami a hashmi; odmietnutie neznámeho ID, ľubovoľnej externej cesty/stdin/URL a zmenenej fixture. Samotné pole `synthetic: true` vo vstupných dátach nie je povolenie. | NOT_TESTED |
| R04 | Kontrola, hash a renderer pracujú nad tou istou zachytenou bajtovou snímkou. | Overiť tok načítania; po validácii nesmie nasledovať opätovné načítanie meniteľnej cesty. Negatívna skúška zmeny obsahu nesmie vytvoriť prehľad iného vstupu. | NOT_TESTED |
| R05 | Očakávané job/case/evidence ID pochádzajú z manifestu alebo iného nezávislého kontextu. | Zameniť každú identitu osobitne. Zostavenie `expected_*` z práve kontrolovaného JSON musí review odmietnuť. | NOT_TESTED |
| R06 | Pozitívne a negatívne IOC demo majú presné, nezávisle stanovené očakávania. | Očakávania nesmú vzniknúť volaním testovaného rendereru. Kontrolovať konkrétne ID, klasifikácie, závažnosti, referencie, časy, počty a chýbajúce údaje. Golden súbor nie je nezávislý len preto, že je v Gite. | NOT_TESTED |
| R07 | Všetky zdrojové warnings/limitations sa zachovajú vrátane poradia, duplicít a poslednej položky. | Porovnanie prvkov so zdrojom po definovanom zobrazovacom escapovaní; hraničný vstup s koncovým markerom. Bez zhrnutia alebo tichého odstránenia opakovaných textov. | NOT_TESTED |
| R08 | Každý nález má dohľadateľnú cestu do prijatého JSON a pôvodnú referenciu, ak existuje. | Referencie musia ukazovať na existujúce položky. Chýbajúci artefaktový odkaz dostane limit; JSON pointer nepredstiera otvorenie pôvodného artefaktu. | NOT_TESTED |
| R09 | Klasifikácie a zdrojové tvrdenia nemenia význam. | `NO_KNOWN_IOC` neznamená všeobecnú bezpečnosť; závažnosť sa neodvodzuje z dramatického textu. Skontrolovať aj prázdne nálezy a rozpor metadát. | NOT_TESTED |
| R10 | Časy sa neprepočítavajú bez podkladu a zachová sa ich pôvodná hodnota. | Offset, neznáma zóna, chýbajúca hodnota a časový rozpor; UTC sa nesmie doplniť odhadom. | NOT_TESTED |
| R11 | Zdrojové tvrdenia, diagnostika a prípadné AI vysvetlenie majú odlišné sekcie. | Demo výslovne uvedie, že AI vysvetlenie nebolo vytvorené. Diagnostika validátora sa nevydáva za pôvodné upozornenie zdroja a zdrojový text za nezávisle overený fakt. | NOT_TESTED |
| R12 | Nedôveryhodný text sa bezpečne zobrazí bez aktívnych obrázkov, HTML alebo vykonania pokynov. | Vstupy s HTML, Markdown odkazmi/obrázkami, spätnými apostrofmi, novými riadkami, riadiacimi a bidi znakmi. Definovať zobrazenie tak, aby bolo dohľadateľné a nič podstatné potichu nezmizlo. Odkazy sa automaticky nenačítajú. | NOT_TESTED |
| R13 | Chybný alebo nadlimitný vstup nevytvorí úspešný prehľad ani čiastočný súbor s úspešnou hlavičkou. | Oddeliť bezpečnú diagnostiku a úspešný dokument; kontrolovať stdout, návratový kód a cieľový súbor po zlyhaní. Nezamieňať chybu briefu za zmenu pôvodného stavu analýzy. | NOT_TESTED |
| R14 | Rovnaké prijaté bajty, politika a renderer vytvoria rovnaké výstupné bajty. | Opakované behy a procesy; žiadny aktuálny čas, náhodné ID alebo absolútna lokálna cesta v kanonickom výstupe. Čas behu patrí do oddeleného reportu. | NOT_TESTED |
| R15 | Hash, podpis, timestamp, zdrojová autentickosť a úplnosť sú samostatné tvrdenia. | SHA-256 prijatého exportu sa nesmie označiť za overenie artefaktu či odborného záveru. Existujúci execution record sa nesmie vydávať za podpis celého výsledku. Nevykonané overenia ostanú `NOT_VERIFIED`. | NOT_TESTED |
| R16 | Testy vedia odhaliť chybný renderer. | Kontrolovaná mutácia výstupu, identity alebo vynechaného warningu musí vyvolať FAIL; testy nesmú iba porovnávať dve volania tej istej chybnej funkcie. | NOT_TESTED |
| R17 | Distribučná skúška zodpovedá skutočnému dosiaľ testovanému spôsobu spustenia. | Čisté izolované prostredie, oba CLI príklady, nedestruktívne výstupy, presné závislosti. Beh v lokálnom checkoute sa nesmie vydávať za úspech doručenia cez Agensi. | NOT_TESTED |
| R18 | Handoff je úplný a pravdivý. | Existujú implementation/results/handoff; zhodujú sa commity, počty, exit kódy a obmedzenia s reprodukciou. Syntetické demo, živý klient a produkcia majú oddelené verdikty. | NOT_TESTED |

Vizuálne escapovanie nezaručuje odolnosť modelu voči vloženým pokynom. Aj dokonale deterministický Markdown obsahuje nedôveryhodné zdrojové texty; modelový test FX-014 zostáva samostatný.

## 4. Integračný kontrakt kontrolovaného adaptéra — návrh

Ide o návrh rozhrania a prijímacích skúšok. V tomto cykle sa adaptér ani renderer neimplementujú. Hub a neskorší lokálny export smú mať samostatné adaptéry, ale volajú jedno spoločné jadro.

### Vstupný kontext pred načítaním výsledkov

Kontext musí určiť overeného používateľa/organizáciu, povolený prípad a dôkaz, požadovaný job, schválený endpoint, pripnutý profil servera/dát a schválenú cieľovú konfiguráciu. Oprávnenie a očakávané identity musia pochádzať z nezávisle overeného kontextu požiadavky a priradenia používateľa k prípadu/jobu. Nesmú sa automaticky prevziať z výsledku, ktorý je práve predmetom kontroly; samotný platný podpis výsledku na to nestačí. Ak zdroj neposkytuje dôveryhodné priradenie, podmienka je blokovaná.

Samostatný syntetický režim má vlastný allowlist fixtures a viditeľné označenie; nezdedí povolenie skutočných prípadov. Názov `forenzx.brief/1` z paralelného experimentu nie je automaticky schémou Hubu. Prípadné použitie vyžaduje vlastný kontrakt a testované mapovanie.

### Pozorovateľná postupnosť

1. Overiť konfiguráciu a oprávnenie. Pred odmietnutím nečítať ani nevracať obsah cudzieho prípadu.
2. Povoliť iba potrebné reportovacie operácie. Alias normalizovať pred kontrolou operácie; zakázané volanie skončí pred vedľajším účinkom.
3. Overiť stav jobu, identity a dostať ohraničenú snímku z povoleného zdroja. Celú transportnú odpoveď, jej extrakciu a identitu naviazať na jednu požiadavku.
4. V kóde skontrolovať podporovaný profil, celú prijatú snímku, úplnosť v doloženom rozsahu, limity a konzistenciu. Počet prijatých položiek nie je dôkaz celkového upstream rozsahu.
5. Pri neúspechu vrátiť iba bezpečný kód/diagnostiku. Odmietnutý prípadový text, zdrojové cesty, token ani surový payload nesmú byť súčasťou MCP obsahu alebo chyby určenej klientovi.
6. Po splnení konkrétneho režimu zavolať spoločné jadro s tou istou snímkou a nezávislými identitami. Model dostane iba schválený výstup a výslovne pomenované obmedzenia.
7. Uchovať minimálny záznam rozhodnutia bez poverení a bez nových neplánovaných kópií nálezov. História a logy majú vopred určené umiestnenie a životnosť.

### Matica integračného prijatia

| ID | Skúška | Požadovaný výsledok | Dnešný dôkaz |
| --- | --- | --- | --- |
| I01 | Reportovacie poverenie: povolené status/results a zakázané start/cancel vrátane aliasov. | Čítania len v oprávnenom rozsahu; odmietnutie zápisov pred vedľajším účinkom. `tools/list` samo nie je vynútenie. | Review a syntetické pozorovania [FX-008](FX008_AUTHORIZATION_REVIEW.md); súčasná politika tento produktový cieľ nesplňuje. |
| I02 | Cudzí prípad, cudzia organizácia, rovnaká organizácia bez udeleného prípadu a kolidujúce používateľské ID. | Reportovacia politika má explicitnú väzbu organizácia → používateľ → prípad/job. Povolenie nevznikne iba z rovnakej organizácie alebo rovnakého reťazca ID. | Aktuálny Hub používa OR pravidlá; to nie je dôkaz prísnej produktovej izolácie. [FX-008](FX008_AUTHORIZATION_REVIEW.md). |
| I03 | Nesúlad job/case/evidence medzi požiadavkou, dôveryhodným job kontextom a výsledkom. | Odmietnutie bez vydania cudzích nálezov. | Lokálny validátor kontroluje nezávisle dodané ID; chýba celý integrovaný tok. |
| I04 | Neplatný/neúplný výsledok obsahuje jedinečný syntetický marker. | Marker sa neobjaví na prijímacom bode klienta/modelu ani v chybách a neplánovaných logoch. | Kontrola pred klientom chýba; [FX-009](FX009_DATA_FLOW_REVIEW.md). |
| I05 | Klient skúsi priamo surové results mimo adaptéra alebo alternatívny alias/transport. | Deklarovaná konfigurácia a poverenia neumožnia obísť kontroly. Odobratie položky zo zoznamu nástrojov nestačí. | NOT_TESTED pre budúci adaptér; priamy Hub dnes vracia celý výsledok. |
| I06 | Zdroj medzi kontrolou a vykreslením zmení obsah alebo kontext. | Výsledok je viazaný na jednu schválenú snímku; žiadne miešanie dvoch jobov alebo verzií. | NOT_TESTED; kontroluje sa po odovzdaní jadra/adaptéra. |
| I07 | Chýbajúci alebo zmenený modelový endpoint, profil alebo schválenie. | Reálny obsah sa nenačíta/nevydá modelu. Syntetický režim zostane explicitne oddelený. | Podporovaný profil zatiaľ nie je doložený. |
| I08 | Výpadok schváleného poskytovateľa a limit kontextu/výstupu. | Žiadny tichý fallback; žiadny úspešný brief pri nepreukázanom pokrytí. | NOT_TESTED; vyžaduje konkrétneho klienta/model a meranie. |

I02 je **navrhovaná prísnejšia politika reportovacieho produktu**, nie tvrdenie, že každý interný organizačný prístup pôvodného Hubu je proti jeho vlastnému kontraktu. Presný spôsob udeľovania prístupu a úmyselné zdieľanie prípadov sa musia pri implementácii pomenovať. Bez takého rozhodnutia zostáva reálne spracovanie nepovolené.

## 5. Povolenie reálnych vstupov — návrh samostatnej brány

Existujúci validátor sa neprepíše na `report_generation_allowed: true`. Budúce povolenie potrebuje nový verziovaný kontrakt rozhodnutia nad celým tokom, naviazaný na presnú konfiguráciu a konkrétnu snímku. Tento dokument ho neudeľuje.

| Oblasť | Podmienka pred povolením | Väzba |
| --- | --- | --- |
| Autorizácia | Vynútené reportovacie operácie a rozsah prípadu; pozitívne aj negatívne testy bez admin poverenia. | FX-008 |
| Klient a protokol | Úspešný skutočný klientský tok, pomenovaná verzia a samostatne vyriešené relevantné chyby discovery/verziovania. | FX-007 |
| Zdroj a úplnosť | Podporovaný profil, nezávislé identity, kontrolovaná snímka, dôkaz transportného pokrytia; žiadne odhadované X/Y. | FX-005 |
| Tok a príjemcovia | Známy klient, model/provider/endpoint, história, diagnostika, retencia a tréning; známe miesto vynútenia zákazu fallbacku. | FX-009 |
| Rozpočet a výstup | Zmeraná celá konfigurácia, rezerva výstupu, zachovanie posledného upozornenia, odmietnutie skrátenia. | FX-005, FX-010–014 |
| Odborná a modelová kontrola | Zodpovedajúca evaluácia faktov, interpretácií, adversariálnych vstupov a odborný kontrolný záznam. | FX-010–014, FX-016 |
| Rozhodnutie pracoviska | Doložené oprávnenie pracovať s konkrétnym typom údajov a cieľovým prostredím; správca konfigurácie, rozsah a životnosť schválenia. | FX-009; nevzniká automaticky nákupom skillu |

Pri neznámej alebo zmenenej podmienke sa povolenie nepoužije. Verejný predaj má navyše vlastné otvorené podmienky licencie, doručenia a pravdivého listingu (FX-003/015/017/018); technické povolenie jednej konfigurácie nie je rozhodnutie o vydaní produktu.

## 6. Konkrétne nasledujúce odovzdanie

Kým renderer nie je dostupný, koordinátor dokončí zdrojové a syntetické dôkazy FX-008/009 a uloží ich na vlastnú súkromnú vetvu. Codex môže súbežne dokončiť svoje FX-010 súbory. Najbližší integračný vstup od Codexu je **skutočný commit alebo patch a tri reporty**, nie iba hlásenie počtu testov.

Ak odovzdanie zostane nedostupné, ďalšia implementačná zmena má riešiť najbližšiu otvorenú bránu FX-007: samostatný upstream patch discovery/verziovania s lokálnou reprodukciou. Pôvodný klientsky beh sa bez zmeny read-only prostredia neopakuje. Oprávnenia FX-008 sú ďalšou samostatnou upstream zmenou, nie vedľajšou úpravou rendereru.
