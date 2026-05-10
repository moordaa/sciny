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

st.set_page_config(page_title="Ściny", page_icon="🪵", layout="centered")

if 'zalogowany' not in st.session_state:
    st.session_state.update({"zalogowany": False, "uzytkownik": "", "rola": "użytkownik"})

# --- 2. FUNKCJE ---
def pobierz_pracownikow():
    try:
        # Próba pobrania danych
        res = supabase.table("sciny_pracownicy").select("*").order("nazwa").execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"⚠️ BAZA NIE ODPOWIADA: {e}")
        return []

def wyloguj():
    st.session_state.zalogowany = False
    st.rerun()

# --- 3. LOGOWANIE ---
if not st.session_state.zalogowany:
    st.title("🪵 ŚCINY")
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
                else: st.error("Błędny login/hasło.")
            except: st.error("Problem z bazą logowania.")
    st.stop()

# --- 4. MENU ---
with st.sidebar:
    st.title("Menu")
    st.success(f"Użytkownik: {st.session_state.uzytkownik}")
    wybor = st.radio("Nawigacja", ["📝 Nowe Wydanie", "🔍 Przeglądaj", "📈 Statystyki", "👥 Pracownicy", "📊 Eksport"])
    if st.button("🚪 Wyloguj"): wyloguj()

# --- 5. ZAKŁADKI ---

if wybor == "👥 Pracownicy":
    st.header("👥 Pracownicy")
    with st.form("f_nowy", clear_on_submit=True):
        nowy = st.text_input("Imię i Nazwisko")
        submit = st.form_submit_button("DODAJ PRACOWNIKA")
        if submit:
            if nowy:
                # WYSYŁKA DO BAZY
                res = supabase.table("sciny_pracownicy").insert({"nazwa": nowy}).execute()
                
                # SPRAWDZAMY CZY FAKTYCZNIE COŚ WRÓCIŁO
                if res.data:
                    st.success(f"✅ Sukces! Dodano: {nowy}")
                    st.rerun()
                else:
                    # Jeśli res.data jest puste, wyświetlamy co poszło nie tak
                    st.error("❌ Błąd! Baza przyjęła zapytanie, ale nie zapisała danych. Sprawdź SQL (Krok 1).")
                    st.write("Szczegóły odpowiedzi z bazy:", res)
            else: st.warning("Wpisz imię!")

    st.divider()
    lista = pobierz_pracownikow()
    if not lista:
        st.info("Lista jest obecnie pusta.")
    for p in lista:
        c1, c2 = st.columns([4, 1])
        c1.write(f"👷 **{p.get('nazwa', 'Brak nazwy')}**")
        if c2.button("Usuń", key=f"d_{p.get('id')}"):
            supabase.table("sciny_pracownicy").delete().eq("id", p.get('id')).execute()
            st.rerun()

elif wybor == "📝 Nowe Wydanie":
    st.header("Nowe wydanie")
    pracownicy = pobierz_pracownikow()
    if not pracownicy:
        st.warning("Najpierw dodaj pracowników.")
    else:
        nazwy = [p['nazwa'] for p in pracownicy]
        with st.form("f_wydanie", clear_on_submit=True):
            kto = st.selectbox("Pracownik", nazwy)
            c1, c2, c3 = st.columns(3)
            d = c1.number_input("Długość")
            o = c2.number_input("Obstawki", step=1)
            m = c3.number_input("Masa m3")
            if st.form_submit_button("ZAPISZ"):
                p_id = next(p['id'] for p in pracownicy if p['nazwa'] == kto)
                supabase.table("sciny_wydania").insert({
                    "pracownik_id": p_id, "dlugosc": d, "obstawki": o, "m3": m,
                    "dodane_przez": st.session_state.uzytkownik
                }).execute()
                st.toast("Zapisano!"); st.rerun()

elif wybor == "🔍 Przeglądaj":
    st.header("Historia")
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").order("id", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        st.dataframe(df[['data', 'Pracownik', 'dlugosc', 'obstawki', 'm3']], use_container_width=True)

elif wybor == "📊 Eksport":
    res = supabase.table("sciny_wydania").select("*, sciny_pracownicy(nazwa)").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['Pracownik'] = df['sciny_pracownicy'].apply(lambda x: x['nazwa'] if x else "?")
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("Pobierz Excel", buf.getvalue(), "Raport.xlsx")
