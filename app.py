import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- POŁĄCZENIE ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Błąd kluczy API: {e}")
    st.stop()

st.title("🪵 ŚCINY - TEST POŁĄCZENIA")

# --- SPRAWDZANIE CO WIDZI APLIKACJA ---
st.write("### 1. Sprawdzam pracowników w bazie...")
try:
    res = supabase.table("sciny_pracownicy").select("*").execute()
    
    if res.data:
        st.success(f"Znaleziono {len(res.data)} pracowników!")
        st.write(res.data)
    else:
        st.warning("Baza jest połączona, ale tabela 'sciny_pracownicy' jest PUSTA.")
        st.info("Jeśli w SQL Editor dodałeś Kamila, a tutaj go nie ma, to masz błędne klucze URL/KEY w Secrets!")
except Exception as e:
    st.error(f"BŁĄD ODCZYTU: {e}")

st.divider()

# --- FORMULARZ DODAWANIA ---
st.write("### 2. Spróbuj dodać pracownika tutaj:")
nowy = st.text_input("Imię i Nazwisko")
if st.button("DODAJ TERAZ"):
    if nowy:
        try:
            ins = supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
            if ins.data:
                st.success(f"Dodano {nowy}! Odśwież stronę.")
                st.rerun()
            else:
                st.error("Baza przyjęła zapytanie, ale nie zapisała danych (prawdopodobnie RLS blokuje).")
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

# --- LOGOWANIE (DODATEK) ---
st.sidebar.title("Status logowania")
if st.sidebar.button("Wyczyść sesję i wróć do logowania"):
    st.session_state.clear()
    st.rerun()
