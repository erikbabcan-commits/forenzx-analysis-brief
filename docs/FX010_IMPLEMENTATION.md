# FX-010 · syntetický prehľad z dokončenej analýzy

Z koreňa checkoutu spusti jednu z dvoch ukážok. Na ich spustenie stačí Python 3.10+ na Linuxe so štandardnou knižnicou. Výstup má kódovanie UTF-8.

```bash
python3 product/brief_cli.py completed-hit
python3 product/brief_cli.py completed-no-ioc
```

Parameter `--output novy-subor.md` zapíše celý dokument do nového súboru. Existujúci cieľ vrátane symbolického odkazu vyvolá chybu. Cieľový adresár musí podporovať pevné odkazy. Bez parametra dokument dostaneš na stdout. Chyba vstupu alebo cieľa má kód 2 a stručnú diagnostiku na stderr.

## Čo kontroluje kód

CLI má dve povolené ID. Z pevne určenej fixture načíta ohraničenú bajtovú snímku. Spoločné jadro `render_demo(scenario, snapshot)` vyžaduje nemenné bajty, pripnutý profil, tri očakávané identity a presný SHA-256 z verziovaného manifestu. Používa existujúci validátor. Ten overí štruktúru aj konzistenciu a spočíta hash tých istých bajtov, ktoré jadro následne dekóduje. Manifest je súčasťou dôveryhodného checkoutu. Zmena fixture vyžaduje samostatnú revíziu manifestu a očakávaní.

Nálezy obsahujú ukazovateľ do JSON a hodnotu pôvodnej referencie. Časová os zachováva poradie zdroja aj neznámu časovú zónu. Varovania a obmedzenia sa prenášajú po položkách. Zdrojové hodnoty sú jednoriadkové JSON literály v odsadených blokoch Markdownu. Úvodzovky, nové riadky, riadiace znaky a smerové značky majú vratnú reprezentáciu. Čitateľ tak rozlíši prázdny reťazec, chýbajúcu hodnotu a doslovný text.

Demo obsahuje sekcie pre diagnostiku validátora a AI vysvetlenie. Faktické hodnoty pochádzajú z prijatej syntetickej vzorky. Výstup výslovne uvádza „AI vysvetlenie nebolo vytvorené.“ Lokálny hash patrí bajtom JSON. Deklarované hashe artefaktov a custody sú metadáta zdroja.

## Akceptačné kritériá FX-010

| Kritérium backlogu v poradí 1–6 | Dôkaz pre syntetické demo |
| --- | --- |
| 1. ID a referencia nálezu | Obe ID a ukazovatele v testoch, pôvodná cesta a riadok pri HIT a viditeľná chýbajúca referencia pri NO_KNOWN_IOC. |
| 2. Všetky upozornenia a obmedzenia | Nezávislé hodnoty porovnávané v poradí vrátane duplicít a mutácie posledného varovania. |
| 3. Identita vstupu a verzie | Obe schválené snímky, tri pripnuté ID, profil, verzia balíka, renderer a SHA-256 prijatých bajtov. |
| 4. Chýbajúce údaje | Chýbajúci hash, referencia, názov IOC a zóna zostávajú explicitné. |
| 5. Riadený prenos údajov | Rovnaký renderer pre oba procesy CLI, nezávislé očakávania aj bajtové porovnanie výstupov. |
| 6. Označenie návrhu, rozsah a kontrola | Hlavička, povinné odborné upozornenie, rozsah prijatého JSON a označenie syntetického dema. |

Tabuľka uvádza technické dôkazy pre dve ukážky. Rozhodnutie o stave celej úlohy patrí koordinátorovi po kontrole závislostí a nezávislej reprodukcii. Pre reálne prípady zostáva v platnosti `report_generation_allowed = false`. Tento beh sa týka distribúcie z checkoutu. Samostatné hodnotenie modelu, klienta MCP, podpisov a distribúcie Agensi je otvorené.

[Strojové výsledky](verification/FX010_RESULTS.json) · [Odovzdanie pre Fedoru](handoffs/FX010_CODEX_HANDOFF.md) · [Integračný checklist](reviews/FX010_INTEGRATION_PRECHECK.md)
