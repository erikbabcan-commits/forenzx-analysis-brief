# Lokálna reprodukcia používateľa — 21. 11. 2026

**Pôvod dôkazu: používateľom poskytnutý textový súhrn.** Samotné súbory `report.json` ani logy zatiaľ neboli doručené do koordinačného prostredia. Nižšie uvedené lokálne výsledky sú preto `USER_REPORTED`, nie nové nezávislé vykonanie alebo kontrola pôvodných artefaktov koordinátorom.

## Nahlásený beh

| Oblasť | Používateľom nahlásený výsledok |
| --- | --- |
| Checkout | `~/Projekty/forenzx-analysis-brief-review`, vetva `chore/fx008-fx009-coordination`, čistý pracovný strom. |
| Testovaný commit | `c2ad1baacfa8b82429eb109514c6b5c4cc8bc3ac`. |
| Celý lokálny blok | Exit `0`. |
| Bootstrap | Inštalácia závislostí, backlog/state testy, produktové testy **46/46**, referencia FX-006 **50/50**, typecheck, launcher testy, build a lokálny HTML/D1 smoke test prešli. |
| FX-007 bez modelu | HTTP **13/13**, `http_acceptance: true`, `requested_acceptance: true`, `codex.status: NOT_REQUESTED`. |
| FX-008 | **53/53** zhôd s pripnutým baseline; `baseline_status: PASS`, `reporting_policy_gate: FAIL`, rovnakých 13 identifikátorov nesplnenej reportovacej politiky. |
| Codex na používateľovom PC | `codex-cli 0.170.0`; `codex login status` oznámil `Not logged in`. |
| Skutočný klientský test | `--with-codex` **nebol spustený**, pretože chýbalo prihlásenie. |

Koordinátor samostatne overil, že vzdialená koordinačná vetva pred týmto dokumentačným zápisom stále ukazovala na uvedený commit. Toto overenie GitHubu nepotvrdzuje obsah súborov na používateľovom počítači.

## Kde majú byť pôvodné artefakty

Nasledujúce cesty pochádzajú zo správy používateľa; nie sú cestami dostupnými v tomto koordinačnom checkoute:

```text
~/Projekty/forenzx-analysis-brief-review/.fx007-runtime/local-checks/bootstrap.log
~/Projekty/forenzx-analysis-brief-review/.fx007-runtime/local-checks/http.log
~/Projekty/forenzx-analysis-brief-review/.fx007-runtime/local-checks/fx008.log
~/Projekty/forenzx-analysis-brief-review/.fx007-runtime/runs/20261121T150119Z-8e9cbbc6/report.json
~/Projekty/forenzx-analysis-brief-review/.fx007-runtime/runs/fx008-local-aps2Io/report.json
```

Ich hashe, úplný obsah, verzie závislostí a jednotlivé výsledky koordinátor zatiaľ neoveril. Nahlásené počty sa nesmú zameniť za novú sadu testov spustenú koordinátorom alebo za hotovú klientsku integráciu.

## Význam výsledkov a presné hranice

`requested_acceptance: true` vo FX-007 sa vzťahuje na **vyžiadaný HTTP rozsah bez Codexu**. Keď `codex.status` ostáva `NOT_REQUESTED`, nejde o dôkaz úspešného klientského toku.

Vo FX-008 znamená „iný API kľúč“ ďalší **nakonfigurovaný platný kľúč** mapovaný do `default_org`, nie ľubovoľný neplatný token. Probe testoval pre túto identitu čítanie a skutočný cancel. Štyri start sentinely sa týkajú owner/empty_roles/reporter_label identít a legacy reporter varianty; z týchto skúšok sa neodvodzuje, že bol osobitne vykonaný start test každého API kľúča. Pozri [skutočný probe](../../integration/fx008/run_authorization_probe.py) a [review](FX008_AUTHORIZATION_REVIEW.md).

Tri odlišné prekážky sa evidujú oddelene:

1. **Historické koordinačné prostredie:** Codex `0.172.0-alpha.2` skončil na read-only úložisku pred prvým MCP volaním.
2. **Aktuálne používateľovo prostredie:** Codex `0.170.0` nie je prihlásený; klientský beh sa nezačal.
3. **Hub:** zdokumentované otázky discovery/verziovania a chýbajúce reportovacie oprávnenie sú vlastnosti skúmaného serverového kódu, nie dôsledok chýbajúceho prihlásenia.

Tento zápis nemení checkboxy, definície úloh, živý dashboard ani povolenie reálnych dát. FX-007 a FX-008 zostávajú otvorené. Predchádzajúce runtime reporty sa neprepisujú.

## Kontrola zdrojovej kompatibility Codexu 0.170.0

Koordinátor overil oficiálny tag `rust-v0.170.0`, ktorý odkazuje na commit `29eb79e9866b3262a777fdf8195c1b9e63684c91`, a porovnal jeho zdrojový kód s príkazom v [aktuálnom probe](../../integration/fx007/run_probe.py). Ide o kontrolu podporovanej syntaxe a konfiguračnej schémy, nie o úspešne vykonaný klientský test.

| Nastavenie probe | Doložené v zdroji 0.170.0 |
| --- | --- |
| `--ephemeral`, `--ignore-user-config`, `--skip-git-repo-check`, `--output-schema` | [Definícia CLI](https://github.com/openai/codex/blob/29eb79e9866b3262a777fdf8195c1b9e63684c91/codex-rs/exec/src/cli.rs). |
| `enabled_tools`, časové limity, per-tool `approval_mode` | [Konfigurácia MCP](https://github.com/openai/codex/blob/29eb79e9866b3262a777fdf8195c1b9e63684c91/codex-rs/config/src/mcp_types.rs). |
| Hodnota `approve` a filtre nástrojov | [Testy konfigurácie MCP](https://github.com/openai/codex/blob/29eb79e9866b3262a777fdf8195c1b9e63684c91/codex-rs/config/src/mcp_types_tests.rs). Testy boli prečítané, nie vykonané v našom prostredí. |
| HTTP `bearer_token_env_var` | [HTTP transport v konfigurácii MCP](https://github.com/openai/codex/blob/29eb79e9866b3262a777fdf8195c1b9e63684c91/codex-rs/config/src/mcp_types.rs). |

Pre tieto nastavenia sa nepotvrdila potreba aktualizovať klienta alebo meniť harness. `enabled_tools` je klientský filter a neuzatvára serverové oprávnenia FX-008. `--ignore-user-config` preskočí používateľský `config.toml`; autentifikácia naďalej používa `CODEX_HOME`. Prítomnosť samotného `MISTRAL_API_KEY` preto nenahrádza chýbajúce prihlásenie v tomto pripravenom toku. Používateľove poverenia ani ich obsah koordinátor nečítal.

## Najbližší krok na používateľovom PC

Používateľ dokončí bežné `codex login` vo vlastnom termináli a overí `codex login status`. Rozhodujúci je stav prihlásenia; samotná neprítomnosť `auth.json` nestačí, pretože CLI môže používať systémové úložisko poverení. [Oficiálna autentifikácia](https://learn.chatgpt.com/docs/auth).

```bash
codex login
codex login status
```

Následne sa spustí iba chýbajúca klientská fáza cez `scripts/fx007-mcp-check.sh --with-codex`, s aktívnym Bash `pipefail` a novým logom. `pipefail` zabráni tomu, aby úspech `tee` zakryl zlyhanie probe. Na túto skúšku sa nevyžaduje opakovaný klon ani celý frontend build. Probe zopakuje vlastné nevyhnutné HTTP kontroly v čerstvom syntetickom prostredí.

```bash
bash <<'BASH'
set -euo pipefail
cd "$HOME/Projekty/forenzx-analysis-brief-review"
codex --version
codex login status
mkdir -p .fx007-runtime/local-checks
forenzx_codex_log="$(mktemp "$PWD/.fx007-runtime/local-checks/codex-XXXXXX.log")"
printf 'Log: %s\n' "$forenzx_codex_log"
bash scripts/fx007-mcp-check.sh --with-codex 2>&1 | tee "$forenzx_codex_log"
BASH
```

Príkazy sú návod pre používateľov počítač. V rámci tohto dokumentačného zápisu koordinátor nespúšťal prihlásenie ani volanie modelu.

Úspech vyžaduje nielen odpoveď modelu, ale aj serverom pozorované úspešné volania oboch reportovacích nástrojov, presnú zhodu vybraných zdrojových polí a absenciu nepovolených volaní. Po doručení skutočných JSON reportov sa skontrolujú tieto položky a konkrétny rozsah dôkazu. [Kontrakt FX-007](../../integration/fx007/README.md).
