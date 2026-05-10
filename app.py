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

# --- 2. USTAWIENIA STRONY ---
st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 3. FUNKCJE POMOCNICZE ---
def pobierz_pracownikow():
    try:
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except Exception as e:
        st.sidebar.error(f"Błąd odczytu: {e}")
        return []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 4. LOGOWANIE ---
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
                    else:
                        st.error("Błędne dane logowania.")
                except:
                    st.error("Błąd połączenia z bazą.")
    st.stop()

# --- 5. MENU BOCZNE ---
with st.sidebar:
    st.title("🪵 Menu")
    st.success(f"Użytkownik: {st.session_state.uzytkownik}")
    opcje = ["📝 Nowe Wydanie", "🔍 Przeglądaj", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport"]
    if st.session_state.rola == "admin": opcje.append("🔐 Konta Web")
    wybor = st.radio("Nawigacja", opcje)
    if st.button("🚪 Wyloguj", use_container_width=True): wyloguj()

# --- 6. ZAKŁADKI ---

if wybor == "📝 Nowe Wydanie":
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.warning("Dodaj pracowników w menu '👥 Pracownicy'.")
    else:
        nazwy_p = [p['nazwa'] for p in pracownicy]
        with st.form("f_wydanie", clear_on_submit=True):
            pracownik = st.selectbox("Pracownik", nazwy_p)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0)
            ob = c2.number_input("Obstawki (szt)", min_value=0)
            m3 = c3.number_input("Masa (m3)", min_value=0.0)
            dat = st.date_input("Data", datetime.today())
            adn = st.text_input("Notatka")
            if st.form_submit_button("ZAPISZ", type="primary", use_container_width=True):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == pracownik)
                supabase.table("sciny_wydania").insert({
                    "pracownik_id": p_id, "data": str(dat), "dlugosc": dl,
                    "obstawki": ob, "m3": m3, "adnotacja": adn,
                    "dodane_przez": st.session_state.uzytkownik
                }).execute()
                st.toast("Zapisano!"); st.rerun()

elif wybor == "🔍 Przeglądaj":
    st.header("Historia")
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("data", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']], use_container_width=True)
    else: st.info("Brak wpisów.")

elif wybor == "📈 Statystyki":
    st.header("Statystyki")
    res = supabase.table("sciny_wydania").select("m3, sciny_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        st.bar_chart(df.groupby("Pracownik")['m3'].sum())
    else: st.info("Brak danych.")

elif wybor == "👥 Pracownicy":
    st.header("Pracownicy")
    with st.form("f_nowy_p", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA", type="primary"):
            if nowy:
                # Tutaj sprawdzamy czy res.data istnieje - jeśli nie, wypisze błąd
                res = supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                if res.data:
                    st.success(f"Dodano: {nowy}")
                    st.rerun()
                else:
                    st.error("Błąd zapisu w bazie danych. Sprawdź SQL Editor.")
            else: st.warning("Wpisz imię!")

    st.divider()
    lista = pobierz_pracownikow()
    for p in lista:
        c1, c2 = st.columns([4, 1])
        c1.write(f"👷 **{p['nazwa']}**")
        if c2.button("Usuń", key=f"d_{p['id']}"):
            supabase.table("sciny_pracownicy").delete().eq("id", p['id']).execute()
            st.rerun()

elif wybor == "📊 Eksport":
    st.header("Eksport")
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
        st.download_button("📥 POBIERZ EXCEL", buf.getvalue(), "Raport.xlsx", type="primary")

elif wybor == "🔐 Konta Web" and st.session_state.rola == "admin":
    st.header("Konta")
    with st.form("f_k"):
        u, h = st.text_input("Login"), st.text_input("Hasło")
        r = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("DODAJ"):
            supabase.table("konta_web").insert({"login": u, "haslo": h, "rola": r}).execute()
            st.rerun()
