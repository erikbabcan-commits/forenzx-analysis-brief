# FX-007 — vykonaný bod 4.2 a lokálne spustenie

Dátum: **21. 11. 2026**, Europe/Bratislava. Finálny integračný beh: 01:10:37–01:10:43 CET (UTC časy sú v JSON reporte).

## Verdikt

**Skutočný ForenZX HTTP server: 13/13 kontrol PASS. Skutočný AI klient: spojenie nepreukázané. FX-007 zostáva BLOKOVANÁ, 2/4 kritérií doložené.**

Codex CLI `0.172.0-alpha.2` sa reálne spustil, ale skončil s návratovým kódom 1 pri inicializácii vlastného aplikačného servera: `Read-only file system (os error 30)`. Jeho spravovaný domovský adresár je iba na čítanie. Pozorovanie servera obsahuje **0 MCP požiadaviek z fázy Codex**. Toto zlyhanie preto nie je dôkazom odmietnutia autentifikácie alebo protokolu ForenZX zo strany Codexu.

Oficiálne vysvetlenie v [OpenAI Codex #51293](https://github.com/openai/codex/issues/51293) uvádza, že aj režim `--ephemeral` potrebuje zapisovateľný adresár klienta; samotné presmerovanie SQLite a logov nepresunie všetok stav. V tomto behu sa domovské adresáre, prihlasovacie údaje, pravidlá ani schvaľovanie neobchádzali. Opakovanie je pripravené pre normálnu lokálnu inštaláciu klienta.

## Čo vzniklo

- [Vykonaný prompt 4.2](prompts/FX007_LIVE_CLIENT_PROMPT.md).
- [Kompletný klonovací obal](../scripts/clone-and-test.sh) a [lokálny bootstrap](../scripts/local-bootstrap.sh).
- [Lokálny dashboard s vlastnou D1](LOCAL_SETUP.md), vrátane uloženia, histórie a reštartu.
- [Reprodukovateľný MCP probe](../integration/fx007/README.md), presná konfigurácia klienta a dočasné syntetické poverenia.
- [Strojový integračný report](verification/fx007-live/report.json), [sanitizovaná komunikácia](verification/fx007-live/http-traffic.jsonl), [chyba klienta](verification/fx007-live/codex-stderr.txt), syntetický vstup a načítaný výsledok.

## Východiskový server a dáta

Použitý bol nezmenený checkout `erikbabcan-commits/forenzx-mcp-hub` na commite **`0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`**, čistý pred behom aj po ňom. Spustila sa skutočná FastAPI aplikácia v samostatnom procese cez uvicorn na `127.0.0.1`. Pozorovacia ASGI vrstva iba zaznamenávala vybrané metadata a hash odpovedí; nemenila požiadavky ani odpovede.

Nastavenie `ENVIRONMENT=production` zaplo produkčné kontroly poverení. Vlastná dočasná databáza a adresáre oddelili test od akejkoľvek existujúcej inštancie. Server dostal náhodné kľúče; čítania používali syntetického analytika. Administrátorský kľúč sa nepoužil na prístup k nástrojom. Po behu sa vlastný server ukončil a dočasná databáza aj poverenia odstránili.

Fixture `product/fixtures/completed-hit.json` sa načítala cez skutočný upstream `AnalysisResult` a uložila cez `job_manager`. Vygenerovalo sa nové `job_id`; zvyšok vstupu zostal syntetický. JSON uložený v SQLite sa po HTTP načítaní zhodoval s očakávaným validovaným objektom. **Žiadna forenzná analýza sa nevykonala.** Nástroje start/cancel sa nevolali a nevznikol znalecký ani AI forenzný prehľad.

## Namerané kontroly

| Oblasť | Skutočný výsledok |
| --- | --- |
| Chýbajúce poverenie | HTTP 401, bez výsledku |
| Neplatný JWT | HTTP 401, bez výsledku |
| Expirovaný JWT | HTTP 401, bez výsledku |
| Vývojový bypass v produkčnom režime | HTTP 401, odmietnutý |
| API key a JWT discovery nástrojov | Úspešné; oba reportovacie nástroje prítomné |
| Nepodporovaná verzia v HTTP hlavičke | HTTP 400; samotná forma chyby má samostatný nedostatok nižšie |
| Stav dokončenej úlohy | Zhodné job/case/evidence ID a `COMPLETED` |
| Výsledok dokončenej úlohy | Presná zhoda so seedovaným validovaným objektom |
| Upozornenia a obmedzenia | Obe polia zachované presne |
| Iný používateľ v inej organizácii | Výsledok odmietnutý, JSON-RPC `-32603` |
| Neexistujúca úloha | Odmietnutá, JSON-RPC `-32602` |
| Samostatná kontrola načítaného výsledku FX-005 | `STRUCTURE_VALID`; stále nepovoľuje vydanie prehľadu |

Celkom je v reporte **13 pomenovaných kontrol**. Negatívne testy zodpovedajú skutočným návratovým kontraktom pripnutého servera; počet PASS netvrdí úplnú zhodu so špecifikáciou MCP.

`/health/ready` počas behu vrátil `READY` a jeden povolený pack. Je to pozorovaná pripravenosť konfigurácie; nespúšťala sa analýza ani Docker, preto to nie je dôkaz funkčného forenzného výpočtu.

## Klient a protokol: tri samostatné výsledky

| Cesta | Výsledok a hranica dôkazu |
| --- | --- |
| Priamy HTTP probe | Úspešne použil `2026-07-28` v `_meta` a HTTP hlavičkách; nejde o AI klienta |
| Oficiálny Python MCP SDK `1.29.0` | Skutočne zavolal `initialize`, potom odmietol serverovú verziu `2026-07-28` ako nepodporovanú |
| Codex CLI `0.172.0-alpha.2` | Zlyhal pred prvou MCP požiadavkou na lokálnom úložisku; kompatibilita sa nevyhodnotila |

Nové [MCP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) nevyžaduje starý handshake. Odmietnutie starším SDK preto označuje nekompatibilitu tejto verzie SDK, nie automaticky chybu samotnej absencie handshake.

Konfigurácia Codexu povoľuje iba status/results, token berie z dočasnej premennej a používa jednorazové nastavenie bez zmeny globálnej konfigurácie. [Oficiálna dokumentácia klienta](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) opisuje použité `bearer_token_env_var`, `enabled_tools` a pravidlá jednotlivých nástrojov. Klientská allowlist nie je serverové oprávnenie iba na čítanie; FX-008 zostáva otvorená.

## Samostatné upstream zistenia

Tieto nedostatky sa zistili priamym HTTP behom a porovnaním s primárnou špecifikáciou. **Nie sú príčinou pozorovanej chyby štartu Codexu**, ktorý sa k serveru nedostal.

| ID | Dôkaz | Potrebné pokračovanie |
| --- | --- | --- |
| FX007-UP01 | `server/discover` vrátil HTTP 200 a JSON-RPC `-32601` | Doplniť moderný discovery kontrakt a overiť ho klientom |
| FX007-UP02 | Nepodporovaná verzia vrátila HTTP 400 s poľom `detail` | Doplniť požadovaný JSON-RPC `-32022` a zoznam podporovaných verzií |

[Versioning and Compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) vyžaduje `server/discover` a formát chyby nepodporovanej verzie. [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) určuje zodpovedajúci HTTP stav a metadata. Pôvodný upstream sa počas FX-007 neupravoval; jeho oprava musí mať vlastný diff, testy a nový pripnutý commit. Úplný audit zhody s MCP nebol rozsahom tohto behu.

## Mapovanie na štyri kritériá

| Kritérium FX-007 | Stav |
| --- | --- |
| Klient/verzia, serverový commit a konfigurácia bez tajomstiev | Doložené |
| Autentifikácia, discovery a status/results v skutočnom AI klientovi | Otvorené; priame HTTP kontroly sú samostatné |
| Reálna protokolová cesta zvoleného AI klienta | Otvorené; Codex nezačal MCP komunikáciu |
| Sanitizovaný záznam a osobitná evidencia upstream problémov | Doložené |

Backlog: `blocked`, splnené indexy kritérií `[0, 3]`. Ostatné úlohy sa automaticky neuzatvárajú. FX-005 stále potrebuje kontrolu pred skutočným LLM a zmerané limity; FX-003 naďalej potrebuje rozhodnutie vlastníka o licencii.

## Overenie lokálneho dashboardu

Celý `bash scripts/local-bootstrap.sh --check-only` prešiel s návratovým kódom 0:

| Kontrola | Výsledok |
| --- | --- |
| Stavový model dashboardu | 22/22 |
| Produktové Python testy | 46/46 |
| Syntetická referencia FX-006 | 50/50 |
| Lokálna HTTP brána | 9/9 |
| Cleanup integračného klienta pri SIGINT/SIGTERM | 2/2 |
| TypeScript a build | PASS |
| Lokálny Wrangler/D1 tok | Načítanie 18 úloh, PATCH, export, história a reštart PASS |

Osobitne bol overený obsadený port bez zastavenia cudzieho procesu a ukončenie vlastného procesového stromu launcherom. Lokálny stav sa neprezentuje ako synchronizovaná kópia hostovaného dashboardu.

Samostatne sa vykonal aj čistý `scripts/fx007-mcp-check.sh --with-legacy-sdk`: čerstvý klon upstreamu, nový venv, inštalácia všetkých pripnutých závislostí a 13/13 HTTP kontrol, návratový kód 0. Codex v tomto overení obalu nebol požadovaný. [Súhrn lokálnych kontrol](verification/FX007_LOCAL_CHECKS.json).

V živom súkromnom dashboarde bola uložená FX-007 ako blokovaná s dvoma doloženými kritériami. Porovnanie exportov potvrdilo jedinú zmenu úlohy FX-007, zachovanie všetkých 15 pôvodných udalostí a jednu novú udalosť. Celkový počet hotových úloh zostal 4/18. [Záznam zachovania stavov](verification/FX007_BOARD_UPDATE.json).

## Opakovanie

Lokálny dashboard a offline kontroly:

```bash
bash scripts/local-bootstrap.sh
# Iba kontroly, build a HTTP/D1 smoke:
bash scripts/local-bootstrap.sh --check-only
```

Skutočný server a syntetické výsledky bez AI klienta:

```bash
bash scripts/fx007-mcp-check.sh --with-legacy-sdk
```

Test požadovaný pre uzavretie FX-007 v prihlásenej lokálnej inštalácii Codexu:

```bash
bash scripts/fx007-mcp-check.sh --with-codex --with-legacy-sdk
```

Integračný skript vyžaduje Python 3.11+, vytvorí vlastný venv a pripnutý checkout. Nevyžaduje produkčný ForenZX kľúč. Každý beh dostane nový adresár reportu. Pri `--with-codex` je návratový kód 0 dovolený iba pri doložených volaniach oboch nástrojov zo správnej fázy a presnej zhode očakávaného výstupu. Samotný neúspech voliteľnej starej SDK diagnostiky sa nepovažuje za neúspech HTTP cesty; nie je to náhrada AI klienta.

## Integrita podkladov

- Finálny report SHA-256: `0eaa9476efa44852cb79ed1da630877ee20d6dbbd225caa8e46bd616f6bf630f`.
- Použitý runner SHA-256: `fb248fd13d6d03ebf61657d6e367417769246d75e07f78b000fc7d129097875e`.
- Desať sprievodných súborov má hash v reporte; pred zaradením boli všetky porovnané.
- Kontrola výstupov nenašla serializované JWT ani súkromné kľúče. Poverenia sa nezapisujú do reportov ani Gitu.

Tieto hashe identifikujú naše testovacie súbory. Neoverujú autenticitu forenzných artefaktov ani podpisy serverových výsledkov.

## Záverečné overenie dodania

Súkromný Site bol úspešne nasadený zo zdroja `57a9f8f06d15446b522c3bf85a840ecb58310370`. GitHub commit s implementáciou `e90ea672ffa919fa7d55582530ad5314ee47360e` má presne rovnaký Git strom. Po obnovení živej stránky sa zachovalo všetkých 18 stavov úloh a 16 udalostí histórie.

Čerstvý lokálny Git klon tohto overeného stromu nemal `node_modules` ani managed profil. Celý bootstrap vrátane novej inštalácie, testov, buildu a lokálneho HTTP/D1 toku skončil kódom 0. Priamy klon súkromného GitHubu cez shell tu zastavilo chýbajúce GitHub prihlásenie; prenos a kontrola súkromného repozitára cez pripojené GitHub API prešli. Preto sa netvrdí overené súkromné GitHub prihlásenie v shelli. [Záznam dodania](verification/FX007_DELIVERY.json).
