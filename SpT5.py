import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
import json
import base64
import io
import time
import threading

# Erforderliche Bibliotheken für erweiterte Funktionen (müssen installiert werden):
# pip install requests Pillow numpy sounddevice googletrans==4.0.0-rc1

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None
    print("Warnung: 'Pillow' nicht gefunden. Bildanzeige deaktiviert. Installieren Sie: pip install Pillow")

try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    np = None
    sd = None
    print("Warnung: 'numpy' oder 'sounddevice' nicht gefunden. Audio-Wiedergabe deaktiviert. Installieren Sie: pip install numpy sounddevice")

try:
    from googletrans import Translator
except ImportError:
    Translator = None
    print("Warnung: 'googletrans' nicht gefunden. Offline-Übersetzungs-Fallback deaktiviert. Installieren Sie: pip install googletrans==4.0.0-rc1")


# --------------------------------------------------------------------------------------
# 1. KONFIGURATION & API-SCHLÜSSEL
# --------------------------------------------------------------------------------------

# ERSETZEN SIE DIESEN PLATZHALTER DURCH IHREN GÜLTIGEN GEMINI API-SCHLÜSSEL!
GEMINI_API_KEY = "AIzaSyA_xJ-YNj_jI6lUqxSwpgOnxodzx4a0vlU"

# WICHTIGE ANPASSUNG: Erhöhe das Timeout von 60s auf 90s, um dem Netzwerk mehr Zeit zu geben.
API_TIMEOUT_SECONDS = 90

# Modelle und Endpunkte
TEXT_MODEL = "gemini-2.5-flash-preview-09-2025"
IMAGE_MODEL = "imagen-3.0-generate-002"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"

# --------------------------------------------------------------------------------------
# 2. HELPER-FUNKTIONEN FÜR API-AUFRUFE UND FEHLERBEHANDLUNG
# --------------------------------------------------------------------------------------

def exponential_backoff_fetch(url, payload, headers, max_retries=5): # Max Retries auf 5 erhöht
    """Führt eine API-Anfrage mit exponentiellem Backoff bei Fehlern durch."""
    for attempt in range(max_retries):
        response = None  # Stellt sicher, dass response immer definiert ist oder None
        try:
            # Timeout auf 90 Sekunden (API_TIMEOUT_SECONDS) gesetzt
            print(f"DEBUG: Starte API-Anfrage (Versuch {attempt + 1}). URL: {url.split('models/')[1].split(':')[0]}")
            response = requests.post(url, headers=headers, json=payload, timeout=API_TIMEOUT_SECONDS)
            response.raise_for_status() # Löst HTTPError für 4xx/5xx Antworten aus

            # Wichtige Prüfung: Manchmal liefert die API keinen JSON-Inhalt zurück, was zu Fehlern führt
            try:
                data = response.json()
                print("DEBUG: API-Anfrage erfolgreich und JSON geparst.")
                return data
            except json.JSONDecodeError:
                error_msg = f"API-Antwort ist kein gültiges JSON. Status: {response.status_code}, Text: {response.text[:200]}..."
                print(f"FEHLER: {error_msg}")
                # Wenn es kein JSON ist, werfen wir eine Exception, um den Backoff/Wiederholungs-Mechanismus zu nutzen.
                raise Exception(error_msg)

        except requests.exceptions.HTTPError as e:
            # Wird ausgelöst, wenn der Aufruf erfolgreich war, aber ein 4xx/5xx Status zurückkam
            error_details = str(e)
            if response is not None:
                try:
                    # Versucht, detaillierte Fehlermeldungen von der API zu extrahieren
                    error_details = response.json().get("error", {}).get("message", str(e))
                except json.JSONDecodeError:
                    error_details = response.text # Gibt den Klartext der Antwort als Fehler

                if response.status_code in [429, 500, 503]:
                    # Wiederholbare Fehler (Rate Limit, Serverfehler)
                    delay = 2 ** attempt
                    print(f"Versuch {attempt + 1} fehlgeschlagen (Status: {response.status_code}, Details: {error_details}). Warte {delay}s...")
                    time.sleep(delay)
                elif response.status_code in [400, 403]:
                    # Kritische Fehler (Ungültiger Schlüssel/Eingabe)
                    print(f"KRITISCHER FEHLER: API-Schlüssel oder Payload ungültig. {error_details}")
                    raise ValueError(f"Kritischer API-Fehler (Schlüssel/Eingabe): {error_details}")
                else:
                    raise Exception(f"Unbekannter HTTP-Fehler: {response.status_code} - {error_details}")
            else:
                # Dies sollte theoretisch nicht passieren, wenn es ein HTTPError ist
                raise Exception(f"Unerwarteter HTTP-Fehler: {str(e)}")


        except requests.exceptions.ReadTimeout:
            # Behandlung für Read Timeout (Netzwerkfehler)
            delay = 2 ** attempt
            # Setze Mindest-Wartezeit auf 2 Sekunden, um das Netzwerk nicht zu überlasten
            delay = max(delay, 2)
            print(f"Versuch {attempt + 1} fehlgeschlagen (Netzwerkfehler: Read timed out). Warte {delay}s...")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            # Allgemeine Netzwerkfehler (z.B. ConnectionError)
            delay = 2 ** attempt
            delay = max(delay, 2)
            print(f"Versuch {attempt + 1} fehlgeschlagen (Netzwerkfehler: {e}). Warte {delay}s...")
            time.sleep(delay)
        except Exception as e:
            # Fangt den JSONDecodeError oder den "API-Antwort ist kein gültiges JSON"-Fehler ab
            delay = 2 ** attempt
            delay = max(delay, 2)
            print(f"Versuch {attempt + 1} fehlgeschlagen (Parsing- oder unbekannter Fehler: {e}). Warte {delay}s...")
            time.sleep(delay)

    # Wenn die Schleife nach max_retries ohne Erfolg beendet wird
    raise Exception(f"API-Anfrage nach {max_retries} Versuchen fehlgeschlagen (letzter Fehler: Timeout/Netzwerk).")

# --------------------------------------------------------------------------------------
# 3. HELPER-FUNKTIONEN FÜR AUDIO-VERARBEITUNG
# --------------------------------------------------------------------------------------

def base64_to_array_buffer(base64_string):
    """Konvertiert Base64-String (enthält PCM-Audio) in ein NumPy Array (Int16)."""
    if np is None:
        raise RuntimeError("NumPy ist für die Audioverarbeitung erforderlich.")
    audio_bytes = base64.b64decode(base64_string)
    # Die Gemini TTS API liefert signierte 16-Bit PCM-Daten (Int16)
    return np.frombuffer(audio_bytes, dtype=np.int16)


class VokabelTrainerApp:
    def __init__(self, master):
        self.master = master
        master.title("Vokabeltrainer (Powered by Gemini)")
        master.state('zoomed') # Startet im Vollbildmodus

        # Zustandsvariablen
        self.current_word = {"de": "Das Wort", "en": "The Word", "description": "Definition/Beschreibung"}
        self.audio_data = None
        self.last_base64_img = None
        self.translation_language = tk.StringVar(value="Englisch")
        self.manual_input = tk.StringVar()

        # GUI-Elemente initialisieren
        self._setup_ui(master)

        # Initialer Status setzen
        self.update_ui_state(False)
        self.set_text_content(self.current_word["de"], self.current_word["en"], self.current_word["description"])

        # Bei Größenänderung die Bildanzeige anpassen
        master.bind('<Configure>', self._on_resize)
        master.after(100, lambda: self._on_resize(None))

        # Kritischer API-Schlüssel Check
        if GEMINI_API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY":
            messagebox.showerror("API-FEHLER", "Bitte tragen Sie Ihren GÜLTIGEN Gemini API-Schlüssel in Zeile 35 des Codes ein, um das Programm zu starten.")
            # Deaktiviert alle Funktionen, bis der Schlüssel gesetzt ist
            self.generate_btn.config(state=tk.DISABLED)
            self.audio_btn.config(state=tk.DISABLED)
            self.input_entry.config(state=tk.DISABLED)
            return

    def _setup_ui(self, master):
        # Schriftart-Konfiguration
        font_large = ('Arial', 24, 'bold')
        font_medium = ('Arial', 14)
        font_small = ('Arial', 10)

        # Haupt-Frame (Grid-Layout)
        main_frame = tk.Frame(master, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=1)  # Vokabel/Bild (flexibel)
        main_frame.grid_rowconfigure(2, weight=0)
        main_frame.grid_rowconfigure(3, weight=0)
        main_frame.grid_columnconfigure(0, weight=1)

        # --------------------------------------------------------------------
        # BEREICH 0: MANUELLE VOKABELEINGABE
        # --------------------------------------------------------------------
        manual_frame = tk.Frame(main_frame, pady=10)
        manual_frame.grid(row=0, column=0, sticky="ew")
        manual_frame.grid_columnconfigure(0, weight=1)

        tk.Label(manual_frame, text="Manuelle Abfrage (Deutsches Wort suchen):", font=font_medium, anchor='w').grid(row=0, column=0, sticky="w", pady=(0, 5))

        input_row = tk.Frame(manual_frame)
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)

        self.input_entry = tk.Entry(input_row, textvariable=self.manual_input, font=font_medium, state=tk.NORMAL)
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind('<Return>', lambda event: self.manual_search())

        tk.Button(input_row, text="Übersetzung finden", command=self.manual_search, font=font_medium).grid(row=0, column=1, sticky="e")

        # --------------------------------------------------------------------
        # BEREICH 1: VOKABEL-INFORMATION UND BILD (FLEXIBEL)
        # --------------------------------------------------------------------
        content_frame = tk.Frame(main_frame, bd=2, relief=tk.RIDGE, padx=15, pady=15)
        content_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 15))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- Linke Seite: Vokabel & Definition ---
        text_frame = tk.Frame(content_frame)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        text_frame.grid_rowconfigure(3, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Wort & Übersetzung
        self.word_label = tk.Label(text_frame, text="Deutsches Wort:", font=font_large, anchor='w', fg='black')
        self.word_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        self.translation_label = tk.Label(text_frame, text="Übersetzung:", font=font_large, fg='blue', anchor='w')
        self.translation_label.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # Definition/Kontext
        tk.Label(text_frame, text="Definition/Beschreibung:", font=font_medium, anchor='w').grid(row=2, column=0, sticky="sw")
        self.description_text = scrolledtext.ScrolledText(text_frame, height=1, wrap=tk.WORD, font=font_medium, state=tk.DISABLED)
        self.description_text.grid(row=3, column=0, sticky="nsew")

        # --- Rechte Seite: Bild ---
        self.image_label = tk.Label(content_frame, text="Generiertes Bild wird hier angezeigt", bg='#dddddd', fg='#888888', font=('Arial', 18), bd=1, relief=tk.SOLID)
        self.image_label.grid(row=0, column=1, sticky="nsew")

        # --------------------------------------------------------------------
        # BEREICH 2: STEUERUNG (FIX)
        # --------------------------------------------------------------------
        control_frame = tk.Frame(main_frame)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(5, 5))
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)
        control_frame.grid_columnconfigure(3, weight=1)

        # 1. Sprachauswahl
        tk.Label(control_frame, text="Zielsprache:", font=font_medium).grid(row=0, column=0, sticky="w", padx=5)
        language_options = ["Englisch", "Spanisch", "Französisch", "Japanisch"]
        tk.OptionMenu(control_frame, self.translation_language, *language_options).grid(row=0, column=1, sticky="ew", padx=5)

        # 2. Generieren-Button
        self.generate_btn = tk.Button(control_frame, text="Neues Wort generieren (API)", command=self.generate_new_word, font=font_medium, bg='#28a745', fg='white', activebackground='#218838')
        self.generate_btn.grid(row=0, column=2, sticky="ew", padx=5)

        # 3. Audio-Button
        self.audio_btn = tk.Button(control_frame, text="🔊 Aussprache (API)", command=self.play_audio, font=font_medium, bg='#007bff', fg='white', activebackground='#0056b3')
        self.audio_btn.grid(row=0, column=3, sticky="ew", padx=5)

        # --------------------------------------------------------------------
        # BEREICH 3: STATUS (FIX)
        # --------------------------------------------------------------------
        self.status_label = tk.Label(main_frame, text="Bereit. Geben Sie ein Wort ein oder klicken Sie auf 'Neues Wort generieren'.", bd=1, relief=tk.SUNKEN, anchor='w', font=font_small, bg='#f8f9fa')
        self.status_label.grid(row=3, column=0, sticky="ew", pady=(5, 0))


    def _on_resize(self, event):
        """Wird bei Größenänderung des Fensters aufgerufen, um das Bild neu zu skalieren."""
        if hasattr(self, 'tk_image') and self.last_base64_img is not None:
            # Threading hier ist wichtig, um die GUI während der Bildverarbeitung nicht zu blockieren
            threading.Thread(target=self._display_image_thread).start()


    def update_ui_state(self, is_loading):
        """Aktiviert/deaktiviert Buttons während des Ladevorgangs."""
        state = tk.DISABLED if is_loading else tk.NORMAL

        # Nur Buttons deaktivieren, wenn nicht bereits durch den API-Check disabled
        if GEMINI_API_KEY != "YOUR_ACTUAL_GEMINI_API_KEY":
            self.generate_btn.config(state=state)
            self.input_entry.config(state=state)

        # Audio-Button nur aktivieren, wenn nicht geladen wird UND Audio-Daten vorhanden sind
        self.audio_btn.config(state=tk.DISABLED if is_loading or not self.audio_data else tk.NORMAL)

    def set_text_content(self, word_de, word_en, description):
        """Aktualisiert die Textfelder der GUI."""
        self.current_word["de"] = word_de
        self.current_word["en"] = word_en
        self.current_word["description"] = description

        self.word_label.config(text=f"Deutsches Wort: {word_de}")
        self.translation_label.config(text=f"Übersetzung ({self.translation_language.get()}): {word_en}")

        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete('1.0', tk.END)
        self.description_text.insert(tk.END, description)
        self.description_text.config(state=tk.DISABLED)

    # --------------------------------------------------------------------------------------
    # 4. MANUELLE SUCHE
    # --------------------------------------------------------------------------------------

    def manual_search(self):
        """Startet die Suche für die manuelle Eingabe."""
        word = self.manual_input.get().strip()
        if not word:
            messagebox.showwarning("Eingabe fehlt", "Bitte geben Sie ein Wort zum Suchen ein.")
            return

        if GEMINI_API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY":
            messagebox.showerror("API-FEHLER", "Bitte GÜLTIGEN API-Schlüssel eintragen.")
            return

        self.audio_data = None
        self.update_ui_state(True)
        self.status_label.config(text=f"Suche nach '{word}' und generiere Informationen...")

        threading.Thread(target=self._run_manual_search_sequence, args=(word,)).start()

    def _run_manual_search_sequence(self, word_de):
        """Führt alle API-Aufrufe für die manuelle Suche aus."""
        target_lang = self.translation_language.get()

        try:
            # Füge hier eine kleine Pause ein, um Netzwerkpuffer freizugeben
            time.sleep(2)

            # 1. Text-Generierung (Übersetzung & Definition)
            print("DEBUG: Starte Text-Generierung (Übersetzung & Definition)")
            self._generate_translation_and_definition(word_de, target_lang)
            print("DEBUG: Text-Generierung abgeschlossen.")

            # 2. Bild-Generierung
            print("DEBUG: Starte Bild-Generierung")
            self._generate_image(word_de)
            print("DEBUG: Bild-Generierung abgeschlossen.")

            # 3. Audio-Generierung
            print("DEBUG: Starte Audio-Generierung")
            self._generate_audio(self.current_word["en"])
            print("DEBUG: Audio-Generierung abgeschlossen.")

            self.master.after(0, lambda: self._on_success())

        except Exception as err:
            self.master.after(0, lambda e=err: self._on_error(f"Generierungsfehler: {e}"))


    def _generate_translation_and_definition(self, word_de, target_lang):
        """Generiert die Übersetzung und eine Definition für ein gegebenes Wort."""
        prompt = (
            f"Finde die beste Übersetzung des deutschen Wortes '{word_de}' in {target_lang}. "
            f"Erstelle dann eine kurze, prägnante Definition in Deutsch (maximal 3 Sätze). "
            f"Antworte NUR und ZWINGEND als JSON-Objekt im folgenden Format:\n"
            f'{{"wort_de": "{word_de}", "wort_en": "The Translation", "definition_de": "Die Definition in Deutsch"}}'
        )

        headers = {"Content-Type": "application/json"}
        url = f"{API_URL}{TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "wort_de": {"type": "STRING"},
                        "wort_en": {"type": "STRING"},
                        "definition_de": {"type": "STRING"}
                    }
                }
            }
        }

        response_data = exponential_backoff_fetch(url, payload, headers)

        try:
            json_text = response_data['candidates'][0]['content']['parts'][0]['text']
            word_data = json.loads(json_text)

            # VERBESSERTES PARSING: Sicherer Zugriff mit .get() anstelle von direkter Indexierung
            word_en = word_data.get("wort_en", "")
            definition_de = word_data.get("definition_de", "Keine Definition von der API erhalten.")
            wort_de_response = word_data.get("wort_de", word_de) # Fallback auf die Eingabe

            # Fallback-Übersetzung falls nötig und googletrans installiert ist
            if not word_en and Translator:
                translator = Translator()
                word_en = translator.translate(word_de, dest=self._get_lang_code(target_lang)).text

            # Aktualisieren des Zustands
            self.current_word["en"] = word_en if word_en else "Übersetzung fehlt"
            self.current_word["description"] = definition_de
            self.current_word["de"] = wort_de_response

            self.master.after(0, lambda: self.set_text_content(
                self.current_word["de"], self.current_word["en"], self.current_word["description"]
            ))

        except (KeyError, json.JSONDecodeError, IndexError) as e:
            raise Exception(f"Fehler beim Parsen der Text-API-Antwort (Prüfen Sie den API-Schlüssel oder die JSON-Antwort): {e}")

    # --------------------------------------------------------------------------------------
    # 5. API-AUFRUFE FÜR ZUFALLS-VOKABELN
    # --------------------------------------------------------------------------------------

    def generate_new_word(self):
        """Startet den Prozess zur Generierung eines neuen Wortes in einem separaten Thread."""
        if GEMINI_API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY":
            messagebox.showerror("API-FEHLER", "Bitte GÜLTIGEN API-Schlüssel eintragen.")
            return

        self.audio_data = None
        self.update_ui_state(True)
        self.status_label.config(text="Generiere neues Wort und Bild... Bitte warten Sie.")

        threading.Thread(target=self._run_generation_sequence).start()

    def _run_generation_sequence(self):
        """Führt alle API-Aufrufe (Text, Bild, Audio) nacheinander aus."""
        target_lang = self.translation_language.get()

        try:
            # Füge hier eine kleine Pause ein, um Netzwerkpuffer freizugeben
            time.sleep(2)

            # 1. Text-Generierung (Wort & Definition)
            print("DEBUG: Starte Text-Generierung (Zufallswort & Definition)")
            self._generate_random_word_and_definition(target_lang)
            print("DEBUG: Text-Generierung abgeschlossen.")

            # 2. Bild-Generierung
            print("DEBUG: Starte Bild-Generierung")
            self._generate_image(self.current_word["de"])
            print("DEBUG: Bild-Generierung abgeschlossen.")

            # 3. Audio-Generierung
            print("DEBUG: Starte Audio-Generierung")
            self._generate_audio(self.current_word["en"])
            print("DEBUG: Audio-Generierung abgeschlossen.")

            self.master.after(0, lambda: self._on_success())

        except Exception as err:
            self.master.after(0, lambda e=err: self._on_error(f"Generierungsfehler: {e}"))

    def _on_success(self):
        """Wird bei erfolgreicher Generierung aufgerufen."""
        print("DEBUG: Generierung abgeschlossen. UI-Update.")
        self.status_label.config(text="Generierung abgeschlossen.")
        self.update_ui_state(False)

    def _on_error(self, message):
        """Wird bei einem Fehler aufgerufen."""
        print(f"DEBUG: Fehlerbehandlung gestartet: {message}")
        self.status_label.config(text="FEHLER! Siehe Meldungsfenster für Details.")
        messagebox.showerror("Fehler", message)
        self.update_ui_state(False)


    def _generate_random_word_and_definition(self, target_lang):
        """Generiert ein zufälliges deutsches Wort, die Übersetzung und eine Definition."""
        prompt = (
            f"Erfinde ein einzelnes, mittelkomplexes deutsches Substantiv mit Artikel. "
            f"Generiere dann die Übersetzung in {target_lang} und eine kurze, prägnante Definition (maximal 3 Sätze). "
            f"Antworte NUR und ZWINGEND als JSON-Objekt im folgenden Format:\n"
            f'{{"wort_de": "Das Wort", "wort_en": "The Translation", "definition_de": "Die Definition in Deutsch"}}'
        )

        headers = {"Content-Type": "application/json"}
        url = f"{API_URL}{TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "wort_de": {"type": "STRING"},
                        "wort_en": {"type": "STRING"},
                        "definition_de": {"type": "STRING"}
                    }
                }
            }
        }

        response_data = exponential_backoff_fetch(url, payload, headers)

        try:
            json_text = response_data['candidates'][0]['content']['parts'][0]['text']
            word_data = json.loads(json_text)

            # VERBESSERTES PARSING: Sicherer Zugriff mit .get() anstelle von direkter Indexierung
            word_de = word_data.get("wort_de", "Zufallswort")
            word_en = word_data.get("wort_en", "")
            definition_de = word_data.get("definition_de", "Keine Definition von der API erhalten.")

            # Fallback-Übersetzung falls nötig und googletrans installiert ist
            if not word_en and Translator:
                translator = Translator()
                word_en = translator.translate(word_de, dest=self._get_lang_code(target_lang)).text

            # Aktualisieren des Zustands
            self.current_word["de"] = word_de
            self.current_word["en"] = word_en if word_en else "Übersetzung fehlt"
            self.current_word["description"] = definition_de

            self.master.after(0, lambda: self.set_text_content(
                self.current_word["de"], self.current_word["en"], self.current_word["description"]
            ))

        except (KeyError, json.JSONDecodeError, IndexError) as e:
            raise Exception(f"Fehler beim Parsen der Text-API-Antwort (Prüfen Sie den API-Schlüssel oder die JSON-Antwort): {e}")

    # --------------------------------------------------------------------------------------
    # 6. BILD- UND AUDIO-FUNKTIONEN
    # --------------------------------------------------------------------------------------

    def _generate_image(self, prompt_text):
        """Generiert ein Bild basierend auf dem deutschen Wort."""
        if Image is None or ImageTk is None:
            return

        prompt = f"Ein fotorealistisches, detailliertes Bild, das das deutsche Wort '{prompt_text}' illustriert. Hohe Qualität, kein Text, neutraler Hintergrund."

        url = f"{API_URL}{IMAGE_MODEL}:predict?key={GEMINI_API_KEY}"
        payload = {
            "instances": {"prompt": prompt},
            "parameters": {"sampleCount": 1}
        }

        try:
            self.master.after(0, lambda: self.status_label.config(text="Generiere Bild..."))
            image_data = exponential_backoff_fetch(url, payload, {"Content-Type": "application/json"})

            base64_img = image_data['predictions'][0]['bytesBase64Encoded']
            self.last_base64_img = base64_img

            self.master.after(0, lambda: self._display_image_thread())

        except Exception as e:
            self.master.after(0, lambda: self.image_label.config(text=f"Bild-Fehler: {e}"))
            print(f"Bildgenerierungsfehler: {e}")

    def _display_image_thread(self):
        """Lädt und skaliert das Bild."""
        try:
            base64_img = getattr(self, 'last_base64_img', None)
            if not base64_img:
                return

            image_bytes = base64.b64decode(base64_img)
            img = Image.open(io.BytesIO(image_bytes))

            self.master.after(0, lambda: self._display_image(img))
        except Exception as e:
            self.master.after(0, lambda: self.image_label.config(text=f"Bild-Fehler: {e}"))


    def _display_image(self, img):
        """Hilfsfunktion, um das skalierte Bild im Label anzuzeigen."""
        self.image_label.update_idletasks()
        label_width = self.image_label.winfo_width()
        label_height = self.image_label.winfo_height()

        if label_width < 10 or label_height < 10:
            # Fallback-Größe, falls winfo_width/height noch 0 sind
            label_width, label_height = 300, 300

        ratio = min(label_width / img.width, label_height / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))

        resized_img = img.resize(new_size, Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_img)

        self.image_label.config(image=self.tk_image, text="")
        self.image_label.image = self.tk_image


    def _generate_audio(self, text_to_speak):
        """Generiert Audio-Daten (TTS) für die Übersetzung."""
        if sd is None or np is None:
            return

        self.master.after(0, lambda: self.status_label.config(text="Generiere Audio..."))

        voice = "Kore"

        url = f"{API_URL}{TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"Sage in klarem, freundlichem Ton: {text_to_speak}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
                }
            },
        }

        try:
            audio_response = exponential_backoff_fetch(url, payload, {"Content-Type": "application/json"})

            mime_type = audio_response['candidates'][0]['content']['parts'][0]['inlineData']['mimeType']
            audio_data_base64 = audio_response['candidates'][0]['content']['parts'][0]['inlineData']['data']

            import re
            match = re.search(r'rate=(\d+)', mime_type)
            if not match:
                raise ValueError("Abtastrate (Sample Rate) konnte nicht aus API-Antwort extrahiert werden.")

            sample_rate = int(match.group(1))

            pcm_array = base64_to_array_buffer(audio_data_base64)
            self.audio_data = {"pcm": pcm_array, "rate": sample_rate}

            self.master.after(0, lambda: self.audio_btn.config(state=tk.NORMAL))

        except Exception as e:
            self.audio_data = None
            self.master.after(0, lambda: self.status_label.config(text="Audio-Generierungsfehler."))
            print(f"Audio-Generierungsfehler: {e}")
            self.master.after(0, lambda: self.audio_btn.config(state=tk.DISABLED))


    def play_audio(self):
        """Spielt die gespeicherten Audio-Daten ab."""
        if sd is None or np is None:
            messagebox.showerror("Audio-Fehler", "NumPy und Sounddevice sind nicht korrekt installiert.")
            return

        if self.audio_data is None:
            if self.current_word["en"] and self.current_word["en"] != "The Word":
                self.status_label.config(text="Generiere Audio jetzt nachträglich...")
                # Versucht, Audio bei Bedarf nachträglich zu generieren
                threading.Thread(target=self._generate_audio, args=(self.current_word["en"],)).start()
                return

            messagebox.showwarning("Wiedergabe", "Es sind keine Audio-Daten zum Abspielen vorhanden.")
            return

        try:
            pcm_array = self.audio_data["pcm"]
            sample_rate = self.audio_data["rate"]

            # Konvertierung zu Float für sounddevice
            float_array = pcm_array.astype(np.float32) / 32768.0

            sd.play(float_array, samplerate=sample_rate)
            self.status_label.config(text="Spiele Audio ab...")

            # Wartet im Hintergrund, bis die Wiedergabe abgeschlossen ist
            threading.Thread(target=self._wait_and_reset_status, args=(len(float_array) / sample_rate,)).start()

        except Exception as e:
            messagebox.showerror("Lokaler Audio-Fehler", f"Fehler bei der Audio-Wiedergabe: {e}")

    def _wait_and_reset_status(self, duration):
        """Wartet die Dauer der Audio-Wiedergabe und setzt dann den Status zurück."""
        time.sleep(duration + 0.5)
        self.master.after(0, lambda: self.status_label.config(text="Wiedergabe abgeschlossen."))


    def _get_lang_code(self, lang):
        """Gibt den Sprachcode für googletrans zurück."""
        if lang == "Englisch": return "en"
        if lang == "Spanisch": return "es"
        if lang == "Französisch": return "fr"
        if lang == "Japanisch": return "ja"
        return "en"


if __name__ == "__main__":
    try:
        # Kurzer Check, ob das Internet erreichbar ist, bevor Tkinter startet
        # Der Timeout hier ist absichtlich kurz, um schnell zu prüfen.
        requests.get("https://google.com", timeout=5)
    except requests.exceptions.ConnectionError:
        print("Kritischer Fehler: Keine Internetverbindung gefunden.")

    root = tk.Tk()
    app = VokabelTrainerApp(root)
    root.mainloop()
