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
# VERSION: SpT1
##############################################################################################

import tkinter as tk
from tkinter import ttk, messagebox
import random

# --- 1. DATENBANK (Vokabeln) ---
# Struktur: {Sprache_1: {Wort_1: {Sprache_2: Übersetzung, ...}, ...}, ...}
# Alle Schlüssel müssen in LANGUAGES enthalten sein.

VOCABULARY = {
    "Englisch": {
        "apple": {"Deutsch": "Apfel", "Italienisch": "mela", "Spanisch": "manzana", "Französisch": "pomme"},
        "house": {"Deutsch": "Haus", "Italienisch": "casa", "Spanisch": "casa", "Französisch": "maison"},
        "water": {"Deutsch": "Wasser", "Italienisch": "acqua", "Spanisch": "agua", "Französisch": "eau"},
        "book": {"Deutsch": "Buch", "Italienisch": "libro", "Spanisch": "libro", "Französisch": "livre"},
        "to walk": {"Deutsch": "gehen", "Italienisch": "camminare", "Spanisch": "caminar", "Französisch": "marcher"},
        "beautiful": {"Deutsch": "schön", "Italienisch": "bello", "Spanisch": "hermoso", "Französisch": "belle"},
        "quickly": {"Deutsch": "schnell", "Italienisch": "velocemente", "Spanisch": "rápidamente", "Französisch": "rapidement"},
        "table": {"Deutsch": "Tisch", "Italienisch": "tavolo", "Spanisch": "mesa", "Französisch": "table"},
        "friend": {"Deutsch": "Freund", "Italienisch": "amico", "Spanisch": "amigo", "Französisch": "ami"},
        "sun": {"Deutsch": "Sonne", "Italienisch": "sole", "Spanisch": "sol", "Französisch": "soleil"},
    },
    # Zusätzliche Einträge zur Sicherstellung der Bidirektionalität, falls nicht alle Wörter direkt abgedeckt sind
    "Deutsch": {
        "Käse": {"Englisch": "cheese", "Italienisch": "formaggio", "Spanisch": "queso", "Französisch": "fromage"},
        "schlafen": {"Englisch": "to sleep", "Italienisch": "dormire", "Spanisch": "dormir", "Französisch": "dormir"},
    },
    # Die anderen Sprachen benötigen keine vollständigen eigenen Einträge, solange die Übersetzung in der
    # Hauptsprache (Englisch/Deutsch) definiert ist, da die Logik alle Paare dynamisch generiert.
}

LANGUAGES = ["Englisch", "Deutsch", "Italienisch", "Spanisch", "Französisch"]


# --- 2. HILFSKLASSE (Tooltip) ---
class Tooltip:
    """Erstellt einen Tooltip für ein Tkinter-Widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None): self.schedule()
    def schedule(self):
        self.unschedule()
        self.tw = self.widget.after(500, self.show)

    def unschedule(self):
        if self.tw: self.widget.after_cancel(self.tw)
        self.tw = None

    def show(self):
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
        self.unschedule()
        if self.tw: self.tw.destroy()
        self.tw = None


# --- 3. HAUPTKLASSE (Vokabeltrainer) ---
class VocabularyTrainer:
    def __init__(self, master):
        self.master = master
        master.title("🌍 Vokabeltrainer")
        master.geometry("600x450")

        # Zustand
        self.current_source_lang = "Englisch"
        self.current_target_lang = "Deutsch"
        self.current_word = None
        self.current_solution = ""

        # UI Setup
        self.create_widgets()
        self.update_selection_display()
        self.next_word()

        # Hotkeys binden
        self.master.bind('<Control-Key-e>', lambda e: self.set_language_pair("Englisch", "Deutsch"))
        self.master.bind('<Control-Key-d>', lambda e: self.set_language_pair("Deutsch", "Englisch"))
        self.master.bind('<Control-Key-i>', lambda e: self.set_language_pair("Italienisch", "Deutsch"))
        self.master.bind('<Control-Key-s>', lambda e: self.set_language_pair("Spanisch", "Deutsch"))
        self.master.bind('<Control-Key-f>', lambda e: self.set_language_pair("Französisch", "Deutsch"))
        self.master.bind('<Return>', lambda e: self.check_answer()) # Enter-Taste zur Überprüfung
        self.master.bind('<space>', lambda e: self.next_word())     # Leertaste für das nächste Wort

        self.answer_entry.focus() # Fokus auf Eingabefeld setzen

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

        # Hotkey-Map für Tooltips
        hotkeys = {'E': 'Englisch', 'D': 'Deutsch', 'I': 'Italienisch', 'S': 'Spanisch', 'F': 'Französisch'}

        # Sprach-Buttons (Übersetzung DEUTSCH <-> ANDERE)
        col = 0
        for lang in LANGUAGES:
            if lang == "Deutsch": continue

            # Button für X -> Deutsch
            btn_to_de = ttk.Button(lang_frame, text=f"{lang} -> Deutsch",
                                   command=lambda l=lang: self.set_language_pair(l, "Deutsch"))
            btn_to_de.grid(row=0, column=col, padx=3, pady=5)
            hotkey_char = next(k for k, v in hotkeys.items() if v == lang)
            Tooltip(btn_to_de, f"Wörter aus {lang} ins Deutsche übersetzen. Hotkey: **Ctrl+{hotkey_char}**")
            col += 1

            # Button für Deutsch -> X
            btn_from_de = ttk.Button(lang_frame, text=f"Deutsch -> {lang}",
                                     command=lambda l=lang: self.set_language_pair("Deutsch", l))
            btn_from_de.grid(row=1, column=col-1, padx=3, pady=5)
            # Spezifische Hotkeys für Deutsch -> X fehlen, da Ctrl+E, Ctrl+I, etc. bereits verwendet werden.


        # --- Aktuelle Auswahl (Mitte) ---
        self.selection_label = ttk.Label(main_frame, text="", font=('Arial', 12, 'bold'), foreground='#005a9c')
        self.selection_label.grid(row=2, column=0, columnspan=2, pady=(15, 10), sticky=tk.W)

        # --- Aufgabenbereich ---
        task_frame = ttk.Frame(main_frame, padding="10", relief=tk.GROOVE)
        task_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        task_frame.columnconfigure(0, weight=1)
        task_frame.columnconfigure(1, weight=1)

        self.word_label = ttk.Label(task_frame, text="Wort: [Bitte wählen Sie ein Sprachpaar]", font=('Arial', 18))
        self.word_label.grid(row=0, column=0, columnspan=2, pady=(5, 15))

        ttk.Label(task_frame, text="Ihre Übersetzung:", font=('Arial', 12)).grid(row=1, column=0, sticky=tk.W, padx=5)
        self.answer_entry = ttk.Entry(task_frame, font=('Arial', 14))
        self.answer_entry.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        Tooltip(self.answer_entry, "Geben Sie die Übersetzung hier ein und drücken Sie Enter.")

        self.check_button = ttk.Button(task_frame, text="Prüfen (Enter)", command=self.check_answer, style='Accent.TButton')
        self.check_button.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        Tooltip(self.check_button, "Überprüft Ihre Eingabe. Hotkey: **Enter**")

        self.result_label = ttk.Label(task_frame, text="", font=('Arial', 12, 'bold'))
        self.result_label.grid(row=3, column=0, columnspan=2, pady=10)

        self.next_button = ttk.Button(task_frame, text="Nächstes Wort (Space)", command=self.next_word)
        self.next_button.grid(row=4, column=0, columnspan=2, pady=(10, 5))
        Tooltip(self.next_button, "Zeigt das nächste Wort an. Hotkey: **Leertaste**")


    # --- 4. LOGIK-METHODEN ---

    def set_language_pair(self, source_lang, target_lang):
        """Setzt das aktuelle Sprachpaar und startet eine neue Runde."""
        self.current_source_lang = source_lang
        self.current_target_lang = target_lang
        self.update_selection_display()
        self.next_word()

    def update_selection_display(self):
        """Aktualisiert die Anzeige des aktuellen Sprachpaars."""
        self.selection_label.config(text=f"Aktuelles Paar: {self.current_source_lang} -> {self.current_target_lang}")

    def next_word(self):
        """Wählt ein zufälliges Wort basierend auf dem aktuellen Sprachpaar."""

        # 1. Wörter aus der Quellsprache finden, die eine Übersetzung in die Zielsprache haben
        possible_words = []

        # Prüfen in der Quellsprache-Sektion (z.B. Englisch: {"apple": {"Deutsch": "Apfel"}})
        if self.current_source_lang in VOCABULARY:
            for word, translations in VOCABULARY[self.current_source_lang].items():
                if self.current_target_lang in translations:
                    possible_words.append((word, translations[self.current_target_lang]))

        # 2. Prüfen in der Zielsprache-Sektion als Reverse-Lookup (z.B. Deutsch: {"Apfel": {"Englisch": "apple"}})
        # Dies ist nur nötig, wenn die Zielsprache die Primärsprache im VOCABULARY ist, um Bidirektionalität zu gewährleisten.
        if self.current_target_lang in VOCABULARY:
            # Wir suchen in der Zielsprache nach Wörtern, die eine Übersetzung in die Quellsprache haben.
            # Wenn wir z.B. Deutsch -> Spanisch wählen, suchen wir in der Sektion "Deutsch" nach Wörtern
            # die eine Spanisch-Übersetzung haben.
            for word, translations in VOCABULARY[self.current_target_lang].items():
                if self.current_source_lang in translations:
                    possible_words.append((translations[self.current_source_lang], word))

        if not possible_words:
            self.word_label.config(text="Keine Vokabeln gefunden für dieses Paar.")
            self.result_label.config(text="", foreground='black')
            self.answer_entry.delete(0, tk.END)
            return

        # Zufälliges Wort auswählen
        self.current_word, self.current_solution = random.choice(possible_words)

        # UI aktualisieren
        self.word_label.config(text=f"Wort ({self.current_source_lang}): **{self.current_word}**")
        self.result_label.config(text="", foreground='black')
        self.answer_entry.delete(0, tk.END)
        self.answer_entry.focus()


    def check_answer(self):
        """Überprüft die eingegebene Übersetzung."""
        if not self.current_word:
            messagebox.showinfo("Info", "Bitte wählen Sie zuerst ein Sprachpaar und klicken Sie auf 'Nächstes Wort'.")
            return

        user_answer = self.answer_entry.get().strip().lower()

        # Bereinigung der Lösung (z.B. Klammern entfernen oder mehrere mögliche Antworten prüfen)
        clean_solution = self.current_solution.lower()

        # Einfache Prüfung
        if user_answer == clean_solution:
            self.result_label.config(text="✅ Richtig!", foreground='green')
            self.master.after(1500, self.next_word) # Automatisches nächstes Wort nach 1.5 Sekunden
        else:
            self.result_label.config(
                text=f"❌ Falsch. Die richtige Antwort war: {self.current_solution}",
                foreground='red'
            )
            # Fokus behalten, damit der Benutzer die Antwort korrigieren oder Leertaste drücken kann


# --- 5. ANWENDUNG STARTEN ---
if __name__ == "__main__":
    root = tk.Tk()
    # Konfiguriere den Stil für den "Prüfen"-Button (Accent-Stil)
    style = ttk.Style()
    style.configure('Accent.TButton', foreground='white', background='#0078d4', font=('Arial', 10, 'bold'))

    app = VocabularyTrainer(root)
    root.mainloop()