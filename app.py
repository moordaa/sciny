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
st.set_page_config(page_title="Ściny Web v1.1", page_icon="🪵", layout="centered")

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

    # --- FUNKCJA POBIERANIA PRACOWNIKÓW ---
    def get_pracownicy_list():
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
        pracownicy = get_pracownicy_list()
        
        if not pracownicy:
            st.warning("⚠️ Brak pracowników w bazie! Dodaj ich najpierw w zakładce 'Pracownicy'.")
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

    # =========================================================================
    # ZAKŁADKA: PRACOWNICY (DODAJ ICH TUTAJ NAJPIERW)
    # =========================================================================
    elif menu == "👥 Pracownicy":
        st.title("👥 Lista pracowników")
        nowy = st.text_input("Dodaj nazwisko pracownika (np. Kamil Kamiński)")
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

    # (Reszta zakładek: Wyszukiwarka, Statystyki, Eksport, Czat, Konta Web - bez zmian)
    # Pamiętaj tylko o używaniu "wydania_scin" zamiast "wydania"
