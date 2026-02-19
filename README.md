# ⬡ WG Monitor

> Moniteur système Windows — Dark, Light, Midnight & Red themes

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![customtkinter](https://img.shields.io/badge/UI-customtkinter-blueviolet?style=flat-square)
![psutil](https://img.shields.io/badge/stats-psutil-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square&logo=windows)

---

## 📸 Aperçu

| 🌙 Dark | ☀️ Light |
|--------|---------|
<<<<<<< HEAD
| <img width="1102" height="812" alt="Dark" src="https://github.com/user-attachments/assets/b8b71ff4-2a9d-4acd-83dc-94d2899d1f6a" /> | <img width="1102" height="812" alt="Light" src="https://github.com/user-attachments/assets/f634c4e9-fc87-4429-bbca-324cb96988b8" /> |

| 🌊 Midnight | 🔥 Red |
|------------|-------|
| <img width="1102" height="812" alt="Midnight" src="https://github.com/user-attachments/assets/3ffe086c-2686-4df9-aaca-7dc270aba976" /> | <img width="1102" height="812" alt="Red" src="https://github.com/user-attachments/assets/5fff8e3e-86dd-4832-bade-acd7bf6a2b34" /> |
=======
| <img width="1102" height="812" alt="image" src="https://github.com/user-attachments/assets/b8b71ff4-2a9d-4acd-83dc-94d2899d1f6a" />
| <img width="1102" height="812" alt="image" src="https://github.com/user-attachments/assets/f634c4e9-fc87-4429-bbca-324cb96988b8" />|

| 🌊 Midnight | 🔥 Red |
|------------|-------|
| <img width="1102" height="812" alt="image" src="https://github.com/user-attachments/assets/3ffe086c-2686-4df9-aaca-7dc270aba976" />
 | <img width="1102" height="812" alt="image" src="https://github.com/user-attachments/assets/5fff8e3e-86dd-4832-bade-acd7bf6a2b34" />
 |
>>>>>>> c35c3a9e638d574c979eeb2b7582845aa651846e

---

## ✨ Fonctionnalités

- **CPU** — Utilisation globale + barre animée par cœur (jusqu'à 16), fréquence en temps réel
- **Mémoire** — RAM + SWAP + stats Available / Cached / Buffers
- **Disque** — Détection automatique des partitions (Windows / Linux / Disque externe)
- **Réseau** — Débit ▼/▲ en temps réel + mini graphe animé 60 fps
- **Système** — Détection correcte Windows 11 (via build number)
- **Theme Manager** — 4 thèmes intégrés, extensible facilement
- **Interface responsive** — S'adapte à la taille de la fenêtre, sans scrollbar

---

## 🚀 Installation

### Prérequis

- Python **3.8+**
- Windows 10 / 11

### 1. Cloner le repo

```bash
git clone https://github.com/TON_USERNAME/wg-monitor.git
cd wg-monitor
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer

```bash
python wg_monitor.py
```

---

## 📦 Compiler en `.exe`

```bash
build.bat
```

L'exécutable sera généré dans `dist/WGMonitor.exe`.

> **Note :** Ajuste le chemin `--add-data` dans `build.bat` selon ton installation Python si nécessaire.

---

## 🎨 Ajouter un thème

Dans `wg_monitor.py`, ajoute une entrée dans le dict `THEMES` :

```python
"MonTheme": {
    "mode":      "dark",          # "dark" ou "light"
    "accent":    "#hexcolor",
    "accent2":   "#hexcolor",
    "bg_main":   "#hexcolor",
    "bg_card":   "#hexcolor",
    "bg_card2":  "#hexcolor",
    "bg_border": "#hexcolor",
    "text_pri":  "#hexcolor",
    "text_sec":  "#hexcolor",
    "text_mut":  "#hexcolor",
    "green":     "#hexcolor",
    "orange":    "#hexcolor",
    "red":       "#hexcolor",
    "blue":      "#hexcolor",
    "icon":      "🎯",            # Emoji affiché dans le sélecteur
},
```

C'est tout — il apparaît automatiquement dans le popup de sélection.

---

## 🧰 Stack

| Lib | Rôle |
|-----|------|
| `customtkinter` | UI moderne style Windows 11 |
| `psutil` | Stats CPU, RAM, disque, réseau |
| `pyinstaller` | Compilation `.exe` |

---

## 📁 Structure

```
wg-monitor/
├── wg_monitor.py      # Application principale
├── requirements.txt   # Dépendances pip
├── build.bat          # Script PyInstaller
└── README.md
```

---

## 📄 Licence

MIT — libre d'utilisation et de modification.
