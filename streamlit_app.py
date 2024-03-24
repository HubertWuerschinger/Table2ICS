import streamlit as st
import pdfplumber
import re
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event
from PIL import Image
import io

# Funktion zum Extrahieren von Text aus einem bestimmten Bereich des hochgeladenen PDFs
def extract_text_from_pdf_area(uploaded_file, bbox):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            cropped_page = page.crop(bbox)
            text += cropped_page.extract_text() or ""
            # Konvertieren in ein PIL-Image und Anzeigen der Vorschau
            image_stream = io.BytesIO()
            cropped_page.to_image(resolution=150).save(image_stream, format="PNG")
            pil_image = Image.open(image_stream)
            st.image(pil_image)
    return text

# Anpassen der Logik zur korrekten Verarbeitung des Textes
def process_schedule(text, team_name):
    events = []
    lines = text.split('\n')
    date_pattern = r'(So\.|Mo\.|Di\.|Mi\.|Do\.|Fr\.|Sa\.)\d{2}\.\d{2}\.\d{4}'  # Datumsmuster
    game_pattern = r'(\d{2}:\d{2})\s(.+)-(.+)'  # Spiel-Muster
    current_date = None  # Speicher für das aktuelle Datum

    for line in lines:
        date_match = re.search(date_pattern, line)
        if date_match:
            # Aktualisiere das aktuelle Datum, wenn ein neues Datum gefunden wird
            current_date = date_match.group(0)[-10:]

        # Verarbeite Spiele nur, wenn ein Datum gesetzt ist
        if current_date:
            game_match = re.search(game_pattern, line)
            if game_match:
                time, team1, team2 = game_match.groups()
                if team_name in team1 or team_name in team2:
                    datetime_str = f"{current_date} {time}"
                    dt_start = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
                    dt_start = pytz.timezone("Europe/Berlin").localize(dt_start)
                    dt_end = dt_start + timedelta(hours=2)  # Annahme: Jedes Spiel dauert 2 Stunden

                    summary = f"{team1.strip()} vs {team2.strip()}"
                    events.append({"dtstart": dt_start, "dtend": dt_end, "summary": summary})

    return events



# Funktion zur Erstellung des ICS-Dateiinhalts
def create_ics(events):
    cal = Calendar()
    cal.add('prodid', '-//SV Dörfleins//Match Schedule//EN')
    cal.add('version', '2.0')
    for event in events:
        cal_event = Event()
        cal_event.add('summary', event['summary'])
        cal_event.add('dtstart', event['dtstart'])
        cal_event.add('dtend', event['dtend'])
        cal.add_component(cal_event)
    return cal.to_ical()

# Streamlit App
st.title("SV Dörfleins Spielplan-ICS-Generator")

uploaded_file = st.file_uploader("Laden Sie den Spielplan als PDF hoch", type="pdf")

# Eingabefelder für die Koordinaten
x1 = st.number_input("X1-Koordinate", min_value=0, value=0)
y1 = st.number_input("Y1-Koordinate", min_value=0, value=0)
x2 = st.number_input("X2-Koordinate", min_value=0, value=100)
y2 = st.number_input("Y2-Koordinate", min_value=0, value=100)

if uploaded_file is not None:
    bbox = (x1, y1, x2, y2)
    schedule_text = extract_text_from_pdf_area(uploaded_file, bbox)
    schedule_text = st.text_area("Bearbeitbarer Spielplan", schedule_text, height=300)

if st.button('ICS-Datei erstellen'):
    # Erstellen der ICS-Datei
    team_name = "SV Dörfleins"
    events = process_schedule(schedule_text, team_name)
    ics_content = create_ics(events)  # Verwenden Sie hier 'events' anstelle von 'processed_events'
    st.text_area("ICS-Datei Inhalt", ics_content.decode("utf-8"), height=300)  # Bearbeitbarer ICS-Inhalt
    st.download_button("Download ICS-Datei", data=ics_content, file_name="sv_doerfleins_schedule.ics", mime="text/calendar")

