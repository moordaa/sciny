-- 1. Czyścimy stare tabele
DROP TABLE IF EXISTS sciny_wydania;
DROP TABLE IF EXISTS sciny_pracownicy;

-- 2. Tworzymy nowe tabele
CREATE TABLE sciny_pracownicy (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nazwa text NOT NULL
);

CREATE TABLE sciny_wydania (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    pracownik_id bigint REFERENCES sciny_pracownicy(id) ON DELETE CASCADE,
    data date DEFAULT now(),
    dlugosc float8 DEFAULT 0,
    obstawki int8 DEFAULT 0,
    m3 float8 DEFAULT 0,
    adnotacja text,
    dodane_przez text
);

-- 3. WYŁĄCZAMY RLS (Blokady)
ALTER TABLE sciny_pracownicy DISABLE ROW LEVEL SECURITY;
ALTER TABLE sciny_wydania DISABLE ROW LEVEL SECURITY;

-- 4. Nadajemy uprawnienia
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- 5. Dodajemy pracownika na start
INSERT INTO sciny_pracownicy (nazwa) VALUES ('Kamil Kamiński');
