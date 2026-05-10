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
    st.error(f"Problem z konfiguracją połączenia: {e}")
    st.stop()

# --- 2. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

# --- 3. STAN SESJI ---
if 'zalogowany' not in st.session_state:
    st.session_state.update({
        "zalogowany": False,
        "uzytkownik": "",
        "rola": "użytkownik"
    })

# --- 4. BEZPIECZNE FUNKCJE POBIERANIA DANYCH ---
def pobierz_pracownikow():
    try:
        res = supabase.table("pracownicy").select("*").order("nazwa").execute()
        # Zwraca listę tylko jeśli res.data faktycznie jest listą
        if res.data and isinstance(res.data, list):
            return res.data
        return []
    except:
        return []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 5. LOGOWANIE ---
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
                    st.error("Błąd połączenia z bazą.")
    st.stop()

# --- 6. MENU BOCZNE (CZAT USUNIĘTY) ---
with st.sidebar:
    st.title("🪵 Ściny")
    st.success(f"Zalogowano: **{st.session_state.uzytkownik}**")
    
    opcje = ["📝 Wydaj ścinki", "🔍 Przeglądaj", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport"]
    if st.session_state.rola == "admin":
        opcje.append("🔐 Konta Web")
    
    wybor = st.radio("Menu", opcje)
    st.divider()
    if st.button("🚪 Wyloguj", use_container_width=True):
        wyloguj()

# --- 7. ZAKŁADKI ---

# --- WYDAJ ŚCINKI ---
if wybor == "📝 Wydaj ścinki":
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.info("Baza pracowników jest pusta. Dodaj pracowników w zakładce 'Pracownicy'.")
    else:
        # Bezpieczne wyciąganie nazw - naprawia TypeError
        nazwy_p = [p['nazwa'] for p in pracownicy if isinstance(p, dict) and 'nazwa' in p]
        
        with st.form("form_wydania", clear_on_submit=True):
            pracownik = st.selectbox("Wybierz pracownika", nazwy_p)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki (szt)", min_value=0, step=1)
            m3 = c3.number_input("Masa (m3)", min_value=0.0, step=0.01)
            
            data_w = st.date_input("Data", datetime.today())
            adn = st.text_input("Adnotacja")
            
            if st.form_submit_button("ZAPISZ", type="primary", use_container_width=True):
                try:
                    p_id = next(p['id'] for p in pracownicy if p.get('nazwa') == pracownik)
                    supabase.table("wydania_scin").insert({
                        "pracownik_id": p_id,
                        "data": str(data_w),
                        "dlugosc": dl,
                        "obstawki": ob,
                        "m3": m3,
                        "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.toast("Zapisano pomyślnie!")
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

# --- PRZEGLĄDAJ ---
elif wybor == "🔍 Przeglądaj":
    st.header("Historia wydań")
    try:
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(res.data)
            # Bezpieczne mapowanie nazwy pracownika
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            
            widok = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']]
            widok.columns = ['Data', 'Pracownik', 'Długość', 'Obstawki', 'Masa', 'Notatka']
            st.dataframe(widok, use_container_width=True, hide_index=True)
        else:
            st.info("Brak wpisów w historii.")
    except:
        st.error("Błąd podczas pobierania historii.")

# --- STATYSTYKI ---
elif wybor == "📈 Statystyki":
    st.header("Podsumowanie")
    try:
        res = supabase.table("wydania_scin").select("m3, pracownicy(nazwa)").execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            sumy = df.groupby("Pracownik")['m3'].sum().sort_values(ascending=False)
            st.bar_chart(sumy)
            st.table(sumy)
        else:
            st.info("Brak danych do analizy.")
    except:
        st.error("Błąd statystyk.")

# --- PRACOWNICY ---
elif wybor == "👥 Pracownicy":
    st.header("Zarządzanie pracownikami")
    
    with st.container(border=True):
        nowy_p = st.text_input("Imię i Nazwisko")
        if st.button("DODAJ PRACOWNIKA", use_container_width=True):
            if nowy_p:
                try:
                    supabase.table("pracownicy").insert({"nazwa": nowy_p}).execute()
                    st.success(f"Dodano: {nowy_p}")
                    st.rerun()
                except:
                    st.error("Błąd podczas dodawania.")

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.write("Brak pracowników.")
    else:
        for p in lista:
            # Naprawia błąd TypeError przy wyświetlaniu listy
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"del_p_{p['id']}"):
                    try:
                        supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                        st.rerun()
                    except:
                        st.error("Nie można usunąć (ma przypisane wydania).")

# --- EKSPORT ---
elif wybor == "📊 Eksport":
    st.header("Pobierz dane")
    try:
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
            
            st.download_button(label="📥 POBIERZ EXCEL", data=buf.getvalue(), file_name="Sciny_Eksport.xlsx", type="primary", use_container_width=True)
        else:
            st.info("Brak danych do eksportu.")
    except:
        st.error("Błąd eksportu.")

# --- KONTA WEB ---
elif wybor == "🔐 Konta Web" and st.session_state.rola == "admin":
    st.header("Zarządzanie dostępem")
    with st.form("nowy_user"):
        u_l = st.text_input("Nowy Login")
        u_p = st.text_input("Hasło")
        u_r = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("UTWÓRZ KONTO"):
            try:
                supabase.table("konta_web").insert({"login": u_l, "haslo": u_p, "rola": u_r}).execute()
                st.success("Dodano konto.")
                st.rerun()
            except:
                st.error("Błąd dodawania konta.")
