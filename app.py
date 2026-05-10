import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Połączenie (wykorzystuje Twoje poprawne Secrets)
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Problem z kluczami API w Secrets!")
    st.stop()

st.set_page_config(page_title="Ściny", page_icon="🪵")

# 2. Logowanie
if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False

if not st.session_state.zalogowany:
    st.title("🪵 LOGOWANIE")
    l = st.text_input("Użytkownik")
    p = st.text_input("Hasło", type="password")
    if st.button("Zaloguj", use_container_width=True, type="primary"):
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany = True
            st.rerun()
        else:
            st.error("Błędne dane")
    st.stop()

# 3. Główna aplikacja (PROSTA I BEZ BŁĘDÓW)
st.title("🪵 SYSTEM ŚCINY")

wybor = st.sidebar.radio("Nawigacja", ["📝 Dodaj wpis", "🔍 Historia"])

if wybor == "📝 Dodaj wpis":
    st.header("Nowe wydanie")
    with st.form("form_dodaj", clear_on_submit=True):
        kto = st.text_input("Imię i Nazwisko pracownika")
        ile = st.number_input("Masa m3", min_value=0.0, step=0.1)
        if st.form_submit_button("ZAPISZ", use_container_width=True, type="primary"):
            if kto:
                try:
                    supabase.table("system_scinki").insert({"pracownik": kto, "m3": ile}).execute()
                    st.success(f"Pomyślnie zapisano: {kto}")
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")
            else:
                st.warning("Musisz podać imię pracownika!")

elif wybor == "🔍 Historia":
    st.header("Historia wydań")
    try:
        res = supabase.table("system_scinki").select("*").order("id", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Wyświetlamy tylko ważne kolumny
            st.dataframe(df[['data', 'pracownik', 'm3']], use_container_width=True, hide_index=True)
        else:
            st.info("Historia jest pusta.")
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")

if st.sidebar.button("🚪 Wyloguj"):
    st.session_state.zalogowany = False
    st.rerun()
