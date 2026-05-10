import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- KONFIGURACJA ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
except KeyError:
    st.error("Błąd: Brak kluczy URL/KEY w Secrets!")
    st.stop()

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Ściny Web v1.6", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False
    st.session_state.uzytkownik = ""
    st.session_state.rola = "użytkownik"

# --- LOGOWANIE ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY WEB")
    l = st.text_input("Login")
    p = st.text_input("Hasło", type="password")
    if st.button("ZALOGUJ", use_container_width=True, type="primary"):
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany, st.session_state.uzytkownik, st.session_state.rola = True, "Emil", "admin"
            st.rerun()
        else:
            try:
                res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                if hasattr(res, 'data') and res.data:
                    dane = res.data[0] if isinstance(res.data, list) else res.data
                    st.session_state.zalogowany = True
                    st.session_state.uzytkownik = l
                    st.session_state.rola = dane.get('rola', "użytkownik") if isinstance(dane, dict) else "użytkownik"
                    st.rerun()
                else: 
                    st.error("Błędne dane!")
            except Exception as e: 
                st.error(f"Problem z bazą: {e}")
else:
    # --- MENU ---
    with st.sidebar:
        st.success(f"Zalogowano: **{st.session_state.uzytkownik}**")
        zakladki_menu = ["🪵 Wydania Ścinek", "🔎 Wyszukiwarka", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport Excel", "💬 Czat"]
        if st.session_state.rola == "admin": 
            zakladki_menu.append("🔐 Konta Web")
        menu = st.radio("MENU", zakladki_menu)
        if st.button("🚪 Wyloguj", use_container_width=True):
            st.session_state.zalogowany = False
            st.rerun()

    def get_pracownicy_list():
        try:
            res = supabase.table("pracownicy").select("*").order("nazwa").execute()
            if hasattr(res, 'data'):
                # Upewniamy się, że zawsze zwracamy listę
                if isinstance(res.data, list):
                    return res.data
                elif isinstance(res.data, dict):
                    return [res.data]
            return []
        except Exception as e:
            st.error(f"Błąd pobierania danych z bazy: {e}")
            return []

    # --- ZAKŁADKA WYDANIA ---
    if menu == "🪵 Wydania Ścinek":
        st.title("Nowe wydanie ścinek")
        pracownicy = get_pracownicy_list()
        
        # Filtrujemy tylko te elementy, które faktycznie są słownikami, aby uniknąć TypeError
        pracownicy_dict = [p for p in pracownicy if isinstance(p, dict)]

        if not pracownicy_dict:
            st.warning("⚠️ Brak pracowników w bazie! Dodaj ich w zakładce 'Pracownicy'.")
        else:
            lista_nazw = [p.get('nazwa', 'Nieznany') for p in pracownicy_dict]
            
            with st.form("form_wydania", clear_on_submit=True):
                kto = st.selectbox("👷 Pracownik", lista_nazw)
                c1, c2, c3 = st.columns(3)
                dlu = c1.number_input("Długość (m)", min_value=0.0)
                obs = c2.number_input("Obstawki (szt)", min_value=0)
                m3 = c3.number_input("M3", min_value=0.0)
                adn = st.text_input("📝 Adnotacja")
                dat = st.date_input("📅 Data", datetime.today())
                
                if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                    # Bezpieczne szukanie ID pracownika
                    p_id = next((p.get('id') for p in pracownicy_dict if p.get('nazwa') == kto), None)
                    
                    if p_id is not None:
                        try:
                            supabase.table("wydania_scin").insert({
                                "pracownik_id": p_id, "data": str(dat), "dlugosc": dlu,
                                "obstawki": obs, "m3": m3, "adnotacja": adn,
                                "dodane_przez": st.session_state.uzytkownik
                            }).execute()
                            st.toast("Zapisano!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Błąd zapisu: {e}")
                    else:
                        st.error("Nie znaleziono odpowiedniego ID pracownika!")

    # --- ZAKŁADKA PRACOWNICY ---
    elif menu == "👥 Pracownicy":
        st.title("👥 Pracownicy")
        nowy = st.text_input("Wpisz Imię i Nazwisko")
        if st.button("DODAJ PRACOWNIKA", type="primary"):
            if nowy:
                try:
                    supabase.table("pracownicy").insert({"nazwa": nowy}).execute()
                    st.success(f"Dodano: {nowy}")
                    st.rerun()
                except Exception as e:
                    st.error(f"BŁĄD PODCZAS DODAWANIA: {e}")
            else: 
                st.warning("Wpisz coś!")

        st.divider()
        pracownicy = get_pracownicy_list()
        for p in pracownicy:
            if isinstance(p, dict) and 'nazwa' in p:
                c1, c2 = st.columns([4, 1])
                c1.write(f"👷 **{p['nazwa']}**")
                # Bezpieczne wyciąganie ID i zabezpieczenie klucza przycisku
                if c2.button("Usuń", key=f"p_{p.get('id', 'unknown')}"):
                    supabase.table("pracownicy").delete().eq("id", p.get('id')).execute()
                    st.rerun()

    # --- RESZTA FUNKCJI ---
    elif menu == "🔎 Wyszukiwarka":
        st.title("🔎 Wyszukiwarka")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
        
        data_to_df = res.data if isinstance(res.data, list) else ([res.data] if isinstance(res.data, dict) else [])
        if data_to_df:
            df = pd.DataFrame(data_to_df)
            if 'pracownicy' in df.columns:
                df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']], use_container_width=True)

    elif menu == "📈 Statystyki":
        st.title("📈 Statystyki")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        
        data_to_df = res.data if isinstance(res.data, list) else ([res.data] if isinstance(res.data, dict) else [])
        if data_to_df:
            df = pd.DataFrame(data_to_df)
            if 'pracownicy' in df.columns:
                df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
                st.bar_chart(df.groupby("Pracownik")['m3'].sum())

    elif menu == "📊 Eksport Excel":
        st.title("📊 Eksport")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        
        data_to_df = res.data if isinstance(res.data, list) else ([res.data] if isinstance(res.data, dict) else [])
        if data_to_df:
            df = pd.DataFrame(data_to_df)
            if 'pracownicy' in df.columns:
                df['Pracownik'] = df['pracownicy'].apply(lambda x: x.get('nazwa', 'Nieznany') if isinstance(x, dict) else "Nieznany")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
            st.download_button("📥 POBIERZ EXCEL", output.getvalue(), "Raport.xlsx", type="primary")

    elif menu == "💬 Czat":
        st.title("💬 Czat")
        msgs = supabase.table("sugestie").select("*").order("id", desc=False).execute()
        
        data_msgs = msgs.data if isinstance(msgs.data, list) else ([msgs.data] if isinstance(msgs.data, dict) else [])
        for m in data_msgs:
            if isinstance(m, dict):
                with st.chat_message("user" if m.get('uzytkownik') == st.session_state.uzytkownik else "assistant"):
                    st.write(f"**{m.get('uzytkownik', 'Ktoś')}**: {m.get('tresc', '')}")
                    
        if p := st.chat_input("Napisz..."):
            supabase.table("sugestie").insert({"uzytkownik": st.session_state.uzytkownik, "tresc": p}).execute()
            st.rerun()

    elif menu == "🔐 Konta Web" and st.session_state.rola == "admin":
        st.title("🔐 Konta Web")
        with st.form("new_u"):
            ul = st.text_input("Login")
            up = st.text_input("Hasło", type="password")
            if st.form_submit_button("DODAJ"):
                supabase.table("konta_web").insert({"login": ul, "haslo": up}).execute()
                st.rerun()
