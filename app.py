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

st.set_page_config(page_title="Ściny", page_icon="🪵")

# --- PROSTE LOGOWANIE ---
if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False

if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY - LOGOWANIE")
    l = st.text_input("Użytkownik")
    p = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany = True
            st.rerun()
        else:
            st.error("Błędne dane")
    st.stop()

# --- FUNKCJA POBIERANIA (ODPORNA NA BŁĘDY) ---
def pobierz_pracownikow():
    try:
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except:
        return []

# --- MENU ---
wybor = st.sidebar.radio("Nawigacja", ["👥 Pracownicy", "📝 Nowe Wydanie", "🔍 Historia"])

if wybor == "👥 Pracownicy":
    st.header("👥 Zarządzanie pracownikami")
    
    with st.form("dodaj_p", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA"):
            if nowy:
                try:
                    supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                    st.success(f"Dodano: {nowy}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd bazy: {e}")

    st.divider()
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.info("Lista pracowników jest pusta.")
    else:
        for p in pracownicy:
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"del_{p['id']}"):
                    supabase.table("sciny_pracownicy").delete().eq("id", p['id']).execute()
                    st.rerun()

elif wybor == "📝 Nowe Wydanie":
    st.header("📝 Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.warning("Najpierw dodaj pracowników w menu obok.")
    else:
        nazwy = [p['nazwa'] for p in pracownicy if 'nazwa' in p]
        with st.form("f_wydanie"):
            kto = st.selectbox("Pracownik", nazwy)
            m3 = st.number_input("Masa m3", min_value=0.0)
            if st.form_submit_button("ZAPISZ"):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                supabase.table("sciny_wydania").insert({
                    "pracownik_id": p_id, 
                    "m3": m3,
                    "dodane_przez": st.session_state.uzytkownik if 'uzytkownik' in st.session_state else "Emil"
                }).execute()
                st.success("Zapisano wydanie!")

elif wybor == "🔍 Historia":
    st.header("🔍 Historia")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("id", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
            st.dataframe(df[['data', 'Pracownik', 'm3']], use_container_width=True)
        else:
            st.info("Brak wpisów w historii.")
    except:
        st.error("Nie udało się pobrać historii.")
