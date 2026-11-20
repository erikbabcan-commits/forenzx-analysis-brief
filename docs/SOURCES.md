# Register odborných zdrojov

Pôvodné overenie odborných zdrojov: 20. november 2026. Revízia požiadaviek a doplnenie technických/právnych podkladov: 21. november 2026 (Europe/Bratislava). Ide o primárne zdroje pre návrh, nie o vyhlásenie zhody, certifikáciu alebo odporúčanie produktu ich autormi. Texty noriem a príručiek sa do predajného balíka nekopírujú. Strojovo čitateľné registre sú v `data/sources.json` a `data/engineering-sources.json`.

| ID | Zdroj a verzia | Použitý význam a hranice |
| --- | --- | --- |
| APZ | [Akadémia Policajného zboru: pedagogická činnosť](https://www.akademiapz.sk/sk/akademia/katedry/katedra-kriminalistiky-forenznych-vied/pedagogicka-cinnost) | Obsah výučby kriminalistickej taktiky. Sylabus nepoužívame ako doslovnú všeobecnú definíciu odboru. Dátum vydania stránky nie je uvedený. |
| NIST-86 | [NIST SP 800-86, august 2006](https://csrc.nist.gov/pubs/sp/800/86/final) | Rozlíšenie zberu, skúmania, analýzy a vykazovania výsledkov; integrita. Metodika incident response z IT perspektívy, nie úplný policajný alebo právny postup. |
| NIST-CUSTODY | [NIST CSRC: Chain of custody](https://csrc.nist.gov/glossary/term/chain_of_CUSTODY) | Význam dokumentovanej histórie manipulácie. Glosár odkazuje na SP 800-72 a SP 800-101 Rev. 1; jeho definícia nepreukazuje úplnosť našich záznamov. |
| SWGDE-REPORT | [SWGDE 18-Q-002, v1.0, 20. 11. 2018](https://www.swgde.org/documents/published-complete-listing/18-q-002-swgde-requirements-for-report-writing-in-digital-and-multimedia-forensics/) | Minimálne prvky správy, podklady názorov, autorizácia a opravy. Tool report môže tvoriť podklad alebo prílohu úplnej správy. |
| SWGDE-TEST | [SWGDE 18-Q-001-2.1, 7. 3. 2024](https://www.swgde.org/documents/published-complete-listing/18-q-001-minimum-requirements-for-testing-tools-used-in-digital-and-multimedia-forensics/) | Známe testovacie dáta a kontrola agregácie/súhrnov, najmä §5.3.3. §3 vylučuje softvér na interpretáciu; nejde o úplnú metodiku evaluácie LLM. |
| ENFSI | [ENFSI-BPM-FIT-01, v01, november 2015](https://enfsi.eu/wp-content/uploads/2016/09/enfsi-bpm-fit-01_1.pdf) | Neistoty, podklady, odborné review a rozlíšenie faktického vykazovania od hodnotiaceho názoru, najmä §6 a §13. Citujeme konkrétnu verziu, nie záruku splnenia všetkých dnešných požiadaviek. |
| ISO-27041 | [ISO/IEC 27041:2015](https://www.iso.org/standard/44405.html) | Vhodnosť metód pre účel, požiadavky a dôkazy. Prečítaný bol verejný oficiálny abstrakt, nie celý platený text; audit zhody nebol vykonaný. |
| NIST-AI | [NIST AI 600-1: Generative Artificial Intelligence Profile, 2024](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) | Použité verejne dostupné pasáže o konfabuláciách, automatizačnom skreslení a integrite informácií. Nie je to úplné posúdenie všetkých opatrení rámca. |
| NIST-TERMS | [NIST TN 1297, Appendix D1](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-d1-terminology) | Opakovateľnosť pri rovnakých a reprodukovateľnosť pri určených zmenených podmienkach. Terminológia meraní z vydania 1994; na stabilitu faktov v AI výstupe ju adaptujeme. |
| MVT | [Amnesty International Security Lab: technický návod MVT/AndroidQF, december 2024](https://securitylab.amnesty.org/latest/2024/12/tech-guide-detecting-novispy-spyware-with-androidqf-and-the-mobile-verification-toolkit-mvt/) | Výstupy MVT majú pred záverom posúdiť odborníci. Konkrétny návod k NoviSpy nedokladá úplné pokrytie všetkého škodlivého softvéru. |

## Technické a právne doplnenia z 21. 11. 2026

Zdrojové stránky boli použité pri rešerši pred touto revíziou. Ich opis nezastupuje kontrolu skutočného nastavenia zákazníka, runtime test ani právne posúdenie konkrétnej zmluvy.

| ID | Primárny zdroj | Použitý význam a hranice |
| --- | --- | --- |
| MISTRAL-ZDR | [Mistral: Zero data retention](https://docs.mistral.ai/admin/monitor-comply/zero-data-retention) | Podporované stateless API, schválenie/aktivácia ZDR, vylúčené produkty a rozdiel od training opt-out. Nevytvára tvrdenie, že zákazník ZDR má alebo že spĺňa právne požiadavky. |
| MISTRAL-LIMITS | [Mistral: Known limitations](https://docs.mistral.ai/resources/known-limitations) | Kontext zahŕňa vstup a výstup; nadlimitný request má chybu 400. Klientské orezanie a celkový tok treba testovať osobitne; limity jedného modelu sa nezovšeobecňujú. |
| OLLAMA-LOCAL | [Ollama: Local FAQ](https://docs.ollama.com/faq) | Konfigurácia kontextu a vypnutie cloudových funkcií. Samotná lokálna inferencia nevylučuje iné cloudové časti workflowu. |
| MCP-TOOLS | [MCP Tools, špecifikácia 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | `outputSchema`, `structuredContent` a odporúčaná validácia klientom pred odovzdaním modelu. Odkaz na špecifikáciu nepotvrdzuje implementáciu v našom klientovi. |
| AGENSI-LOAD | [Agensi: How agents load skills](https://www.agensi.io/docs/how-agents-load-skills) | Doručovanie cez `get_skill`, načítanie aktuálnej živej verzie a dočasné spúšťanie skriptov. Rozlíšenie ukážky bez vlastného servera od úplne offline použitia. |
| GDPR | [Nariadenie (EÚ) 2016/679, oficiálny text](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) | Najmä čl. 2 (rozsah), 5–6 (zásady a zákonnosť), 28 (sprostredkovateľ), 32 (ochrana) a 44 (prenosy). Posúdenie závisí od skutočných rolí a účelu; pri príslušných orgánoch v trestnom vyšetrovaní môže platiť osobitný režim. |
| EU-DIGITAL | [Smernica (EÚ) 2019/770, oficiálny text](https://eur-lex.europa.eu/eli/dir/2019/770/oj/eng) | Čl. 22 o povinnej povahe ochrany spotrebiteľa. Konkrétne podmienky predaja sa posudzujú podľa vykonávacieho práva a modelu dodávky; nejde o hotovú EULA ani všeobecný právny audit. |

Zdrojový baseline je naďalej `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`. `CODE-MODEL` odkazuje na [pripnutý dátový model](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/models/forensic.py), kde `AnalysisResult` nemá `schema_version` ani `forenzx_version`; `pack_version` sa nesmie prezentovať ako verzia výsledkovej schémy. Ostatné technické podklady vrátane `AGENSI-PACK`, `MCP-2026` a `MCP-SDK` sú v strojovo čitateľnom technickom registri.

## Používanie zdrojov

Pri aktualizácii zaznamenať názov, verziu alebo dátum, použitú časť a dopad na naše požiadavky. Pri SWGDE ponechať presné identifikátory verzií a nepripisovať organizácii podporu produktu. Na otvorené odborné otázky vytvoriť úlohu s konkrétnym výsledkom; odkaz na autoritu sám neuzatvára test ani review.
