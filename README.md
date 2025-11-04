Ein interaktives, desktop-basiertes Vokabeltrainer-Tool, entwickelt in Python unter Verwendung
von Tkinter für die grafische Benutzeroberfläche. Dieses Tool ist darauf ausgelegt, das Üben von
Vokabeln in verschiedenen Sprachen durch eine intuitive Oberfläche und anpassbare
Sprachpaare zu erleichtern.

Features
GUI-basiert: Eine benutzerfreundliche grafische Oberfläche, erstellt mit tkinter.
Anpassbare Sprachpaare: Schnelles Umschalten zwischen verschiedenen Sprachkombinationen.
Mehrsprachig: Unterstützt standardmäßig Deutsch, Englisch, Italienisch, Spanisch und Französisch.
Hotkeys: Produktives Üben durch Tastaturkürzel für häufige Aktionen.
Tooltip-Unterstützung: Hilfreiche Tooltips (Hover-Texte) für eine bessere Usability.
Lokale Speicherung (Vorbereitet/Geplant): Nutzung einer lokalen Struktur (einfache Python-dict-Datenbank 
im aktuellen Prototyp), die leicht auf eine persistente SQLite-Datenbank umgestellt werden kann 
(im aktuellen Code-Kommentar erwähnt, aber noch nicht implementiert).
Online-Übersetzung (Optional): Vorbereitung zur dynamischen Ergänzung der Datenbank mit dem 
googletrans-Paket (optional, im aktuellen Prototyp noch nicht aktiv).

Installation & Voraussetzungen
Das Projekt basiert auf Standardbibliotheken von Python, mit einer optionalen Abhängigkeit für erweiterte Funktionen.

1. Grundvoraussetzungen
Stellen Sie sicher, dass Sie Python 3 installiert haben. tkinter und sqlite3 sind in der Regel in der Standardinstallation enthalten.

2. Optionale Abhängigkeit (Online-Übersetzung)
Falls Sie die optionale Funktion zur Online-Übersetzung nutzen möchten (setzt eine Implementierung des googletrans-Moduls voraus), installieren Sie die spezifische Version wie folgt:

Bash

pip install googletrans==4.0.0-rc1
3. Ausführung
Speichern Sie den Code in einer Datei (z.B. vokabeltrainer.py) und führen Sie ihn aus:

Bash

python vokabeltrainer.py

Hotkeys (Tastaturkürzel)Um den Lernprozess zu beschleunigen, wurden folgende Hotkeys implementiert:AktionHotkeyBeschreibung
Nächstes WortSpace (Leertaste)Zeigt das nächste zufällige Wort an.Antwort prüfen
EnterÜberprüft die Eingabe im Textfeld.Englisch -> DeutschStrg+EWechselt zum Sprachpaar Englisch -> Deutsch.Deutsch -> EnglischStrg+DWechselt
zum Sprachpaar Deutsch -> Englisch.Italienisch -> DeutschStrg+IWechselt zum Sprachpaar Italienisch -> Deutsch.Spanisch -> DeutschStrg+SWechselt
zum Sprachpaar Spanisch -> Deutsch.Französisch -> DeutschStrg+FWechselt zum Sprachpaar Französisch -> Deutsch.

🛠️ Technische Details (Code-Struktur)Der Code ist in logische Abschnitte unterteilt:Datenbank (VOCABULARY): Eine einfache dict-Struktur dient
im Prototyp als Vokabelspeicher.Hilfsklasse (Tooltip): Eine wiederverwendbare Klasse für Tooltip-Funktionalität in Tkinter.
Hauptklasse (VocabularyTrainer): Initialisiert die GUI, verwaltet den Zustand und implementiert die gesamte Trainingslogik (set_language_pair, next_word, check_answer).

#########################################################################################################################################################################################################################################

 Die Integration von SQLite und die optionale Anbindung an googletrans heben den Vokabeltrainer auf eine professionelle Ebene.
 Besonders hervorzuheben ist die neue Funktionalität der manuellen Abfrage, die sowohl die Datenbank als auch den
 Online-Dienst nutzt und dabei die gelernten Wörter direkt speichert.

Ich habe das gesamte Programm in einer einzigen Python-Datei namens vokabeltrainer_v2.py zusammengefasst.

Verbesserungen in Version SpT2

SQLite-Persistenz: Die VOCABULARY-Datenbankstruktur wurde durch die SQLite-Datenbank vokabeln.db ersetzt.

Die Funktion initialize_db() sorgt dafür, dass die Tabelle existiert und beim ersten Start mit Initialdaten befüllt wird.

Die Methode fetch_all_words_for_pair() wurde implementiert, um Vokabeln für die Übung aus der Datenbank zu laden.

Online-Übersetzung (Robust):

Die Abhängigkeit zu googletrans ist nun optional und wird mit einem robusten try/except-Block gehandhabt.
Ist das Modul nicht installiert, wird die Online-Funktionalität deaktiviert, ohne das Programm zum Absturz zu bringen.

Die neue Kernmethode check_db_and_get_translation() prüft zuerst die lokale Datenbank und verwendet nur bei Fehlen den Online-Übersetzer.

Automatisches Speichern: Jede neue Übersetzung, die über den Online-Translator ermittelt wird, wird
automatisch in die SQLite-Datenbank eingefügt, um zukünftige Online-Anfragen zu vermeiden und die Trainingsbasis zu erweitern.

Hotkeys und Usability:

Erweiterte Hotkeys: Die Hotkeys für Deutsch -> Andere Sprache wurden mit Strg+Shift+[Buchstabe] (z.B. Strg+Shift+E für Deutsch -> Englisch)
ergänzt und in den Button-Texten kommuniziert.

Manuelle Abfrage: Ein neuer Abschnitt zur manuellen Abfrage (find_manual_translation) wurde hinzugefügt,
der Enter im Eingabefeld bindet und sofortige Übersetzungen liefert.

Datenbereinigung: Alle Wörter werden beim Speichern und Abfragen in der Datenbank als Kleinbuchstaben (.lower()) gespeichert,
um eine konsistente, case-insensitive Überprüfung zu gewährleisten.

Wichtige Aspekte für den Betrieb
SQLite-Dateipfad: Die Datenbankdatei vokabeln.db wird im selben Verzeichnis erstellt, in dem das Python-Skript ausgeführt wird.
Bei Problemen mit der Persistenz (z.B. wenn hinzugefügte Wörter nach dem Neustart fehlen) sollte geprüft werden, 
Logische Verfeinerungen
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
Attach files by dragging & dropping, selecting or pasting them.
New File at / · Rliegard/Sprachtrainer

