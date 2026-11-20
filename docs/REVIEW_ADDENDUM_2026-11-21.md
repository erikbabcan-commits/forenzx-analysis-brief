# Doplnenie požiadaviek po kontrole šiestich pripomienok

Dátum: 21. 11. 2026 (Europe/Bratislava).

## Rozhodnutie a rozsah

Prijímame všetkých šesť tém ako spresnenie požiadaviek na ForenZX Analysis Brief v0.1. Zachovávame jeden účel produktu, navrhovanú cenu 19 USD a 18 existujúcich úloh. Najväčšie nové kontrolné body sú veľkosť/úplnosť vstupu a kompatibilita schémy. Tok dát, syntetické príklady, označenie návrhu a evidencia modelu už boli v backlogu; teraz dostávajú presnejšie kritériá.

Tento dokument zaznamenáva rozhodnutie o požiadavkách. **Nevyhlasuje úspešnú implementáciu ani splnenie úloh.** Každá kontrola musí mať vlastný výsledok a záznam. Stav dashboardu, lokálneho validátora, reálneho MCP pripojenia, správania LLM a odborného review sa eviduje oddelene.

## Mapa požiadaviek do existujúceho backlogu

| Téma | Úlohy | Prijaté doplnenie | Dôkaz pred splnením |
| --- | --- | --- | --- |
| Citlivé údaje | FX-009, FX-015, FX-017 | Oznámenie a kontrola konfigurácie pred načítaním reálnych výsledkov; model/endpoint, história, logy, telemetria, retencia a tréningové nastavenie; bez automatického provider failover. | Záznam celého toku so syntetickými dátami a rozlíšením technického vynútenia od pokynov. |
| Veľké vstupy | FX-005, FX-006, FX-014 | Oddelené limity parsera a kontextu LLM; odmietnutie neúplného/nadlimitného vstupu; kontrola dokončenia generovania. | Hraničné vstupy a upozornenie na konci veľkého JSON; žiadne úspešné spracovanie mimo limitov; X/Y iba s podkladom. |
| Schéma výsledku | FX-005, FX-006, FX-007 | Explicitne podporovaný dátový profil a validácia skutočného obsahu; odlíšené verzie MCP, servera, schémy, packu a skillu. | Pripnutý zdroj, pravidlá kompatibility a testy neznámej verzie, chýbajúcich polí, typov a identity. |
| Podmienky a upozornenie | FX-003, FX-010, FX-017 | Licencia a obchodné podmienky oddelené od označenia AI návrhu; rozsah dodávky, podpory a aktualizácií. | Rozhodnutie vlastníka a primeraná kontrola podmienok; pravdivá pätička a predajný opis. |
| Jednoduchá ukážka | FX-006, FX-015, FX-017 | Dva od začiatku syntetické príklady a samostatná cesta bez vlastného ForenZX servera. | Čistý beh cez spôsob doručenia Agensi, vzorový výstup a odmerané predpoklady. |
| Závislosť od modelu | FX-014, FX-016, FX-017 | Jedna primárna konfigurácia a lacnejšia porovnávacia konfigurácia, rovnaké kritériá, presné verzie a viditeľné limity podpory. | Opakované výsledky a zlyhania; matica podpory; ľudské odborné review ostáva samostatné. |

## Spresnenia pôvodných návrhov

### ZDR a lokálny model

ZDR nie je totožné s vylúčením tréningu a nie je osvedčením právneho súladu. Konkrétne pokrytie služby a nastavenie sa overí pred použitím. Zákazník môže mať lokálny ForenZX a súčasne cloudový model alebo históriu klienta. Všetky relevantné časti musia byť viditeľné v návode. Prípadná podmienka povinného ZDR je rozhodnutím konkrétneho nasadenia, nie automatickou všeobecnou požiadavkou GDPR. [MISTRAL-ZDR, OLLAMA-LOCAL, GDPR]

### Neúplný prehľad a pôvodná analýza

Prekročenie kontextu nemusí vždy znamenať tiché orezanie; niektoré API vracajú chybu. Orezanie klientom a neúplnú odpoveď treba otestovať na celom toku. Neúspech prehľadu nesmie zmeniť pôvodný stav analýzy. Pri neznámom rozsahu sa nesmie vymyslieť počet nespracovaných nálezov. Počet záznamov sám nedokladá zachovanie varovaní, obmedzení a podkladov. [MISTRAL-LIMITS]

### Existujúca schéma

V preskúmanom `AnalysisResult` chýbajú `schema_version` a `forenzx_version`. Tieto názvy predstavujú návrh budúceho kontraktu, nie dnešné polia upstreamu. Dovtedy možno podporovať výslovne pomenovaný profil pripnutej baseline. Jeho identitu dodá overená konfigurácia/adaptér; nesmie sa odhadovať z približne podobného JSON ani zamieňať s `pack_version`. [CODE-MODEL, MCP-TOOLS]

### Upozornenie a zmluva

Krátke označenie AI návrhu vyžaduje odbornú kontrolu a opisuje limity. Veta „as-is“ ani priradenie kontroly analytikovi automaticky nevylučuje zodpovednosť dodávateľa alebo povinné práva spotrebiteľa. FX-003 musí riešiť skutočný predajný model a príslušné podmienky. [EU-DIGITAL]

### Ukážka a offline tvrdenie

Ukážka bez vlastného ForenZX servera zostáva užitočná, ale Agensi doručuje texty cez službu a klient môže používať cloudový model. Označenie „úplne offline“ a časový sľub „do dvoch minút“ vyžadujú samostatné meranie pri deklarovaných predpokladoch. Agensi skripty sú samostatné dočasné súbory; ukážka a validátor nesmú spoliehať na neoverené susedné súbory balíka. [AGENSI-LOAD, AGENSI-PACK]

### Overené konfigurácie

Silný model nie je zárukou správnych tvrdení ani odolnosti proti vloženým pokynom. Zverejní sa konkrétna testovaná konfigurácia a jej hranice, nie univerzálne poradie „model X a všetko vyššie“. Zlyhanie porovnávacieho modelu sa zaznamená a obmedzí deklarovanú podporu. [NIST-AI]

## Technická hranica implementácie

Schému, identitu, limity, úplnosť a oprávnenia treba kontrolovať kódom na správnom mieste pred odovzdaním dát modelu. `SKILL.md` môže opísať postup, ale sám nevynúti sieťové obmedzenia ani neobnoví odrezané dáta. Výsledok lokálneho validátora bude dôkazom iba jeho konkrétnych kontrol na prijatom vstupe. Neuzavrie overenie úplnosti pôvodného exportu, kontextu klienta, podpisu ani kvality AI interpretácie. [MCP-TOOLS]

## Zachovanie už vykonanej práce

Pôvodný baseline, forenzné definície a dôkazy prípravných úloh zostávajú zachované. Nové podmienky sa nesmú označiť za splnené len preto, že boli doplnené do textu. Zmena významu kritéria vyžaduje nové posúdenie; uložené dôkazy a história sa pri nasadení nesmú potichu zmazať alebo preniesť na nový význam.

Ďalší technický krok zostáva FX-005: explicitný vstupný kontrakt a deterministická kontrola. Nadväzuje referenčná sada, reálny klient, šablóna a hodnotenie, balík, odborné review a predaj. Licenčné rozhodnutie sa rieši súbežne.

Podklady: [register zdrojov](SOURCES.md), [produktový kontrakt](PRODUCT_CONTRACT.md), [brány kvality](QUALITY_GATES.md), [metodika](METHODOLOGY.md).
