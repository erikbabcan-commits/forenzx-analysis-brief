# Backlog v0.1

Katalóg pripravený 20. 11. 2026. Aktuálne pracovné stavy a história sú v dashboarde; tento súbor je verziovaný počiatočný snapshot. Tri hotové úlohy označujú prípravu, nie validovaný produkt.

## FX-001 — Zafixovať zdrojový kód a inventár nástrojov

**Základ · P0 · done**

Doložiť, z ktorého stavu ForenZX vychádza návrh. Ide o kontrolu kódu, nie o dôkaz funkčného servera.

Závislosti: žiadne. Odhad: Dokončená kontrola kódu.

- [x] Zaznamenaný úplný commit upstream repozitára.
- [x] Overené kontrakty forenzx_analysis_status a forenzx_analysis_results s job_id.
- [x] Vymenované hranice kontroly: bez spustenia servera a bez reálneho AI klienta.

Dôkaz: Kontrola zdrojov 20. 11. 2026: erikbabcan-commits/forenzx-mcp-hub @ 0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f. Overené definície v core/server.py a core/models/forensic.py. Runtime ani klient neboli týmto overené.

## FX-002 — Uzavrieť rozsah prvého produktu

**Základ · P0 · done**

Existujúca dokončená analýza → návrh prehľadu pre analytika. Prvé vydanie má jeden jasný účel.

Závislosti: FX-001. Odhad: Produktový návrh pripravený.

- [x] Zdokumentovaný vstup job_id a výstup v docs/PRODUCT_CONTRACT.md.
- [x] Vymedzené povolené čítania a vylúčené spúšťanie či rušenie analýz.
- [x] Výstup označený ako AI návrh s kontrolou analytikom, bez sľubov certifikácie.

Dôkaz: docs/PRODUCT_CONTRACT.md: návrh rozsahu v0.1, vstup/výstup, povolené čítania a vylúčené schopnosti. Implementácia a hodnotenie skillu zostávajú úlohami FX-005 až FX-016.

## FX-003 — Rozhodnúť licenciu servera aj plateného skillu

**Základ · P0 · blocked**

Zákazník potrebuje jasné oprávnenie prevádzkovať vlastný ForenZX a používať zakúpený skill. Rozhoduje vlastník projektu.

Závislosti: žiadne. Odhad: Rozhodnutie vlastníka + úprava podmienok.

- [ ] Vlastník schválil podmienky použitia servera; zaznamenaná konkrétna verzia.
- [ ] Samostatne určené podmienky distribúcie a používania skillu.
- [ ] LICENSE-TODO.md vyriešený alebo doložená oprávnená cesta k vlastnej inštancii.

Dôkaz: Upstream LICENSE-TODO.md ponecháva externé použitie nevyriešené. Automaticky sa nevolí MIT ani iná licencia.

## FX-004 — Spísať terminológiu a pravidlá tvrdení

**Základ · P0 · done**

Pracovné definície, primárne zdroje a hranice forenzného reportovania. Nezávislé odborné posúdenie má vlastnú úlohu FX-016.

Závislosti: FX-002. Odhad: Výskumný návrh pripravený.

- [x] Existuje metodika s rozlíšením faktov, interpretácie, integrity a pôvodu.
- [x] Každý odborný zdroj má URL, verziu alebo rok a obmedzenie rozsahu.
- [x] Merateľné brány sú označené ako naše kritériá; odborné review zostáva otvorené.

Dôkaz: docs/METHODOLOGY.md, docs/QUALITY_GATES.md a docs/SOURCES.md pripravené z primárnych zdrojov 20. 11. 2026. ISO: iba verejný abstrakt. Žiadna certifikácia ani odborné schválenie sa týmto netvrdí.

## FX-005 — Overiť schému výsledkov a identitu úlohy

**Integrácia · P0 · todo**

Pred sumarizáciou odmietnuť nekonzistentný alebo neúplný zdroj a presne pomenovať chýbajúce údaje.

Závislosti: FX-001, FX-002. Odhad: 2–4 h, pracovný odhad.

- [ ] Definované povinné polia a správanie pri neplatnej schéme.
- [ ] Požadované a vrátené job_id, case_id a evidence_id sa kontrolujú na konzistenciu.
- [ ] Chýbajúce referencie a rozporné údaje vytvoria viditeľný limit alebo chybu.

Dôkaz: Zatiaľ nedoložené.

## FX-006 — Pripraviť syntetickú referenčnú sadu

**Integrácia · P0 · todo**

Najprv zapísať očakávania, potom ladiť prompt. Demo dáta musia byť jasne označené ako syntetické.

Závislosti: FX-005. Odhad: 3–6 h, pracovný odhad.

- [ ] Pokryté dokončené, bežiace, zlyhané, zrušené, zablokované a chýbajúce úlohy aj odmietnutý prístup.
- [ ] Existujú nálezy s chýbajúcou referenciou, neznámou zónou a rozpornou identitou.
- [ ] Pridaný negatívny IOC výsledok a text artefaktu s vloženými škodlivými inštrukciami.
- [ ] Očakávané hodnoty a výstupné správanie zaznamenané pred hodnotením.

Dôkaz: Zatiaľ nedoložené.

## FX-007 — Preukázať pripojenie jedného reálneho klienta

**Integrácia · P0 · todo**

Overiť celý tok v konkrétnom AI klientovi a verzii. Samostatný dispatcher test nestačí na tvrdenie o kompatibilite.

Závislosti: FX-001, FX-006. Odhad: 0,5–2 pracovné dni podľa prekážok.

- [ ] Zaznamenaný klient, jeho verzia, server commit a presná konfigurácia bez tajomstiev.
- [ ] Prešli autentifikácia, objavenie nástrojov a volania status/results.
- [ ] Overená skutočná cesta vyjednania MCP verzie alebo podporované priame pripnutie verzie.
- [ ] Uložený redigovaný záznam behu; opravy upstreamu evidované samostatne.

Dôkaz: NOT_VERIFIED. Súčasný MCP 2026-07-28 už nevyžaduje starý inicializačný handshake. Nepovažovať jeho absenciu automaticky za chybu; otestovať reálnu kompatibilitu.

## FX-008 — Obmedziť prístup na reportovanie

**Integrácia · P0 · todo**

Rozlíšiť pokyny skillu od technicky vynútených oprávnení. Aktuálny analytický kľúč sám osebe nemusí zakazovať zápisové nástroje.

Závislosti: FX-002, FX-007. Odhad: 3–6 h + prípadná oprava servera.

- [ ] Zdokumentované a otestované povolené čítania a zakázané start/cancel volania.
- [ ] Návod správne rozlišuje X-API-Key alebo APIKey od Bearer JWT.
- [ ] Pozitívny aj negatívny test prístupu k úlohe; bez potreby admin kľúča.
- [ ] Výslovne uvedené, ktoré obmedzenia vynucuje server/klient a ktoré sú iba pokynom.

Dôkaz: Zatiaľ nedoložené.

## FX-009 — Opísať tok dát a zachádzanie s kľúčmi

**Integrácia · P0 · todo**

Kupujúci musí vedieť, kam idú výsledky a kto ich spracúva. Vlastný MCP server automaticky neznamená lokálny AI model.

Závislosti: FX-008. Odhad: 2–3 h, pracovný odhad.

- [ ] Endpoint je používateľský; žiadne skryté odosielanie na nové služby.
- [ ] ZIP, demo a logy neobsahujú kľúče ani skutočné dôkazové dáta.
- [ ] Návod opisuje spracovanie výsledkov zvoleným AI klientom/poskytovateľom.
- [ ] Nastavenie, rotácia a chybné poverenia majú overený postup.

Dôkaz: Zatiaľ nedoložené.

## FX-010 — Vytvoriť šablónu prehľadu s referenciami

**Kvalita · P0 · todo**

Každý fakt sa musí dať dohľadať v prijatom zdrojovom výstupe. Odkaz na JSON nie je nezávislé skúmanie artefaktu.

Závislosti: FX-004, FX-005. Odhad: 3–5 h, pracovný odhad.

- [ ] Každý nález má pôvodné ID a dostupnú referenciu na artefakt alebo JSON položku.
- [ ] Zachované všetky zdrojové upozornenia a obmedzenia.
- [ ] Uvedené job/case/evidence ID, dostupné verzie a identita zdrojového výstupu.
- [ ] Chýbajúci údaj je označený; nikdy doplnený odhadom.

Dôkaz: Zatiaľ nedoložené.

## FX-011 — Oddeliť zdrojové fakty od vysvetlenia AI

**Kvalita · P0 · todo**

Jazykový model môže vysvetľovať, ale nesmie meniť nálezy, vyrábať istotu alebo vydávať negatívnu zhodu IOC za bezpečné zariadenie.

Závislosti: FX-010. Odhad: 2–4 h, pracovný odhad.

- [ ] Klasifikácie a závažnosti zostávajú zhodné so zdrojom.
- [ ] Interpretácia AI je oddelená, označená a má uvedené podklady.
- [ ] Nevzniká číselná istota ani atribúcia bez zdrojového podkladu.
- [ ] NO_KNOWN_IOC sa vzťahuje iba na skúmaný rozsah a použité indikátory.

Dôkaz: Zatiaľ nedoložené.

## FX-012 — Pravdivo zobraziť hash a rozsah podpisu

**Kvalita · P0 · todo**

Existujúci podpis execution record nepokrýva nálezy, časovú os, upozornenia ani AI prehľad. Zobrazenie metadát nie je overenie.

Závislosti: FX-005, FX-010. Odhad: 2–4 h; verifier by bol samostatný rozsah.

- [ ] Predvolený stav metadát je NOT_VERIFIED, kým neexistuje skutočný overovací krok.
- [ ] Presne pomenovaný podpísaný payload a väzba na overovací kľúč.
- [ ] Žiadna značka naznačujúca overenie celého výsledku alebo AI prehľadu.
- [ ] Ak pribudne verifier, prejde aj test zmeneného payloadu a nedôveryhodného kľúča.

Dôkaz: Zatiaľ nedoložené.

## FX-013 — Zachovať časové údaje a neistotu

**Kvalita · P0 · todo**

Časová os má vychádzať zo zdroja. Neznáma zóna ani chýbajúci čas sa nesmú potichu domyslieť.

Závislosti: FX-010. Odhad: 1–3 h, pracovný odhad.

- [ ] Zachované pôvodné časy, offsety a zdrojové poznámky k normalizácii.
- [ ] Konverzia na UTC iba pri známom východisku.
- [ ] Neznáma časová zóna a rozpory sú viditeľné.
- [ ] Bez vymysleného poradia, času alebo osoby vykonávajúcej udalosť.

Dôkaz: Zatiaľ nedoložené.

## FX-014 — Otestovať vložené pokyny a chybové stavy

**Kvalita · P0 · todo**

Obsah artefaktov sa spracúva ako dáta. Zlyhanie alebo odmietnutie prístupu sa nesmie premeniť na predstieraný úspešný prehľad.

Závislosti: FX-006, FX-008, FX-009, FX-010, FX-011, FX-012, FX-013. Odhad: 3–6 h, pracovný odhad.

- [ ] Text artefaktu nevyvolá nové nástroje, endpointy ani vyzradenie kľúčov.
- [ ] Volania zostanú v povolenom rozsahu čítania.
- [ ] Nedokončená alebo zlyhaná úloha vráti stav a limit, nie úspešný findings brief.
- [ ] Chyby, timeouty a neúplné odpovede majú uchovaný testovací výsledok.

Dôkaz: Zatiaľ nedoložené.

## FX-015 — Zabaliť skill a overiť čistú inštaláciu

**Balenie · P0 · todo**

Pripraviť malý textový balík pre presne otestovaného klienta; samotný dashboard nie je predajný skill.

Závislosti: FX-007, FX-008, FX-009, FX-010, FX-011, FX-012, FX-013, FX-014. Odhad: 3–6 h, pracovný odhad.

- [ ] SKILL.md v koreni má name/description a presný workflow.
- [ ] Priložené setup/auth pokyny, konfiguračná šablóna, šablóna prehľadu a syntetický príklad.
- [ ] Predpoklady servera/modelu a verzie sú výslovne uvedené.
- [ ] Čistá inštalácia a celý príklad prešli bez neverejných závislostí a tajomstiev.

Dôkaz: Zatiaľ nedoložené.

## FX-016 — Dokončiť hodnotenie a nezávislé odborné review

**Kvalita · P0 · todo**

Doložiť vhodnosť pre konkrétny účel. Druhý AI model nenahrádza kompetentného nezávislého forenzného hodnotiteľa.

Závislosti: FX-015. Odhad: 1–2 dni testovania + dostupnosť hodnotiteľa.

- [ ] Referenčná sada má 100 % zhodu kontrolovaných faktov a všetky varovania/limity.
- [ ] Nula nepodložených faktických tvrdení, nepovolených zápisov a únikov tajomstiev v testovanej sade.
- [ ] Aspoň tri opakované behy na scenár podľa nášho navrhnutého minima; verzie a model zaznamenané.
- [ ] Menovitý odborný hodnotiteľ posúdil výstupy; kritické pripomienky vyriešené.
- [ ] Zostávajúce hranice pokrytia a neistoty sú zaznamenané.

Dôkaz: Nezávislý odborný hodnotiteľ zatiaľ nebol zabezpečený. Tri behy sú projektový návrh, nie norma ani dôkaz všeobecnej spoľahlivosti.

## FX-017 — Pripraviť demo, ponuku a príjem výplat

**Predaj · P1 · todo**

Ukázať skutočný vstup a výstup z overeného balíka. Navrhovaná úvodná cena je 19 USD jednorazovo.

Závislosti: FX-003, FX-016. Odhad: 2–4 h + nastavenie výplat.

- [ ] Krátke funkčné demo používa označené syntetické dáta.
- [ ] Listing uvádza vlastný ForenZX, podporovaného klienta a ďalšie možné náklady.
- [ ] Cena/podmienky a spôsob prijímania výplat skontrolované v Agensi.
- [ ] Marketing neobsahuje nepodložené certified/court-grade ani sľub súdnej prípustnosti.

Dôkaz: 19 USD je úvodný návrh, nie overená ochota trhu zaplatiť.

## FX-018 — Odoslať na posúdenie a potvrdiť vydanie

**Predaj · P1 · blocked**

Až po splnení všetkých brán podať verziovaný balík. Posúdenie Agensi sa eviduje oddelene od nášho testovania.

Závislosti: FX-003, FX-016, FX-017. Odhad: Verejný odhad Agensi 24–48 h od podania.

- [ ] Všetky predchádzajúce brány majú splnené kritériá a dohľadateľné dôkazy.
- [ ] Uložené číslo verzie, hash ZIP a changelog.
- [ ] Zaznamenané odoslanie, výsledok kontroly Agensi a vyriešenie pripomienok.
- [ ] Živý listing overený až po skutočnom schválení a publikácii.

Dôkaz: Zatiaľ nepodané. Joeri neuviedol termín, do ktorého musíme produkt dodať. Jeho odhad kontroly začína až podaním.
