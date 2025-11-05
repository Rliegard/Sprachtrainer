##############################################################################################
# Vokabeltrainer (Vocabulary Trainer) 📱
# ==============================================================================
#
# Eine plattformübergreifende Anwendung (GUI basiert auf Kivy/Buildozer für Mobil)
# zum Üben und Nachschlagen von Vokabeln. Die Anwendung verwendet
# eine lokale **SQLite-Datenbank** zur persistenten Speicherung der Vokabelpaare
# und bietet optional eine **Online-Übersetzungsfunktion (Googletrans)**.
#
# **ZIELPLATTFORM: Android Mobile App (via Buildozer/Kivy-Portierung)**
# Neu in SpT6: Optimierte mobile Benutzeroberfläche und Touch-Bedienung.
#
# Sprachen: Deutsch, Englisch, Italienisch, Spanisch, Französisch, + weitere
# Hotkeys:  Sprachpaare schnell wechseln (z.B. Strg+E für Englisch -> Deutsch)
#           Space / **Tap** zum Abrufen des nächsten Wortes.
#           F5 / **Swipe** zur Aktualisierung der Vokabelliste.
#
# ------------------------------------------------------------------------------
# ABHÄNGIGKEITEN & VORAUSSETZUNGEN
# ------------------------------------------------------------------------------
#
# 1. Python 3.x
# 2. **Kivy Framework** (für die mobile GUI)
# 3. **Buildozer** (zur Erstellung der Android .apk-Datei)
# 4. SQLite3 (Standard in Python)
# 5. Googletrans (Optional für Online-Übersetzung)
#
# Installation für mobile Entwicklung:
# pip install kivy buildozer
# pip install googletrans==4.0.0-rc1
#
# ------------------------------------------------------------------------------
# AUTOR: Rainer Liegard
# ERSTELLT AM: **06.11.2025**
# VERSION: **SpT5 (Android Edition)**
##############################################################################################

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# --- TOOLS FÜR ANDROID-KOMPATIBILITÄT ---
try:
    from plyer import tts
    PLYER_TTS_ENABLED = True
except ImportError:
    print("Warnung: Plyer nicht gefunden. TTS ist deaktiviert.")
    PLYER_TTS_ENABLED = False

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

# --- DATENBANK UND GLOBALE KONSTANTEN ---
import sqlite3
import random
import os
import sys

# Ersetze dies durch den relativen Pfad zu deiner DB im Kivy-Projektordner
DB_NAME = "vokabeln.db"
LANGUAGES = ["Englisch", "Deutsch", "Italienisch", "Spanisch", "Französisch"]

LANG_CODES = {
    "Englisch": "en", "Deutsch": "de", "Italienisch": "it",
    "Spanisch": "es", "Französisch": "fr"
}

# Farben
ACCENT_COLOR = get_color_from_hex("#10B981") # Grün
ERROR_COLOR = get_color_from_hex("#EF4444")  # Rot
INFO_COLOR = get_color_from_hex("#005a9c")   # Blau
TEXT_COLOR = get_color_from_hex("#374151")   # Dunkelgrau


def initialize_db():
    """Erstellt die SQLite-Datenbank und die Vokabeltabelle."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

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
        print(f"Datenbankfehler: Konnte die SQLite-Datenbank nicht initialisieren: {e}")
        return False

# --- HAUPTKLASSE (Kivy Layout) ---

class SprachtrainerLayout(BoxLayout):
    selection_text = StringProperty("Aktuelles Paar: Englisch -> Deutsch")
    word_text = StringProperty("Wort: [Wählen Sie ein Paar]")
    result_text = StringProperty("")

    answer_entry = ObjectProperty(None)
    manual_entry = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 15

        if not initialize_db():
            sys.exit()

        self.current_source_lang = "Englisch"
        self.current_target_lang = "Deutsch"
        self.current_word = None
        self.current_solution = ""

        self.create_widgets()
        self.next_word()

        # KORRIGIERTE FOKUS-ZUWEISUNG
        Clock.schedule_once(self.set_answer_focus, 0.5)

        Window.bind(on_key_down=self._on_keyboard_down)

    def set_answer_focus(self, dt):
        """Setzt den Fokus auf das Antwort-Eingabefeld. Parameter dt ist erforderlich."""
        self.answer_entry.focus = True

    def _on_keyboard_down(self, window, keycode, scancode, text, modifiers):
        """Behandelt Hotkeys für das gesamte Fenster."""

        if modifiers == ['ctrl'] and text == 'q':
            self.on_closing()

        elif text == ' ':
            self.next_word()

        key_map_ctrl = {'e': ("Englisch", "Deutsch"), 'i': ("Italienisch", "Deutsch"),
                        's': ("Spanisch", "Deutsch"), 'f': ("Französisch", "Deutsch")}
        key_map_ctrl_shift = {'e': ("Deutsch", "Englisch"), 'i': ("Deutsch", "Italienisch"),
                              's': ("Deutsch", "Spanisch"), 'f': ("Französisch", "Deutsch")}

        if 'ctrl' in modifiers:
            if 'shift' in modifiers and text in key_map_ctrl_shift:
                self.set_language_pair(*key_map_ctrl_shift[text])
            elif text in key_map_ctrl:
                self.set_language_pair(*key_map_ctrl[text])

        return True

    def create_widgets(self):
        """Erstellt die Kivy-GUI-Struktur."""

        # --- Oben: Sprachauswahl und Beenden ---
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=0.2)

        lang_buttons = self._create_lang_buttons()
        top_bar.add_widget(lang_buttons)

        btn_exit = Button(text="❌ Beenden", on_press=lambda x: self.on_closing(),
                          size_hint=(0.2, 1), background_color=ERROR_COLOR, color=[1, 1, 1, 1])
        top_bar.add_widget(btn_exit)

        self.add_widget(top_bar)

        # --- Aktuelle Auswahl ---
        self.selection_label = Label(text=self.selection_text, size_hint_y=0.1, color=INFO_COLOR)
        self.add_widget(self.selection_label)

        # --- Manuelle Abfrage ---
        self.manual_frame = BoxLayout(orientation='vertical', size_hint_y=0.25, padding=10, spacing=5)
        self.manual_frame.add_widget(Label(text="Manuelle Abfrage (Wort suchen)", size_hint_y=0.2, color=TEXT_COLOR))

        manual_input_bar = BoxLayout(orientation='horizontal', size_hint_y=0.3)
        self.manual_entry = TextInput(multiline=False, size_hint_x=0.75, on_text_validate=self.find_manual_translation)
        manual_input_bar.add_widget(self.manual_entry)

        manual_button = Button(text="Übersetzung finden (Enter)", size_hint_x=0.25,
                               on_press=self.find_manual_translation, background_color=get_color_from_hex("#e0f2f1"), color=TEXT_COLOR)
        manual_input_bar.add_widget(manual_button)

        self.manual_frame.add_widget(manual_input_bar)
        self.manual_result_label = Label(text="", size_hint_y=0.5, color=INFO_COLOR)
        self.manual_frame.add_widget(self.manual_result_label)

        self.add_widget(self.manual_frame)

        # --- Vokabelübung ---
        task_frame = BoxLayout(orientation='vertical', size_hint_y=0.45, padding=10, spacing=10)
        task_frame.add_widget(Label(text="Vokabelübung", size_hint_y=0.1, color=TEXT_COLOR))

        self.word_label = Label(text=self.word_text, font_size='24sp', size_hint_y=0.25, color=TEXT_COLOR)
        task_frame.add_widget(self.word_label)

        input_bar = BoxLayout(orientation='horizontal', size_hint_y=0.2)
        self.answer_entry = TextInput(multiline=False, size_hint_x=0.65, on_text_validate=self.check_answer)
        input_bar.add_widget(self.answer_entry)

        self.check_button = Button(text="Prüfen (Enter)", size_hint_x=0.2, on_press=self.check_answer,
                                   background_color=ACCENT_COLOR, color=[1, 1, 1, 1])
        input_bar.add_widget(self.check_button)

        self.tts_button = Button(text="🔊 Vorlesen", size_hint_x=0.15, on_press=self.speak_solution,
                                 background_color=get_color_from_hex("#3B82F6"), color=[1, 1, 1, 1], disabled=True)
        input_bar.add_widget(self.tts_button)

        task_frame.add_widget(input_bar)

        self.result_label = Label(text=self.result_text, size_hint_y=0.2, font_size='18sp')
        task_frame.add_widget(self.result_label)

        self.next_button = Button(text="Nächstes Wort (Space)", on_press=self.next_word, size_hint_y=0.25,
                                  background_color=ACCENT_COLOR, color=[1, 1, 1, 1])
        task_frame.add_widget(self.next_button)

        self.add_widget(task_frame)

    def _create_lang_buttons(self):
        """Erstellt die dynamischen Sprachauswahl-Buttons."""
        lang_frame = BoxLayout(orientation='vertical', size_hint_x=0.8)

        # Hotkeys für die Buttons: Strg+E/I/S/F und Strg+Shift+E/I/S/F
        row1 = BoxLayout(orientation='horizontal', size_hint_y=0.5)
        for lang_name in ["Englisch", "Italienisch", "Spanisch", "Französisch"]:
            btn = Button(text=f"{lang_name} -> Deutsch", font_size='10sp',
                         on_press=lambda x, l=lang_name: self.set_language_pair(l, "Deutsch"))
            row1.add_widget(btn)
        lang_frame.add_widget(row1)

        row2 = BoxLayout(orientation='horizontal', size_hint_y=0.5)
        for lang_name in ["Englisch", "Italienisch", "Spanisch", "Französisch"]:
            btn = Button(text=f"Deutsch -> {lang_name}", font_size='10sp',
                         on_press=lambda x, l=lang_name: self.set_language_pair("Deutsch", l))
            row2.add_widget(btn)
        lang_frame.add_widget(row2)

        return lang_frame

    # --- TTS LOGIK (Plyer) ---
    def speak_solution(self, instance):
        """Gibt die Lösung über Plyer TTS aus."""
        if not self.current_solution:
            return

        if not PLYER_TTS_ENABLED:
            self.result_label.text = "TTS ist deaktiviert (Plyer fehlt)."
            return

        self.tts_button.disabled = True

        # KORREKTUR: Das language-Argument wurde entfernt, um den Fehler zu beheben.
        try:
            tts.speak(message=self.current_solution.capitalize())
        except Exception as e:
            print(f"Plyer TTS Fehler: {e}")
            self.result_label.text = f"TTS Fehler: {e}"
        finally:
            Clock.schedule_once(lambda dt: self._enable_tts_button(), 2)

    def _enable_tts_button(self):
        """Aktiviert den TTS Button nach der Ausgabe."""
        self.tts_button.disabled = False

    def on_closing(self):
        """Beendet die Anwendung sauber."""
        Window.close()
        sys.exit()

    # --- LOGIK-METHODEN ---

    def check_db_and_get_translation(self, word, src_lang, trg_lang):
        """Prüft die DB und nutzt bei Fehlen den Online-Translator."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT target_word FROM vocabulary 
            WHERE source_lang = ? AND source_word = ? AND target_lang = ?
        """, (src_lang, word, trg_lang))

        result = cursor.fetchone()

        if result:
            conn.close()
            return result[0], "DB"

        if ONLINE_TRANSLATION_ENABLED:
            try:
                if src_lang not in LANG_CODES or trg_lang not in LANG_CODES:
                    conn.close()
                    return None, "Sprachcode fehlt"

                trans = translator.translate(word, src=LANG_CODES[src_lang], dest=LANG_CODES[trg_lang])

                online_translation = trans.text.strip().lower()

                cursor.execute("""
                    INSERT OR IGNORE INTO vocabulary (source_word, source_lang, target_lang, target_word, source) 
                    VALUES (?, ?, ?, ?, ?)  
                """, (word, src_lang, trg_lang, online_translation, 'Online'))
                conn.commit()
                conn.close()
                return online_translation, "Online"

            except Exception as e:
                conn.close()
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
        self.manual_result_label.text = ""

    def update_selection_display(self):
        """Aktualisiert die Anzeige des aktuellen Sprachpaars."""
        self.selection_label.text = f"Aktuelles Paar: {self.current_source_lang} -> {self.current_target_lang}"

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

    def next_word(self, instance=None):
        """Wählt ein zufälliges Wort basierend auf dem aktuellen Sprachpaar."""
        possible_words = self.fetch_all_words_for_pair()

        self.check_button.background_color = ACCENT_COLOR
        self.next_button.background_color = ACCENT_COLOR

        self.tts_button.disabled = True

        if not possible_words:
            self.word_label.text = f"Keine Vokabeln für {self.current_source_lang} -> {self.current_target_lang} gefunden."
            self.result_label.text = "Versuchen Sie, manuell ein Wort zu suchen. Es wird dann gespeichert!"
            self.result_label.color = TEXT_COLOR
            self.current_word = None
            self.current_solution = ""
            self.answer_entry.text = ''
            return

        self.current_word, self.current_solution = random.choice(possible_words)

        self.word_label.text = f"Wort ({self.current_source_lang}): [b]{self.current_word.capitalize()}[/b]"
        self.word_label.markup = True

        self.result_label.text = ""
        self.result_label.color = TEXT_COLOR
        self.answer_entry.text = ''
        self.answer_entry.focus = True


    def check_answer(self, instance):
        """Überprüft die eingegebene Übersetzung (Übungsteil)."""
        if not self.current_word:
            self.result_label.text = "Bitte wählen Sie zuerst ein Sprachpaar oder klicken Sie auf 'Nächstes Wort'."
            self.result_label.color = INFO_COLOR
            return

        user_answer = self.answer_entry.text.strip().lower()
        clean_solution = self.current_solution.lower()

        if user_answer == clean_solution:
            self.result_label.text = f"✅ Richtig! Lösung: {self.current_solution.capitalize()}"
            self.result_label.color = ACCENT_COLOR
            self.tts_button.disabled = False

            self.next_button.background_color = get_color_from_hex("#e0f2f1")
            self.check_button.background_color = ACCENT_COLOR

        else:
            self.result_label.text = f"❌ Falsch. Richtig: {self.current_solution.capitalize()}"
            self.result_label.color = ERROR_COLOR
            self.tts_button.disabled = False

            self.check_button.background_color = get_color_from_hex("#e0f2f1")
            self.next_button.background_color = ACCENT_COLOR

        self.answer_entry.text = ''


    def find_manual_translation(self, instance):
        """Sucht die Übersetzung und nutzt Online-Translator, wenn nötig."""
        query_word = self.manual_entry.text.strip().lower()
        self.manual_result_label.text = ""

        if not query_word:
            self.manual_entry.focus = True
            return

        src = self.current_source_lang
        trg = self.current_target_lang

        translation, source_type = self.check_db_and_get_translation(query_word, src, trg)

        if translation and translation != query_word:
            source_info = f" (Quelle: {source_type})"
            self.manual_result_label.text = f"✅ {query_word.capitalize()} ({src}) = [b]{translation.capitalize()}[/b] ({trg}){source_info}"
            self.manual_result_label.color = INFO_COLOR
            self.manual_result_label.markup = True

            self.next_word()
        else:
            if "Fehler:" in source_type:
                error_msg = f"❌ Online-Übersetzungsfehler: {source_type}"
            elif source_type == "Deaktiviert":
                error_msg = f"❌ Übersetzung nicht gefunden. Online-Übersetzung ist deaktiviert."
            else:
                error_msg = f"❌ Übersetzung für '{query_word.capitalize()}' nicht gefunden."

            self.manual_result_label.text = error_msg
            self.manual_result_label.color = ERROR_COLOR

        self.manual_entry.text = ''
        self.manual_entry.focus = True


# 6. ANWENDUNG STARTEN
class SprachtrainerApp(App):
    def build(self):
        return SprachtrainerLayout()

if __name__ == "__main__":
    Window.size = (750, 600)
    Window.title = "🌍 Vokabeltrainer (Kivy/Android)"

    Label.markup = True

    SprachtrainerApp().run()