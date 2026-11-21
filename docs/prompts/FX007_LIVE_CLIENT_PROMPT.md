# Bod 4.2 — FX-007: reálny klient a reprodukovateľné spustenie

## Vykonateľný prompt

Pracuj v súkromnom projekte `erikbabcan-commits/forenzx-analysis-brief`. Dokonči reprodukovateľné lokálne spustenie existujúceho dashboardu a vykonaj **FX-007 — preukázať pripojenie jedného reálneho AI klienta**. Zaznamenaj skutočné výsledky vrátane zlyhaní. Úspech pomocného HTTP skriptu nezamieňaj s kompatibilitou AI klienta.

### 1. Over východiskový stav

Prečítaj pokyny projektu, Git stav, backlog, produktový kontrakt, FX-005 a hotovú sadu FX-006. Zachovaj rozpracované súbory, existujúce stavy a históriu. Upstream pripni na `0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f`; over čistotu checkoutu. Dátový profil zostáva `forenzx-analysis-result-0e4c7fae`. Neprerábaj referenčné očakávania FX-006 podľa nameraných výsledkov.

### 2. Priprav úplné lokálne spustenie

Vytvor skript na klonovanie súkromného repozitára cez existujúce oprávnenie používateľa. Nezapisuj token do príkazu ani súboru. Existujúci cieľový adresár neprepisuj. Skontroluj Node 22.13+, Python 3.10+, Git a npm. Použi lockfile a lokálne závislosti. Spusti testy backlogu a ukladania, produktové testy, referenčnú sadu, typovú kontrolu a build.

Lokálny dashboard musí vedieť načítať úlohy, uložiť zmenu, prežiť reštart a exportovať históriu. Hostingovú autentifikáciu v produkcii nemeň. Pre lokálny režim použi iba loopback, explicitne syntetickú identitu a samostatnú lokálnu D1. Validuj Host a Origin pred pridaním dôveryhodných hlavičiek. Nevytváraj verejný tunel. Obsadený port nesmie viesť k ukončeniu cudzieho procesu. Ctrl+C ukončí iba vlastné procesy. Vysvetli, že lokálna databáza sa automaticky nesynchronizuje so živým dashboardom.

### 3. Zafixuj integračné očakávania pred behom

Zaznamenaj názov a verziu skutočne dostupného klienta, verziu Pythonu, serverový commit a presnú konfiguráciu bez tajomstiev. Ako testovacie dáta použi existujúcu syntetickú fixture; žiadne vyšetrovacie spisy. Zaveď ju cez skutočný upstream model a správcu úloh do novej dočasnej SQLite databázy. Jediná potrebná adaptácia je nové `job_id`; presne ju zaznamenaj. Výsledok je nasadený testovací záznam, nie vykonaná forenzná analýza.

Spusť nezmenenú serverovú aplikáciu v samostatnom procese na 127.0.0.1, s produkčnými kontrolami autentifikácie a náhodnými dočasnými kľúčmi. Vypni len nepotrebné automatické sondovanie cudzích serverov. Dočasný JWT používateľa má rolu analytika, nie administrátora. Nespoliehaj sa na vývojový bypass.

Pred testom stanov očakávania: platné poverenie dovolí zoznam nástrojov a status/results vlastnej dokončenej úlohy; chýbajúce, neplatné a expirované poverenie sa odmietne; cudzí používateľ z cudzej organizácie nezíska výsledok; chýbajúca úloha nevráti úspešný výsledok. Over presnú identitu a zhodu načítaného výsledku so syntetickým vstupom vrátane všetkých upozornení a obmedzení.

### 4. Preukáž skutočnú cestu MCP klienta

Over aktuálnu oficiálnu špecifikáciu protokolu aj dokumentáciu klienta. MCP 2026-07-28 je bez starého inicializačného handshake; jeho absenciu automaticky neoznač za chybu. Zaznamenaj reálne verzie v požiadavkách, metadata, discovery a odpovede. Ak starší SDK nepodporuje túto verziu, zapíš konkrétnu nekompatibilitu.

Nakonfiguruj dostupný AI klient jednorazovo, bez zásahu do globálnej konfigurácie používateľa. Klientovi sprístupni iba `forenzx_analysis_status` a `forenzx_analysis_results`. Token načítaj z dočasnej premennej prostredia. Nepúšťaj start/cancel. Skutočný klient musí nástroje objaviť a oba zavolať. Požiadaj ho iba o presné syntetické údaje; negeneruj odborný forenzný záver.

Zaznamenaj klientské udalosti a sanitizované serverové požiadavky. Pozorovanie nesmie meniť telo, hlavičky ani výsledok komunikácie. Oddel úspech HTTP vrstvy, podporu protokolu, úspech nástrojov a dostupnosť modelu. Ak klient alebo sieť zlyhá, nevydávaj ručný HTTP test za náhradný dôkaz kompatibility.

### 5. Zachovaj hranice produktu

Poverenia nesmú byť v Gite, reportoch ani konzolovom výstupe. Dočasné služby a databázu uprac po behu. Nekopíruj upstream server do distribučného balíka a nerozhoduj jeho nevyriešenú licenciu. Nepublikuj na Agensi ani neposielaj správy.

Pri chybe najprv ulož pôvodný výsledok. Prípadnú kompatibilitnú opravu eviduj osobitne s diffom a novým behom; nesmie sa tváriť ako nezmenený upstream. Úspech čítania existujúceho výsledku nedokazuje funkčný forenzný engine, serverové oprávnenie iba na čítanie, odolnosť LLM, maximálny kontext, podpisy ani správnosť finálneho briefu.

### 6. Uzavri len doložené kritériá

Ulož prompt, reprodukovateľné skripty, presné verzie, report a známe prekážky. Spusti zmysluplné regresné kontroly. FX-007 označ hotovo iba pri splnení všetkých štyroch kritérií. Pri zlyhaní ju nechaj rozpracovanú alebo zablokovanú s konkrétnou príčinou a ďalším krokom. FX-005, FX-008 a ďalšie brány sa neuzatvárajú automaticky.

Synchronizuj súkromný GitHub a súkromný dashboard; zachovaj ostatné dáta. Odovzdaj úplný kopírovateľný štartovací skript, presné príkazy na opakovanie testov, výsledky a najbližší ďalší krok.

## Pôvod a prispôsobenie

Východiskom je už prečítaná šablóna **Software Quality Assurance Tester**, autor `iuzn`, z offline katalógu f/prompts.chat, commit `c7257bace9dc146405a183c7b316fb5ae97b1452`, snapshot z 22. 10. 2026. [Katalóg](https://github.com/f/prompts.chat/blob/c7257bace9dc146405a183c7b316fb5ae97b1452/prompts.csv).

Prispôsobenie: skutočný proces a klient, zmrazený upstream, izolované syntetické dáta, očakávania pred behom, ochrana poverení, oddelenie transportu od modelu a presná evidencia neúspechu. Aktuálne technické pravidlá určujú primárne zdroje a pozorovaný beh, nie komunitná šablóna.
