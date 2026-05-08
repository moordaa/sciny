import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- KONFIGURACJA (POBRANA Z SECRETS) ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
except KeyError:
    st.error("Błąd: Nie znaleziono kluczy URL i KEY w Secrets!")
    st.stop()

# Inicjalizacja klienta Supabase
supabase: Client = create_client(URL, KEY)

# Konfiguracja strony
st.set_page_config(page_title="Ściny Web v1.0", page_icon="🪵", layout="centered")

# Inicjalizacja stanu sesji
if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False
    st.session_state.uzytkownik = ""
    st.session_state.rola = "użytkownik"

# --- SYSTEM LOGOWANIA ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY WEB - Logowanie")
    l = st.text_input("Login")
    p = st.text_input("Hasło", type="password")
    
    if st.button("ZALOGUJ", use_container_width=True, type="primary"):
        # Master Admin (Emil)
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany = True
            st.session_state.uzytkownik = "Emil"
            st.session_state.rola = "admin"
            st.rerun()
        else:
            try:
                # Logowanie przez tabelę konta_web
                res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                if res.data:
                    st.session_state.zalogowany = True
                    st.session_state.uzytkownik = l
                    st.session_state.rola = res.data[0].get('rola') or "użytkownik"
                    st.rerun()
                else:
                    st.error("Nieprawidłowy login lub hasło!")
            except Exception as e:
                st.error(f"Problem z połączeniem: {e}")

else:
    # --- MENU BOCZNE ---
    with st.sidebar:
        st.success(f"Zalogowano: **{st.session_state.uzytkownik}**")
        st.divider()
        
        zakladki_menu = ["🪵 Wydania Ścinek", "🔎 Wyszukiwarka", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport Excel", "💬 Czat"]
        
        if st.session_state.rola == "admin":
            zakladki_menu.append("🔐 Konta Web")
            
        menu = st.radio("MENU", zakladki_menu)
        
        st.divider()
        if st.button("🚪 Wyloguj", use_container_width=True):
            st.session_state.zalogowany = False
            st.rerun()

    # Funkcja pomocnicza do pobierania pracowników
    def get_pracownicy_list():
        res = supabase.table("pracownicy").select("*").order("nazwa").execute()
        return res.data

    # =========================================================================
    # ZAKŁADKA: WYDANIA ŚCINEK
    # =========================================================================
    if menu == "🪵 Wydania Ścinek":
        st.title("Nowe wydanie ścinek")
        pracownicy = get_pracownicy_list()
        
        if not pracownicy:
            st.info("Brak pracowników w bazie. Dodaj ich w zakładce 'Pracownicy'.")
        else:
            lista_nazw = [p['nazwa'] for p in pracownicy]
            
            with st.form("form_wydania", clear_on_submit=True):
                kto = st.selectbox("👷 Pracownik odbierający", lista_nazw)
                
                col1, col2, col3 = st.columns(3)
                dlu = col1.number_input("Długość (m)", min_value=0.0, step=0.01)
                obs = col2.number_input("Obstawki (szt)", min_value=0, step=1)
                m3 = col3.number_input("M3 (objętość)", min_value=0.0, step=0.01)
                
                uwagi = st.text_input("📝 Adnotacja / Uwagi")
                data_wyb = st.date_input("📅 Data wydania", datetime.today())
                
                if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                    # Pobieranie ID wybranego pracownika
                    p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                    
                    supabase.table("wydania_scin").insert({
                        "pracownik_id": p_id,
                        "data": str(data_wyb),
                        "dlugosc": dlu,
                        "obstawki": obs,
                        "m3": m3,
                        "adnotacja": uwagi,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.toast(f"Zapisano wydanie dla: {kto}")
                    st.rerun()

            st.divider()
            st.subheader("🕒 Ostatnie 5 wpisów")
            # Pobieranie ostatnich wpisów z połączeniem nazwy pracownika
            ostatnie = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("id", desc=True).limit(5).execute()
            
            for r in ostatnie.data:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"👤 **{r['pracownicy']['nazwa']}** | 📅 {r['data']}")
                    c1.caption(f"📏 {r['dlugosc']}m | 🧱 {r['obstawki']} szt | 🧊 {r['m3']} m3 | 🔑 {r['dodane_przez']}")
                    if r['adnotacja']: c1.info(f"Notatka: {r['adnotacja']}")
                    
                    if c2.button("🗑️", key=f"del_{r['id']}", use_container_width=True):
                        supabase.table("wydania_scin").delete().eq("id", r['id']).execute()
                        st.rerun()

    # =========================================================================
    # ZAKŁADKA: WYSZUKIWARKA
    # =========================================================================
    elif menu == "🔎 Wyszukiwarka":
        st.title("🔎 Historia wydań")
        pracownicy = get_pracownicy_list()
        opcje_prac = ["-- Wszyscy --"] + [p['nazwa'] for p in pracownicy]
        
        f_kto = st.selectbox("Filtruj pracownika", opcje_prac)
        
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # Spłaszczenie danych (wyciągnięcie nazwy pracownika z obiektu)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'])
            
            if f_kto != "-- Wszyscy --":
                df = df[df['Pracownik'] == f_kto]
            
            # Wyświetlenie tabeli
            st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja', 'dodane_przez']], use_container_width=True)
        else:
            st.warning("Baza wydań jest pusta.")

    # =========================================================================
    # ZAKŁADKA: STATYSTYKI
    # =========================================================================
    elif menu == "📈 Statystyki":
        st.title("📈 Statystyki")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'])
            
            tab1, tab2 = st.tabs(["📊 Suma m3", "📏 Suma długości"])
            with tab1:
                st.bar_chart(df.groupby("Pracownik")['m3'].sum())
            with tab2:
                st.bar_chart(df.groupby("Pracownik")['dlugosc'].sum())

    # =========================================================================
    # ZAKŁADKA: PRACOWNICY
    # =========================================================================
    elif menu == "👥 Pracownicy":
        st.title("👥 Lista pracowników")
        nowy = st.text_input("Dodaj nazwisko pracownika (odbiorcy ścinek)")
        if st.button("DODAJ PRACOWNIKA", type="primary") and nowy:
            supabase.table("pracownicy").insert({"nazwa": nowy}).execute()
            st.rerun()
            
        st.divider()
        pracownicy = get_pracownicy_list()
        for p in pracownicy:
            c1, c2 = st.columns([4, 1])
            c1.write(f"👷 {p['nazwa']}")
            if c2.button("Usuń", key=f"p_del_{p['id']}"):
                supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                st.rerun()

    # =========================================================================
    # ZAKŁADKA: EKSPORT
    # =========================================================================
    elif menu == "📊 Eksport Excel":
        st.title("📊 Pobieranie danych")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'])
            final_df = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja', 'dodane_przez']]
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Wydania')
            
            st.download_button(
                label="📥 POBIERZ PLIK EXCEL",
                data=output.getvalue(),
                file_name=f"Raport_Sciny_{datetime.today().date()}.xlsx",
                mime="application/vnd.ms-excel",
                type="primary"
            )

    # =========================================================================
    # ZAKŁADKA: CZAT
    # =========================================================================
    elif menu == "💬 Czat":
        st.title("💬 Tablica ogłoszeń")
        chat_data = supabase.table("sugestie").select("*").order("id", desc=False).execute()
        
        chat_container = st.container(height=400)
        with chat_container:
            for msg in chat_data.data:
                role = "user" if msg['uzytkownik'] == st.session_state.uzytkownik else "assistant"
                with st.chat_message(role):
                    st.write(f"**{msg['uzytkownik']}**")
                    st.write(msg['tresc'])
                    if st.session_state.rola == "admin":
                        if st.button("Usuń", key=f"c_{msg['id']}"):
                            supabase.table("sugestie").delete().eq("id", msg['id']).execute()
                            st.rerun()
                            
        if prompt := st.chat_input("Napisz wiadomość..."):
            supabase.table("sugestie").insert({
                "uzytkownik": st.session_state.uzytkownik,
                "tresc": prompt
            }).execute()
            st.rerun()

    # =========================================================================
    # ZAKŁADKA: KONTA WEB (ADMIN)
    # =========================================================================
    elif menu == "🔐 Konta Web" and st.session_state.rola == "admin":
        st.title("🔐 Zarządzanie dostępem")
        with st.form("add_user"):
            new_l = st.text_input("Login")
            new_p = st.text_input("Hasło", type="password")
            new_r = st.selectbox("Rola", ["użytkownik", "admin"])
            if st.form_submit_button("STWÓRZ KONTO"):
                supabase.table("konta_web").insert({"login": new_l, "haslo": new_p, "rola": new_r}).execute()
                st.rerun()
                
        st.divider()
        users = supabase.table("konta_web").select("*").execute()
        for u in users.data:
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"👤 {u['login']}")
            c2.write(f"🔑 {u['haslo']}")
            if u['login'] != "Emil" and c3.button("Usuń", key=f"u_{u['id']}"):
                supabase.table("konta_web").delete().eq("id", u['id']).execute()
                st.rerun()
