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
    st.error(f"Błąd kluczy API w Secrets: {e}")
    st.stop()

st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 2. FUNKCJE ---
def pobierz_pracownikow():
    try:
        # Pobieranie danych z Twoich nowych tabel
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"🚨 Błąd połączenia z bazą: {e}")
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
                    if res.data:
                        st.session_state.update({"zalogowany": True, "uzytkownik": l, "rola": res.data[0].get('rola', 'użytkownik')})
                        st.rerun()
                    else: st.error("Nieprawidłowy login lub hasło.")
                except: st.error("Błąd bazy danych.")
    st.stop()

# --- 4. MENU ---
with st.sidebar:
    st.title("Menu")
    st.success(f"Zalogowano: {st.session_state.uzytkownik}")
    wybor = st.radio("Nawigacja", ["📝 Nowe Wydanie", "🔍 Przeglądaj", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport"])
    st.divider()
    if st.button("🚪 Wyloguj", use_container_width=True):
        wyloguj()

# --- 5. ZAKŁADKI ---

if wybor == "👥 Pracownicy":
    st.header("👥 Zarządzanie pracownikami")
    
    with st.form("f_nowy", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA", type="primary", use_container_width=True):
            if nowy:
                # Wysłanie danych do bazy
                res = supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                if res.data:
                    st.success(f"✅ Dodano pomyślnie: {nowy}")
                    st.rerun()
                else:
                    st.error("Baza przyjęła dane, ale ich nie wyświetla. Upewnij się, że kliknąłeś RUN w Supabase!")
            else:
                st.warning("Wpisz imię i nazwisko!")

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.info("Baza pracowników jest pusta.")
    
    for p in lista:
        if isinstance(p, dict) and 'nazwa' in p:
            c1, c2 = st.columns([4, 1])
            c1.write(f"👷 **{p['nazwa']}**")
            if c2.button("Usuń", key=f"d_{p['id']}"):
                supabase.table("sciny_pracownicy").delete().eq("id", p['id']).execute()
                st.rerun()

elif wybor == "📝 Nowe Wydanie":
    st.header("📝 Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.warning("Baza pracowników jest pusta. Dodaj kogoś w zakładce 'Pracownicy'.")
    else:
        nazwy = [p['nazwa'] for p in pracownicy if 'nazwa' in p]
        with st.form("f_wydanie", clear_on_submit=True):
            kto = st.selectbox("Wybierz pracownika", nazwy)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki", min_value=0, step=1)
            m3 = c3.number_input("Masa m3", min_value=0.0, step=0.01)
            adn = st.text_input("Notatka")
            if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                supabase.table("sciny_wydania").insert({
                    "pracownik_id": p_id, "dlugosc": dl, "obstawki": ob, "m3": m3,
                    "adnotacja": adn, "dodane_przez": st.session_state.uzytkownik
                }).execute()
                st.toast("Zapisano!"); st.rerun()

elif wybor == "🔍 Przeglądaj":
    st.header("🔍 Historia")
    # Pobieramy wydania wraz z nazwą pracownika (relacja)
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("id", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        # Naprawa wyświetlania nazwy pracownika z klucza obcego
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
        st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']], use_container_width=True)
    else: st.info("Brak wpisów w historii.")

elif wybor == "📈 Statystyki":
    st.header("📈 Statystyki")
    res = supabase.table("sciny_wydania").select("m3, sciny_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
        st.bar_chart(df.groupby("Pracownik")['m3'].sum())
    else: st.info("Brak danych.")

elif wybor == "📊 Eksport":
    st.header("📊 Eksport danych")
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 POBIERZ EXCEL", buf.getvalue(), "Raport_Sciny.xlsx", type="primary")
