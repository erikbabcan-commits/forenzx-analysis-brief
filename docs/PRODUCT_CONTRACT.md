# Produktový kontrakt v0.1 — návrh
Dátum: 20. 11. 2026. Produkt ešte nie je implementovaný ani validovaný.

## Jedna úloha
**ForenZX Analysis Brief pripraví AI asistovaný návrh prehľadu výsledkov existujúcej dokončenej digitálnej forenznej analýzy, s referenciami na zdrojový výstup a zachovanými upozorneniami a obmedzeniami.**

Cieľovým používateľom je analytik alebo oprávnený pracovník, ktorý už prevádzkuje vlastnú funkčnú inštanciu ForenZX. Zákazník kupuje workflow a návody. Samotný balík nezabezpečuje hosting servera ani modelu.

## Vstup a čítanie
- Používateľom zvolený endpoint a poverenie uložené v podporovanom klientovi; žiadne kľúče v balíku.
- Explicitné `job_id` existujúcej úlohy.
- Povolené hlavné nástroje: `forenzx_analysis_status` a `forenzx_analysis_results`.
- Prípadné čítanie health/capabilities slúži iba nastaveniu. Odpoveď READY sama nedokazuje pripravenosť workerov.
- Skill nesmie spustiť ani zrušiť analýzu. Skutočné vynútenie oprávnení sa musí overiť, nestačí text promptu.

## Výstup
Návrh má hlavičku „AI asistovaný návrh — vyžaduje kontrolu analytikom“. Obsahuje identitu úlohy, dostupné case/evidence ID a verzie, zdrojové nálezy, referencie, samostatne označené vysvetlenie AI, všetky pôvodné warnings/limitations a viditeľné chýbajúce údaje. Dostupné pôvodné časy sa zachovajú.

Referencia do prijatého JSON dokladá pôvod tvrdenia vo výstupe ForenZX. Netvrdí, že skill znovu otvoril a preskúmal pôvodný artefakt. Zdrojové nálezy sú tvrdeniami zdrojového systému, ktorých vecnú správnosť samotné preformulovanie neoveruje.

Pri nedokončenom, zlyhanom, zrušenom alebo zablokovanom stave vznikne stavové hlásenie. Pri odmietnutom prístupe alebo neexistujúcej úlohe sa nevytvára falošný findings brief. Detailné správanie spresní FX-005 a referenčná sada.

## Hranice tvrdení
Vydanie v0.1 nezískava dôkazy, nevykonáva novú analýzu zariadenia, neriadi vyšetrovanie a nevydáva znalecký posudok. Nesmie sľubovať identifikáciu páchateľa, úplnú detekciu kompromitácie, certifikáciu ani súdnu prípustnosť.

Prítomnosť hashov, podpisu či chain_of_custody v zdroji je metadata. Ak nebol vykonaný osobitný overovací krok, stav je `NOT_VERIFIED`. Súčasný execution record nepodpisuje nálezy, časovú os, warnings/limitations ani AI prehľad.

## Predajný návrh
- Jeden skill, navrhovaná cena **19 USD jednorazovo**.
- Prvý listing uvedie iba skutočne otestovaného klienta a verziu.
- Syntetické demo ukáže konkrétny vstup → výstup.
- Serverová licencia a podmienky plateného skillu sú samostatné otvorené rozhodnutia.
- Vlastný platobný systém, prenájom MCP a ďalšie balíky sú neskoršie možnosti; nepatria do v0.1.

## Dôkaz pripravenosti
O vydaní rozhodujú [brány kvality](QUALITY_GATES.md), nie existencia tohto textu. Referenčné testy reporting skillu samy nevalidujú upstream forenzný engine. Zmena rozsahu alebo podporovaného prostredia vyžaduje novú kontrolu dotknutých tvrdení.

Podklady: [metodika](METHODOLOGY.md), [zdroje](SOURCES.md), [pripnutý upstream model](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/models/forensic.py), [AI boundary](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/docs/security/AI_EVIDENCE_BOUNDARY.md).

