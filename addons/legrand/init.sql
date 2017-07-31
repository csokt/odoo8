-- összes adat törlése
-- delete from datawh_files ;
-- alter sequence datawh_files_id_seq RESTART WITH 1 ;
-- delete from datawh_documents ;
-- alter sequence datawh_documents_id_seq RESTART WITH 1 ;

delete from legrand_mozgassor ;
delete from legrand_mozgasfej ;

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
('GYV001','SZF001','Szerelt gyv /GYV001/'),
('GYV004','SZF002','Szerelt gyv VL /GYV004/'),
('GYV005','SZF003','Szerelt gyv VL /GYV005/'),
('GYV006','SZF004','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF005','Szerelt gyv /GYV007/'),
('GYV009','SZF006','Szerelt gyv nélküli kazetta /GYV009/'),
('MR001','SZF007','M-Rugózott /MR001/'),
('NAU001','SZF008','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF009','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF010','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF011','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF012','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF013','Nausicaa szerelt betét /NAU008/'),
('UHF001','SZF014','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF015','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF016','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF017','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF018','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF019','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF020','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF021','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF022','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF023','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF024','Ultrahangos fedelek /UHF014/'),
('HFD001','SZF025','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF026','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF027','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF028','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF029','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF030','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF031','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF032','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF033','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF034','Hegesztett földelőérintkező /HFD010/'),
('HFS001','SZF035','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF036','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF037','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF038','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF039','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF040','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF041','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF042','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF043','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF044','Cseh null érintkező /VE001/'),
('VE002','SZF045','Cseh fázis érintkező /VE002/'),
('VE016','SZF046','Csavarozott érintkező cariva /VE016/'),
('FLK001','SZF047','(3.200.0040-00) Érintkező berakás /FLK001/')
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
('GYV001','SZF001','Szerelt gyv /GYV001/'),
('GYV004','SZF002','Szerelt gyv VL /GYV004/'),
('GYV005','SZF003','Szerelt gyv VL /GYV005/'),
('GYV006','SZF004','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF005','Szerelt gyv /GYV007/'),
('GYV009','SZF006','Szerelt gyv nélküli kazetta /GYV009/'),
('MR001','SZF007','M-Rugózott /MR001/'),
('NAU001','SZF008','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF009','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF010','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF011','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF012','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF013','Nausicaa szerelt betét /NAU008/'),
('UHF001','SZF014','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF015','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF016','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF017','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF018','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF019','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF020','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF021','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF022','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF023','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF024','Ultrahangos fedelek /UHF014/'),
('HFD001','SZF025','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF026','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF027','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF028','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF029','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF030','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF031','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF032','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF033','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF034','Hegesztett földelőérintkező /HFD010/'),
('HFS001','SZF035','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF036','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF037','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF038','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF039','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF040','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF041','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF042','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF043','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF044','Cseh null érintkező /VE001/'),
('VE002','SZF045','Cseh fázis érintkező /VE002/'),
('VE016','SZF046','Csavarozott érintkező cariva /VE016/'),
('FLK001','SZF047','(3.200.0040-00) Érintkező berakás /FLK001/')
)
insert into legrand_bom (name, cikk_id, verzio, gylap_default_e, beepul_e)
  select uj_cikkszam || ' félkésztermék', legrand_cikk.id, 'félkésztermék', false, true from felkesz
    join legrand_cikk on cikkszam = uj_cikkszam ;

-- bom_line feltöltése anyagjegyzékből, kiválasztott félkész termékekre
WITH felkesz (regi_cikkszam, uj_cikkszam, uj_cikknev) AS (VALUES
('GYV001','SZF001','Szerelt gyv /GYV001/'),
('GYV004','SZF002','Szerelt gyv VL /GYV004/'),
('GYV005','SZF003','Szerelt gyv VL /GYV005/'),
('GYV006','SZF004','Szerelt gyv Izrael /GYV006/'),
('GYV007','SZF005','Szerelt gyv /GYV007/'),
('GYV009','SZF006','Szerelt gyv nélküli kazetta /GYV009/'),
('MR001','SZF007','M-Rugózott /MR001/'),
('NAU001','SZF008','Nausicaa szerelt betét /NAU001/'),
('NAU002','SZF009','Nausicaa szerelt betét /NAU002/'),
('NAU003','SZF010','Nausicaa szerelt betét /NAU003/'),
('NAU006','SZF011','Nausicaa szerelt betét /NAU006/'),
('NAU007','SZF012','Nausicaa szerelt betét /NAU007/'),
('NAU008','SZF013','Nausicaa szerelt betét /NAU008/'),
('UHF001','SZF014','Ultrahangos fedelek /UHF001/'),
('UHF002','SZF015','Ultrahangos fedelek /UHF002/'),
('UHF004','SZF016','Ultrahangos fedelek /UHF004/'),
('UHF005','SZF017','Ultrahangos fedelek /UHF005/'),
('UHF006','SZF018','Ultrahangos fedelek /UHF006/'),
('UHF007','SZF019','Ultrahangos fedelek /UHF007/'),
('UHF008','SZF020','Ultrahangos fedelek /UHF008/'),
('UHF009','SZF021','Ultrahangos fedelek /UHF009/'),
('UHF010','SZF022','Ultrahangos fedelek /UHF010/'),
('UHF011','SZF023','Ultrahangos fedelek /UHF011/'),
('UHF014','SZF024','Ultrahangos fedelek /UHF014/'),
('HFD001','SZF025','Hegesztett földelőérintkező /HFD001/'),
('HFD002','SZF026','Hegesztett földelőérintkező /HFD002/'),
('HFD003','SZF027','Hegesztett földelőérintkező /HFD003/'),
('HFD004','SZF028','Hegesztett földelőérintkező /HFD004/'),
('HFD005','SZF029','Hegesztett földelőérintkező /HFD005/'),
('HFD006','SZF030','Hegesztett földelőérintkező /HFD006/'),
('HFD007','SZF031','Hegesztett földelőérintkező /HFD007/'),
('HFD008','SZF032','Hegesztett földelőérintkező /HFD008/'),
('HFD009','SZF033','Hegesztett földelőérintkező /HFD009/'),
('HFD010','SZF034','Hegesztett földelőérintkező /HFD010/'),
('HFS001','SZF035','Hegesztett fázisérintkező jobbos /HFS001/'),
('HFS002','SZF036','Hegesztett fázisérintkező balos /HFS002/'),
('HFS003','SZF037','Hegesztett fázisérintkező jobbos /HFS003/'),
('HFS004','SZF038','Hegesztett fázisérintkező balos /HFS004/'),
('HFS005','SZF039','Hegesztett fázisérintkező jobbos /HFS005/'),
('HFS006','SZF040','Hegesztett fázisérintkező balos /HFS006/'),
('HFS007','SZF041','Hegesztett fázisérintkező jobbos,balos /HFS007-HSF008/'),
('HFS013','SZF042','Hegesztett fázisérintkező jobbos /HFS013/'),
('HFS014','SZF043','Hegesztett fázisérintkező balos /HFS014/'),
('VE001','SZF044','Cseh null érintkező /VE001/'),
('VE002','SZF045','Cseh fázis érintkező /VE002/'),
('VE016','SZF046','Csavarozott érintkező cariva /VE016/'),
('FLK001','SZF047','(3.200.0040-00) Érintkező berakás /FLK001/')
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