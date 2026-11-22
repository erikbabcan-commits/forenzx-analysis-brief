# Nezávislé overenie FX-010 na Fedore

Implementácia vychádza z vetvy `audit/release-board-sync-20261122` na commite `5c922ac0a67a66504cb1557e833b7458d3d4df32`. Použi publikované plné SHA FX-010 z odovzdania. Pracuj v novom worktree, aby hlavný checkout, bežiaci dashboard a jeho pracovná D1 mohli zostať otvorené.

```bash
(
  set -euo pipefail
  repo="$HOME/Projekty/forenzx-analysis-brief-fedora"
  branch=feat/fx010-deterministic-brief
  work=$(mktemp -d "$HOME/Projekty/fx010-review-XXXXXXXX")
  : "${FX010_SHA:?Najprv nastav FX010_SHA na presny publikovany commit.}"
  git -C "$repo" fetch origin "refs/heads/$branch"
  test "$(git -C "$repo" rev-parse FETCH_HEAD)" = "$FX010_SHA"
  git -C "$repo" worktree add --detach "$work/checkout" "$FX010_SHA"
  cd "$work/checkout"
  python3 --version
  git rev-parse HEAD
  python3 -m unittest discover -s product/tests -v
  python3 product/run_reference_suite.py
  for scenario in completed-hit completed-no-ioc; do
    python3 product/brief_cli.py "$scenario" --output "$work/$scenario.md"
    cmp "$work/$scenario.md" "product/brief_reference/$scenario.md"
    sha256sum "$work/$scenario.md"
  done
  printf 'Výstupy sú v %s\n' "$work"
)
```

Na nezávislý kontrolný beh Release Boardu v tom istom novom checkoute použi `bash scripts/local-bootstrap.sh --check-only --port 0`. Tento krok potrebuje aj Node.js, npm a pri prvej inštalácii závislostí internet. Samotné dve ukážky používajú iba Python.

Koordinátorovi odovzdaj SHA, verzie, počty testov, oba hashe a prípadnú odchýlku. Kontrolované vypustenie posledného varovania možno reprodukovať iba v ďalšej pracovnej kópii: vo funkcii `_source_list` pri poli `warnings` vynechaj posledný prvok a spusti `python3 -m unittest product.tests.test_render_brief.RendererTests.test_independent_reference_content`. Očakávaný výsledok je kód 1 a zlyhanie oboch podprípadov. Pôvodné očakávania sa pri tomto pokuse musia zachovať.
