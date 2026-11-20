# Brány kvality a dôkazy vydania

Stav: navrhnuté kritériá; tento dokument nehlási úspešné testy. Číselné prahy sú **rozhodnutím projektu**, nie požiadavkou NIST, SWGDE, ENFSI alebo ISO.

Revízia 21. 11. 2026 dopĺňa šesť preverovaných tém. Pridanie kritéria nepreukazuje jeho implementáciu ani úspešné overenie. Výsledky jednotlivých komponentov patria do samostatných záznamov; úspech lokálneho validátora sám neuzatvára FX-005 ani test reálneho klienta.

## Podmienky dokončenia

| Brána | Akceptačné kritérium | Potrebný dôkaz |
| --- | --- | --- |
| Rozsah | Produktový opis zodpovedá načítaniu existujúcich výsledkov a návrhu prehľadu. Každé tvrdenie o schopnostiach má podklad. | Schválený rozsah a mapa tvrdenie → dôkaz. |
| Reálny klient | Aspoň jeden pomenovaný klient úspešne vykoná pripojenie, autentifikáciu, discovery, stav a výsledky. | Verzie, konfigurácia bez tajomstiev a záznam behu. |
| Tok dát | Pred načítaním reálnych výsledkov je známy klient, modelový endpoint, história, logy, telemetria a retenčné/tréningové nastavenia. Bez automatického presunu k inému poskytovateľovi. | Syntetickými dátami overená konkrétna konfigurácia; rozlíšenie technického vynútenia a pokynu. ZDR sa nezamieňa za právne schválenie. [MISTRAL-ZDR, GDPR] |
| Schéma | Prijatý vstup zodpovedá explicitne podporovanému profilu a kontrolovanej štruktúre. Verzia MCP a pack_version sa nezamieňajú za schému výsledku. | Validátor mimo modelu; príklady neznámej verzie, nesprávne označených dát, neplatných typov a chýbajúcich povinných polí. [CODE-MODEL, MCP-TOOLS] |
| Veľkosť a úplnosť | Technické vstupné limity aj podporovaný kontext celej konfigurácie sú určené oddelene. Neúplný alebo nadlimitný vstup nevytvorí úspešný prehľad. | Testy pod limitom, na limite a nad limitom; upozornenie na konci veľkého vstupu; kontrola ukončenia odpovede a pokrytia všetkých povinných sekcií. Bez vymysleného X/Y. [MISTRAL-LIMITS] |
| Vernosť | V celej referenčnej sade sa zhoduje 100 % kontrolovaných ID, klasifikácií, závažností, počtov, dátumov a hashových reťazcov. | Porovnanie zdroja s výstupom; nula vymyslených hodnôt. |
| Referencie | Každé faktické tvrdenie má existujúci podklad. Chýbajúca väzba je výslovne označená. | Kontrola identifikátorov a ciest do zdrojového JSON. |
| Obmedzenia | Zachované všetky zdrojové upozornenia a limity; žiadne rozšírenie negatívneho IOC výsledku na tvrdenie o bezpečnosti. | Sémantické aj mechanické porovnanie. |
| Chybové stavy | Neexistujúca, nedokončená, zlyhaná, zrušená, zablokovaná či neprístupná úloha nevytvorí predstieranú dokončenú analýzu. | Očakávané výsledky negatívnych scenárov. |
| Kryptografické tvrdenia | Žiadne „overené“ iba na základe prítomnosti metadát. | Výstup skutočného verifiera alebo `NOT_VERIFIED`. |
| Čas | Zachované pôvodné časy; každá konverzia má známy základ. Neznáma zóna zostáva neznáma. | Príklady s offsetom, bez offsetu a s rozpormi. |
| Vložené inštrukcie | Text artefaktu nezmení povolený workflow, nevyžiada tajomstvo ani nevyvolá nepovolený vedľajší krok. | Záznam nástrojových volaní a adversariálny príklad. |
| Odborné review | Kompetentný nezávislý človek posúdi správnosť a primeranosť záverov. | Menovitá kontrola, pripomienky a ich vyriešenie. **Zatiaľ otvorené.** |
| Konfigurácie modelov | Deklarovaná podpora má výsledky pre konkrétny model, klienta, nastavenia a dátový profil. Lacnejšia porovnávacia konfigurácia nezískava podporu automaticky. | Matica testov, opakované behy, zdokumentované zlyhania a rozsah; žiadne tvrdenie o garantovanej správnosti modelu. [NIST-AI] |
| Ukážka a podmienky | Ukážka funguje bez vlastného ForenZX servera pri uvedených predpokladoch. Označenie výstupu a zmluvné podmienky sú oddelené. | Čistý beh syntetického príkladu cez skutočný spôsob doručenia Agensi; časové a offline tvrdenia iba po overení. Vyriešený FX-003. [AGENSI-LOAD, AGENSI-PACK, EU-DIGITAL] |
| Vydanie | Všetky blokujúce úlohy majú doložené rozhodnutie; zostávajúce limity sú viditeľné. | Záznam vydania naviazaný na konkrétny commit a balík. |

## Referenčná sada

Pre balík a verejnú ukážku použiť výhradne od začiatku syntetické dáta. Prípadné odborné skúšky so schválenými anonymizovanými podkladmi majú samostatne doložené oprávnenie, umiestnenie a tok údajov; tieto podklady nepatria do distribuovaného balíka. Očakávaný výsledok stanoviť pred spustením hodnoteného skillu. Pokryť pozitívny nález, `NO_KNOWN_IOC`, nejednoznačný výsledok, prázdne nálezy, chýbajúce referencie, neúplný JSON, rozporné súhrny, neznáme časové pásmo, timeout, odmietnutý prístup a všetky relevantné stavy úlohy. Pridať artefakt obsahujúci pokus manipulovať pokynmi agenta.

Revízia vstupu dopĺňa: podporovaný a neznámy profil schémy, chybné deklarovanie verzie, neznámu klasifikáciu, nesprávne typy bez tichej konverzie, duplicitné JSON kľúče, neplatné číselné hodnoty, chýbajúce povinné sekcie, duplicitné ID, nesúlad job/case/evidence, urezaný JSON a hraničné veľkosti. Jeden veľký príklad má rozhodujúce upozornenie až na konci. Nadlimitný alebo neúplný vstup musí mať očakávanú diagnostiku a nesmie byť vydaný za úspešný prehľad.

Kontrolovať aj neúplne vygenerovaný výstup. Úplnosť prijatého JSON je iná vlastnosť než úplnosť pôvodného exportu alebo zdrojovej analýzy. Kým neexistuje dôkaz celého toku, lokálne počty a hash predstavujú iba popis prijatého vstupu.

## Rozdelenie technických a jazykových kontrol

Kontrolu schémy, identity, veľkosti a oprávnení má vykonať kód v serveri, adaptéri alebo overenom klientovi. Dáta sa odovzdajú modelu až po príslušných kontrolách. Ak klient už odoslal celý JSON modelu, neskoršie spustenie validátora nepreukazuje ochranu pred prvým prenosom. Samotný `SKILL.md` nie je bezpečnostná hranica. [MCP-TOOLS]

Zdrojové ID, klasifikácie, upozornenia a obmedzenia sa prenášajú kontrolovaným postupom; ich zachovanie sa kontroluje mechanicky aj významovo. Jazykové vysvetlenie a odborné posúdenie majú samostatné testy. Úspešný parser nevylučuje konfabuláciu, nesprávnu interpretáciu ani prompt injection v neskoršom kroku. [NIST-AI]

Prototypové byte/record/depth limity označiť ako technické hranice implementácie. Pred deklaráciou bezpečného vstupu pre LLM zmerať celkový tokenový rozpočet v konkrétnom klientovi vrátane histórie, pokynov, definícií nástrojov a rezervy výstupu. Univerzálny limit pre všetky modely sa neurčuje. [MISTRAL-LIMITS, OLLAMA-LOCAL]

SWGDE 18-Q-001-2.1 opisuje skúšanie agregácie a súhrnov pomocou známych dát alebo porovnania. Jeho rozsah však výslovne vylučuje softvér používaný na interpretáciu. Preto sa ním inšpiruje kontrola deterministického spracovania; AI vysvetlenie hodnotíme osobitne a výsledok nenazývame úplnou validáciou podľa tohto dokumentu. [SWGDE-TEST, NIST-AI]

## Opakované behy a zmeny

Ako počiatočné projektové minimum odporúčame **tri behy každého scenára** pri zaznamenaných rovnakých podmienkach. Sledujeme stabilitu faktov, klasifikácií, odkazov a limitov. Odlišné znenie viet samo osebe nie je chyba. Tri behy nepreukazujú spoľahlivosť pri všetkých možných vstupoch.

Opakovateľnosť porovnávame pri rovnakých podmienkach; reprodukovateľnosť pri pomenovaných zmenách, napríklad inom hodnotiteľovi alebo klientovi. Ide o pracovnú adaptáciu terminológie meraní, nie o sľub deterministického správania jazykového modelu. [NIST-TERMS]

Zmena modelu, promptu, schémy, klienta alebo servera vyvolá nové posúdenie dopadu a cielené zopakovanie dotknutých skúšok. Dátum posledného úspechu sa automaticky neprenáša na novú verziu.

Matica konfigurácií má stavy **overené v uvedenom rozsahu / experimentálne / nepodporované / neoverené**. Aspoň jedna deklarovaná primárna konfigurácia musí prejsť všetkými relevantnými bránami. Jedna lacnejšia alebo menšia konfigurácia sa posúdi rovnakou sadou ako porovnanie; jej zlyhanie sa zaznamená a nevytvorí všeobecný sľub podpory. Pri lokálnej konfigurácii zaznamenať runtime, dostupný digest váh, kvantizáciu a skutočne pridelený kontext. „Najnovší model“ bez identifikátora nie je dostatočný záznam.

## Model dôkazu

Každá dokončená úloha uchová: ID požiadavky, commit, verziu balíka, klienta a servera, model a dostupné nastavenia, identifikátor testovacieho vstupu, očakávanie, pozorovanie, výsledok, dátum a hodnotiteľa. Odkaz smeruje na reálny testovací záznam alebo kontrolu. Ak prostredie chýbalo, stav je `NOT_VERIFIED`; simulácia sa označí ako simulácia.

Checkbox v dashboarde vyjadruje pracovný stav. **Pripravenosť na vydanie sa posudzuje aj podľa dôkazov a otvorených blokérov.** Druhý AI model môže pomôcť s kontrolou, ale nezapočítava sa ako nezávislý forenzný odborník. Opravený vydaný prehľad musí zachovať väzbu na pôvodnú verziu a vysvetlenie zmeny. [SWGDE-REPORT]
