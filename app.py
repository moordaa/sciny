import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- 1. KONFIGURACJA POŁĄCZENIA ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Błąd kluczy w Secrets: {e}")
    st.stop()

# --- 2. USTAWIENIA STRONY ---
st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 3. FUNKCJE POMOCNICZE ---
def pobierz_pracownikow():
    try:
        # Korzystamy z nowej tabeli sciny_pracownicy
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        if res.data and isinstance(res.data, list):
            return res.data
        return []
    except:
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
                    if res.data and len(res.data) > 0:
                        st.session_state.update({
                            "zalogowany": True, 
                            "uzytkownik": l, 
                            "rola": res.data[0].get('rola', 'użytkownik')
                        })
                        st.rerun()
                    else:
                        st.error("Błędne dane logowania.")
                except:
                    st.error("Błąd połączenia z bazą danych.")
    st.stop()

# --- 5. MENU BOCZNE ---
with st.sidebar:
    st.title("🪵 Ściny")
    st.success(f"Zalogowano: **{st.session_state.uzytkownik}**")
    
    opcje = ["📝 Nowe Wydanie", "🔍 Przeglądaj", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport"]
    if st.session_state.rola == "admin":
        opcje.append("🔐 Konta Web")
    
    wybor = st.radio("Nawigacja", opcje)
    st.divider()
    if st.button("🚪 Wyloguj", use_container_width=True):
        wyloguj()

# --- 6. ZAKŁADKI ---

# --- NOWE WYDANIE ---
if wybor == "📝 Nowe Wydanie":
    st.header("Nowe wydanie ścinek")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.warning("Baza pracowników jest pusta. Najpierw dodaj pracowników w zakładce '👥 Pracownicy'.")
    else:
        nazwy_p = [p['nazwa'] for p in pracownicy if isinstance(p, dict) and 'nazwa' in p]
        
        with st.form("form_wydania", clear_on_submit=True):
            pracownik = st.selectbox("Wybierz pracownika", nazwy_p)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki (szt)", min_value=0, step=1)
            m3 = c3.number_input("Masa (m3)", min_value=0.0, step=0.01)
            
            data_w = st.date_input("Data", datetime.today())
            adn = st.text_input("Notatka")
            
            if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                try:
                    p_id = next(p['id'] for p in pracownicy if p.get('nazwa') == pracownik)
                    supabase.table("sciny_wydania").insert({
                        "pracownik_id": p_id, "data": str(data_w), "dlugosc": dl,
                        "obstawki": ob, "m3": m3, "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.toast("Zapisano pomyślnie!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

# --- PRZEGLĄDAJ ---
elif wybor == "🔍 Przeglądaj":
    st.header("Historia wydań")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("data", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Pobieramy nazwę z połączonej tabeli sciny_pracownicy
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
            
            widok = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']]
            widok.columns = ['Data', 'Pracownik', 'Długość', 'Obstawki', 'Masa', 'Notatka']
            st.dataframe(widok, use_container_width=True, hide_index=True)
        else:
            st.info("Historia jest pusta.")
    except:
        st.error("Błąd ładowania danych. Upewnij się, że tabele w Supabase są utworzone.")

# --- STATYSTYKI ---
elif wybor == "📈 Statystyki":
    st.header("Statystyki")
    try:
        res = supabase.table("sciny_wydania").select("m3, sciny_pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
            st.bar_chart(df.groupby("Pracownik")['m3'].sum())
        else:
            st.info("Brak danych do analizy.")
    except:
        st.error("Błąd ładowania statystyk.")

# --- PRACOWNICY ---
elif wybor == "👥 Pracownicy":
    st.header("Zarządzanie pracownikami")
    
    with st.form("f_dodaj", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko nowego pracownika")
        if st.form_submit_button("DODAJ PRACOWNIKA", use_container_width=True):
            if nowy:
                try:
                    supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                    st.success(f"Dodano: {nowy}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd bazy: {e}")
            else:
                st.warning("Wpisz imię i nazwisko!")

    st.divider()
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.info("Baza pracowników jest pusta.")
    else:
        for p in pracownicy:
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"del_{p['id']}"):
                    try:
                        supabase.table("sciny_pracownicy").delete().eq("id", p['id']).execute()
                        st.rerun()
                    except:
                        st.error("Nie można usunąć pracownika (ma historię wydań).")

# --- EKSPORT ---
elif wybor == "📊 Eksport":
    st.header("Eksport danych")
    try:
        res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x.get('nazwa', '?') if isinstance(x, dict) else "?")
            
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
            st.download_button("📥 POBIERZ EXCEL", buf.getvalue(), "Raport_Sciny.xlsx", type="primary", use_container_width=True)
        else:
            st.info("Brak danych do eksportu.")
    except:
        st.error("Błąd przygotowania pliku.")

# --- KONTA WEB ---
elif wybor == "🔐 Konta Web" and st.session_state.rola == "admin":
    st.header("Zarządzanie dostępem")
    with st.form("f_konta"):
        u_log = st.text_input("Nowy Login")
        u_has = st.text_input("Hasło")
        u_rol = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("DODAJ KONTO"):
            try:
                supabase.table("konta_web").insert({"login": u_log, "haslo": u_has, "rola": u_rol}).execute()
                st.success("Konto dodane pomyślnie.")
                st.rerun()
            except:
                st.error("Błąd tworzenia konta.")
