-- Gyártási lap 'rendelt_ora' beírása 'gylap_homogen' táblából #### nincs kész ####
WITH
homogen AS (
  SELECT gyartasi_lap_id, SUM(rendelt_ora) AS rendelt_ora FROM legrand_gylap_homogen WHERE sajat GROUP BY gyartasi_lap_id
)
SELECT gylap.id, homogen.rendelt_ora FROM legrand_gyartasi_lap AS gylap
JOIN homogen ON homogen.gyartasi_lap_id = gylap.id
WHERE gylap.active AND gylap.state = 'uj'
ORDER BY id
;

-- statisztika adatok beírása

WITH
mozgassor AS (
  SELECT sor.gyartasi_lap_id,
         sor.mennyiseg,
         date(fej.create_date) AS create_date,
         gylap.hatarido,
         CASE WHEN date(fej.create_date) <= gylap.hatarido THEN sor.mennyiseg ELSE 0 END AS idoben_db,
         CASE WHEN date(fej.create_date) >  gylap.hatarido THEN sor.mennyiseg ELSE 0 END AS idontul_db
  FROM legrand_mozgassor AS sor
  JOIN legrand_mozgasfej AS fej ON fej.id = sor.mozgasfej_id AND fej.mozgasnem = 'ki'
  JOIN legrand_gyartasi_lap AS gylap ON gylap.id = sor.gyartasi_lap_id
  ),
min_max AS (
  SELECT gyartasi_lap_id,
         min(create_date) AS min_date,
         max(create_date) AS max_date,
         sum(idoben_db) AS idoben_db ,
         sum(idontul_db) AS idontul_db
  FROM mozgassor
  GROUP BY gyartasi_lap_id
  )
UPDATE legrand_gyartasi_lap AS gylap
  SET elso_teljesites   = min_date,
      utolso_teljesites = max_date,
      hatarido_elott_db = idoben_db,
      hatarido_utan_db  = idontul_db
  FROM min_max
  WHERE gylap.id = min_max.gyartasi_lap_id
;

WITH
gylap_ids AS (
  SELECT distinct gyartasi_lap_id
  FROM legrand_mozgassor AS sor
  JOIN legrand_mozgasfej AS fej ON fej.id = sor.mozgasfej_id AND fej.mozgasnem = 'ki'
  ),
stat AS (
  SELECT id,
         round(rendelt_ora/modositott_db*hatarido_elott_db, 2) AS hatarido_elott_ora,
         round(rendelt_ora/modositott_db*hatarido_utan_db, 2) AS hatarido_utan_ora,
         elso_teljesites - date(create_date) AS elsoig_eltelt_nap,
         utolso_teljesites - date(create_date) AS utolsoig_eltelt_nap
  FROM legrand_gyartasi_lap
  JOIN gylap_ids ON gyartasi_lap_id = id
  WHERE active AND modositott_db != 0 AND (hatarido_elott_db > 0 or hatarido_utan_db > 0)
  )
UPDATE legrand_gyartasi_lap AS gylap
  SET hatarido_elott_ora  = stat.hatarido_elott_ora,
      hatarido_utan_ora   = stat.hatarido_utan_ora,
      elsoig_eltelt_nap   = stat.elsoig_eltelt_nap,
      utolsoig_eltelt_nap = stat.utolsoig_eltelt_nap
  FROM stat
  WHERE stat.id = gylap.id
;

-- statisztika adatok lekérdezése

select id, elso_teljesites, utolso_teljesites, hatarido_elott_db, hatarido_utan_db, hatarido_elott_ora, hatarido_utan_ora, elsoig_eltelt_nap, utolsoig_eltelt_nap
from legrand_gyartasi_lap where elso_teljesites is not null limit 100
;



select termekcsoport, to_char(create_date, 'YYYY.MM') as honap, sum(rendelt_ora) as rendelt_ora, round(avg(elsoig_eltelt_nap), 1) as elsoig, round(avg(utolsoig_eltelt_nap), 1) as utolsoig
  from legrand_gyartasi_lap where active and elsoig_eltelt_nap > 0 and hatralek_db = 0 and termekcsoport is not null
  group by termekcsoport, to_char(create_date, 'YYYY.MM')
  order by termekcsoport, to_char(create_date, 'YYYY.MM')
;

select termekcsoport, sum(rendelt_ora) as rendelt_ora, round(avg(elsoig_eltelt_nap), 1) as elsoig, round(avg(utolsoig_eltelt_nap), 1) as utolsoig
  from legrand_gyartasi_lap where active and elsoig_eltelt_nap > 0 and hatralek_db = 0 and termekcsoport is not null
  group by termekcsoport
  order by termekcsoport
;

select termekkod, sum(rendelt_db) as rendelt_db, round(avg(elsoig_eltelt_nap), 1) as elsoig, round(avg(utolsoig_eltelt_nap), 1) as utolsoig
  from legrand_gyartasi_lap where active and elsoig_eltelt_nap > 0 and hatralek_db = 0 and termekkod is not null
  group by termekkod
  order by termekkod
;

select termekcsoport, date(create_date) as felveve, round(avg(elsoig_eltelt_nap), 1) as elsoig, round(avg(utolsoig_eltelt_nap), 1) as utolsoig
  from legrand_gyartasi_lap where active and elsoig_eltelt_nap > 0 and hatralek_db = 0 and termekcsoport is not null
  group by termekcsoport, date(create_date)
  order by termekcsoport, date(create_date)
;

select termekkod, date(create_date) as felveve, elsoig_eltelt_nap, utolsoig_eltelt_nap
  from legrand_gyartasi_lap where active and elsoig_eltelt_nap > 0
  order by termekkod, date(create_date)
;

-- statisztika adatok lekérdezése vége


select * from update_rel
order by max_id desc
limit 10
;

limit 100 ;


update legrand_cikk set cimke_e = true where cikknev ilike 'címke%' ;


delete from chance_mozgassor ;
alter sequence chance_mozgassor_id_seq RESTART WITH 1 ;
delete from chance_mozgasfej ;
alter sequence chance_mozgasfej_id_seq RESTART WITH 1 ;


-- Legrand árlista átvétele VIR-be
-- import impexbe
-- id keresés
WITH
arak as ( select imp.id, cikk.id as cikk_id from legrand_impex as imp join legrand_cikk as cikk on cikk.cikkszam ilike imp.cikkszam where imp.create_uid = 6)
update legrand_impex as imp set cikk_id = arak.cikk_id from arak where imp.create_uid = 6 and arak.id = imp.id
;

delete from legrand_impex as imp where imp.create_uid = 6 and imp.cikk_id is null
;

update legrand_cikk as cikk set bekerulesi_ar = imp.beepules from legrand_impex as imp where cikk.id = imp.cikk_id and imp.create_uid = 6 and imp.beepules != cikk.bekerulesi_ar
;

select imp.beepules, cikk.bekerulesi_ar from legrand_impex as imp join legrand_cikk as cikk on cikk.id = imp.cikk_id where imp.create_uid = 6 and imp.beepules != cikk.bekerulesi_ar
;

delete from legrand_impex as imp where imp.create_uid = 6
;

-- impex alapján cikktörzs árak és gyártási lap árak összevetése
select cikk.cikkszam, cikk.cikknev, cikk.bekerulesi_ar as cikk, dbj.bekerulesi_ar as gylap from legrand_impex as imp
  join legrand_cikk as cikk on cikk.id = imp.cikk_id
  join legrand_gylap_dbjegyzek as dbj on dbj.cikk_id = imp.cikk_id and dbj.gyartasi_lap_id = imp.gyartasi_lap_id
  -- where cikk.bekerulesi_ar = dbj.bekerulesi_ar
;






eszkoz as ( select max(id) as max_id, eszkoz_id from leltar_eszkozatvetel where regi_hasznalo_id is null group by eszkoz_id having count(*) > 1 ),
eszkoz_elozok as ( select atvet.id as prev_id, eszkoz.* from leltar_eszkozatvetel as atvet, eszkoz where atvet.eszkoz_id = eszkoz.eszkoz_id and atvet.id < eszkoz.max_id ),
atvet_rel as (select eszkoz_id, max_id, max(prev_id) as prev_id from eszkoz_elozok group by eszkoz_id, max_id),
update_rel as (select atvet_rel.*, atvet.uj_hasznalo_id as prev_hasznalo_id from atvet_rel join leltar_eszkozatvetel as atvet on atvet_rel.prev_id = atvet.id)
update leltar_eszkozatvetel set regi_hasznalo_id = prev_hasznalo_id from update_rel where id = max_id
;




-- összes adat törlése
-- delete from datawh_files ;
-- alter sequence datawh_files_id_seq RESTART WITH 1 ;
-- delete from datawh_documents ;
-- alter sequence datawh_documents_id_seq RESTART WITH 1 ;

delete from legrand_mozgassor ;
alter sequence legrand_mozgassor_id_seq RESTART WITH 1 ;
delete from legrand_mozgasfej ;
alter sequence legrand_mozgasfej_id_seq RESTART WITH 1 ;

delete from legrand_meo_jkv_selejt ;
delete from legrand_meo_jegyzokonyv ;
delete from legrand_muveletvegzes ;
delete from legrand_gylap_szefo_muvelet ;
delete from legrand_gylap_dbjegyzek ;
delete from legrand_gylap_legrand_muvelet ;
delete from legrand_feljegyzes ;
delete from legrand_gylap_homogen ;

delete from legrand_anyagigeny ;
alter sequence legrand_anyagigeny_id_seq RESTART WITH 1 ;
delete from legrand_gyartasi_lap ;
alter sequence legrand_gyartasi_lap_id_seq RESTART WITH 1000 ;

delete from legrand_bom_line ;
alter sequence legrand_bom_line_id_seq RESTART WITH 1 ;
delete from legrand_bom ;
alter sequence legrand_bom_id_seq RESTART WITH 1 ;

-- delete from legrand_hely ;
 delete from legrand_muvelet ;
delete from legrand_lezer_tampon ;
delete from legrand_hibakod ;
delete from legrand_homogen ;
delete from legrand_cikk ;

-- legrand_cikk feltöltése product_product-ból
insert into legrand_cikk (id, cikkszam, cikknev, alkatresz_e, bekerulesi_ar, active)
  select id, CASE WHEN cikkszam is null THEN ltrim(split_part(name_template, '|', 1)) ELSE cikkszam END, ltrim(split_part(name_template, '|', 2)), anyag,
-- A következő select lassú, ezért lett ideiglenesen helyettesítve az alatta lévővel
--   (select bekerulesi_ar from raktar_darabjegyzek where product_product.id=product_id order by id desc limit 1), true from product_product
   (select bekerulesi_ar from raktar_darabjegyzek where product_product.id=product_id limit 1), true from product_product
-- Saját összeállítású félkésztermékeket kivesszük, később néhány egyszeres beépüléssel bírót visszateszünk
  where active and name_template not like 'referencia%' and name_template not like 'FLK%' and name_template not like 'GYV%' and name_template not like 'HF%'
               and name_template not like 'MR%' and name_template not like 'NAU%' and name_template not like 'UHF%' and name_template not like 'VE%'
  order by id ;

-- legrand_cikk feltöltése kiválasztott félkész termékekkel
WITH felkesz (regi_cikkszam, uj_cikkszam, uj_cikknev) AS (VALUES
('HFD001','SZF001','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF002','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF003','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF004','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF005','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF006','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF007','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF008','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF009','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF010','Hegesztett földelőérintkező /HFD010/'),
('HFD011','SZF011','Hegesztett földelőérintkező /HFD011/'),
('HFS001','SZF012','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF013','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF014','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF015','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF016','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF017','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF018','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF019','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF020','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF021','Cseh null érintkező /VE001/'),
('VE002','SZF022','Cseh fázis érintkező /VE002/'),
('MR001','SZF101','M-Rugózott /MR001/'),
('VE016','SZF201','Csavarozott érintkező cariva /VE016/'),
('UHF001','SZF301','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF302','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF303','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF304','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF305','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF306','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF307','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF308','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF309','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF310','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF311','Ultrahangos fedelek /UHF014/'),
('GYV001','SZF401','Szerelt gyv /GYV001/'),
('GYV004','SZF402','Szerelt gyv VL /GYV004/'),
('GYV005','SZF403','Szerelt gyv VL /GYV005/'),
('GYV006','SZF404','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF405','Szerelt gyv /GYV007/'),
('GYV009','SZF406','Szerelt gyv nélküli kazetta /GYV009/'),
('NAU001','SZF501','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF502','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF503','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF504','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF505','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF506','Nausicaa szerelt betét /NAU008/'),
('FLK001','SZF601','(3.200.0040-00) Érintkező berakás /FLK001/')
)
insert into legrand_cikk (id, cikkszam, cikknev, alkatresz_e, bekerulesi_ar, active, szefo_cikk_e)
  select product_product.id, uj_cikkszam, uj_cikknev, false, 0, true, true from felkesz
    join product_product on cikkszam = regi_cikkszam ;
ALTER SEQUENCE legrand_cikk_id_seq RESTART WITH 3000 ;


-- bom feltöltése raktar_gyartasi_lap-ból
insert into legrand_bom (name, cikk_id, verzio, gylap_default_e, raktar_gylap_id)
  select termekkod || ' késztermék', product_id, 'késztermék', true, id from raktar_gyartasi_lap
    join (select termekkod as utkod, max(id) as utid from raktar_gyartasi_lap where rendelesszam not ilike 'j%' and active group by termekkod) as utgylap on id = utid ;

-- bom_line feltöltése raktar_darabjegyzek-ből
insert into legrand_bom_line (bom_id, cikk_id, beepules)
  select legrand_bom.id, dbjegyzek.product_id, dbjegyzek.ossz_beepules / gylap.rendelt_db as beep from raktar_darabjegyzek as dbjegyzek
    join (select termekkod as utkod, max(id) as utid from raktar_gyartasi_lap where rendelesszam not ilike 'j%' and active group by termekkod) as utgylap on gyartasi_lap_id = utid
    join legrand_bom on raktar_gylap_id = gyartasi_lap_id
    join raktar_gyartasi_lap as gylap on gylap.id = gyartasi_lap_id;

-- bom feltöltése anyagjegyzékből, kiválasztott félkész termékekre
WITH felkesz (regi_cikkszam, uj_cikkszam, uj_cikknev) AS (VALUES
('HFD001','SZF001','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF002','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF003','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF004','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF005','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF006','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF007','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF008','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF009','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF010','Hegesztett földelőérintkező /HFD010/'),
('HFD011','SZF011','Hegesztett földelőérintkező /HFD011/'),
('HFS001','SZF012','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF013','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF014','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF015','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF016','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF017','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF018','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF019','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF020','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF021','Cseh null érintkező /VE001/'),
('VE002','SZF022','Cseh fázis érintkező /VE002/'),
('MR001','SZF101','M-Rugózott /MR001/'),
('VE016','SZF201','Csavarozott érintkező cariva /VE016/'),
('UHF001','SZF301','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF302','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF303','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF304','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF305','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF306','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF307','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF308','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF309','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF310','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF311','Ultrahangos fedelek /UHF014/'),
('GYV001','SZF401','Szerelt gyv /GYV001/'),
('GYV004','SZF402','Szerelt gyv VL /GYV004/'),
('GYV005','SZF403','Szerelt gyv VL /GYV005/'),
('GYV006','SZF404','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF405','Szerelt gyv /GYV007/'),
('GYV009','SZF406','Szerelt gyv nélküli kazetta /GYV009/'),
('NAU001','SZF501','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF502','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF503','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF504','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF505','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF506','Nausicaa szerelt betét /NAU008/'),
('FLK001','SZF601','(3.200.0040-00) Érintkező berakás /FLK001/')
)
insert into legrand_bom (name, cikk_id, verzio, gylap_default_e, beepul_e)
  select uj_cikkszam || ' félkésztermék', legrand_cikk.id, 'félkésztermék', false, true from felkesz
    join legrand_cikk on cikkszam = uj_cikkszam ;

-- bom_line feltöltése anyagjegyzékből, kiválasztott félkész termékekre
WITH felkesz (regi_cikkszam, uj_cikkszam, uj_cikknev) AS (VALUES
('HFD001','SZF001','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF002','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF003','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF004','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF005','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF006','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF007','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF008','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF009','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF010','Hegesztett földelőérintkező /HFD010/'),
('HFD011','SZF011','Hegesztett földelőérintkező /HFD011/'),
('HFS001','SZF012','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF013','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF014','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF015','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF016','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF017','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF018','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF019','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF020','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF021','Cseh null érintkező /VE001/'),
('VE002','SZF022','Cseh fázis érintkező /VE002/'),
('MR001','SZF101','M-Rugózott /MR001/'),
('VE016','SZF201','Csavarozott érintkező cariva /VE016/'),
('UHF001','SZF301','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF302','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF303','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF304','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF305','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF306','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF307','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF308','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF309','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF310','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF311','Ultrahangos fedelek /UHF014/'),
('GYV001','SZF401','Szerelt gyv /GYV001/'),
('GYV004','SZF402','Szerelt gyv VL /GYV004/'),
('GYV005','SZF403','Szerelt gyv VL /GYV005/'),
('GYV006','SZF404','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF405','Szerelt gyv /GYV007/'),
('GYV009','SZF406','Szerelt gyv nélküli kazetta /GYV009/'),
('NAU001','SZF501','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF502','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF503','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF504','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF505','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF506','Nausicaa szerelt betét /NAU008/'),
('FLK001','SZF601','(3.200.0040-00) Érintkező berakás /FLK001/')
)
insert into legrand_bom_line (bom_id, cikk_id, beepules)
  select legrand_bom.id, mrp_bom_line.product_id, mrp_bom_line.product_qty from felkesz
    join legrand_cikk on legrand_cikk.cikkszam    = uj_cikkszam
    join legrand_bom  on legrand_bom.cikk_id      = legrand_cikk.id
    join mrp_bom      on mrp_bom.product_tmpl_id  = legrand_cikk.id
    join mrp_bom_line on mrp_bom_line.bom_id      = mrp_bom.id ;


-- lezer_tampon feltöltése raktar_lezer_tampon-ból
insert into legrand_lezer_tampon (muvelet, termekkod, termek_id, alkatresz, alkatresz_id, pozicio, rajz_felirat, muvelet_db, megjegyzes)
  select muvelet, termekkod, termek_id, alkatresz, alkatresz_id, pozicio, rajz_felirat, muvelet_db, megjegyzes from raktar_lezer_tampon order by id ;

-- hibakod feltöltése raktar_hibakod-ból
insert into legrand_hibakod (name, kod, nev, active)
  select name, kod, nev, active from raktar_hibakod order by kod ;

-- homogen feltöltése sajathomogen-ből
insert into legrand_homogen (homogen, homogennev, sajat_homogen)
  select homogen, nev, true from raktar_sajathomogen order by homogen ;


--########################################################################################################################################################  Egyebek  ###

-- mozgasfej feltöltése picking-ből
delete from legrand_mozgassor ;
delete from legrand_mozgasfej ;

insert into legrand_mozgasfej (id, state, mozgasnem, forrashely_id, celallomas_id, forrasdokumentum, megjegyzes)
  select id, state, mozgas, 1, 4, forrasdokumentum, megjegyzes from raktar_picking where mozgas = 'be' order by id;
insert into legrand_mozgasfej (id, state, mozgasnem, forrashely_id, celallomas_id, forrasdokumentum, megjegyzes)
  select id, state, mozgas, 4, 1, forrasdokumentum, megjegyzes from raktar_picking where mozgas in ('ki', 'vissza', 'selejt') order by id;
insert into legrand_mozgasfej (id, state, mozgasnem, forrashely_id, celallomas_id, forrasdokumentum, megjegyzes)
  select id, state, 'belso', 4, 5, forrasdokumentum, megjegyzes from raktar_picking where mozgas in ('belso', 'szall') order by id;
alter sequence legrand_mozgasfej_id_seq RESTART WITH 10000 ;

-- mozgassor feltöltése move-ból
alter sequence legrand_mozgassor_id_seq RESTART WITH 1 ;
insert into legrand_mozgassor (mozgasfej_id, mozgasfej_sorszam, cikk_id, mennyiseg, megjegyzes)
  select raktar_picking_id, raktar_picking_id, product_id, product_uom_qty, megjegyzes from raktar_move order by id;


-- Szállított félkész termékek összegyűjtése

\o out.txt
select referencia, sum(mennyiseg) from (
  select p.name_template as referencia, m.product_uom_qty as mennyiseg from raktar_move as m join product_product as p on m.product_id = p.id
    where active and (
      name_template like 'referencia%' or name_template like 'FLK%' or name_template like 'GYV%' or name_template like 'HF%' or
      name_template like 'MR%' or name_template like 'NAU%' or name_template like 'UHF%' or name_template like 'VE%'
      )
    ) as szall
group by referencia
order by referencia
;
\q


-- virtual table
select * from ( values ('egy','ketto'), ('3','4') ) as t (colname1, colname2);

WITH temp (k,v) AS (VALUES (0,-9999), (1, 100)) SELECT * FROM temp;


#########################################################################################

delete from legrand_anyaghiany_log ;

INSERT INTO legrand_anyaghiany_log (create_date, datum, cikk_id, szefo_keszlet, mterv_igeny, gyartas_igeny, mterv_gyartas_elter, gyartas_elter)
  SELECT now(), now(), cikk_id, szefo_keszlet, mterv_igeny, gyartas_igeny, mterv_gyartas_elter, gyartas_elter
  FROM legrand_anyaghiany
  WHERE mterv_gyartas_elter < 0
  ORDER BY cikk_id
;


delete from legrand_gyartasi_lap_log ;

INSERT INTO legrand_gyartasi_lap_log (datum, create_uid, create_date, write_uid, write_date, gyartasi_lap_id, state, gyartasi_hely_id, rendelesszam, termekkod, hatarido,
                                      hatralek_db, rendelt_ora, teljesitett_ora, hatralek_ora, szamlazott_ora, szamlazhato_ora, termekcsoport, leallas_ok, aktivitas, leallas_felelos)
  SELECT now(), create_uid, create_date, write_uid, write_date, id, state, gyartasi_hely_id, rendelesszam, termekkod, hatarido,
    hatralek_db, rendelt_ora, teljesitett_ora, hatralek_ora, szamlazott_ora, szamlazhato_ora, termekcsoport, leallas_ok, aktivitas, leallas_felelos
  FROM legrand_gyartasi_lap
  WHERE state IN ('mterv', 'gyartas') AND active
  ORDER BY id
;

update legrand_gyartasi_lap set aktivitas = '' where aktivitas = 'mind' ;
update legrand_gyartasi_lap set aktivitas = 'folyamatban' where aktivitas = 'foly' ;
update legrand_gyartasi_lap set aktivitas = 'áll' where aktivitas = 'all' ;

update legrand_gyartasi_lap_log set aktivitas = '' where aktivitas = 'mind' ;
update legrand_gyartasi_lap_log set aktivitas = 'folyamatban' where aktivitas = 'foly' ;
update legrand_gyartasi_lap_log set aktivitas = 'áll' where aktivitas = 'all' ;


WITH
anyag AS (
  SELECT state, cikk_id, SUM(hatralek) AS hatralek FROM legrand_anyagszukseglet GROUP BY state, cikk_id
),
igeny AS (
  SELECT keszlet.cikk_id, keszlet.szefo_keszlet,
    CASE WHEN gyartas.state IS NULL THEN 0.0 ELSE gyartas.hatralek END AS gyartas_igeny,
    CASE WHEN mterv.state   IS NULL THEN 0.0 ELSE mterv.hatralek   END AS mterv_igeny
  FROM legrand_vall_keszlet AS keszlet
  LEFT JOIN anyag AS gyartas ON gyartas.cikk_id = keszlet.cikk_id AND gyartas.state = 'gyartas'
  LEFT JOIN anyag AS mterv ON mterv.cikk_id = keszlet.cikk_id AND mterv.state = 'mterv'
),
elter AS (
  SELECT cikk_id, szefo_keszlet, gyartas_igeny, mterv_igeny, szefo_keszlet - gyartas_igeny AS gyartas_elter , szefo_keszlet - gyartas_igeny - mterv_igeny AS mterv_gyartas_elter FROM igeny
)
--        SELECT row_number() over() AS id, elter.* FROM elter WHERE mterv_gyartas_elter < 0 AND gyartas_igeny + mterv_igeny > 0
SELECT row_number() over() AS id, elter.* FROM elter WHERE gyartas_igeny + mterv_igeny > 0
;

WITH
eszkoz as ( select max(id) as max_id, eszkoz_id from leltar_eszkozatvetel where regi_hasznalo_id is null group by eszkoz_id having count(*) > 1 ),
eszkoz_elozok as ( select atvet.id as prev_id, eszkoz.* from leltar_eszkozatvetel as atvet, eszkoz where atvet.eszkoz_id = eszkoz.eszkoz_id and atvet.id < eszkoz.max_id ),
atvet_rel as (select eszkoz_id, max_id, max(prev_id) as prev_id from eszkoz_elozok group by eszkoz_id, max_id),
update_rel as (select atvet_rel.*, atvet.uj_hasznalo_id as prev_hasznalo_id from atvet_rel join leltar_eszkozatvetel as atvet on atvet_rel.prev_id = atvet.id)
update leltar_eszkozatvetel set regi_hasznalo_id = prev_hasznalo_id from update_rel where id = max_id
;

select * from update_rel
order by max_id desc
limit 10
;
