# Lokálne naklonovanie, overenie a spustenie

Tento repozitár obsahuje dashboard backlogu a produktové validátory/referenčné dáta. Lokálny launcher spustí **skutočný dashboard s ukladaním do lokálnej D1 databázy**. Dáta na hostovanej stránke sa do lokálnej databázy nekopírujú. Prvé otvorenie ju naplní seedom z aktuálneho checkoutu; ďalšie lokálne zmeny zostávajú uložené medzi spusteniami.

## Predpoklady

- Linux, macOS alebo Windows cez WSL s Bashom.
- Git a prístup k súkromnému repozitáru `erikbabcan-commits/forenzx-analysis-brief`.
- Node.js **22.13.0 alebo novší** a npm.
- Python **3.10 alebo novší**, dostupný ako `python3`.
- Internet pri prvom `npm ci`; ďalšia lokálna práca používa nainštalované závislosti.

Skript nevyžaduje Docker, `sudo`, Cloudflare prihlásenie, AI API kľúč ani produkčné ChatGPT prihlásenie. Použije existujúce nastavenia npm registry, proxy a TLS. Neinštaluje systémové balíky a nemení globálnu konfiguráciu.

## 1. Prvý klon

Ak už máš tento repozitár naklonovaný, preskoč do jeho adresára. Nasledujúci klonovací príkaz patrí do adresára, v ktorom ešte podadresár `forenzx-analysis-brief` neexistuje:

```bash
git clone https://github.com/erikbabcan-commits/forenzx-analysis-brief.git
cd forenzx-analysis-brief
bash scripts/local-bootstrap.sh
```

Pri súkromnom repozitári musí byť Git autentifikovaný tvojím existujúcim spôsobom. Heslo ani token nevkladaj do URL. Pri chybe prístupu treba vyriešiť GitHub prístup a zopakovať klonovanie. Skript nerobí `git pull`, `reset`, `stash`, zmenu vetvy ani prepísanie existujúceho adresára.

## 2. Čo vykoná bootstrap

1. Overí verzie Node.js, npm a Pythonu a identitu projektu.
2. Ak chýbajú závislosti alebo sa nainštalované priame verzie nezhodujú s lockfile, spustí `npm ci`. Pri opakovanom spustení vie existujúce závislosti znovu použiť. Prepínač `--install` vynúti úplnú inštaláciu podľa lockfile.
3. Spustí `npm test`, `npm run test:product`, `npm run test:reference`, `npm run typecheck` a testy lokálneho gateway.
4. Vytvorí nový build cez `npm run build`.
5. Na dočasnej, samostatnej lokálnej D1 databáze preverí HTML stránku, načítanie úloh, uloženie zmeny cez API, export vrátane histórie, odmietnutie cudzieho Origin a zachovanie zmeny po reštarte. Potom túto vlastnú testovaciu databázu zmaže.
6. Aplikuje existujúce SQL migrácie z `drizzle/` na lokálnu pracovnú databázu a spustí dashboard. V termináli vypíše presnú URL, predvolene `http://127.0.0.1:5173`.

Pri chybe sa zastaví s nenulovým návratovým kódom. Neprejde cez neúspešné testy do spustenia. Testy ani zobrazenie dashboardu nepotvrdzujú pripojenie skutočného AI klienta k vzdialenému ForenZX serveru; to je samostatné overenie FX-007.

## 3. Ovládanie

| Úloha | Príkaz |
| --- | --- |
| Inštalácia podľa potreby, testy, build a spustenie | `bash scripts/local-bootstrap.sh` |
| Celé overenie vrátane buildu a HTTP testu, potom skončiť | `bash scripts/local-bootstrap.sh --check-only` |
| Znova nainštalovať celý uzamknutý strom závislostí | `bash scripts/local-bootstrap.sh --install` |
| Vybrať voľný port automaticky | `bash scripts/local-bootstrap.sh --port 0` |
| Použiť iný konkrétny port | `bash scripts/local-bootstrap.sh --port 5180` |
| Rýchlo spustiť už overený existujúci build | `node scripts/local-dashboard.mjs --port 5173` |
| Preveriť iba existujúci build na dočasnej lokálnej D1 | `node scripts/local-dashboard.mjs --smoke` |
| Zobraziť všetky prepínače | `bash scripts/local-bootstrap.sh --help` |

Terminál nechaj počas používania otvorený. **Ctrl+C** ukončí launcher a jeho vlastný Wrangler/Worker. Ak je konkrétny port obsadený, launcher zlyhá; cudzí proces nezastaví. Použi `--port 0` alebo iný port.

Po zmene zdrojového kódu použi bootstrap znova. Rýchly príkaz `node scripts/local-dashboard.mjs` používa už vytvorený build, preto v ňom nové úpravy zdrojov bez ďalšieho buildu neuvidíš.

## Lokálna identita a údaje

V lokálnom režime sa zobrazí syntetický účet **ForenZX Local Demo**, `local-demo@forenzx.invalid`. Slúži len na testovanie tohto checkoutu. Prihlásenie ani odhlásenie cez ChatGPT v tomto režime nevytvára živú reláciu; tieto lokálne adresy zobrazia vysvetlenie.

Node gateway aj Wrangler Worker počúvajú výlučne na `127.0.0.1`. Gateway povoľuje iba svoju presnú lokálnu adresu `Host`, pri zápise vyžaduje zhodný `Origin`, odmieta cudzie Origins a odstraňuje dodané autentifikačné/forwarded hlavičky. Internému lokálnemu Workeru pridá pevnú syntetickú identitu. Produkčný `app/chatgpt-auth.ts` zostáva nezmenený. Launcher je vývojový nástroj pre vlastníka počítača; neposkytuje izoláciu pred inými programami spustenými pod tým istým OS používateľom. Nepoužívaj preň verejný tunel ani verejné rozhranie.

Pracovný stav je v `.wrangler/forenzx-local/state`. Dočasné testovanie vytvára svoj vlastný adresár cez `mkdtemp` a po skončení ho odstráni. Lokálna konfigurácia používa samostatný názov databázy a placeholder ID; všetky migračné a spúšťacie príkazy majú explicitné `--local`. Nespúšťa sa žiadna vzdialená migrácia.

Lokálne dáta môžeš uložiť tlačidlom exportu v dashboarde. Export z lokálnej inštancie je snímka jej lokálnych úloh a histórie, nie záloha hostovanej D1. Pri opakovanom spustení zostáva pracovná databáza zachovaná a aplikácia použije existujúci mechanizmus zosúladenia definícií úloh so seedom v gite.

## Rýchla diagnostika

- **Nedostatočná verzia Node/Python:** skript vypíše potrebnú verziu. Doplň runtime svojím bežným správcom a zopakuj príkaz.
- **Chyba `npm ci`:** skontroluj pripojenie, registry a existujúce proxy/TLS nastavenia. Skript ich neobchádza. Rieš prvú uvedenú chybu; nepokračuj s neúspešnou inštaláciou.
- **Obsadený port / `EADDRINUSE`:** spusti s `--port 0`. Nie je potrebné hľadať a zabíjať cudzí proces.
- **401 pri samostatnom `npm start`:** tento príkaz spúšťa priamo produkčný Worker bez lokálneho identity adaptéra. Pre funkčné lokálne ukladanie použi `local-bootstrap.sh` alebo `local-dashboard.mjs`.
- **Zmeny zo zdrojov sa nezobrazujú:** opakuj bootstrap, aby vznikol nový build.
- **Iné odškrtnuté úlohy než na hostovanej stránke:** je to samostatná lokálna databáza, nie synchronizovaná kópia hostovanej služby.

Aktuálny výsledok a počty testov sú v konzolovom výstupe daného spustenia. Referenčné produktové dáta sú syntetické a nesmú byť prezentované ako úspešné overenie na reálnom dôkaznom materiáli.
