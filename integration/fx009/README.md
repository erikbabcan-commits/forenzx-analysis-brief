# FX-009 — kontrola prenosu pred modelom

Z koreňa Release Boardu spusti:

```bash
python3 -m unittest discover -s integration/fx009 -p test_boundary.py -v
python3 integration/fx009/provider_probe.py
```

Voľba `--output novy-report.json` vyžaduje nový súbor. Sonda potrebuje Python 3.10+ a dostupný loopback. Otvára vlastné tri dočasné porty. Používa iba syntetickú fixatúru projektu a produktový `validate_bytes`. Nevyžaduje kľúče ani modelový účet.

Prijímajúci klient číta odpoveď testovacieho MCP nástroja cez HTTP. Dva ďalšie HTTP prijímače merajú požiadavky adresované primárnemu a náhradnému modelovému cieľu. Obidva absolvujú kalibráciu ešte pred meraním. Meranie sleduje každú požiadavku POST a každé neprázdne telo vrátane fragmentu bez značky. Overenie celého výstupu zachytí aj stratu posledného varovania či obmedzenia. Komunikačné telá, značka a hlavičky sa porovnávajú v pamäti.

| Pozorovanie na referenčnom adaptéri | Súvisiaca podmienka |
| --- | --- |
| Neschválený provider, zmena modelu alebo endpointu a chýbajúca retencia zastavia čítanie. | F09-04 |
| Neúplná snímka a nesúlad identity skončia bezpečnou diagnostikou pred odovzdaním klientovi. | F09-02 |
| Pri simulovanej 503 sa zistí pokus na primárnom cieli a nula pokusov na náhradnom. | F09-05 |
| Schválený príklad sa zhoduje v celom prenesenom obsahu. | Referenčná kontrola pre F09-07 |

Záznam z 22. novembra obsahuje osem scenárov. Pozitívna kontrola potvrdila, že prijímač zachytáva odoslané dáta. Výsledok patrí tejto syntetickej implementácii. Hlavná konfigurácia Codexu v `integration/fx007/run_probe.py` smeruje na Hub. Produkčné zapojenie adaptéra, modelový kontext, história klienta, tréning a retencia poskytovateľa vyžadujú samostatné dôkazy. `report_generation_allowed=false`.

## Nezávislé meranie odpovede a diagnostiky

Pôvodná kontrola v sonde skladá očakávanú aj skutočnú MCP odpoveď rovnakou funkciou `tool_reply`. Nový test sleduje skutočnú odpoveď na loopback HTTP, kontroluje jej celý obsah podľa osobitne definovaného očakávania a odmieta duplicitné JSON kľúče. Počíta vyvolania čítacej funkcie na hranici adaptéra a požiadavky na cestu `/model`. Príprava syntetickej fixture na začiatku scenára a kalibračné požiadavky sú samostatné operácie.

| Scenár v Codex Work | Čítania výsledku cez adaptér | Primárny POST | Náhradný POST | Odpoveď |
| --- | ---: | ---: | ---: | --- |
| Neznámy provider | 0 | 0 | 0 | Iba chyba `UNAPPROVED_PROFILE` v MCP obálke |
| Schválený profil, neúplný JSON | 1 | 0 | 0 | Iba chyba `INVALID_RESULT` v MCP obálke |
| Schválený syntetický profil | 1 | 1 | 0 | Klient aj primárny prijímač získali presné bajty syntetického výsledku v textovom obsahu |

Pri spustení CLI s `--output` v prázdnom pracovnom adresári mal stdout aj stderr 0 B a vznikol iba požadovaný report. V samostatnej skúške sa report bajtovo zhodoval s verziovaným výsledkom pre všetkých osem scenárov. Šesť regresných testov prešlo. Skúška s úmyselne pridaným krátkym úryvkom zo syntetickej fixture do ďalšieho poľa chybovej odpovede prešla pôvodnými štyrmi testami aj ôsmimi scenármi. Nová kontrola ju zachytila pri oboch chybových odpovediach. Samostatná skúška so zápisom úryvku na stderr zlyhala podľa očakávania.

V tomto repozitári `run_codex` spúšťa externý klient pre FX-007. Konfiguruje jeho priame spojenie na Hub. Samostatná HTTP sonda volá výsledkový nástroj na [riadku 439](https://github.com/erikbabcan-commits/forenzx-analysis-brief/blob/4268ff406c915ea1056ed0437582bd7d55d0a637/integration/fx007/run_probe.py#L439) a potom spúšťa štrukturálnu validáciu. Produktová cesta potrebuje podporovaný reportovací MCP endpoint, ktorý overí profil pred načítaním výsledku z Hubu, a klientsky vstup, ktorý použije túto konfiguráciu aj pri odoslaní modelu. V pripnutom Hube je čítací bod [volanie get_result](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/server.py#L239) a následný [SELECT result_json](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/jobs.py#L188). Produkčný klient, jeho história a telemetria poskytovateľa zostávajú `NOT_VERIFIED`.

[Záznam scenárov](../../docs/verification/FX009_LOOPBACK_2026-11-22.json) · [Mapa toku dát a akceptačné kritériá](../../docs/reviews/FX009_DATA_FLOW_REVIEW.md)

## Samostatný syntetický reportovací klient

Spusti `python3 -m unittest discover -s integration/fx009 -p test_report_client.py -v`.
Testy spúšťajú skutočný vstup `report_client.py` v podprocese a merajú jeho
HTTP požiadavky na troch lokálnych prijímačoch.

`python3 integration/fx009/report_client.py --hub-port PORT --approved-model-port PORT`
očakáva syntetický MCP prijímač na `127.0.0.1` a lokálny modelový prijímač
na samostatnom porte. Profil `synthetic / fixture / memory-only / disabled`
sa overí pred prvou HTTP požiadavkou. Klient požaduje pevne pripnuté demo
`job_id`, validuje identitu a štruktúru odpovede a odošle presné bajty
až po úspešnej validácii. Na výstup vypisuje iba stavový kód.

| Scenár CLI | MCP čítania | Primárny POST | Náhradný POST |
| --- | ---: | ---: | ---: |
| Zmenený provider, model, port, retencia alebo tréning | 0 | 0 | 0 |
| Platný profil a platná fixture | 1 | 1 | 0 |
| Neúplná fixture | 1 | 0 | 0 |
| Primárny prijímač vracia 503 | 1 | 1 | 0 |

Ide o syntetický CLI prototyp. Reálny Codex klient, prihlasovanie k Hubu,
nasadený provider a jeho retencia zostávajú neoverené.
`report_generation_allowed=false`.
