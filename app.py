import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- 1. POŁĄCZENIE Z BAZĄ ---
try:
    URL = st.secrets["URL"]
    KEY = st.secrets["KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Problem z konfiguracją: {e}")
    st.stop()

# --- 2. USTAWIENIA STRONY ---
st.set_page_config(page_title="Ściny Web v2.0", page_icon="🪵", layout="centered")

# --- 3. SESSION STATE (LOGOWANIE) ---
if 'zalogowany' not in st.session_state:
    st.session_state.update({
        "zalogowany": False,
        "uzytkownik": "",
        "rola": "użytkownik"
    })

# --- 4. FUNKCJE POMOCNICZE ---
def pobierz_pracownikow():
    res = supabase.table("pracownicy").select("*").order("nazwa").execute()
    return res.data if res.data else []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 5. PANEL LOGOWANIA ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY WEB v2.0")
    with st.container(border=True):
        l = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True, type="primary"):
            # Superadmin
            if l == "Emil" and p == "Sosna100%":
                st.session_state.update({"zalogowany": True, "uzytkownik": "Emil", "rola": "admin"})
                st.rerun()
            else:
                # Sprawdzanie w bazie konta_web
                res = supabase.table("konta_web").select("*").eq("login", l).eq("haslo", p).execute()
                if res.data:
                    st.session_state.update({
                        "zalogowany": True, 
                        "uzytkownik": l, 
                        "rola": res.data[0].get('rola', 'użytkownik')
                    })
                    st.rerun()
                else:
                    st.error("Nieprawidłowy login lub hasło.")
    st.stop()

# --- 6. INTERFEJS GŁÓWNY ---
with st.sidebar:
    st.title("🪵 Ściny Menu")
    st.write(f"Zalogowano: **{st.session_state.uzytkownik}**")
    
    opcje = ["📝 Nowe Wydanie", "📋 Lista Wydań", "📊 Statystyki", "👥 Pracownicy", "📥 Eksport", "💬 Czat"]
    if st.session_state.rola == "admin":
        opcje.append("🔐 Zarządzanie Kontami")
    
    wybor = st.radio("Nawigacja", opcje)
    st.divider()
    if st.button("🚪 Wyloguj"):
        wyloguj()

# --- 7. ZAKŁADKI ---

# --- NOWE WYDANIE ---
if wybor == "📝 Nowe Wydanie":
    st.header("📝 Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    
    if not pracownicy:
        st.info("Najpierw dodaj pracowników w zakładce 'Pracownicy'.")
    else:
        nazwy_pracownikow = [p['nazwa'] for p in pracownicy]
        
        with st.form("form_scinki", clear_on_submit=True):
            pracownik = st.selectbox("Wybierz pracownika", nazwy_pracownikow)
            c1, c2, c3 = st.columns(3)
            dl = c1.number_input("Długość (m)", min_value=0.0, step=0.1)
            ob = c2.number_input("Obstawki (szt)", min_value=0, step=1)
            m3 = c3.number_input("Masa (m3)", min_value=0.0, step=0.01)
            
            data_w = st.date_input("Data wydania", datetime.today())
            adn = st.text_area("Adnotacja (opcjonalnie)")
            
            if st.form_submit_button("ZAPISZ DO BAZY", type="primary", use_container_width=True):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == pracownik)
                try:
                    supabase.table("wydania_scin").insert({
                        "pracownik_id": p_id,
                        "data": str(data_w),
                        "dlugosc": dl,
                        "obstawki": ob,
                        "m3": m3,
                        "adnotacja": adn,
                        "dodane_przez": st.session_state.uzytkownik
                    }).execute()
                    st.success("Wydanie zapisane pomyślnie!")
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

# --- LISTA WYDAŃ (WYSZUKIWARKA) ---
elif wybor == "📋 Lista Wydań":
    st.header("📋 Historia wydań")
    res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").order("data", desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Przekształcenie danych z relacji
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        
        # Wybór kolumn do wyświetlenia
        df_display = df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']]
        df_display.columns = ['Data', 'Pracownik', 'Długość (m)', 'Obstawki', 'Masa (m3)', 'Notatka']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.write("Brak zapisanych wydań.")

# --- STATYSTYKI ---
elif wybor == "📊 Statystyki":
    st.header("📊 Podsumowanie pracy")
    res = supabase.table("wydania_scin").select("m3, pracownicy(nazwa)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        stats = df.groupby("Pracownik")['m3'].sum().sort_values(ascending=False)
        st.bar_chart(stats)
        st.table(stats)
    else:
        st.info("Brak danych do wykresu.")

# --- PRACOWNICY ---
elif wybor == "👥 Pracownicy":
    st.header("👥 Lista pracowników")
    
    with st.expander("➕ Dodaj nowego pracownika"):
        nowy_p = st.text_input("Imię i Nazwisko")
        if st.button("Zatwierdź"):
            if nowy_p:
                supabase.table("pracownicy").insert({"nazwa": nowy_p}).execute()
                st.success(f"Dodano: {nowy_p}")
                st.rerun()

    st.divider()
    lista = pobierz_pracownikow()
    for p in lista:
        c1, c2 = st.columns([3, 1])
        c1.write(f"👷 {p['nazwa']}")
        if c2.button("❌ Usuń", key=f"del_{p['id']}"):
            try:
                supabase.table("pracownicy").delete().eq("id", p['id']).execute()
                st.rerun()
            except:
                st.error("Nie można usunąć pracownika z historią wydań.")

# --- EKSPORT ---
elif wybor == "📥 Eksport":
    st.header("📥 Eksport do Excel")
    res = supabase.table("wydania_scin").select("*, pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['pracownicy'].apply(lambda x: x['nazwa'] if x else "Nieznany")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3', 'adnotacja']].to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Pobierz plik .xlsx",
            data=output.getvalue(),
            file_name=f"Raport_Sciny_{datetime.now().date()}.xlsx",
            mime="application/vnd.ms-excel",
            type="primary"
        )

# --- CZAT ---
elif wybor == "💬 Czat":
    st.header("💬 Wymiana informacji")
    msgs = supabase.table("sugestie").select("*").order("id", desc=True).limit(20).execute()
    
    # Wyświetlanie wiadomości
    for m in reversed(msgs.data):
        with st.chat_message("user" if m['uzytkownik'] == st.session_state.uzytkownik else "assistant"):
            st.write(f"**{m['uzytkownik']}**: {m['tresc']}")
            
    if tekst := st.chat_input("Napisz coś..."):
        supabase.table("sugestie").insert({
            "uzytkownik": st.session_state.uzytkownik, 
            "tresc": tekst
        }).execute()
        st.rerun()

# --- KONTA (ADMIN) ---
elif wybor == "🔐 Zarządzanie Kontami" and st.session_state.rola == "admin":
    st.header("🔐 Konta użytkowników")
    with st.form("dodaj_konto"):
        u_log = st.text_input("Login")
        u_has = st.text_input("Hasło (tekst jawny)")
        u_rola = st.selectbox("Rola", ["użytkownik", "admin"])
        if st.form_submit_button("DODAJ UŻYTKOWNIKA"):
            supabase.table("konta_web").insert({"login": u_log, "haslo": u_has, "rola": u_rola}).execute()
            st.success("Konto utworzone.")
            st.rerun()
