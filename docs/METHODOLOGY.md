# Metodika ForenZX Analysis Brief

Stav: návrh metodiky pred validáciou produktu. Zdroje overené 20. novembra 2026. Odborné posúdenie nezávislým človekom zostáva otvorené. Identifikátory v hranatých zátvorkách odkazujú na [register zdrojov](SOURCES.md).

Revízia požiadaviek z 21. novembra 2026 dopĺňa tok údajov, limity vstupu, kompatibilitu schémy, označenie výstupu, syntetickú ukážku a hodnotenie modelov. Pôvodný forenzný rozsah sa nemení. Doklady implementácie a skúšok sa evidujú osobitne; táto metodika sama neoznačuje nové kontroly za splnené.

## Účel a hranice

ForenZX Analysis Brief pripravuje **AI asistovaný návrh prehľadu existujúcich výsledkov digitálnej forenznej analýzy**. Používateľ zadá identifikátor úlohy. Skill má načítať jej stav a dostupné výsledky z určenej inštancie ForenZX a vytvoriť dohľadateľné zhrnutie pre kontrolu analytikom.

Tento rozsah patrí predovšetkým do vykazovania výsledkov. Nezahŕňa získavanie dôkazového materiálu, nové skúmanie zariadenia, kriminalistický výsluch ani automatické posudzovanie viny. Výstup nástroja môže byť podkladom širšej správy; jej úplnosť a autorizáciu zabezpečuje zodpovedná osoba. [NIST-86, SWGDE-REPORT]

Použitie odborných odporúčaní neznamená certifikáciu, akreditáciu, schválenie organizáciou uvedenou medzi zdrojmi ani záruku súdnej prípustnosti. Kvalitu preukazujeme výsledkami konkrétnych skúšok v opísanom rozsahu.

## Pracovný slovník

Nasledujúce slovenské vysvetlenia sú parafrázy a pracovné definície projektu, nie doslovné citácie noriem.

| Pojem | Používanie v projekte |
| --- | --- |
| Kriminalistická taktika | Príprava a realizácia postupov, napríklad výsluchu, obhliadky, rekognície, prehliadky a tvorby kriminalistických verzií. Sylabus APZ dokladá obsah odboru, nie jednu záväznú definíciu. [APZ] |
| Zber | Identifikovanie, zaznamenanie a získanie relevantných údajov pri ochrane ich integrity. [NIST-86] |
| Technické skúmanie | Spracovanie získaných údajov a extrakcia relevantných informácií. [NIST-86] |
| Analýza | Vyhodnotenie výsledkov skúmania vo vzťahu k otázke, ktorú treba zodpovedať. [NIST-86] |
| Vykazovanie výsledkov | Zrozumiteľné zdokumentovanie postupov, výsledkov, podkladov a obmedzení. [NIST-86, SWGDE-REPORT] |
| Integrita | Zachovanie údajov; pri hashovej kontrole zhoda konkrétnych bajtov s konkrétnym referenčným stavom. |
| Pôvod a autentickosť | Čo materiál predstavuje, odkiaľ pochádza a ako vznikol; treba ich hodnotiť v kontexte dostupnej dokumentácie. [ENFSI] |
| Chain of custody | Dokumentovaná história manipulácie a odovzdávania: osoba, čas, predmet a účel. [NIST-CUSTODY] |
| Pozorovanie a interpretácia | Pozorovanie má konkrétny podklad; interpretácia vysvetľuje jeho možný význam. Čitateľ musí rozpoznať rozdiel. [ENFSI] |
| Validácia | Doloženie vhodnosti procesu na stanovený účel prostredníctvom požiadaviek a dôkazov ich splnenia. [ISO-27041] |

## Hash, podpis a pravdivosť

Prítomnosť hashového reťazca nie je vykonaná kontrola integrity. Prítomnosť podpisu nie je overenie podpisu. Zobrazenie takýchto polí preto používa označenie „údaj uvedený zdrojom“ a stav `NOT_VERIFIED`, pokiaľ skutočný overovací krok neexistuje a nemá uchovaný výsledok.

Aj úspešné kryptografické overenie má obmedzený význam: viaže sa na konkrétne dáta, algoritmus, kľúč a dôveryhodnosť referencie. Samo neurčuje, či opisovaná udalosť nastala, kto vykonal skutok alebo či bol materiál získaný oprávnene. Je to technické rozlíšenie významu overenia, nie právny záver.

Rovnako zoznam udalostí `chain_of_custody` nezaručuje úplnú históriu pred vstupom do systému. Chýbajúce úseky označíme, nedopĺňame ich domnienkou.

## Postup vytvorenia prehľadu

1. **Určiť rozsah a tok údajov.** Zaznamenať požiadavku, identifikátor úlohy, endpoint a konfiguráciu klienta/modelu. Pred načítaním reálnych výsledkov informovať používateľa o príjemcoch, histórii a logovaní; overiť oprávnenie a schválené prostredie. Vlastný MCP nie je dôkaz lokálneho LLM. Pri výpadku neprechádzať automaticky k inému poskytovateľovi. [MISTRAL-ZDR, OLLAMA-LOCAL]
2. **Skontrolovať stav.** Nedokončená, zlyhaná, zrušená alebo zablokovaná úloha dostane pravdivé stavové hlásenie. Chýbajúce výsledky sa nesmú nahradiť vymysleným obsahom.
3. **Zachytiť a skontrolovať zdroj.** Uchovať identitu zdrojového výstupu, dostupné verzie a čas získania podľa pravidiel pracoviska. Pred odovzdaním modelu overiť podporovanú schému, povinné sekcie, identitu úlohy a zdokumentované limity. Hash prijatých bajtov nepreukazuje pravdivosť ani úplnosť upstream exportu. Citlivý obsah ani prihlasovacie údaje nepatria do verejných testovacích záznamov. [MCP-TOOLS]
4. **Preukázať rozsah spracovania.** Pri neznámej schéme, nepreukázanej úplnosti, prekročení limitu alebo nedokončenej odpovedi vydať diagnostiku prehľadu. Neoznačovať tým svojvoľne pôvodnú dokončenú analýzu za neúplnú. Počty X/Y použiť iba s podkladom pre obe hodnoty. [MISTRAL-LIMITS]
5. **Pripraviť faktický prehľad.** Zachovať klasifikácie, závažnosti, identifikátory, časy, upozornenia a limity kontrolovaným postupom. Odkaz na položku JSON dokladá pôvod vo výstupe ForenZX; nenahrádza preskúmanie pôvodného artefaktu.
6. **Označiť vysvetlenie AI.** Interpretácie uviesť v samostatnej časti s podkladmi a neistotami. Obsah artefaktov považovať za údaje, nikdy za príkazy pre agenta. Riziká konfabulácie a nadmernej dôvery v automatizáciu riešime samostatnou evaluáciou pre konkrétny model a konfiguráciu. [NIST-AI]
7. **Odovzdať na kontrolu.** Overiť, že výstup nie je urezaný, a zachovať označenie pracovného návrhu. Analytik preverí vecnú správnosť, rozsah a referencie; schválenie alebo oprava má vlastný záznam.

Pri `NO_KNOWN_IOC` používame formuláciu obmedzenú na skúmané dáta a použité indikátory. Z nej nevyvodzujeme všeobecnú bezpečnosť zariadenia. Aj tvorcovia MVT požadujú odbornú interpretáciu výstupov pred závermi o napadnutí. [MVT]

## Čo musí zostať otvorene uvedené

Neznáme časové pásmo, chýbajúca referencia, neúplný vstup a rozporné údaje sa musia ukázať používateľovi. Vlastná inštancia MCP sama neznamená lokálne spracovanie AI: dokumentácia musí vysvetliť, ktoré výsledky dostáva zvolený agent alebo jeho poskytovateľ. Odborné review, test reálneho klienta a kvalita každého konkrétneho vydania sa posudzujú podľa [brán kvality](QUALITY_GATES.md).

## Právne a prevádzkové hranice

Označenie AI návrhu vysvetľuje účel a potrebu kontroly, nenahrádza licenciu alebo obchodné podmienky. Pri spotrebiteľskom predaji nemožno plošnú formuláciu „as-is“ považovať za zrušenie povinných práv zákazníka. Rozsah použiteľných podmienok závisí od predajného modelu a uplatniteľného práva. [EU-DIGITAL]

ZDR alebo lokálny model nie sú všeobecným dôkazom zákonnosti spracovania. Posúdenie zohľadní konkrétny účel, právny režim, roly a tok dát. GDPR sa nepoužíva ako univerzálny štítok pre každú činnosť trestného vyšetrovania; pri príslušných orgánoch môže ísť o osobitný režim. Dokumentácia produktu preto netvrdí automatický právny súlad. [GDPR]

Ukážkové dáta balíka sú od začiatku syntetické. Ukážka bez vlastného ForenZX servera sa odlišuje od úplne offline prevádzky. Deklarovaná podpora modelu/klienta a každý sľub o čase spustenia musia mať konkrétny testovací záznam. [AGENSI-LOAD, NIST-AI]
