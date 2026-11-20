// Immutable definitions shipped before definition snapshots existed.
// Source: ff8dda95fb47173b0adba355ce687a108f6388cb:data/backlog.json.
// Never update this baseline when the current catalog changes.
export const legacyTaskDefinitions = {
  "FX-001": {
    "acceptance": [
      "Zaznamenaný úplný commit upstream repozitára.",
      "Overené kontrakty forenzx_analysis_status a forenzx_analysis_results s job_id.",
      "Vymenované hranice kontroly: bez spustenia servera a bez reálneho AI klienta."
    ],
    "dependencies": []
  },
  "FX-002": {
    "acceptance": [
      "Zdokumentovaný vstup job_id a výstup v docs/PRODUCT_CONTRACT.md.",
      "Vymedzené povolené čítania a vylúčené spúšťanie či rušenie analýz.",
      "Výstup označený ako AI návrh s kontrolou analytikom, bez sľubov certifikácie."
    ],
    "dependencies": [
      "FX-001"
    ]
  },
  "FX-003": {
    "acceptance": [
      "Vlastník schválil podmienky použitia servera; zaznamenaná konkrétna verzia.",
      "Samostatne určené podmienky distribúcie a používania skillu.",
      "LICENSE-TODO.md vyriešený alebo doložená oprávnená cesta k vlastnej inštancii."
    ],
    "dependencies": []
  },
  "FX-004": {
    "acceptance": [
      "Existuje metodika s rozlíšením faktov, interpretácie, integrity a pôvodu.",
      "Každý odborný zdroj má URL, verziu alebo rok a obmedzenie rozsahu.",
      "Merateľné brány sú označené ako naše kritériá; odborné review zostáva otvorené."
    ],
    "dependencies": [
      "FX-002"
    ]
  },
  "FX-005": {
    "acceptance": [
      "Definované povinné polia a správanie pri neplatnej schéme.",
      "Požadované a vrátené job_id, case_id a evidence_id sa kontrolujú na konzistenciu.",
      "Chýbajúce referencie a rozporné údaje vytvoria viditeľný limit alebo chybu."
    ],
    "dependencies": [
      "FX-001",
      "FX-002"
    ]
  },
  "FX-006": {
    "acceptance": [
      "Pokryté dokončené, bežiace, zlyhané, zrušené, zablokované a chýbajúce úlohy aj odmietnutý prístup.",
      "Existujú nálezy s chýbajúcou referenciou, neznámou zónou a rozpornou identitou.",
      "Pridaný negatívny IOC výsledok a text artefaktu s vloženými škodlivými inštrukciami.",
      "Očakávané hodnoty a výstupné správanie zaznamenané pred hodnotením."
    ],
    "dependencies": [
      "FX-005"
    ]
  },
  "FX-007": {
    "acceptance": [
      "Zaznamenaný klient, jeho verzia, server commit a presná konfigurácia bez tajomstiev.",
      "Prešli autentifikácia, objavenie nástrojov a volania status/results.",
      "Overená skutočná cesta vyjednania MCP verzie alebo podporované priame pripnutie verzie.",
      "Uložený redigovaný záznam behu; opravy upstreamu evidované samostatne."
    ],
    "dependencies": [
      "FX-001",
      "FX-006"
    ]
  },
  "FX-008": {
    "acceptance": [
      "Zdokumentované a otestované povolené čítania a zakázané start/cancel volania.",
      "Návod správne rozlišuje X-API-Key alebo APIKey od Bearer JWT.",
      "Pozitívny aj negatívny test prístupu k úlohe; bez potreby admin kľúča.",
      "Výslovne uvedené, ktoré obmedzenia vynucuje server/klient a ktoré sú iba pokynom."
    ],
    "dependencies": [
      "FX-002",
      "FX-007"
    ]
  },
  "FX-009": {
    "acceptance": [
      "Endpoint je používateľský; žiadne skryté odosielanie na nové služby.",
      "ZIP, demo a logy neobsahujú kľúče ani skutočné dôkazové dáta.",
      "Návod opisuje spracovanie výsledkov zvoleným AI klientom/poskytovateľom.",
      "Nastavenie, rotácia a chybné poverenia majú overený postup."
    ],
    "dependencies": [
      "FX-008"
    ]
  },
  "FX-010": {
    "acceptance": [
      "Každý nález má pôvodné ID a dostupnú referenciu na artefakt alebo JSON položku.",
      "Zachované všetky zdrojové upozornenia a obmedzenia.",
      "Uvedené job/case/evidence ID, dostupné verzie a identita zdrojového výstupu.",
      "Chýbajúci údaj je označený; nikdy doplnený odhadom."
    ],
    "dependencies": [
      "FX-004",
      "FX-005"
    ]
  },
  "FX-011": {
    "acceptance": [
      "Klasifikácie a závažnosti zostávajú zhodné so zdrojom.",
      "Interpretácia AI je oddelená, označená a má uvedené podklady.",
      "Nevzniká číselná istota ani atribúcia bez zdrojového podkladu.",
      "NO_KNOWN_IOC sa vzťahuje iba na skúmaný rozsah a použité indikátory."
    ],
    "dependencies": [
      "FX-010"
    ]
  },
  "FX-012": {
    "acceptance": [
      "Predvolený stav metadát je NOT_VERIFIED, kým neexistuje skutočný overovací krok.",
      "Presne pomenovaný podpísaný payload a väzba na overovací kľúč.",
      "Žiadna značka naznačujúca overenie celého výsledku alebo AI prehľadu.",
      "Ak pribudne verifier, prejde aj test zmeneného payloadu a nedôveryhodného kľúča."
    ],
    "dependencies": [
      "FX-005",
      "FX-010"
    ]
  },
  "FX-013": {
    "acceptance": [
      "Zachované pôvodné časy, offsety a zdrojové poznámky k normalizácii.",
      "Konverzia na UTC iba pri známom východisku.",
      "Neznáma časová zóna a rozpory sú viditeľné.",
      "Bez vymysleného poradia, času alebo osoby vykonávajúcej udalosť."
    ],
    "dependencies": [
      "FX-010"
    ]
  },
  "FX-014": {
    "acceptance": [
      "Text artefaktu nevyvolá nové nástroje, endpointy ani vyzradenie kľúčov.",
      "Volania zostanú v povolenom rozsahu čítania.",
      "Nedokončená alebo zlyhaná úloha vráti stav a limit, nie úspešný findings brief.",
      "Chyby, timeouty a neúplné odpovede majú uchovaný testovací výsledok."
    ],
    "dependencies": [
      "FX-006",
      "FX-008",
      "FX-009",
      "FX-010",
      "FX-011",
      "FX-012",
      "FX-013"
    ]
  },
  "FX-015": {
    "acceptance": [
      "SKILL.md v koreni má name/description a presný workflow.",
      "Priložené setup/auth pokyny, konfiguračná šablóna, šablóna prehľadu a syntetický príklad.",
      "Predpoklady servera/modelu a verzie sú výslovne uvedené.",
      "Čistá inštalácia a celý príklad prešli bez neverejných závislostí a tajomstiev."
    ],
    "dependencies": [
      "FX-007",
      "FX-008",
      "FX-009",
      "FX-010",
      "FX-011",
      "FX-012",
      "FX-013",
      "FX-014"
    ]
  },
  "FX-016": {
    "acceptance": [
      "Referenčná sada má 100 % zhodu kontrolovaných faktov a všetky varovania/limity.",
      "Nula nepodložených faktických tvrdení, nepovolených zápisov a únikov tajomstiev v testovanej sade.",
      "Aspoň tri opakované behy na scenár podľa nášho navrhnutého minima; verzie a model zaznamenané.",
      "Menovitý odborný hodnotiteľ posúdil výstupy; kritické pripomienky vyriešené.",
      "Zostávajúce hranice pokrytia a neistoty sú zaznamenané."
    ],
    "dependencies": [
      "FX-015"
    ]
  },
  "FX-017": {
    "acceptance": [
      "Krátke funkčné demo používa označené syntetické dáta.",
      "Listing uvádza vlastný ForenZX, podporovaného klienta a ďalšie možné náklady.",
      "Cena/podmienky a spôsob prijímania výplat skontrolované v Agensi.",
      "Marketing neobsahuje nepodložené certified/court-grade ani sľub súdnej prípustnosti."
    ],
    "dependencies": [
      "FX-003",
      "FX-016"
    ]
  },
  "FX-018": {
    "acceptance": [
      "Všetky predchádzajúce brány majú splnené kritériá a dohľadateľné dôkazy.",
      "Uložené číslo verzie, hash ZIP a changelog.",
      "Zaznamenané odoslanie, výsledok kontroly Agensi a vyriešenie pripomienok.",
      "Živý listing overený až po skutočnom schválení a publikácii."
    ],
    "dependencies": [
      "FX-003",
      "FX-016",
      "FX-017"
    ]
  }
};
