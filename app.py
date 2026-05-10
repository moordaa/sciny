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
    st.error(f"Błąd konfiguracji kluczy: {e}")
    st.stop()

# --- 2. USTAWIENIA ---
st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 3. BEZPIECZNE FUNKCJE ---
def pobierz_pracownikow():
    try:
        res = supabase.table("pracownicy").select("*").order("nazwa").execute()
        # Naprawa TypeError: upewniamy się, że zwracamy listę
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
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.warning("Najpierw dodaj pracowników w zakładce '👥 Pracownicy'.")
    else:
        # Bezpieczne pobieranie nazw
        nazwy_p = [p['nazwa'] for p in pracownicy if isinstance(p, dict) and 'nazwa' in p]
        
        with st.form("form_wydania", clear_on_submit=True):
            pracownik = st.selectbox("Wybierz pracownika", nazwy_p)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki (szt)", min_value=0)
            m3 = c3.number_input("Masa (m3)", min_value=0.0, step=0.01)
            
            data_w = st.date_input("Data", datetime.today())
            adn = st.text_input("Notatka")
            
            if st.form_submit_button("ZAPISZ", type="primary", use_container_width=True):
                try:
                    p_id = next(p['id'] for p in pracownicy if p.get('nazwa') == pracownik)
                    supabase.table("wydania_scin").insert({
                        "pracownik_id": p_id, "data": str(data_w), "dlugosc": dl,
                        "obstawki": ob, "m3": m3, "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.toast("Zapisano pomyślnie!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Nie udało się zapisać wydania: {e}")

# --- PRZEGLĄDAJ ---
elif wybor == "🔍 Przeglądaj":
    st.header("Historia wydań")
    try:
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            
            widok = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']]
            widok.columns = ['Data', 'Pracownik', 'Długość', 'Obstawki', 'Masa', 'Notatka']
            st.dataframe(widok, use_container_width=True, hide_index=True)
        else:
            st.info("Brak wpisów w historii.")
    except:
        st.error("Wystąpił błąd podczas ładowania danych.")

# --- STATYSTYKI ---
elif wybor == "📈 Statystyki":
    st.header("Statystyki pracy")
    try:
        res = supabase.table("wydania_scin").select("m3, pracownicy(nazwa)").execute()
        if res.data and len(res.data) > 0:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            st.bar_chart(df.groupby("Pracownik")['m3'].sum())
        else:
            st.info("Brak danych do wykresu.")
    except:
        st.error("Błąd ładowania statystyk.")

# --- PRACOWNICY ---
elif wybor == "👥 Pracownicy":
    st.header("Zarządzanie pracownikami")
    
    with st.form("f_dodaj_pracownika", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        if st.form_submit_button("DODAJ PRACOWNIKA", use_container_width=True):
            if nowy:
                try:
                    # Naprawa błędu dodawania
                    res = supabase.table("pracownicy").insert({"nazwa": nowy}).execute()
                    if res.data:
                        st.success(f"Dodano pracownika: {nowy}")
                        st.rerun()
                    else:
                        st.error("Baza nie zapisała pracownika (sprawdź RLS w Supabase).")
                except Exception as e:
                    st.error(f"Błąd bazy: {e}")
            else:
                st.warning("Wpisz imię i nazwisko!")

    st.divider()
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.info("Brak pracowników w bazie.")
    else:
        for p in pracownicy:
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                if c2.button("Usuń", key=f"del_{p['id']}"):
                    try:
                        supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                        st.rerun()
                    except:
                        st.error("Nie można usunąć (pracownik ma wpisy w historii).")

# --- EKSPORT ---
elif wybor == "📊 Eksport":
    st.header("Pobieranie danych")
    try:
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
            st.download_button("📥 POBIERZ PLIK EXCEL", buf.getvalue(), "Raport_Sciny.xlsx", type="primary", use_container_width=True)
        else:
            st.info("Brak danych do wyeksportowania.")
    except:
        st.error("Błąd podczas przygotowywania pliku.")

# --- KONTA WEB (ADMIN) ---
elif wybor == "🔐 Konta Web" and st.session_state.rola == "admin":
    st.header("Dostęp do aplikacji")
    with st.form("f_konta"):
        u_log = st.text_input("Login")
        u_has = st.text_input("Hasło")
        u_rol = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("DODAJ KONTO"):
            try:
                supabase.table("konta_web").insert({"login": u_log, "haslo": u_has, "rola": u_rol}).execute()
                st.success("Konto utworzone.")
                st.rerun()
            except:
                st.error("Nie udało się dodać konta.")
