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

[Záznam scenárov](../../docs/verification/FX009_LOOPBACK_2026-11-22.json) · [Mapa toku dát a akceptačné kritériá](../../docs/reviews/FX009_DATA_FLOW_REVIEW.md)
