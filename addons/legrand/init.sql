-- összes adat törlése
delete from datawh_files ;
alter sequence datawh_files_id_seq RESTART WITH 1 ;
delete from datawh_documents ;
alter sequence datawh_documents_id_seq RESTART WITH 1 ;

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
--   (select bekerulesi_ar from raktar_darabjegyzek where product_product.id=product_id order by id desc limit 1), true from product_product
   (select bekerulesi_ar from raktar_darabjegyzek where product_product.id=product_id limit 1), true from product_product
--  where active and name_template not like 'referencia%' and name_template not like 'FLK%' and name_template not like 'GYV%' and name_template not like 'HF%'
--               and name_template not like 'MR%' and name_template not like 'NAU%' and name_template not like 'UHF%' and name_template not like 'VE%'
  order by id ;
ALTER SEQUENCE legrand_cikk_id_seq RESTART WITH 3000 ;


-- -- bom feltöltése legrand_cikk-ből
-- insert into legrand_bom (id, name, cikk_id, verzio, alkatresz_e)
-- --  select cikkszam || ' alkatrész', id, 'alkatrész' from legrand_cikk where alkatresz_e order by id ;
--   select id, cikkszam || ' alkatrész', id, 'alkatrész', true from legrand_cikk order by id ;
-- ALTER SEQUENCE legrand_bom_id_seq RESTART WITH 3000 ;
--
-- -- bom_line feltöltése bom-ból
-- insert into legrand_bom_line (bom_id, cikk_id, beepules)
--   select id, cikk_id, 1.0 from legrand_bom order by id ;



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


-- lezer_tampon feltöltése raktar_lezer_tampon-ból
insert into legrand_lezer_tampon (muvelet, termekkod, termek_id, alkatresz, alkatresz_id, pozicio, rajz_felirat, muvelet_db, megjegyzes)
  select muvelet, termekkod, termek_id, alkatresz, alkatresz_id, pozicio, rajz_felirat, muvelet_db, megjegyzes from raktar_lezer_tampon order by id ;

-- hibakod feltöltése raktar_hibakod-ból
insert into legrand_hibakod (name, kod, nev, active)
  select name, kod, nev, active from raktar_hibakod order by kod ;

-- homogen feltöltése sajathomogen-ből
insert into legrand_homogen (homogen, homogennev, sajat_homogen)
  select homogen, nev, true from raktar_sajathomogen order by homogen ;




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
