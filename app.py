import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Połączenie
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Błąd kluczy API!")
    st.stop()

st.title("🪵 SYSTEM ŚCINY")

if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False

if not st.session_state.zalogowany:
    l = st.text_input("Użytkownik")
    p = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany = True
            st.rerun()
        else:
            st.error("Błędne dane")
    st.stop()

tab1, tab2 = st.tabs(["📝 Dodaj wpis", "🔍 Historia"])

with tab1:
    with st.form("form_dodaj", clear_on_submit=True):
        kto = st.text_input("Imię i Nazwisko pracownika")
        ile = st.number_input("Masa m3", min_value=0.0, step=0.1)
        if st.form_submit_button("ZAPISZ"):
            if kto:
                supabase.table("system_scinki").insert({"pracownik": kto, "m3": ile}).execute()
                st.success(f"Zapisano: {kto}")
                st.rerun()

with tab2:
    res = supabase.table("system_scinki").select("*").order("id", desc=True).execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data)[['data', 'pracownik', 'm3']], use_container_width=True)

if st.sidebar.button("Wyloguj"):
    st.session_state.zalogowany = False
    st.rerun()
