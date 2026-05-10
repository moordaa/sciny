import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- 1. POŁĄCZENIE ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Błąd kluczy API: {e}")
    st.stop()

st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 2. FUNKCJE (BEZPIECZNE) ---
def pobierz_pracownikow():
    try:
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        # Naprawa TypeError: jeśli res.data jest None lub nie jest listą, zwracamy pustą listę
        if res and hasattr(res, 'data') and isinstance(res.data, list):
            return res.data
        return []
    except:
        return []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 3. LOGOWANIE ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY")
    with st.container(border=True):
        l = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True, type="primary"):
            if l == "Emil" and p == "Sosna100%":
                st.session_state.update({"zalogowany": True, "uzytkownik": "Emil", "rola": "admin"})
                st.rerun()
            else:
                try:
                    res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                    if res.data and len(res.data) > 0:
                        st.session_state.update({"zalogowany": True, "uzytkownik": l, "rola": res.data[0].get('rola', 'użytkownik')})
                        st.rerun()
                    else: st.error("Błędne dane.")
                except: st.error("Błąd połączenia.")
    st.stop()

# --- 4. MENU ---
with st.sidebar:
    st.title("Menu")
    wybor = st.radio("Nawigacja", ["👥 Pracownicy", "📝 Nowe Wydanie", "🔍 Historia", "📊 Eksport"])
    st.divider()
    if st.button("🚪 Wyloguj", use_container_width=True):
        wyloguj()

# --- 5. ZAKŁADKI ---

if wybor == "👥 Pracownicy":
    st.header("👥 Pracownicy")
    with st.form("f_nowy", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA", type="primary"):
            if nowy:
                try:
                    # Próba zapisu
                    ins = supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                    if ins.data:
                        st.success(f"Dodano: {nowy}")
                        st.rerun()
                    else:
                        st.error("Baza nie zwróciła danych. Kliknij RUN w Supabase!")
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

    st.divider()
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.info("Lista jest pusta. Dodaj kogoś powyżej.")
    else:
        for p in pracownicy:
            # Sprawdzamy czy p to słownik i ma klucz 'nazwa' (blokuje błąd TypeError)
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"d_{p['id']}"):
                    supabase.table("sciny_pracownicy").delete().eq("id", p['id']).execute()
                    st.rerun()

elif wybor == "📝 Nowe Wydanie":
    st.header("📝 Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    # Bezpieczne tworzenie listy nazw
    nazwy = []
    if pracownicy:
        nazwy = [p['nazwa'] for p in pracownicy if isinstance(p, dict) and 'nazwa' in p]

    if not nazwy:
        st.warning("Najpierw dodaj pracowników.")
    else:
        with st.form("f_wydanie", clear_on_submit=True):
            kto = st.selectbox("Pracownik", nazwy)
            m3 = st.number_input("Masa m3", min_value=0.0, step=0.1)
            adn = st.text_input("Notatka")
            if st.form_submit_button("ZAPISZ"):
                # Znajdujemy ID wybranego pracownika
                p_id = next((p['id'] for p in pracownicy if p.get('nazwa') == kto), None)
                if p_id:
                    supabase.table("sciny_wydania").insert({
                        "pracownik_id": p_id, "m3": m3, "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.success("Zapisano!")
                    st.rerun()

elif wybor == "🔍 Historia":
    st.header("🔍 Historia")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("id", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
            st.dataframe(df[['data', 'Pracownik', 'm3', 'adnotacja']], use_container_width=True)
        else:
            st.info("Brak wpisów.")
    except:
        st.error("Błąd ładowania historii.")

elif wybor == "📊 Eksport":
    st.header("📊 Eksport")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("Pobierz Excel", buf.getvalue(), "Raport.xlsx", type="primary")
    except:
        st.error("Błąd eksportu.")
