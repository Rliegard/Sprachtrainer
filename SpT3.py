##############################################################################################
# Vokabeltrainer (Vocabulary Trainer)
# ==============================================================================
#
# Eine interaktive Desktop-Anwendung (GUI basiert auf Tkinter) zum Üben und
# Nachschlagen von Vokabeln in verschiedenen Sprachen. Die Anwendung verwendet
# eine lokale SQLite-Datenbank zur persistenten Speicherung der Vokabelpaare
# und bietet optional eine Online-Übersetzungsfunktion (Googletrans), um
# Vokabeln dynamisch zur Datenbank hinzuzufügen, falls diese fehlen.
#
# Sprachen: Deutsch, Englisch, Italienisch, Spanisch, Französisch
# Hotkeys:  Sprachpaare schnell wechseln (z.B. Strg+E für Englisch -> Deutsch)
#           Space zum Abrufen des nächsten Wortes.
#
# ------------------------------------------------------------------------------
# ABHÄNGIGKEITEN & VORAUSSETZUNGEN
# ------------------------------------------------------------------------------
#
# 1. Tkinter (Standard in den meisten Python-Distributionen)
# 2. SQLite3 (Standard in Python)
# 3. Googletrans (Optional für Online-Übersetzung)
#
# Installation für Online-Übersetzung:
# pip install googletrans==4.0.0-rc1
#
# ------------------------------------------------------------------------------
# AUTOR: Rainer Liegard
# ERSTELLT AM: 03.11.2025
# VERSION: SpT3
################################################################################################
import tkinter as tk
from tkinter import ttk, messagebox
import random
import sqlite3
import os

# WICHTIG: Installation: pip install googletrans==4.0.0-rc1
try:
    from googletrans import Translator
    translator = Translator()
    ONLINE_TRANSLATION_ENABLED = True
except ImportError:
    # Nur eine Warnung, damit das Programm ohne Online-Übersetzung läuft
    print("Warnung: Die 'googletrans' Bibliothek wurde nicht gefunden. Online-Übersetzung ist deaktiviert. Bitte installieren Sie sie mit: pip install googletrans==4.0.0-rc1")
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
                ("apple", "Englisch", "Italienisch", "mela"),
                ("house", "Englisch", "Spanisch", "casa"),
                ("to walk", "Englisch", "Französisch", "marcher"),
                ("Apfel", "Deutsch", "Englisch", "apple"),
                ("Käse", "Deutsch", "Englisch", "cheese"),
                ("schlafen", "Deutsch", "Englisch", "to sleep"),
            ]

            for word, src_lang, trg_lang, trg_word in initial_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO vocabulary (source_word, source_lang, target_lang, target_word, source) 
                    VALUES (?, ?, ?, ?, 'DB')
                """, (word.lower(), src_lang, trg_lang, trg_word.lower()))

            conn.commit()
            messagebox.showinfo("Datenbank", "Initialvokabeln wurden in die Datenbank geladen.")

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

        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
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
        master.title("🌍 Vokabeltrainer")
        master.geometry("650x550")

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
        # Andere Sprache -> Deutsch (Ctrl + Buchstabe)
        self.master.bind('<Control-Key-e>', lambda e: self.set_language_pair("Englisch", "Deutsch"))
        self.master.bind('<Control-Key-i>', lambda e: self.set_language_pair("Italienisch", "Deutsch"))
        self.master.bind('<Control-Key-s>', lambda e: self.set_language_pair("Spanisch", "Deutsch"))
        self.master.bind('<Control-Key-f>', lambda e: self.set_language_pair("Französisch", "Deutsch"))

        # Hotkeys für Deutsch -> Andere Sprache (Ctrl + Shift + Buchstabe)
        self.master.bind('<Control-Shift-E>', lambda e: self.set_language_pair("Deutsch", "Englisch"))
        self.master.bind('<Control-Shift-I>', lambda e: self.set_language_pair("Deutsch", "Italienisch"))
        self.master.bind('<Control-Shift-S>', lambda e: self.set_language_pair("Deutsch", "Spanisch"))
        self.master.bind('<Control-Shift-F>', lambda e: self.set_language_pair("Deutsch", "Französisch"))

        # Allgemeiner Hotkey
        self.master.bind('<space>', lambda e: self.next_word())

        self.answer_entry.focus()

    def create_widgets(self):
        # Konfiguration des Haupt-Frames
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # --- Sprachpaarauswahl (Oben) ---
        ttk.Label(main_frame, text="Sprachpaar auswählen:", font=('Arial', 11, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)

        # Button-Frame für Sprachen
        lang_frame = ttk.Frame(main_frame)
        lang_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        # Hotkey-Map für Tooltips und Button-Text
        hotkey_map = {'E': 'Englisch', 'I': 'Italienisch', 'S': 'Spanisch', 'F': 'Französisch'}

        # Sprach-Buttons (Übersetzung DEUTSCH <-> ANDERE)
        col = 0
        for lang_char, lang_name in hotkey_map.items():

            # Button für X -> Deutsch (Ctrl + Buchstabe)
            btn_to_de = ttk.Button(lang_frame, text=f"{lang_name} -> Deutsch (Ctrl+{lang_char})",
                                   command=lambda l=lang_name: self.set_language_pair(l, "Deutsch"))
            btn_to_de.grid(row=0, column=col, padx=3, pady=5)
            Tooltip(btn_to_de, f"Wörter aus {lang_name} ins Deutsche übersetzen. Hotkey: **Ctrl+{lang_char}**")
            col += 1

            # Button für Deutsch -> X (Ctrl + Shift + Buchstabe)
            btn_from_de = ttk.Button(lang_frame, text=f"Deutsch -> {lang_name} (Ctrl+Shift+{lang_char})",
                                     command=lambda l=lang_name: self.set_language_pair("Deutsch", l))
            btn_from_de.grid(row=1, column=col-1, padx=3, pady=5)
            Tooltip(btn_from_de, f"Wörter aus Deutsch in {lang_name} übersetzen. Hotkey: **Ctrl+Shift+{lang_char}**")


        # --- Aktuelle Auswahl (Mitte) ---
        self.selection_label = ttk.Label(main_frame, text="", font=('Arial', 12, 'bold'), foreground='#005a9c')
        self.selection_label.grid(row=2, column=0, columnspan=2, pady=(15, 10), sticky=tk.W)


        # --- Manuelle Abfrage (IM HAUPTMENÜ) ---
        manual_frame = ttk.LabelFrame(main_frame, text="Manuelle Abfrage (Wort suchen)", padding="10")
        manual_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        manual_frame.columnconfigure(0, weight=1)

        self.manual_entry = ttk.Entry(manual_frame, font=('Arial', 12))
        self.manual_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        Tooltip(self.manual_entry, "Geben Sie ein Wort ein und drücken Sie Enter, um die Übersetzung zu finden.")

        self.manual_entry.bind('<Return>', self.find_manual_translation)

        self.manual_button = ttk.Button(manual_frame, text="Übersetzung finden (Enter)",
                                        command=self.find_manual_translation,
                                        style='Manual.TButton')
        self.manual_button.grid(row=0, column=1, padx=5, pady=5)
        Tooltip(self.manual_button, "Sucht die Übersetzung des eingegebenen Wortes basierend auf dem aktuellen Sprachpaar.")

        # Separates Ausgabefeld für die manuelle Abfrage
        self.manual_result_label = ttk.Label(manual_frame, text="", font=('Arial', 11, 'bold'))
        self.manual_result_label.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)


        # --- Aufgabenbereich (Vokabelübung) ---
        task_frame = ttk.LabelFrame(main_frame, text="Vokabelübung", padding="10")
        task_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        task_frame.columnconfigure(0, weight=1)
        task_frame.columnconfigure(1, weight=1)

        self.word_label = ttk.Label(task_frame, text="Wort: [Wählen Sie ein Paar]", font=('Arial', 18))
        self.word_label.grid(row=0, column=0, columnspan=2, pady=(5, 15))

        ttk.Label(task_frame, text="Ihre Übersetzung:", font=('Arial', 12)).grid(row=1, column=0, sticky=tk.W, padx=5)
        self.answer_entry = ttk.Entry(task_frame, font=('Arial', 14))
        self.answer_entry.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        Tooltip(self.answer_entry, "Geben Sie die Übersetzung hier ein. Enter zum Prüfen.")

        self.answer_entry.bind('<Return>', self.check_answer)

        self.check_button = ttk.Button(task_frame, text="Prüfen (Enter)", command=self.check_answer, style='Accent.TButton')
        self.check_button.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        Tooltip(self.check_button, "Prüft die eingegebene Antwort gegen die gespeicherte Lösung.")

        self.result_label = ttk.Label(task_frame, text="", font=('Arial', 12, 'bold'))
        self.result_label.grid(row=3, column=0, columnspan=2, pady=10)

        self.next_button = ttk.Button(task_frame, text="Nächstes Wort (Space)", command=self.next_word)
        self.next_button.grid(row=4, column=0, columnspan=2, pady=(10, 5))
        Tooltip(self.next_button, "Springt zum nächsten zufälligen Vokabel (Spacebar).")


    # --- 4. LOGIK-METHODEN (Inklusive Datenbank- und Online-Translator-Nutzung) ---

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
                online_translation = trans.text.strip().lower()

                # KORREKTUR: Jetzt 5 Platzhalter 'VALUES (?, ?, ?, ?, ?)' für 5 übergebene Werte
                cursor.execute("""
                    INSERT OR IGNORE INTO vocabulary (source_word, source_lang, target_lang, target_word, source) 
                    VALUES (?, ?, ?, ?, ?)  
                """, (word, src_lang, trg_lang, online_translation, 'Online'))
                conn.commit()
                conn.close()
                return online_translation, "Online"

            except Exception as e:
                conn.close()
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

        if not possible_words:
            self.word_label.config(text="Keine Vokabeln gefunden für dieses Paar in der Datenbank.")
            self.result_label.config(text="", foreground='black')
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
            messagebox.showinfo("Info", "Bitte wählen Sie zuerst ein Sprachpaar und klicken Sie auf 'Nächstes Wort'.")
            return

        user_answer = self.answer_entry.get().strip().lower()
        clean_solution = self.current_solution.lower()

        if user_answer == clean_solution:
            self.result_label.config(text="✅ Richtig!", foreground='green')
            self.master.after(1500, self.next_word)
        else:
            self.result_label.config(
                text=f"❌ Falsch. Richtig: {self.current_solution.capitalize()}",
                foreground='red'
            )

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

        if translation:
            source_info = f" (Quelle: {source_type})"
            self.manual_result_label.config(
                text=f"✅ {query_word.capitalize()} ({src}) = **{translation.capitalize()}** ({trg}){source_info}",
                foreground='green'
            )
        else:
            if "Fehler:" in source_type:
                error_msg = f"❌ Online-Übersetzungsfehler: {source_type}"
            elif source_type == "Deaktiviert":
                error_msg = f"❌ Übersetzung nicht gefunden. Online-Übersetzung ist deaktiviert (googletrans fehlt oder Fehler)."
            else:
                error_msg = f"❌ Übersetzung für '{query_word.capitalize()}' nicht gefunden."

            self.manual_result_label.config(text=error_msg, foreground='red')

        self.manual_entry.delete(0, tk.END)
        self.manual_entry.focus() # Fokus zurücksetzen


# --- 5. ANWENDUNG STARTEN ---
if __name__ == "__main__":
    root = tk.Tk()

    # Konfiguriere Stile
    style = ttk.Style()
    style.configure('Accent.TButton', foreground='white', background='#0078d4', font=('Arial', 10, 'bold'))
    style.configure('Manual.TButton', background='#cce6ff', font=('Arial', 10, 'normal'))

    app = VocabularyTrainer(root)
    root.mainloop()