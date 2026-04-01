# DiagDocu_Agent

> **GitHub Copilot Extension** that generates diagnostic documentation (DiagDocu)
> for automotive ECU software directly from C/H source files and A2L calibration
> description files.

---

## So geht's (Schnellstart)

1. Öffne einen neuen Copilot Chat (oder nutze den aktuellen Chat).
2. Klicke auf das **Agent-Dropdown** im Chat-Eingabefeld (Symbol links neben dem Textfeld, oder tippe einfach `@`).
3. Wähle **DiagDocu** aus der Liste.
4. Gib deine Anfrage ein, z. B.:

   ```
   Erstelle die DiagDocu für DFC_rbe_CddUTnet_UTnet1Plaus
   ```

Der Agent analysiert automatisch die C-, H- und A2L-Quelldateien und erstellt eine strukturierte Markdown-Dokumentation.

---

## Funktionsweise

```
Eingabe:  "Erstelle die DiagDocu für DFC_rbe_CddUTnet_UTnet1Plaus"
              │
              ▼
      ┌───────────────────┐
      │  DFC-Name extrahieren │
      └───────────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  C/H-Parser     A2L-Parser
  (Funktionen,   (MEASUREMENT,
   Makros,        CHARACTERISTIC)
   Kommentare)
       │             │
       └──────┬──────┘
              ▼
      ┌───────────────────┐
      │  DiagDocu-Generator │
      └───────────────────┘
              │
              ▼
   Markdown-Dokumentation
   (via SSE an Copilot Chat)
```

Die generierte DiagDocu enthält:

| Abschnitt | Inhalt |
|-----------|--------|
| **1. Übersicht** | DFC-Name, Typ, Quelldateien |
| **2. Eingangsgrößen** | Funktions-Signaturen aus dem C-Code |
| **3. Fehlerbedingungen** | `#define`-Makros und Enum-Werte |
| **4. Fehlerspeicherung** | Debouncing- und Heal-Parameter (Template) |
| **5. Kalibrierparameter** | MEASUREMENT / CHARACTERISTIC aus der A2L |
| **6. Quellcode-Referenzen** | Pfade zu allen gefundenen Dateien |

---

## Architektur

```
DiagDocu_Agent/
├── agent/
│   ├── app.py               # FastAPI-Server (GitHub Copilot Extension Endpoint)
│   ├── diagdocu.py          # Kernlogik: DFC-Extraktion & Dokumentationsgenerator
│   └── parsers/
│       ├── c_parser.py      # Parser für C- und H-Quelldateien
│       └── a2l_parser.py    # Parser für ASAP2 (A2L) Kalibrierungsdateien
├── tests/
│   ├── fixtures/            # Beispiel-Quelldateien für Tests
│   ├── test_c_parser.py
│   ├── test_a2l_parser.py
│   ├── test_diagdocu.py
│   └── test_app.py
└── requirements.txt
```

---

## Setup

### Voraussetzungen

- Python ≥ 3.12
- GitHub-App mit Copilot Extension Berechtigung

### Installation

```bash
pip install -r requirements.txt
```

### Server starten

```bash
# Optional: Pfad zu den Quelldateien angeben
export SOURCE_ROOT=/path/to/your/ecu/sources

uvicorn agent.app:app --host 0.0.0.0 --port 8080
```

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|--------------|---------|
| `SOURCE_ROOT` | Wurzelverzeichnis mit C/H- und A2L-Dateien | aktuelles Verzeichnis |
| `PORT` | TCP-Port des Servers | `8080` |

### Tests ausführen

```bash
pytest tests/ -v
```

---

## GitHub Copilot Extension einrichten

1. Erstelle eine **GitHub App** unter *Settings → Developer settings → GitHub Apps*.
2. Aktiviere **Copilot** unter *Permissions & Events → Copilot Chat → Read* (Agent type).
3. Setze die **Callback URL** auf deine Server-URL, z. B. `https://your-server.example.com/`.
4. Veröffentliche die App und installiere sie in deiner Organisation.
5. Der Agent erscheint danach im Copilot-Chat-Dropdown unter dem Namen der GitHub App.

Detaillierte Anleitung: [GitHub Copilot Extensions documentation](https://docs.github.com/en/copilot/building-copilot-extensions)

---

## Beispielausgabe

```markdown
# DiagDocu: `DFC_rbe_CddUTnet_UTnet1Plaus`

## 1. Übersicht
| Attribut | Wert |
|----------|------|
| DFC-Name | `DFC_rbe_CddUTnet_UTnet1Plaus` |
| Typ      | Diagnostic Fault Code (DFC)   |

## 2. Eingangsgrößen
```c
void DFC_rbe_CddUTnet_UTnet1Plaus_Run(void)
```

## 5. Kalibrierparameter (aus A2L)
### Messgrößen (MEASUREMENT)
| Name | Datentyp | ECU-Adresse | Beschreibung |
|------|----------|-------------|--------------|
| Rbe_CddUTnet_UTnet1PlausStatus | UBYTE | 0x20001234 | Status of UTnet1 plausibility DFC |
...
```
