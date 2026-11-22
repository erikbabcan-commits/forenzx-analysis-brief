# Produktový kontrakt v0.1 — návrh

Pôvodný návrh: 20. 11. 2026. Revízia požiadaviek: 21. 11. 2026 (Europe/Bratislava).

Stav: celý produkt ešte neprešiel integračným a odborným overením. Tento kontrakt opisuje požadované správanie; implementáciu a výsledky skúšok treba doložiť osobitne. Doplnenia z kontroly šiestich pripomienok sú zaznamenané v [revíznom dodatku](REVIEW_ADDENDUM_2026-11-21.md).

## Jedna úloha
**ForenZX Analysis Brief pripraví AI asistovaný návrh prehľadu výsledkov existujúcej dokončenej digitálnej forenznej analýzy, s referenciami na zdrojový výstup a zachovanými upozorneniami a obmedzeniami.**

Cieľovým používateľom je analytik alebo oprávnený pracovník, ktorý už prevádzkuje vlastnú funkčnú inštanciu ForenZX. Zákazník kupuje workflow a návody. Samotný balík nezabezpečuje hosting servera ani modelu.

## Vstup a čítanie
- Používateľom zvolený endpoint a poverenie uložené v podporovanom klientovi; žiadne kľúče v balíku.
- Explicitné `job_id` existujúcej úlohy.
- Povolené hlavné nástroje: `forenzx_analysis_status` a `forenzx_analysis_results`.
- Prípadné čítanie health/capabilities slúži iba nastaveniu. Odpoveď READY sama nedokazuje pripravenosť workerov.
- Skill nesmie spustiť ani zrušiť analýzu. Skutočné vynútenie oprávnení sa musí overiť, nestačí text promptu.

## Tok dát pred prvým použitím

Pred načítaním skutočných MCP výsledkov musí používateľ poznať celý tok: ForenZX endpoint, AI klient a jeho verziu, model a jeho poskytovateľa/endpoint, históriu rozhovoru, diagnostické záznamy a telemetriu. Pri každej podporovanej konfigurácii sa zaznamenajú retenčné podmienky, nastavenie používania dát na tréning a technicky vynútené obmedzenia. Vlastný MCP server nepreukazuje lokálne spracovanie modelom. Upozornenie vo výslednom prehľade je na rozhodnutie o prvom prenose údajov neskoré. [MISTRAL-ZDR, OLLAMA-LOCAL]

Schválená konfigurácia nesmie pri chybe automaticky prejsť k inému poskytovateľovi. Neznáma konfigurácia sa nepovažuje za overenú. Pravidlá musia rozlišovať, čo presadzuje kód alebo prostredie a čo je iba pokyn v `SKILL.md`. Samotný text skillu nevynucuje sieťovú izoláciu hostiteľského klienta. Kontrolu vykonať pred odovzdaním dát modelu. [MCP-TOOLS]

ZDR, vylúčenie z tréningu, lokálna prevádzka a oprávnenosť spracovania sú samostatné otázky. ZDR je vlastnosť konkrétnej služby a nastavenia; nie je všeobecným dôkazom splnenia GDPR alebo mlčanlivosti. Kde sa GDPR uplatňuje, spracovanie treba posúdiť podľa konkrétnych rolí, účelu a podmienok, vrátane zákonnosti, minimalizácie a primeranej ochrany. Samotný predaj balíka neurčuje, že jeho autor spracúva prípadové údaje zákazníka. [GDPR]

## Dátový kontrakt, úplnosť a limity

Pripnutý upstream `AnalysisResult` v commite `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f` nemá `schema_version` ani `forenzx_version`. Pole `pack_version` označuje analytický balík. Verziu MCP protokolu, serverové zostavenie, schému výsledku a verziu skillu evidujeme oddelene. Adaptér môže pomenovať podporovaný profil pripnutej schémy; nesmie tvrdiť, že tento identifikátor dodal pôvodný server. [CODE-MODEL, MCP-TOOLS]

Pred sumarizáciou sa deterministicky kontrolujú podporovaný profil a skutočná štruktúra vstupu, povinné sekcie, typy, identita job/case/evidence, konzistencia vnorených záznamov a úplnosť dostupného vstupu. Neznáma verzia, chýbajúce povinné polia alebo nesúlad sa nesmú opraviť domnienkou modelu. Pravidlá pre dodatočné polia a nové hodnoty klasifikácií musia byť explicitné.

Limit bajtov, počet položiek a prípadné obmedzenie hĺbky JSON chránia validátor. **Tieto technické limity samy nepreukazujú, že vstup vojde do kontextu modelu.** Osobitne treba zmerať podporovaný klient a model vrátane pokynov, schém nástrojov, histórie a rezervy na výstup. Pri prekročení overeného limitu, nepreukázanej úplnosti alebo nedokončenej generácii nevznikne úspešný prehľad nálezov. Vznikne diagnostika „Prehľad nevytvorený“ s dôvodom; stav pôvodnej analýzy sa tým svojvoľne nemení. [MISTRAL-LIMITS]

Počet „X z Y“ uvádzať iba pri dôveryhodnom určení oboch hodnôt. Zhodný počet nálezov nepreukazuje úplnosť varovaní, obmedzení alebo referencií. Schéma a hash prijatého JSON dokladajú len kontrolovanú reprezentáciu prijatého vstupu; samy nepotvrdzujú, že upstream export alebo klient nič nevynechal. Automatický výber časti nálezov ani spracovanie po častiach nie sú v prvom vydaní deklarované, kým nemajú samostatne overené pokrytie.

## Výstup
Návrh má hlavičku „AI asistovaný návrh — vyžaduje kontrolu analytikom“. Obsahuje identitu úlohy, dostupné case/evidence ID a verzie, zdrojové nálezy, referencie, samostatne označené vysvetlenie AI, všetky pôvodné warnings/limitations a viditeľné chýbajúce údaje. Dostupné pôvodné časy sa zachovajú.

Referencia do prijatého JSON dokladá pôvod tvrdenia vo výstupe ForenZX. Netvrdí, že skill znovu otvoril a preskúmal pôvodný artefakt. Zdrojové nálezy sú tvrdeniami zdrojového systému, ktorých vecnú správnosť samotné preformulovanie neoveruje.

Pri nedokončenom, zlyhanom, zrušenom alebo zablokovanom stave vznikne stavové hlásenie. Pri odmietnutom prístupe alebo neexistujúcej úlohe sa nevytvára falošný findings brief. Detailné správanie spresní FX-005 a referenčná sada.

Požadované označenie v každom prehľade:

> Tento dokument je AI asistovaný pracovný návrh prehľadu z poskytnutých výsledkov ForenZX. Pred odborným použitím musí analytik overiť údaje, odkazy a závery oproti zdrojovým výsledkom a relevantným podkladom. Dokument sám osebe nepreukazuje úplnosť vyšetrovania ani prípustnosť dôkazov.

Tento text opisuje účel a potrebu kontroly. Nie je náhradou licencie ani obchodných podmienok a sám neprenáša všetku právnu zodpovednosť na analytika.

## Hranice tvrdení
Vydanie v0.1 nezískava dôkazy, nevykonáva novú analýzu zariadenia, neriadi vyšetrovanie a nevydáva znalecký posudok. Nesmie sľubovať identifikáciu páchateľa, úplnú detekciu kompromitácie, certifikáciu ani súdnu prípustnosť.

Prítomnosť hashov, podpisu či chain_of_custody v zdroji je metadata. Ak nebol vykonaný osobitný overovací krok, stav je `NOT_VERIFIED`. Súčasný execution record nepodpisuje nálezy, časovú os, warnings/limitations ani AI prehľad.

## Predajný návrh
- Jeden skill, navrhovaná cena **19 USD jednorazovo**.
- Prvý listing uvedie iba skutočne otestovaného klienta a verziu.
- Syntetické demo ukáže konkrétny vstup → výstup.
- Serverová licencia a podmienky plateného skillu sú samostatné otvorené rozhodnutia.
- Vlastný platobný systém, prenájom MCP a ďalšie balíky sú neskoršie možnosti; nepatria do v0.1.

## Ukážka a podporované konfigurácie

Balík má obsahovať dva od začiatku syntetické príklady: nález s referenciami a výsledok s významným obmedzením. Samostatný ukážkový postup nepotrebuje vlastný ForenZX server. Označenie „úplne offline“ sa nepoužije bez testu celého toku: Agensi doručuje skill cez svoju službu a zvolený model môže byť cloudový. Cieľ krátkeho spustenia ukážky sa môže zmeniť na časový sľub až po meraní pri uvedených predpokladoch. Agensi skripty spúšťa jednotlivo z dočasných súborov; balík nesmie bez overenia spoliehať na susedné súbory na disku. [AGENSI-LOAD, AGENSI-PACK]

Pre prvú verziu sa overí jedna presne pomenovaná primárna konfigurácia. Jedna lacnejšia alebo menšia konfigurácia slúži na porovnanie hraníc; ak neprejde, nebude deklarovaná ako podporovaná. Matica uvedie model/identifikátor verzie, poskytovateľa, klienta/verziu, kontext, nastavenia, skill verziu a serverový/dátový profil. Pri lokálnom modeli doplní dostupný digest váh, kvantizáciu a runtime. Žiadny model sa neoznačí ako záruka správnosti. [NIST-AI, OLLAMA-LOCAL]

Podmienky používania musia určiť rozsah dodávky, licenciu, podporu a aktualizácie. Ak ide o spotrebiteľský predaj, formulácia „as-is“ sama nevylučuje povinné spotrebiteľské práva; konkrétne podmienky sa posúdia podľa predajného modelu a uplatniteľného práva. FX-003 zostáva otvorený do rozhodnutia vlastníka a potrebnej kontroly podmienok. [EU-DIGITAL]

## Dôkaz pripravenosti
O vydaní rozhodujú [brány kvality](QUALITY_GATES.md), nie existencia tohto textu. Referenčné testy reporting skillu samy nevalidujú upstream forenzný engine. Zmena rozsahu alebo podporovaného prostredia vyžaduje novú kontrolu dotknutých tvrdení.

Podklady: [metodika](METHODOLOGY.md), [zdroje](SOURCES.md), [pripnutý upstream model](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/models/forensic.py), [AI boundary](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/docs/security/AI_EVIDENCE_BOUNDARY.md).

## Overenie z 22. novembra 2026

[Aktuálne výsledky, testované revízie a otvorené podmienky](reviews/FX_AUDIT_2026-11-22.md).
