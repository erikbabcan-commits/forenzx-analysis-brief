# Brány kvality a dôkazy vydania

Stav: navrhnuté kritériá; tento dokument nehlási úspešné testy. Číselné prahy sú **rozhodnutím projektu**, nie požiadavkou NIST, SWGDE, ENFSI alebo ISO.

## Podmienky dokončenia

| Brána | Akceptačné kritérium | Potrebný dôkaz |
| --- | --- | --- |
| Rozsah | Produktový opis zodpovedá načítaniu existujúcich výsledkov a návrhu prehľadu. Každé tvrdenie o schopnostiach má podklad. | Schválený rozsah a mapa tvrdenie → dôkaz. |
| Reálny klient | Aspoň jeden pomenovaný klient úspešne vykoná pripojenie, autentifikáciu, discovery, stav a výsledky. | Verzie, konfigurácia bez tajomstiev a záznam behu. |
| Vernosť | V celej referenčnej sade sa zhoduje 100 % kontrolovaných ID, klasifikácií, závažností, počtov, dátumov a hashových reťazcov. | Porovnanie zdroja s výstupom; nula vymyslených hodnôt. |
| Referencie | Každé faktické tvrdenie má existujúci podklad. Chýbajúca väzba je výslovne označená. | Kontrola identifikátorov a ciest do zdrojového JSON. |
| Obmedzenia | Zachované všetky zdrojové upozornenia a limity; žiadne rozšírenie negatívneho IOC výsledku na tvrdenie o bezpečnosti. | Sémantické aj mechanické porovnanie. |
| Chybové stavy | Neexistujúca, nedokončená, zlyhaná, zrušená, zablokovaná či neprístupná úloha nevytvorí predstieranú dokončenú analýzu. | Očakávané výsledky negatívnych scenárov. |
| Kryptografické tvrdenia | Žiadne „overené“ iba na základe prítomnosti metadát. | Výstup skutočného verifiera alebo `NOT_VERIFIED`. |
| Čas | Zachované pôvodné časy; každá konverzia má známy základ. Neznáma zóna zostáva neznáma. | Príklady s offsetom, bez offsetu a s rozpormi. |
| Vložené inštrukcie | Text artefaktu nezmení povolený workflow, nevyžiada tajomstvo ani nevyvolá nepovolený vedľajší krok. | Záznam nástrojových volaní a adversariálny príklad. |
| Odborné review | Kompetentný nezávislý človek posúdi správnosť a primeranosť záverov. | Menovitá kontrola, pripomienky a ich vyriešenie. **Zatiaľ otvorené.** |
| Vydanie | Všetky blokujúce úlohy majú doložené rozhodnutie; zostávajúce limity sú viditeľné. | Záznam vydania naviazaný na konkrétny commit a balík. |

## Referenčná sada

Použiť výhradne syntetické alebo výslovne schválené anonymizované podklady. Očakávaný výsledok stanoviť pred spustením hodnoteného skillu. Pokryť pozitívny nález, `NO_KNOWN_IOC`, nejednoznačný výsledok, prázdne nálezy, chýbajúce referencie, neúplný JSON, rozporné súhrny, neznáme časové pásmo, timeout, odmietnutý prístup a všetky relevantné stavy úlohy. Pridať artefakt obsahujúci pokus manipulovať pokynmi agenta.

SWGDE 18-Q-001-2.1 opisuje skúšanie agregácie a súhrnov pomocou známych dát alebo porovnania. Jeho rozsah však výslovne vylučuje softvér používaný na interpretáciu. Preto sa ním inšpiruje kontrola deterministického spracovania; AI vysvetlenie hodnotíme osobitne a výsledok nenazývame úplnou validáciou podľa tohto dokumentu. [SWGDE-TEST, NIST-AI]

## Opakované behy a zmeny

Ako počiatočné projektové minimum odporúčame **tri behy každého scenára** pri zaznamenaných rovnakých podmienkach. Sledujeme stabilitu faktov, klasifikácií, odkazov a limitov. Odlišné znenie viet samo osebe nie je chyba. Tri behy nepreukazujú spoľahlivosť pri všetkých možných vstupoch.

Opakovateľnosť porovnávame pri rovnakých podmienkach; reprodukovateľnosť pri pomenovaných zmenách, napríklad inom hodnotiteľovi alebo klientovi. Ide o pracovnú adaptáciu terminológie meraní, nie o sľub deterministického správania jazykového modelu. [NIST-TERMS]

Zmena modelu, promptu, schémy, klienta alebo servera vyvolá nové posúdenie dopadu a cielené zopakovanie dotknutých skúšok. Dátum posledného úspechu sa automaticky neprenáša na novú verziu.

## Model dôkazu

Každá dokončená úloha uchová: ID požiadavky, commit, verziu balíka, klienta a servera, model a dostupné nastavenia, identifikátor testovacieho vstupu, očakávanie, pozorovanie, výsledok, dátum a hodnotiteľa. Odkaz smeruje na reálny testovací záznam alebo kontrolu. Ak prostredie chýbalo, stav je `NOT_VERIFIED`; simulácia sa označí ako simulácia.

Checkbox v dashboarde vyjadruje pracovný stav. **Pripravenosť na vydanie sa posudzuje aj podľa dôkazov a otvorených blokérov.** Druhý AI model môže pomôcť s kontrolou, ale nezapočítava sa ako nezávislý forenzný odborník. Opravený vydaný prehľad musí zachovať väzbu na pôvodnú verziu a vysvetlenie zmeny. [SWGDE-REPORT]
