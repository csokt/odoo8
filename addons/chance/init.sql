-- összes adat törlése
delete from chance_mozgassor ;
alter sequence chance_mozgassor_id_seq RESTART WITH 1 ;
delete from chance_mozgasfej ;
alter sequence chance_mozgasfej_id_seq RESTART WITH 1 ;
delete from chance_feljegyzes ;
alter sequence chance_feljegyzes_id_seq RESTART WITH 1 ;

-- delete from chance_cikkar ;
-- alter sequence chance_cikkar_id_seq RESTART WITH 1 ;
-- delete from chance_cikk ;
-- alter sequence chance_cikk_id_seq RESTART WITH 1 ;
-- delete from chance_hely ;
-- alter sequence chance_hely_id_seq RESTART WITH 1 ;
-- delete from chance_partner ;
-- alter sequence chance_partner_id_seq RESTART WITH 1 ;
-- delete from chance_mozgastorzs ;
-- alter sequence chance_mozgastorzs_id_seq RESTART WITH 1 ;


-- cikk.csv importálása
-- közben: alter sequence chance_cikk_id_seq RESTART WITH 1 ;
-- cikkar.csv importálása

-- chance_cikkar hiányzó mezőinek kitöltése
update chance_cikkar set hely_id = (select id from chance_hely where azonosito = hely_azonosito limit 1) ;
-- update chance_cikkar as cikkar set megnevezes = cikk.megnevezes from chance_cikk as cikk where cikkar.cikkszam = cikk.cikkszam ;


-- Készletraktár induló készlet feltöltése chance_cikk-ből
insert into chance_mozgasfej (state, mozgasnem, forrashely_id, celallomas_id) values ('elter', 'indulo', 16, 2) ;
insert into chance_mozgassor (mozgasfej_id, cikk_id, mennyiseg, egysegar, mozgasfej_sorszam)
  select 1, id, indulo_keszlet, onkoltseg, 1 from chance_cikk order by id ;

-- /data hivatkozásokat openerp.py-ből kivenni
