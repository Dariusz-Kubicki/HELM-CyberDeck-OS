# Wydanie HELM v1.2.0

Ten dokument opisuje kontrolowane zakończenie gałęzi
`feature/helm-v1.2.0`, merge do `master`, utworzenie taga i wydania GitHub.
Nie przesuwaj istniejących tagów i nie używaj `--force`.

## 1. Punkt zamrożenia

Kod funkcjonalny v1.2 został zamrożony na:

```text
1d4b9ce Harden runtime diagnostics and release checks
```

Po tym commicie dozwolone są tylko poprawki dokumentacji, screenshotów, metadanych
wydania oraz wąskie naprawy wykrytych blokerów bezpieczeństwa/utraty danych.

## 2. Wykonaj pełny backup

```bash
cd ~/.cyberdeck/nexus
helm backup
```

Zapisz ścieżkę archiwum. Wersja v1.2 obejmuje także aktywny katalog danych
runtime. Archiwum nie jest szyfrowane.

## 3. Sprawdź gałąź

```bash
cd ~/.cyberdeck/nexus
git switch feature/helm-v1.2.0
git status --short --branch
git log --oneline --decorate -n 12
```

Nie kontynuuj z nierozpoznanymi zmianami lokalnymi.

## 4. Dokumentacja i przygotowanie screenshotów

Sprawdź zgodność dokumentacji oraz danych demonstracyjnych przed sesją:

- `README.md` i `README.pl.md`;
- `CHANGELOG.md`;
- `RELEASE_NOTES_v1.2.0.md`;
- `docs/CODEBASE.md`;
- `docs/RUNTIME_DATA.md`;
- `docs/DEVELOPMENT.md`;
- `docs/DECISIONS.md`;
- `docs/SCREENSHOTS.md`;
- wszystkie obrazy użyte przez README.

Nie wykonuj jeszcze finalnych screenshotów z oznaczeniem `-dev`.

## 5. Finalna zmiana wersji i screenshoty

Po zatwierdzeniu dokumentacji, lecz przed finalną sesją screenshotów:

```bash
printf '1.2.0\n' > VERSION
```

W `CHANGELOG.md` zmień sekcję `Unreleased` na datę wydania. W README zmień stan
`v1.2.0-dev` na finalne `v1.2.0`. Uruchom HELM ponownie z finalnego commita i
dopiero wtedy wykonaj obrazy zgodnie z [SCREENSHOTS.md](SCREENSHOTS.md). Numer
w sidebarze i modalu bootowania musi odpowiadać plikowi `VERSION`.

## 6. Walidacja release candidate

```bash
cd ~/.cyberdeck/nexus

scripts/check-release.sh
scripts/desktop/doctor.sh
git diff --check

git status --short --branch
git diff --stat
git diff
```

Docelowy pełny CyberDeck powinien zakończyć doctor stanem `SYSTEM STATE: NOMINAL`.
Każde ostrzeżenie musi być zrozumiane przed wydaniem.

## 7. Commit przygotowania wydania

```bash
git add -A
git diff --cached --check
git diff --cached --stat
git commit -m "Prepare HELM CyberDeck OS v1.2.0 release"
git push origin feature/helm-v1.2.0
```

Po pushu powtórz release check i sprawdź GitHub Actions.

## 8. Merge do `master`

```bash
git switch master
git pull --ff-only origin master
git merge --no-ff feature/helm-v1.2.0 \
    -m "Merge HELM CyberDeck OS v1.2.0"

scripts/check-release.sh
scripts/desktop/doctor.sh
git status --short --branch
```

## 9. Tag i push

Tag twórz na sprawdzonym commicie merge:

```bash
git tag -a v1.2.0 -m "HELM CyberDeck OS v1.2.0"
git push origin master
git push origin v1.2.0
```

Zweryfikuj:

```bash
git show --stat --oneline v1.2.0
git ls-remote --tags origin v1.2.0
```

## 10. GitHub Release

```bash
gh release create v1.2.0 \
    --title "HELM CyberDeck OS v1.2.0" \
    --notes-file RELEASE_NOTES_v1.2.0.md
```

Na stronie repozytorium sprawdź:

- poprawne renderowanie README i diagramów Mermaid;
- wszystkie obrazy;
- zielony workflow Python checks;
- tag i release wskazujące ten sam commit;
- brak plików runtime, backupów, logów i sekretów;
- poprawny tekst `VERSION`.

## 11. Powrót po błędzie

Przed push/tagiem można przerwać merge:

```bash
git merge --abort
```

Po wypchnięciu `master` nie przepisuj historii. Napraw błąd nowym commitem i, jeśli
wydanie jest wadliwe, oznacz release jako draft/prerelease lub opublikuj następną
wersję poprawkową.
