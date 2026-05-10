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

st.title("🪵 ŚCINY - RESTART")

# --- FUNKCJE ---
def pobierz_pracownikow():
    try:
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except:
        return []

# --- LOGOWANIE ---
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

# --- MENU ---
wybor = st.sidebar.radio("Nawigacja", ["👥 Pracownicy", "📝 Nowe Wydanie", "🔍 Historia"])

if wybor == "👥 Pracownicy":
    st.header("Zarządzanie pracownikami")
    with st.form("f_nowy", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ"):
            if nowy:
                supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                st.success(f"Dodano: {nowy}")
                st.rerun()

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.info("Lista jest pusta.")
    for p in lista:
        st.write(f"👷 **{p.get('nazwa', 'Nieznany')}**")

elif wybor == "📝 Nowe Wydanie":
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.warning("Najpierw dodaj pracowników.")
    else:
        nazwy = [p['nazwa'] for p in pracownicy]
        with st.form("f_wydanie"):
            kto = st.selectbox("Wybierz pracownika", nazwy)
            m3 = st.number_input("Masa m3", min_value=0.0)
            if st.form_submit_button("ZAPISZ"):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                supabase.table("sciny_wydania").insert({"pracownik_id": p_id, "m3": m3}).execute()
                st.success("Zapisano!")

elif wybor == "🔍 Historia":
    st.header("Historia")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
            st.dataframe(df[['data', 'Pracownik', 'm3']], use_container_width=True)
        else:
            st.info("Brak wpisów.")
    except Exception as e:
        st.error(f"Błąd historii: {e}")
