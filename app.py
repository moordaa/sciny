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
st.set_page_config(page_title="Ściny Web v1.3", page_icon="🪵", layout="centered")

# Inicjalizacja stanu sesji
if 'zalogowany' not in st.session_state:
    st.session_state.zalogowany = False
    st.session_state.uzytkownik = ""
    st.session_state.rola = "użytkownik"

# --- SYSTEM LOGOWANIA ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY WEB")
    l = st.text_input("Login")
    p = st.text_input("Hasło", type="password")
    
    if st.button("ZALOGUJ", use_container_width=True, type="primary"):
        if l == "Emil" and p == "Sosna100%":
            st.session_state.zalogowany = True
            st.session_state.uzytkownik = "Emil"
            st.session_state.rola = "admin"
            st.rerun()
        else:
            try:
                res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                if res.data:
                    st.session_state.zalogowany = True
                    st.session_state.uzytkownik = l
                    st.session_state.rola = res.data[0].get('rola') or "użytkownik"
                    st.rerun()
                else:
                    st.error("Błędne dane logowania!")
            except Exception as e:
                st.error(f"Problem z bazą: {e}")
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

    # --- FUNKCJE POMOCNICZE (ZABEZPIECZONE) ---
    def get_pracownicy_data():
        try:
            res = supabase.table("pracownicy").select("*").order("nazwa").execute()
            return res.data if res.data else []
        except:
            return []

    # =========================================================================
    # ZAKŁADKA: WYDANIA ŚCINEK
    # =========================================================================
    if menu == "🪵 Wydania Ścinek":
        st.title("Nowe wydanie ścinek")
        pracownicy = get_pracownicy_data()
        
        if not pracownicy:
            st.warning("⚠️ Brak pracowników w bazie! Dodaj ich najpierw w zakładce 'Pracownicy'.")
        else:
            # Tworzymy listę nazw do selectboxa
            lista_nazw = [p['nazwa'] for p in pracownicy if isinstance(p, dict)]
            
            with st.form("form_wydania", clear_on_submit=True):
                kto_nazwa = st.selectbox("👷 Wybierz pracownika", lista_nazw)
                c1, c2, c3 = st.columns(3)
                dlu = c1.number_input("Długość (m)", min_value=0.0, step=0.01)
                obs = c2.number_input("Obstawki (szt)", min_value=0, step=1)
                m3 = c3.number_input("Objętość (m3)", min_value=0.0, step=0.01)
                uwagi = st.text_input("📝 Adnotacja")
                data_wyb = st.date_input("📅 Data", datetime.today())
                
                if st.form_submit_button("ZAPISZ WYDANIE", type="primary", use_container_width=True):
                    # Pobranie ID pracownika
                    p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto_nazwa)
                    
                    try:
                        supabase.table("wydania_scin").insert({
                            "pracownik_id": p_id,
                            "data": str(data_wyb),
                            "dlugosc": dlu,
                            "obstawki": obs,
                            "m3": m3,
                            "adnotacja": uwagi,
                            "dodane_przez": st.session_state.uzytkownik
                        }).execute()
                        st.success(f"Zapisano wydanie dla: {kto_nazwa}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu: {e}")

            st.divider()
            st.subheader("🕒 Ostatnie wydania")
            ostatnie = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("id", desc=True).limit(10).execute()
            if ostatnie.data:
                for r in ostatnie.data:
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        nazwa_p = r.get('pracownicy', {}).get('nazwa', 'Nieznany')
                        col1.markdown(f"**{nazwa_p}** | 📅 {r['data']}")
                        col1.caption(f"📏 {r['dlugosc']}m | 🧱 {r['obstawki']}szt | 🧊 {r['m3']}m3 | 📝 {r['adnotacja']}")
                        if col2.button("🗑️", key=f"del_{r['id']}", use_container_width=True):
                            supabase.table("wydania_scin").delete().eq("id", r['id']).execute()
                            st.rerun()

    # =========================================================================
    # ZAKŁADKA: PRACOWNICY
    # =========================================================================
    elif menu == "👥 Pracownicy":
        st.title("👥 Zarządzanie pracownikami")
        with st.container(border=True):
            nowy = st.text_input("Imię i Nazwisko pracownika")
            if st.button("DODAJ NOWEGO PRACOWNIKA", type="primary", use_container_width=True):
                if nowy:
                    try:
                        supabase.table("pracownicy").insert({"nazwa": nowy}).execute()
                        st.success(f"Dodano: {nowy}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Nie udało się dodać: {e}")
        
        st.divider()
        pracownicy = get_pracownicy_data()
        if pracownicy:
            for p in pracownicy:
                if isinstance(p, dict):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"👷 {p['nazwa']}")
                    if c2.button("Usuń", key=f"p_del_{p['id']}", use_container_width=True):
                        supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                        st.rerun()
        else:
            st.info("Lista pracowników jest pusta.")

    # =========================================================================
    # ZAKŁADKA: WYSZUKIWARKA
    # =========================================================================
    elif menu == "🔎 Wyszukiwarka":
        st.title("🔎 Historia i Filtry")
        pracownicy = get_pracownicy_data()
        opcje = ["-- Wszyscy --"] + [p['nazwa'] for p in pracownicy]
        f_kto = st.selectbox("Filtruj wg pracownika", opcje)
        
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Nieznany")
            
            if f_kto != "-- Wszyscy --":
                df = df[df['Pracownik'] == f_kto]
            
            pokaz_df = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja', 'dodane_przez']]
            st.dataframe(pokaz_df, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia.")

    # =========================================================================
    # ZAKŁADKA: STATYSTYKI
    # =========================================================================
    elif menu == "📈 Statystyki":
        st.title("📈 Statystyki")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Nieznany")
            
            t1, t2 = st.tabs(["Objętość (m3)", "Długość (m)"])
            with t1:
                st.bar_chart(df.groupby("Pracownik")['m3'].sum())
            with t2:
                st.bar_chart(df.groupby("Pracownik")['dlugosc'].sum())

    # =========================================================================
    # ZAKŁADKA: EKSPORT
    # =========================================================================
    elif menu == "📊 Eksport Excel":
        st.title("📊 Pobieranie raportu")
        res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Nieznany")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
            
            st.download_button("📥 POBIERZ PLIK EXCEL", output.getvalue(), f"Sciny_{datetime.today().date()}.xlsx", type="primary")

    # =========================================================================
    # ZAKŁADKA: CZAT
    # =========================================================================
    elif menu == "💬 Czat":
        st.title("💬 Czat firmowy")
        msgs = supabase.table("sugestie").select("*").order("id", desc=False).execute()
        
        chat_container = st.container(height=400)
        with chat_container:
            for m in msgs.data:
                role = "user" if m['uzytkownik'] == st.session_state.uzytkownik else "assistant"
                with st.chat_message(role):
                    st.write(f"**{m['uzytkownik']}**: {m['tresc']}")
                    if st.session_state.rola == "admin":
                        if st.button("🗑️", key=f"c_del_{m['id']}"):
                            supabase.table("sugestie").delete().eq("id", m['id']).execute()
                            st.rerun()
                            
        if prompt := st.chat_input("Napisz wiadomość..."):
            supabase.table("sugestie").insert({"uzytkownik": st.session_state.uzytkownik, "tresc": prompt}).execute()
            st.rerun()

    # =========================================================================
    # ZAKŁADKA: KONTA WEB (DLA ADMINA)
    # =========================================================================
    elif menu == "🔐 Konta Web" and st.session_state.rola == "admin":
        st.title("🔐 Konta Web")
        with st.form("new_user_form"):
            nl = st.text_input("Login")
            np = st.text_input("Hasło", type="password")
            nr = st.selectbox("Rola", ["użytkownik", "admin"])
            if st.form_submit_button("DODAJ KONTO"):
                if nl and np:
                    supabase.table("konta_web").insert({"login": nl, "haslo": np, "rola": nr}).execute()
                    st.rerun()
        
        st.divider()
        users = supabase.table("konta_web").select("*").execute()
        for u in users.data:
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"👤 {u['login']} ({u['rola']})")
            c2.write(f"🔑 {u['haslo']}")
            if u['login'] != "Emil" and c3.button("Usuń", key=f"u_del_{u['id']}"):
                supabase.table("konta_web").delete().eq("id", u['id']).execute()
                st.rerun()
