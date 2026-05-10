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
    st.error(f"Problem z połączeniem (Secrets): {e}")
    st.stop()

# --- 2. KONFIGURACJA ---
st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 3. FUNKCJE ---
def pobierz_pracownikow():
    try:
        res = supabase.table("pracownicy").select("*").order("nazwa").execute()
        # Zawsze zwracamy listę, nawet jeśli jest pusta, aby uniknąć błędów TypeError
        return res.data if res.data and isinstance(res.data, list) else []
    except:
        return []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 4. LOGOWANIE ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY")
    with st.container(border=True):
        l = st.text_input("Login")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True, type="primary"):
            if l == "Emil" and p == "Sosna100%":
                st.session_state.update({"zalogowany": True, "uzytkownik": "Emil", "rola": "admin"})
                st.rerun()
            else:
                try:
                    res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                    if res.data:
                        st.session_state.update({
                            "zalogowany": True, 
                            "uzytkownik": l, 
                            "rola": res.data[0].get('rola', 'użytkownik')
                        })
                        st.rerun()
                    else:
                        st.error("Błędne dane!")
                except:
                    st.error("Błąd bazy!")
    st.stop()

# --- 5. MENU (CZAT USUNIĘTY) ---
with st.sidebar:
    st.title("🪵 Ściny")
    st.success(f"Użytkownik: **{st.session_state.uzytkownik}**")
    
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
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.warning("Dodaj pracowników w zakładce 'Pracownicy', aby móc rejestrować wydania.")
    else:
        # Bezpieczne tworzenie listy - naprawia błędy TypeError widoczne na zrzutach
        nazwy_p = [p['nazwa'] for p in pracownicy if isinstance(p, dict) and 'nazwa' in p]
        
        with st.form("f_wydanie", clear_on_submit=True):
            pracownik = st.selectbox("Pracownik", nazwy_p)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki (szt)", min_value=0)
            m3 = c3.number_input("Masa (m3)", min_value=0.0, step=0.01)
            
            data_w = st.date_input("Data", datetime.today())
            adn = st.text_input("Notatka")
            
            if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                try:
                    p_id = next(p['id'] for p in pracownicy if p['nazwa'] == pracownik)
                    supabase.table("wydania_scin").insert({
                        "pracownik_id": p_id, "data": str(data_w), "dlugosc": dl,
                        "obstawki": ob, "m3": m3, "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.toast("Zapisano!"); st.rerun()
                except Exception as e:
                    st.error(f"Błąd: {e}")

# --- PRZEGLĄDAJ ---
elif wybor == "🔍 Przeglądaj":
    st.header("Historia")
    res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']], use_container_width=True)
    else:
        st.info("Brak wpisów.")

# --- STATYSTYKI ---
elif wybor == "📈 Statystyki":
    st.header("Statystyki")
    res = supabase.table("wydania_scin").select("m3, pracownicy(nazwa)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        st.bar_chart(df.groupby("Pracownik")['m3'].sum())
    else:
        st.info("Brak danych.")

# --- PRACOWNICY ---
elif wybor == "👥 Pracownicy":
    st.header("Pracownicy")
    
    with st.form("f_pracownik", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA"):
            if nowy:
                try:
                    supabase.table("pracownicy").insert({"nazwa": nowy}).execute()
                    st.success(f"Dodano: {nowy}")
                    st.rerun()
                except:
                    st.error("Błąd podczas dodawania.")
            else:
                st.warning("Wpisz nazwę!")

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.info("Brak pracowników w bazie.")
    else:
        for p in lista:
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"del_{p['id']}"):
                    try:
                        supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                        st.rerun()
                    except:
                        st.error("Nie można usunąć (pracownik ma historię wydań).")

# --- EKSPORT ---
elif wybor == "📊 Eksport":
    st.header("Eksport")
    res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
        st.download_button("📥 POBIERZ EXCEL", buf.getvalue(), "Raport_Sciny.xlsx", type="primary")

# --- KONTA WEB ---
elif wybor == "🔐 Konta Web" and st.session_state.rola == "admin":
    st.header("Użytkownicy aplikacji")
    with st.form("f_konta"):
        u_l, u_p = st.text_input("Login"), st.text_input("Hasło")
        u_r = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("UTWÓRZ KONTO"):
            supabase.table("konta_web").insert({"login": u_l, "haslo": u_p, "rola": u_r}).execute()
            st.rerun()
