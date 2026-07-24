# Publikacja repozytorium na GitHubie

Ten dokument opisuje publikację istniejącego lokalnego repozytorium HELM z zachowaniem całej historii commitów i taga `v1.0.0`.

## 1. Zabezpiecz lokalne dane i wgraj pliki publikacyjne

Najpierw zachowaj własne ustawienia, projekty i tryby, ponieważ paczka zawiera oczyszczoną konfigurację demonstracyjną przeznaczoną do publicznego repozytorium.

```bash
mkdir -p ~/HELM-local-config-backup
cp ~/.cyberdeck/nexus/config/settings.json ~/HELM-local-config-backup/
cp ~/.cyberdeck/nexus/config/modes.json ~/HELM-local-config-backup/
cp ~/.cyberdeck/nexus/config/projects.json ~/HELM-local-config-backup/
cp ~/.cyberdeck/nexus/config/mode_state.json ~/HELM-local-config-backup/ 2>/dev/null || true
```

Rozpakuj paczkę publikacyjną poza katalogiem projektu, a następnie skopiuj jej zawartość do `~/.cyberdeck/nexus`. Nie usuwaj katalogu `.git` ani danych runtime.

```bash
mkdir -p ~/HELM-public-release
tar -xzf ~/HELM-CyberDeck-OS-public-v1.0.0.tar.gz \
    -C ~/HELM-public-release \
    --strip-components=1

rsync -av --delete \
    --exclude='.git/' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --exclude='logs/*.log' \
    --exclude='logs/exports/' \
    --exclude='config/backups/' \
    --exclude='config/exports/' \
    --exclude='config/mode_state.json' \
    ~/HELM-public-release/ \
    ~/.cyberdeck/nexus/
```

`--delete` usuwa stare pliki źródłowe, których nie ma w czystej paczce. Wykluczenia chronią historię Git, środowisko wirtualne, logi, eksporty, backupy i aktywny lokalny tryb.

## 2. Uruchom kontrolę wydania

```bash
cd ~/.cyberdeck/nexus
source venv/bin/activate
./scripts/check-release.sh
git status --short
```

Przejrzyj zmiany:

```bash
git diff --stat
git diff -- README.md README.pl.md .gitignore
```

## 3. Zapisz dokumentację w historii

```bash
git add -A
git commit -m "Prepare public GitHub release documentation"
```

Istniejący tag `v1.0.0` wskazuje wcześniejszy commit interfejsu. Aby wydanie GitHub zawierało również dokumentację, przesuń tag na nowy commit:

```bash
git tag -d v1.0.0
git tag -a v1.0.0 -m "HELM CyberDeck OS v1.0.0"
```

## 4. Zainstaluj i zaloguj GitHub CLI

```bash
sudo pacman -S --needed github-cli
gh auth login
```

W kreatorze wybierz GitHub.com, HTTPS i logowanie przez przeglądarkę. Sprawdź sesję:

```bash
gh auth status
```

## 5. Utwórz publiczne repozytorium i wyślij kod

```bash
cd ~/.cyberdeck/nexus

gh repo create HELM-CyberDeck-OS \
    --public \
    --source=. \
    --remote=origin \
    --description "Cyberpunk terminal control center for Arch Linux with telemetry, diagnostics, UART, workspaces and local Ollama AI." \
    --push
```

Wyślij tag:

```bash
git push origin v1.0.0 --force
```

`--force` jest potrzebne tylko dlatego, że lokalny tag został przesunięty z wcześniejszego commita na końcowy commit dokumentacji. Nie używaj go do gałęzi `master`.

## 6. Utwórz wydanie GitHub

```bash
gh release create v1.0.0 \
    --title "HELM CyberDeck OS v1.0.0" \
    --notes-file RELEASE_NOTES_v1.0.0.md
```

## 7. Ustaw tematy repozytorium

```bash
gh repo edit \
    --add-topic arch-linux \
    --add-topic cyberdeck \
    --add-topic textual \
    --add-topic python \
    --add-topic terminal-ui \
    --add-topic ollama \
    --add-topic system-monitor \
    --add-topic embedded \
    --add-topic uart
```

## 8. Końcowa kontrola

```bash
gh repo view --web
```

Na stronie sprawdź:

- czy obraz SYSTEM pojawia się na początku README;
- czy README przełącza się na wersję polską;
- czy zakładka Actions przechodzi test `Python checks`;
- czy release `v1.0.0` istnieje;
- czy w repozytorium nie ma logów, backupów ani `mode_state.json`.

## 9. Opcjonalnie przywróć prywatną konfigurację po publikacji

Publiczny commit powinien zawierać oczyszczone pliki z paczki. Po wysłaniu repozytorium możesz przywrócić własne dane do lokalnej maszyny:

```bash
cp ~/HELM-local-config-backup/settings.json ~/.cyberdeck/nexus/config/
cp ~/HELM-local-config-backup/modes.json ~/.cyberdeck/nexus/config/
cp ~/HELM-local-config-backup/projects.json ~/.cyberdeck/nexus/config/
cp ~/HELM-local-config-backup/mode_state.json ~/.cyberdeck/nexus/config/ 2>/dev/null || true
```

Te pliki mogą wtedy pojawić się jako lokalne zmiany w `git status`. Nie wypychaj ich bez ponownego przeglądu.
