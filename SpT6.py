import tkinter as tk
from tkinter import ttk, messagebox
import random
import sqlite3
import os
import threading
import sys

# --- WICHTIG: NEUE TTS IMPORTZEILE ---
try:
    import pyttsx3
    # Engine wird nur noch im Thread initialisiert.
    TTS_ENGINE = None
    REAL_TTS_ENABLED = True
except ImportError:
    print("Warnung: pyttsx3 ist nicht installiert. Echte TTS ist deaktiviert. Bitte 'pip install pyttsx3' ausführen.")
    REAL_TTS_ENABLED = False
except Exception as e:
    print(f"Warnung: Fehler beim Importieren von pyttsx3: {e}. Echte TTS ist deaktiviert.")
    REAL_TTS_ENABLED = False

# --- GOOGLETRANS IMPORT ---
try:
    from googletrans import Translator
    translator = Translator()
    ONLINE_TRANSLATION_ENABLED = True
except ImportError:
    print("Warnung: Die 'googletrans' Bibliothek wurde nicht gefunden. Online-Übersetzung ist deaktiviert.")
    ONLINE_TRANSLATION_ENABLED = False
except Exception as e:
    print(f"Warnung: Konnte den Online-Translator nicht initialisieren: {e}. Online-Übersetzung ist deaktiviert.")
    ONLINE_TRANSLATION_ENABLED = False


# --- 1. GLOBALE KONSTANTEN UND DATENBANK-SETUP ---
DB_NAME = "vokabeln.db"
LANGUAGES = ["Englisch", "Deutsch", "Italienisch", "Spanisch", "Französisch"]

# Map für Googletrans Codes
LANG_CODES = {
    "Englisch": "en", "Deutsch": "de", "Italienisch": "it",
    "Spanisch": "es", "Französisch": "fr"
}


def initialize_db():
    """Erstellt die SQLite-Datenbank und die Vokabeltabelle."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Tabelle für Vokabeln (Wort, Quellsprache, Zielsprache, Übersetzung)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY,
                source_word TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                target_word TEXT NOT NULL,
                source TEXT NOT NULL,
                UNIQUE (source_word, source_lang, target_lang)
            )
        """)
        conn.commit()

        # Initialdaten einfügen, falls die Datenbank leer ist
        if not cursor.execute("SELECT 1 FROM vocabulary LIMIT 1").fetchone():
            initial_data = [
                ("apple", "Englisch", "Deutsch", "Apfel"),
                ("house", "Englisch", "Deutsch", "Haus"),
                ("water", "Englisch", "Deutsch", "Wasser"),
                ("to walk", "Englisch", "Deutsch", "gehen"),
                ("beautiful", "Englisch", "Deutsch", "schön"),
                ("dog", "Englisch", "Deutsch", "Hund"),
                ("cat", "Englisch", "Deutsch", "Katze"),
                ("apple", "Englisch", "Italienisch", "mela"),
                ("house", "Englisch", "Spanisch", "casa"),
                ("to walk", "Englisch", "Französisch", "marcher"),
                ("Apfel", "Deutsch", "Englisch", "apple"),
                ("Käse", "Deutsch", "Englisch", "cheese"),
                ("schlafen", "Deutsch", "Englisch", "to sleep"),
                ("Garten", "Deutsch", "Französisch", "jardin"),
                ("caminare", "Italienisch", "Deutsch", "gehen"),
                ("le chat", "Französisch", "Englisch", "the cat"),
            ]

            for word, src_lang, trg_lang, trg_word in initial_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO vocabulary (source_word, source_lang, target_lang, target_word, source) 
                    VALUES (?, ?, ?, ?, 'DB')
                """, (word.lower(), src_lang, trg_lang, trg_word.lower()))

            conn.commit()

        conn.close()
        return True
    except Exception as e:
        messagebox.showerror("Datenbankfehler", f"Konnte die SQLite-Datenbank nicht initialisieren: {e}")
        return False

# --- 2. HILFSKLASSE (Tooltip) ---
class Tooltip:
    """
    Erstellt einen Tooltip für ein Tkinter-Widget.
    Zeigt sich nur beim Überfahren mit dem Cursor.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None
        self.after_id = None

    def enter(self, event=None):
        self.schedule()

    def schedule(self):
        """Plant die Anzeige des Tooltips nach 500ms."""
        self.unschedule()
        self.after_id = self.widget.after(500, self.show)

    def unschedule(self):
        """Bricht die geplante Anzeige ab."""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show(self):
        """Zeigt den Tooltip an."""
        if self.tw: return

        # Positionierung des Tooltips
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True) # Entfernt den Fensterrahmen
        self.tw.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(self.tw, text=self.text, justify='left',
                          background="#ffffe0", relief='solid', borderwidth=1,
                          font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        """Schließt den Tooltip sofort."""
        self.unschedule()
        if self.tw:
            self.tw.destroy()
            self.tw = None


# --- 3. HAUPTKLASSE (Vokabeltrainer) ---
class VocabularyTrainer:
    def __init__(self, master):
        self.master = master
        master.title("🌍 Vokabeltrainer (Python/Tkinter)")
        master.geometry("750x600")

        if not initialize_db():
            master.quit()
            return

        # Zustand
        self.current_source_lang = "Englisch"
        self.current_target_lang = "Deutsch"
        self.current_word = None
        self.current_solution = ""

        # UI Setup
        self.create_widgets()
        self.update_selection_display()
        self.next_word()

        # Globale Hotkeys binden
        self.master.bind('<Control-Key-e>', lambda e: self.set_language_pair("Englisch", "Deutsch"))
        self.master.bind('<Control-Key-i>', lambda e: self.set_language_pair("Italienisch", "Deutsch"))
        self.master.bind('<Control-Key-s>', lambda e: self.set_language_pair("Spanisch", "Deutsch"))
        self.master.bind('<Control-Key-f>', lambda e: self.set_language_pair("Französisch", "Deutsch"))
        self.master.bind('<Control-Shift-E>', lambda e: self.set_language_pair("Deutsch", "Englisch"))
        self.master.bind('<Control-Shift-I>', lambda e: self.set_language_pair("Deutsch", "Italienisch"))
        self.master.bind('<Control-Shift-S>', lambda e: self.set_language_pair("Deutsch", "Spanisch"))
        self.master.bind('<Control-Shift-F>', lambda e: self.set_language_pair("Deutsch", "Französisch"))
        self.master.bind('<space>', lambda e: self.next_word())
        # NEU: Hotkey für Beenden
        self.master.bind('<Control-Key-q>', lambda e: self.on_closing())


        # Behandelt das Schließen des Fensters
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.answer_entry.focus()

    def on_closing(self):
        """Beendet die Anwendung sauber."""
        # Da die TTS-Engine nun nur noch lokal in den Threads erstellt/gestoppt wird,
        # müssen wir hier nur das Hauptfenster zerstören.
        self.master.destroy()
        sys.exit() # Beendet auch alle Daemon-Threads

    def create_widgets(self):
        # Konfiguration des Haupt-Frames
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Konfiguriere Stile (für ein moderneres Aussehen)
        style = ttk.Style()
        style.theme_use('clam') # Wähle ein modernes Theme
        style.configure('Accent.TButton', foreground='white', background='#10B981', font=('Arial', 10, 'bold'), borderwidth=0)
        style.map('Accent.TButton', background=[('active', '#059669')])

        style.configure('Manual.TButton', background='#e0f2f1', font=('Arial', 10, 'normal'))
        style.map('Manual.TButton', background=[('active', '#b2dfdb')])

        style.configure('TTS.TButton', foreground='white', background='#3B82F6', font=('Arial', 10, 'bold'), borderwidth=0)
        style.map('TTS.TButton', background=[('active', '#2563EB')])

        style.configure('Lang.TButton', background='#f3f4f6', font=('Arial', 9, 'normal'), borderwidth=0)
        style.map('Lang.TButton', background=[('active', '#e5e7eb')])

        # NEU: Beenden Button Style
        style.configure('Exit.TButton', foreground='white', background='#EF4444', font=('Arial', 9, 'bold'), borderwidth=0)
        style.map('Exit.TButton', background=[('active', '#DC2626')])


        # --- Sprachpaarauswahl (Oben links) ---
        ttk.Label(main_frame, text="Sprachpaar auswählen:", font=('Arial', 11, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)

        # Button-Frame für Sprachen
        lang_frame = ttk.Frame(main_frame)
        lang_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        # Flexiblere Spaltenkonfiguration für Buttons
        for i in range(4): lang_frame.columnconfigure(i, weight=1)

        hotkey_map = {'E': 'Englisch', 'I': 'Italienisch', 'S': 'Spanisch', 'F': 'Französisch'}

        col = 0
        for lang_char, lang_name in hotkey_map.items():
            btn_to_de = ttk.Button(lang_frame, text=f"{lang_name} -> Deutsch (Ctrl+{lang_char})",
                                   command=lambda l=lang_name: self.set_language_pair(l, "Deutsch"),
                                   style='Lang.TButton')
            btn_to_de.grid(row=0, column=col, padx=3, pady=5, sticky=(tk.W, tk.E))
            Tooltip(btn_to_de, f"Hotkey: Ctrl+{lang_char}")

            btn_from_de = ttk.Button(lang_frame, text=f"Deutsch -> {lang_name} (Ctrl+Shift+{lang_char})",
                                     command=lambda l=lang_name: self.set_language_pair("Deutsch", l),
                                     style='Lang.TButton')
            btn_from_de.grid(row=1, column=col, padx=3, pady=5, sticky=(tk.W, tk.E))
            Tooltip(btn_from_de, f"Hotkey: Ctrl+Shift+{lang_char}")
            col += 1

        # NEU: Beenden-Button (Oben rechts)
        btn_exit = ttk.Button(main_frame, text="❌ Beenden (Ctrl+Q)", command=self.on_closing, style='Exit.TButton')
        btn_exit.grid(row=0, column=1, sticky=tk.E, pady=(0, 10))
        Tooltip(btn_exit, "Schließt die Anwendung. Hotkey: Ctrl+Q")


        # --- Aktuelle Auswahl (Mitte) ---
        self.selection_label = ttk.Label(main_frame, text="", font=('Arial', 12, 'bold'), foreground='#005a9c')
        self.selection_label.grid(row=2, column=0, columnspan=2, pady=(15, 10), sticky=tk.W)


        # --- Manuelle Abfrage (Wort suchen) ---
        manual_frame = ttk.LabelFrame(main_frame, text="Manuelle Abfrage (Wort suchen)", padding="10")
        manual_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        manual_frame.columnconfigure(0, weight=1)

        input_manual_frame = ttk.Frame(manual_frame)
        input_manual_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        input_manual_frame.columnconfigure(0, weight=1)

        self.manual_entry = ttk.Entry(input_manual_frame, font=('Arial', 12))
        self.manual_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.manual_entry.bind('<Return>', self.find_manual_translation)

        self.manual_button = ttk.Button(input_manual_frame, text="Übersetzung finden (Enter)",
                                        command=self.find_manual_translation,
                                        style='Manual.TButton')
        self.manual_button.grid(row=0, column=1)

        self.manual_result_label = ttk.Label(manual_frame, text="", font=('Arial', 11, 'bold'))
        self.manual_result_label.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)


        # --- Aufgabenbereich (Vokabelübung) ---
        task_frame = ttk.LabelFrame(main_frame, text="Vokabelübung", padding="15")
        task_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))
        task_frame.columnconfigure(0, weight=1)
        task_frame.columnconfigure(1, weight=1)


        # Anzeige des aktuellen Worts
        self.word_label = ttk.Label(task_frame, text="Wort: [Wählen Sie ein Paar]", font=('Arial', 18, 'bold'), foreground='#374151')
        self.word_label.grid(row=0, column=0, columnspan=2, pady=(5, 15))


        # Frame für Eingabe und Buttons
        input_button_frame = ttk.Frame(task_frame)
        input_button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        input_button_frame.columnconfigure(0, weight=1)

        ttk.Label(input_button_frame, text="Ihre Übersetzung:", font=('Arial', 12)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=(0, 3))


        self.answer_entry = ttk.Entry(input_button_frame, font=('Arial', 14))
        self.answer_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.answer_entry.bind('<Return>', self.check_answer)

        self.check_button = ttk.Button(input_button_frame, text="Prüfen (Enter)", command=self.check_answer, style='Accent.TButton')
        self.check_button.grid(row=1, column=1, padx=(0, 5))

        # NEU: TTS Button
        self.tts_button = ttk.Button(input_button_frame, text="🔊 Vorlesen", command=self.speak_solution, style='TTS.TButton', state=tk.DISABLED)
        self.tts_button.grid(row=1, column=2)

        self.result_label = ttk.Label(task_frame, text="", font=('Arial', 12, 'bold'))
        self.result_label.grid(row=2, column=0, columnspan=2, pady=(10, 5))

        self.next_button = ttk.Button(task_frame, text="Nächstes Wort (Space)", command=self.next_word, style='Accent.TButton')
        self.next_button.grid(row=3, column=0, columnspan=2, pady=(10, 5), sticky=(tk.W, tk.E), padx=5)


    # --- HILFSFUNKTION FÜR TTS-THREAD (KORREKTUR: NEU-INITIALISIERUNG INNERHALB DES THREADS) ---
    def _tts_thread(self, solution, lang_code):
        """
        Interne Funktion, die in einem separaten Thread ausgeführt wird.
        Die Engine wird *innerhalb* des Threads initialisiert und gestoppt.
        """
        engine = None
        try:
            # Engine nur HIER initialisieren
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)

            # 1. Stimmen-Setup
            voices = engine.getProperty('voices')
            if lang_code:
                for voice in voices:
                    # Sucht nach dem Sprachcode in der ID/Namens-Zeichenkette
                    if lang_code in voice.id.lower() or lang_code in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break

            # 2. TTS ausführen (blockiert nur diesen Thread)
            engine.say(solution)
            engine.runAndWait()

        except Exception as e:
            # Fehler im Thread abfangen und auf der GUI anzeigen
            self.master.after(0, lambda: messagebox.showerror("TTS Fehler", f"Konnte das Wort nicht aussprechen: {e}"))
            print(f"Fehler im TTS-Thread: {e}")

        finally:
            # 3. Engine sofort stoppen/beenden (wichtig für die Freigabe der Ressourcen)
            if engine:
                engine.stop()

            # 4. Button im Haupt-GUI-Thread wieder aktivieren
            self.master.after(0, lambda: self.tts_button.config(state=tk.NORMAL))


    # --- 4. TTS LOGIK ---
    def speak_solution(self):
        """
        Gibt die Lösung in einem separaten Thread aus.
        """
        if not self.current_solution:
            return

        if not REAL_TTS_ENABLED:
            messagebox.showinfo("Sprachausgabe (SIMULIERT)",
                                f"Lösung: '{self.current_solution.capitalize()}'\n\n"
                                "Für echte TTS bitte 'pip install pyttsx3' ausführen und die App neu starten.")
            return

        self.tts_button.config(state=tk.DISABLED)

        # Bestimme den Sprachcode. **Wichtig:** Wir wollen die Zielsprache sprechen.
        lang_code = LANG_CODES.get(self.current_target_lang)

        # Starte die Sprachausgabe in einem separaten Thread
        tts_thread = threading.Thread(target=self._tts_thread, args=(self.current_solution.capitalize(), lang_code))
        tts_thread.daemon = True # Wichtig: Thread beenden, wenn Hauptprogramm beendet
        tts_thread.start()


    # --- 5. LOGIK-METHODEN (Datenbank- und Online-Translator-Nutzung) ---

    def check_db_and_get_translation(self, word, src_lang, trg_lang):
        """Prüft die DB und nutzt bei Fehlen den Online-Translator."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Datenbank-Abfrage
        cursor.execute("""
            SELECT target_word FROM vocabulary 
            WHERE source_lang = ? AND source_word = ? AND target_lang = ?
        """, (src_lang, word, trg_lang))

        result = cursor.fetchone()

        if result:
            conn.close()
            return result[0], "DB"

        # 2. Online-Übersetzung, falls nicht in DB
        if ONLINE_TRANSLATION_ENABLED:
            try:
                if src_lang not in LANG_CODES or trg_lang not in LANG_CODES:
                    conn.close()
                    return None, "Sprachcode fehlt"

                trans = translator.translate(word, src=LANG_CODES[src_lang], dest=LANG_CODES[trg_lang])

                # Manchmal liefert Googletrans Listen zurück, nimm den Text.
                online_translation = trans.text.strip().lower()

                # Speichere die Online-Übersetzung in der Datenbank
                cursor.execute("""
                    INSERT OR IGNORE INTO vocabulary (source_word, source_lang, target_lang, target_word, source) 
                    VALUES (?, ?, ?, ?, ?)  
                """, (word, src_lang, trg_lang, online_translation, 'Online'))
                conn.commit()
                conn.close()
                return online_translation, "Online"

            except Exception as e:
                conn.close()
                # Fehlermeldung im Console-Output und als Source-Typ zurückgeben
                print(f"Online-Übersetzungsfehler: {e}")
                return None, f"Fehler: {e}"

        conn.close()
        return None, "Deaktiviert"


    def set_language_pair(self, source_lang, target_lang):
        """Setzt das aktuelle Sprachpaar und startet eine neue Runde."""
        self.current_source_lang = source_lang
        self.current_target_lang = target_lang
        self.update_selection_display()
        self.next_word()
        self.manual_result_label.config(text="")

    def update_selection_display(self):
        """Aktualisiert die Anzeige des aktuellen Sprachpaars."""
        self.selection_label.config(text=f"Aktuelles Paar: {self.current_source_lang} -> {self.current_target_lang}")

    def fetch_all_words_for_pair(self):
        """Holt alle verfügbaren Vokabelpaare aus der Datenbank für das aktuelle Paar."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        src = self.current_source_lang
        trg = self.current_target_lang

        query = """
        SELECT source_word, target_word FROM vocabulary 
        WHERE source_lang = ? AND target_lang = ?
        """

        possible_words = cursor.execute(query, (src, trg)).fetchall()

        conn.close()
        return possible_words

    def next_word(self):
        """Wählt ein zufälliges Wort basierend auf dem aktuellen Sprachpaar."""
        possible_words = self.fetch_all_words_for_pair()

        # Setzt die Buttons zurück in den normalen Akzentstil
        self.next_button.config(style='Accent.TButton')
        self.check_button.config(style='Accent.TButton')


        self.tts_button.config(state=tk.DISABLED) # TTS Button deaktivieren, bis die Antwort geprüft ist

        if not possible_words:
            self.word_label.config(text=f"Keine Vokabeln für {self.current_source_lang} -> {self.current_target_lang} gefunden.")
            self.result_label.config(text="Versuchen Sie, manuell ein Wort zu suchen. Es wird dann gespeichert!", foreground='black')
            self.current_word = None
            self.current_solution = ""
            self.answer_entry.delete(0, tk.END)
            return

        self.current_word, self.current_solution = random.choice(possible_words)

        self.word_label.config(text=f"Wort ({self.current_source_lang}): **{self.current_word.capitalize()}**")
        self.result_label.config(text="", foreground='black')
        self.answer_entry.delete(0, tk.END)
        self.answer_entry.focus()


    def check_answer(self, event=None):
        """Überprüft die eingegebene Übersetzung (Übungsteil)."""
        if not self.current_word:
            messagebox.showinfo("Info", "Bitte wählen Sie zuerst ein Sprachpaar oder klicken Sie auf 'Nächstes Wort'.")
            return

        user_answer = self.answer_entry.get().strip().lower()
        clean_solution = self.current_solution.lower()

        # Überprüfung: Case-insensitive und Whitespace-tolerant
        if user_answer == clean_solution:
            self.result_label.config(text=f"✅ Richtig! Lösung: {self.current_solution.capitalize()}", foreground='green')
            self.tts_button.config(state=tk.NORMAL) # TTS aktivieren

            # Hebe den "Nächstes Wort"-Button hervor.
            self.next_button.config(style='Manual.TButton')
            self.check_button.config(style='Accent.TButton')

        else:
            self.result_label.config(
                text=f"❌ Falsch. Richtig: {self.current_solution.capitalize()}",
                foreground='#cc0000'
            )
            self.tts_button.config(state=tk.NORMAL) # TTS aktivieren, um die Lösung zu hören
            # Hebe den "Prüfen"-Button hervor.
            self.check_button.config(style='Manual.TButton')
            self.next_button.config(style='Accent.TButton')


    def find_manual_translation(self, event=None):
        """Sucht die Übersetzung und nutzt Online-Translator, wenn nötig."""
        query_word = self.manual_entry.get().strip().lower()

        # Ergebnis-Label zurücksetzen
        self.manual_result_label.config(text="")

        if not query_word:
            self.manual_entry.focus()
            return

        src = self.current_source_lang
        trg = self.current_target_lang

        # Ruft die Logik auf, die DB und Online-Translator prüft
        translation, source_type = self.check_db_and_get_translation(query_word, src, trg)

        if translation and translation != query_word: # Vermeide Anzeige, wenn Wort sich selbst übersetzt (Fehler)
            source_info = f" (Quelle: {source_type})"
            self.manual_result_label.config(
                text=f"✅ {query_word.capitalize()} ({src}) = **{translation.capitalize()}** ({trg}){source_info}",
                foreground='#005a9c'
            )
            # Nach erfolgreicher manueller Suche, gleich zur nächsten Übung gehen
            self.next_word()
        else:
            if "Fehler:" in source_type:
                error_msg = f"❌ Online-Übersetzungsfehler: {source_type}"
            elif source_type == "Deaktiviert":
                error_msg = f"❌ Übersetzung nicht gefunden. Online-Übersetzung ist deaktiviert (googletrans fehlt oder Fehler)."
            else:
                error_msg = f"❌ Übersetzung für '{query_word.capitalize()}' nicht gefunden oder das Wort wurde bereits übersetzt."

            self.manual_result_label.config(text=error_msg, foreground='red')

        self.manual_entry.delete(0, tk.END)
        self.manual_entry.focus()


# --- 6. ANWENDUNG STARTEN ---
if __name__ == "__main__":
    root = tk.Tk()

    # Sicherstellen, dass die globale TTS_ENGINE (falls sie existiert) auf None gesetzt ist.
    if 'TTS_ENGINE' in globals():
        TTS_ENGINE = None

    app = VocabularyTrainer(root)

    root.mainloop()