import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA POŁĄCZENIA ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Błąd kluczy w Secrets: {e}")
    st.stop()

st.set_page_config(page_title="Ściny 2.0", page_icon="🪵")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- FUNKCJE ---
def pobierz_pracownikow():
    try:
        res = supabase.table("fin_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except:
        return []

# --- LOGOWANIE ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY 2.0 - RESTART")
    l = st.text_input("Login")
    p = st.text_input("Hasło", type="password")
    if st.button("ZALOGUJ", use_container_width=True, type="primary"):
        try:
            res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
            if res.data:
                st.session_state.update({"zalogowany": True, "uzytkownik": l, "rola": res.data[0]['rola']})
                st.rerun()
            else:
                st.error("Błędny login lub hasło.")
        except Exception as e:
            st.error(f"Błąd bazy kont: {e}")
    st.stop()

# --- MENU ---
with st.sidebar:
    st.title("Menu")
    st.success(f"Zalogowano: {st.session_state.uzytkownik}")
    wybor = st.radio("Nawigacja", ["👥 Pracownicy", "📝 Nowe Wydanie", "🔍 Historia"])
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany = False
        st.rerun()

# --- ZAKŁADKI ---

if wybor == "👥 Pracownicy":
    st.header("Lista pracowników")
    with st.form("dodaj_p", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ"):
            if nowy:
                res = supabase.table("fin_pracownicy").insert({"nazwa": nowy}).execute()
                if res.data:
                    st.success("Dodano!")
                    st.rerun()
                else: st.error("Baza nie zapisała danych.")
            else: st.warning("Wpisz imię!")

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.info("Baza jest pusta. Jeśli w SQL dodałeś pracownika, a tu go nie ma, sprawdź URL i KEY w Secrets.")
    for p in lista:
        st.write(f"👷 **{p['nazwa']}**")

elif wybor == "📝 Nowe Wydanie":
    st.header("Wydanie ścinek")
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.warning("Najpierw dodaj pracowników.")
    else:
        nazwy = [p['nazwa'] for p in pracownicy]
        with st.form("wydanie_f", clear_on_submit=True):
            kto = st.selectbox("Pracownik", nazwy)
            masa = st.number_input("Masa m3", min_value=0.0)
            if st.form_submit_button("ZAPISZ"):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                supabase.table("fin_wydania").insert({
                    "pracownik_id": p_id, "m3": masa, "dodane_przez": st.session_state.uzytkownik
                }).execute()
                st.success("Zapisano!")

elif wybor == "🔍 Historia":
    st.header("Historia")
    res = supabase.table("fin_wydania").select("*, fin_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['fin_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        st.dataframe(df[['data', 'Pracownik', 'm3']], use_container_width=True)
    else:
        st.info("Brak danych.")
