import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Połączenie
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets.")
    st.stop()

st.set_page_config(page_title="System Ściny", page_icon="🪵")

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
            st.error("Błędne dane!")
    st.stop()

# 3. Nawigacja (TU SĄ TWOJE OPCJE!)
st.sidebar.title("MENU")
wybor = st.sidebar.radio("Wybierz czynność:", [
    "👥 Pracownicy (DODAJ TUTAJ)", 
    "📝 Nowe Wydanie", 
    "🔍 Historia wydań"
])

# --- ZAKŁADKA: PRACOWNICY ---
if wybor == "👥 Pracownicy (DODAJ TUTAJ)":
    st.header("👥 Zarządzanie pracownikami")
    
    # FORMULARZ DODAWANIA - TO O TO CI CHODZIŁO!
    with st.form("form_pracownik", clear_on_submit=True):
        nowy_pracownik = st.text_input("Imię i Nazwisko nowego pracownika")
        if st.form_submit_button("DODAJ PRACOWNIKA DO BAZY"):
            if nowy_pracownik:
                supabase.table("sciny_pracownicy").insert({"nazwa": nowy_pracownik}).execute()
                st.success(f"Pomyślnie dodano: {nowy_pracownik}")
                st.rerun()
            else:
                st.warning("Wpisz imię!")

    st.divider()
    st.subheader("Aktualna lista:")
    res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
    if res.data:
        for p in res.data:
            st.write(f"👷 {p['nazwa']}")
    else:
        st.info("Baza pracowników jest pusta.")

# --- ZAKŁADKA: NOWE WYDANIE ---
elif wybor == "📝 Nowe Wydanie":
    st.header("📝 Nowe wydanie ścinek")
    res_p = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
    
    if not res_p.data:
        st.warning("Najpierw dodaj pracowników w menu po lewej!")
    else:
        pracownicy = {p['nazwa']: p['id'] for p in res_p.data}
        with st.form("form_wydanie", clear_on_submit=True):
            kto = st.selectbox("Wybierz pracownika", list(pracownicy.keys()))
            m3 = st.number_input("Masa (m3)", min_value=0.0, step=0.1)
            notatka = st.text_input("Notatka")
            if st.form_submit_button("ZAPISZ WYDANIE"):
                supabase.table("sciny_wydania").insert({
                    "pracownik_id": pracownicy[kto], 
                    "m3": m3, 
                    "adnotacja": notatka
                }).execute()
                st.success("Zapisano!")

# --- ZAKŁADKA: HISTORIA ---
elif wybor == "🔍 Historia wydań":
    st.header("🔍 Historia")
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("id", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        st.dataframe(df[['data', 'Pracownik', 'm3', 'adnotacja']], use_container_width=True)
    else:
        st.info("Historia jest pusta.")

if st.sidebar.button("Wyloguj"):
    st.session_state.zalogowany = False
    st.rerun()
