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

#########################################################################################################################################################################################################################################

Wichtigste Verbesserungen in SpT3:
Behoben: Korrekte Datenbank-Einfügung (Critical Fix)

Die Methode check_db_and_get_translation wurde korrigiert, um die Online-Übersetzung korrekt in die Datenbank zu speichern.

Vorher (SpT2): Die SQL-Anweisung hatte eine unklare Anzahl von Parametern.

Jetzt (SpT3): Die INSERT OR IGNORE Anweisung verwendet nun korrekt fünf Platzhalter (?,?,?,?,?) und übergibt präzise fünf Werte (word, src_lang, trg_lang, online_translation, 'Online').
Das verhindert potenzielle Laufzeitfehler beim Speichern neuer Online-Vokabeln.

Verbessert: Manuelle Suche und Fehlerhandling

Die Funktion find_manual_translation ist nun viel robuster und benutzerfreundlicher:

Fokus-Management: Der Cursor wird nun nach jeder Suche (egal ob erfolgreich oder fehlerhaft) korrekt auf das Eingabefeld zurückgesetzt (self.manual_entry.focus()).

Leere Eingabe: Die Funktion prüft sofort, ob das Eingabefeld leer ist, und kehrt zurück, ohne eine unnötige Datenbankabfrage zu starten.

Detailliertere Fehlermeldungen: Die Fehlermeldung, falls die Online-Übersetzung deaktiviert ist, ist nun viel klarer: ❌ Übersetzung nicht gefunden. Online-Übersetzung ist deaktiviert (googletrans fehlt oder Fehler).

Bereinigt: Hotkeys-Logik

Die überflüssige und verwirrende Hotkey-Zuweisung für <Control-Key-d> (Deutsch -> Englisch) wurde aus der __init__ Methode entfernt, da diese Zuweisung ohnehin doppelt mit <Control-Shift-E> belegt war

########################################################################################################################################################################################################################################


Zusammenfassung der Verbesserungen von SpT3 zu SpT4
Die Hauptverbesserungen in SpT4 drehen sich um die Integration der Sprachausgabe (Text-to-Speech, TTS), die Erweiterung der Benutzeroberfläche und die Strukturierung des Codes für mehr Stabilität.
SpT4 (Verbesserung)Kernfunktion
Fügt asynchrone Sprachausgabe (TTS) hinzu.
Architektur (TTS)
Nutzt pyttsx3 und den threading-Modul, um die TTS-Ausgabe nicht-blockierend auszuführen.
TTS-Implementierung
Die TTS-Engine wird innerhalb des Threads initialisiert und gestoppt, um Ressourcen freizugeben und Deadlocks zu vermeiden (eine kritische Verbesserung für pyttsx3).
Benutzererfahrung 
Modernisiertes Design (style.theme_use('clam')), verbesserte Button-Styles.
Interaktion
Zusätzlicher TTS-Button (🔊 Vorlesen), der nach dem Prüfen der Antwort aktiviert wird, um die korrekte Lösung zu hören.
Visuelles Feedback
Hervorhebung der Buttons (Accent.TButton vs. Manual.TButton) nach der Prüfung, um den nächsten logischen Schritt
(Prüfen oder Nächstes Wort) zu signalisieren.
Initialdaten
Erweiterung der Initialdaten um weitere Sprachpaare (Italienisch-Deutsch, Französisch-Englisch),
um die Mehrsprachigkeit zu demonstrieren.
Die größte architektonische Änderung: 
Threading für TTSDie Einführung der TTS-Funktionalität in SpT4 ist nicht trivial.
Da die pyttsx3.runAndWait()-Methode das Hauptprogramm blockieren würde, wurde die gesamte Sprachlogik in einen separaten Thread (_tts_thread) ausgelagert.

Kann nur einmal eine Sprachausgabe tätigen, muss über arbeitet werden

#########################################################################################################################################################################################################################################

SpT5
Versuch es für Android-Sasteme nutzbar zu machen
Ubuntu auf Windows lauffähig zu machen
Nicht ganz ausgereift (Testversuch)

#########################################################################################################################################################################################################################################

SpT6
Die Hauptunterschiede und Verbesserungen konzentrieren sich auf die Behandlung des Fensterschließens und des Beenden-Vorgangs der App.

Sauberes Beenden (on_closing)
NEU: Die Methode on_closing wird hinzugefügt. Sie ruft self.master.destroy() und sys.exit() auf, was eine garantierte und saubere Beendigung aller Prozesse (auch Daemon-Threads) sicherstellt

Fensterprotokoll
NEU: self.master.protocol("WM_DELETE_WINDOW", self.on_closing) wird hinzugefügt. Dies fängt den Klick auf das standardmäßige Schließ-X des Fensters ab und leitet ihn an die neue, saubere on_closing-Methode weiter.

NEU: Ein auffälliger "❌ Beenden (Ctrl+Q)" Button wird in der oberen rechten Ecke (row=0, column=1) hinzugefügt und mit dem neuen Exit.TButton-Style (rot) versehen.

NEU: Der Style Exit.TButton (#EF4444 rot) wird für den neuen Beenden-Button definiert.

Das Problem, das es nur einmal eine Sprachausgabe gibt ist behoben worden!! 
#########################################################################################################################################################################################################################################

SpT7
Startbidschirm hinzugefügt.
Programm startet im Fullscreen-Modus

#########################################################################################################################################################################################################################################
