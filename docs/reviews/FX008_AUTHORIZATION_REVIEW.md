# FX-008 — oprávnenia reportovacieho toku

**Výsledok: report-only brána FAIL; FX-008 zostáva otvorená.** Skutočný Hub v pripnutej verzii vynucuje prístup k jobu/case, ale neodlišuje čítanie výsledkov od zrušenia jobu a nemá implementovaný reportovací scope. Klientská allowlist ani názov roly v JWT túto hranicu nevytvárajú.

## Presný predmet a vykonané overenie

- Upstream: `erikbabcan-commits/forenzx-mcp-hub`, commit `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`; checkout pred aj po behu čistý a nezmenený.
- Koordinačný základ: `fb6b03f57297358381bf7b91ee7c811fc08146c6`. Pracovná vetva: `chore/fx008-fx009-coordination`; tento dokument sám nepreukazuje commitovanie ani push.
- Skutočný beh: `2026-11-21T09:39:26.877058+00:00` až `2026-11-21T09:39:27.814021+00:00`.
- CPython `3.12.14`, HTTPX `0.28.1`, FastAPI `0.162.7`, Starlette `1.10.0`, Pydantic `2.14.4`, pydantic-settings `2.16.3`, PyJWT `2.15.1`, cryptography `46.0.7`.
- **53/53 pozorovaní súhlasilo s očakávaným baseline. Produktová report-only politika má 13 doložených protikladov:** deväť skutočných cancel zmien a štyri dosiahnutia kontrolného bodu za start ACL.
- Zdrojové a skriptové SHA-256, konkrétne kontroly, pozitívne/negatívne výsledky a izolácia: [FX008_AUTHORIZATION_RESULTS.json](../verification/FX008_AUTHORIZATION_RESULTS.json).

Príkaz vykonaný z koordinačného checkoutu:

```bash
/workspace/scratch/203c591095ce/fx007-venv/bin/python -B \
  integration/fx008/run_authorization_probe.py \
  --upstream /workspace/scratch/203c591095ce/fx007-upstream \
  --output docs/verification/FX008_AUTHORIZATION_RESULTS.json
```

Návratový kód bol `0`, čo pri tomto nástroji znamená úspešnú **charakterizáciu baseline**, nie schválenie reportovacieho produktu. Pri opakovaní treba zvoliť nový výstupný súbor. Podrobnosti izolácie obsahuje [README probe](../../integration/fx008/README.md).

## Pozorované správanie

Všetky požiadavky používali neadmin identity. Pri `start` sa test zastavil sentinelom na prvom volaní `pack_registry.get_pack` za case autorizáciou; nebol vytvorený job ani worker. Pri `cancel` išlo o skutočnú zmenu iba syntetického čakajúceho jobu.

| Identita / cesta | Status a výsledok | Cancel | Interpretácia |
| --- | --- | --- | --- |
| Vlastník, správna organizácia, analyst JWT | Povolené, identity a výsledok súhlasia | `CANCELLED` | Poverenie vie čítať aj meniť stav. |
| Iný používateľ v rovnakej organizácii | Povolené | `CANCELLED` | Organizácia je samostatná povoľujúca vetva. Individuálny case grant sa nevyžaduje. |
| Iný používateľ, iná organizácia, bez dostupného case | Odmietnuté, bez výsledku | Odmietnuté, DB aj `QUEUED` zachované | Otestovaná negatívna hranica funguje. |
| Rovnaké owner `user_id`, iná organizácia | Povolené | `CANCELLED` | Vlastník sa porovnáva bez súčasnej zhody organizácie. |
| Iný vlastník aj organizácia jobu; dostupný case | Povolené | `CANCELLED` | Prístup k case je ďalšia OR vetva. Scenár zámerne izoluje rozdiel org case/job. |
| JWT `roles=[]`, správna organizácia | Povolené | `CANCELLED` | Členstvo roly nie je podmienkou tejto ACL vetvy. |
| JWT `roles=["reporter"]`, správna organizácia | Povolené | `CANCELLED` | Hub túto rolu neimplementuje; jej názov sám nevytvára report-only oprávnenie. |
| API key A vlastní job | Povolené | `CANCELLED` | `X-API-Key` funguje; admin sa nevyžaduje. |
| Iný API key B číta job A | Povolené | `CANCELLED` | `Authorization: APIKey ...` funguje; oba kľúče mapuje Hub do `default_org`. |

`owner`, `empty_roles` a `reporter_label` prešli start ACL po sentinel na `/mcp`. `reporter_label` sa tam dostal aj cez `mcp_start_analysis` na `/mcp/jsonrpc`. Cudzia organizácia bez grantu bola pri oboch cestách odmietnutá **pred sentinelom**. Nie je tým otestované reálne spustenie packu ani výsledok enginu.

Legacy `mcp_get_results` a `mcp_get_job_status` na `/mcp/jsonrpc` vrátili správne identity vlastníkovi a odmietli cudzieho používateľa. Canonical cancel na legacy route zostáva povolený dostupnej `reporter_label` identite. Pri SSE sa dokončený stav vlastníkovi sprístupnil a cudzí používateľ dostal HTTP 403 pred otvorením streamu.

Chýbajúce poverenie, nesprávny API kľúč, expirovaný JWT, development bypass v produkcii a API kľúč poslaný ako Bearer skončili HTTP 401. Nesprávny `X-API-Key` mal prednosť pred inak platným Bearer JWT a požiadavku odmietol.

## Zdrojový dôkaz a hranice tvrdení

Všetky odkazy v tejto sekcii sú na **pripnutý upstream commit**, nie na pohyblivú vetvu `main`.

### 1. Chýba centrálne rozlíšenie čítania a zmeny

[`core/server.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/server.py), `MCPServer.handle_tool_call`: alias sa normalizuje na riadku 113. Start kontroluje case ACL na riadku 151. Status, cancel a results zdieľajú vetvu 221–241 a rovnaký `enforce_job_access` na 228; cancel potom volá `cancel_job` na 236–237. Samostatný reporting scope sa tu nekontroluje. `list_tools_schema` (43–110) a `tools/list` (280–281) nefiltrujú nástroje podľa identity.

[`core/jobs.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/jobs.py), `cancel_job` (205–213) vykonáva zmenu stavu. Runtime kontroloval skutočné `QUEUED → CANCELLED`, nie iba úspešný status HTTP.

**Dopad:** súčasné analytické poverenie nemožno označiť za serverom vynútené read-only poverenie. Tieto výsledky samy netvrdia chybu v úmyselne širokej analyst politike Hubu; dokazujú nesplnenú užšiu požiadavku produktu.

### 2. ACL je zložená z alternatívnych povolení

[`core/acl.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/acl.py), `can_access_case` (76–100): admin, vlastník alebo rovnaká organizácia. `can_access_job` (102–130): admin, vlastník, rovnaká organizácia alebo dostupný case. Owner zhoda na 115–116 nevyžaduje zhodu organizácie; org vetva je 119–120; case fallback 123–125. Neznámy job/case neadminovi provider odmieta.

**Dopad:** jedna úspešná cross-org negatívna skúška nestačí na tvrdenie striktnej izolácie každého case alebo pri zmene aktuálnej organizácie vlastníka. Produkt musí konkrétne určiť, či povoľuje celú organizáciu, vybrané prípady alebo vybrané joby; existujúce širšie povolenie sa nesmie zakryť iba promptom.

### 3. API kľúče a JWT majú odlišnú identitu, nie odlišný reportovací rozsah

[`core/main.py`](https://github.com/erikbabcan-commits/forenzx-mcp-hub/blob/0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f/core/main.py), `AuthConfig.api_key_user` (117–126) dáva každému bežnému API kľúču odvodené `user_id`, rolu analyst a `organization="default_org"`. `jwt_user` (129–151) overuje podpis HS256 a expiráciu, vyžaduje subject/user_id a prijme aj prázdny zoznam rolí. `get_current_user` (161–183) odlišuje `X-API-Key`/`APIKey` od `Bearer` JWT; `get_admin` (186–189) vynucuje admin rolu pre administratívne endpointy.

**Dopad:** návod má presne pomenovať header a typ poverenia. Výmena za iný obyčajný API kľúč sama neizoluje organizáciu ani prípad. Tento audit neposudzoval politiku JWT issuer/audience ani životný cyklus produkčných poverení.

### 4. Alternatívne cesty nezahadzujú aktuálnu ACL, ale musia zdediť budúci scope

V tom istom `core/main.py` `/mcp` (227–248) aj `/mcp/jsonrpc` (251–258) používajú skutočnú autentifikáciu a spoločný dispatcher. SSE (261–279) získa serverový JobSpec a vykoná `enforce_job_access` pred streamom. Preto zavedenie novej kontroly iba v jednom HTTP route nechá druhú cestu otvorenú. Kontrola nástrojových oprávnení patrí po normalizácii aliasov do spoločnej hranice.

`run_cli_stdio` (495–508) vytvára lokálnu identitu `cli_examiner` s rolami admin a analyst (501) a používa ju pre každé volanie (508). Ide o **zdrojové zistenie**, stdio runtime sa v tomto kroku nespúšťal. Lokálne procesové oprávnenia nenahrádzajú reporting scope; nejde o obídenie vzdialenej HTTP autentifikácie.

### 5. Prístup a správna identita vráteného payloadu sú dve kontroly

Status/results/cancel čítajú case_id z uloženého JobSpec (`core/server.py` 225–228), čo zabraňuje klientovi jednoducho dosadiť iný case argument do tejto kontroly. `store_result` (`core/jobs.py` 151–157) však vkladá model pod odovzdaný job_id bez osobitného porovnania identity celého payloadu voči JobSpec; `get_result` (187–189) ho znovu načíta a modelovo validuje. Preto kontrolovaný produktový adaptér stále potrebuje nezávisle očakávané job/case/evidence identity. Autorizácia podľa jobu nenahrádza samostatné evidence oprávnenie.

Provider ACL používa in-memory slovníky (`core/acl.py` 70–74). Obnova zo SQLite (`core/jobs.py` 44–50) registruje joby; príslušnú trvalú obnovu case grantov tento kód neukazuje. Import job managera navyše mení staré aktívne joby na prerušené (53–57), preto probe bez výnimky používa novú dočasnú databázu. Produkčné provisionovanie case ani restart sa v runtime skúške neoverovali.

## Čo je vynútené kde

| Hranica | Aktuálny dôkaz | Čo nemožno tvrdiť |
| --- | --- | --- |
| HTTP server | Produkčná autentifikácia; opísané job/case ACL a odmietnutie testovaného cudzieho používateľa | Reporting poverenie nemôže start/cancel; každý case má osobitnú allowlist; API kľúče tvoria oddelených tenantov. |
| Konfigurácia AI klienta | V FX-007 existuje konfigurácia s `enabled_tools` len status/results; v tomto probe sa AI klient nespúšťal | Že podkladové poverenie je serverom obmedzené na tieto dve operácie. |
| Skill/prompt | Pokyn použiť iba povolené čítania je pravidlom správania agenta | Autorizácia servera, ochrana pred priamym volaním alebo pred obídením klienta. |
| Syntetický testovací harness | Izolovaný DB, skutočná auth/ACL, žiadny worker, explicitný post-ACL sentinel | Zmena produkčného správania alebo povolenie reálnych vstupov. |

## Najmenší nasledujúci krok

Pripraviť samostatnú upstream zmenu, ktorá zavedie konkrétne reportovacie oprávnenie v spoločnej hranici po normalizácii aliasov. Akceptácia musí doložiť:

1. Neadmin reportovacie poverenie prečíta iba povolené status/results a zachová serverom určené job/case/evidence identity.
2. Canonical aj alias start a canonical cancel odmietne **pred** vytvorením jobu, lookupom packu, worker taskom alebo mutáciou stavu; rovnako na `/mcp` a `/mcp/jsonrpc`.
3. Pri odmietnutí sa nemennosť DB a absencia workeru preukáže. Neúspech packu alebo infraštruktúry sa nepovažuje za zamietnutie oprávnenia.
4. Kontrakt pomenuje org/case/job hranicu vrátane rovnakého `user_id` v inej organizácii a case fallbacku; záporné príklady sa z nej odvodia.
5. SSE aj lokálna stdio varianta majú explicitnú politiku. Doklad o lokálnom stdio nesmie automaticky nahradiť overenie HTTP oprávnení.

Do tejto zmeny sa nedotýka renderer FX-010. Existujúci reportovací adaptér môže zúžiť svoje rozhranie, ale bez oddelenej ochrany jeho širšieho upstream poverenia sa nesmie vydávať za serverové obmedzenie Hubu. **FX-008 nie je done a report_generation_allowed zostáva false.**
