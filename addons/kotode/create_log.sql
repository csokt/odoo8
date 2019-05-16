------------------------------------
-- mqtt,kotogep,status logok törlése
------------------------------------
-- delete from kotode_mqtt_log ;
-- alter sequence kotode_mqtt_log_id_seq RESTART WITH 1 ;

delete from kotode_kotogep_log ;
alter sequence kotode_kotogep_log_id_seq RESTART WITH 1 ;

delete from kotode_status_log ;
alter sequence kotode_status_log_id_seq RESTART WITH 1 ;

---------------------------
-- kotode_kotogep_log írása
---------------------------
WITH
last_id AS (
  SELECT COALESCE(MAX(mqtt_log_id), 0) AS lastid FROM kotode_kotogep_log
),
log1 AS (
  SELECT id, create_date AS datum, extract(hour FROM write_date) AS ora, split_part(topic, '/', 2) AS gepazonosito, split_part(topic, '/', 3) AS source, split_part(topic, '/', 4) AS sensor, payload
  FROM kotode_mqtt_log JOIN last_id ON lastid < id
),
log AS (
  SELECT log1.*, gep.id AS kotogep_id, gep.name AS gepnev, gep.uzem,
  CASE WHEN ora < 6 THEN '3/2'
       WHEN ora < 14 THEN '1'
       WHEN ora < 22 THEN '2'
  ELSE '3/1'
  END AS muszak,
  CASE source
    WHEN 'status' THEN
      CASE payload
        WHEN 'offline' THEN 'ki'
      END
    WHEN 'sensor' THEN
    CASE sensor
      WHEN 'green' THEN
        CASE payload
          WHEN '1.0' THEN 'termel'
          WHEN '0.5' THEN 'all'
        END
      WHEN 'yellow' THEN
        CASE payload
          WHEN '1.0' THEN 'all'
        END
      WHEN 'red' THEN
        CASE payload
          WHEN '1.0' THEN 'hiba'
          WHEN '0.5' THEN 'hiba'
        END
    END
  END AS jelzes
  FROM log1
  JOIN kotode_kotogep AS gep ON gep.azonosito = log1.gepazonosito
)
INSERT INTO kotode_kotogep_log (jelzes, datum, uzem, kotogep_id, gepazonosito, gep, muszak, mqtt_log_id)
SELECT jelzes, datum, uzem, kotogep_id, gepazonosito, gepnev, muszak, id FROM log WHERE jelzes IS NOT NULL order by id
;

WITH
ido AS (
  SELECT t1.id, extract('epoch' from t2.datum - t1.datum) AS sec FROM kotode_kotogep_log AS t1
  JOIN kotode_kotogep_log AS t2 ON t2.id = t1.id + 1
  WHERE t1.idotartam IS NULL
)
UPDATE kotode_kotogep_log AS log SET idotartam = ido.sec, idotartam_perc = ido.sec / 60,  idotartam_ora = ido.sec / 3600
FROM ido WHERE ido.id = log.id
;

--------------------------
-- kotode_status_log írása
--------------------------
WITH
last_id AS (
  SELECT COALESCE(MAX(mqtt_log_id), 0) AS lastid FROM kotode_status_log
),
log1 AS (
  SELECT id, create_date AS datum, extract(hour FROM write_date) AS ora, split_part(topic, '/', 2) AS gepazonosito, split_part(topic, '/', 3) AS source, split_part(topic, '/', 4) AS sensor, payload
  FROM kotode_mqtt_log JOIN last_id ON lastid < id
),
log AS (
  SELECT log1.*, gep.name AS gepnev, gep.uzem,
  CASE WHEN ora < 6 THEN '3/2'
       WHEN ora < 14 THEN '1'
       WHEN ora < 22 THEN '2'
  ELSE '3/1'
  END AS muszak,
  CASE source
    WHEN 'status' THEN payload
  END AS jelzes
  FROM log1
  JOIN kotode_kotogep AS gep ON gep.azonosito = log1.gepazonosito
)
INSERT INTO kotode_status_log (jelzes, datum, uzem, gepazonosito, gep, muszak, mqtt_log_id)
SELECT jelzes, datum, uzem, gepazonosito, gepnev, muszak, id FROM log WHERE jelzes IS NOT NULL order by id
;

WITH
ido AS (
  SELECT t1.id, extract('epoch' from t2.datum - t1.datum) AS sec FROM kotode_status_log AS t1
  JOIN kotode_status_log AS t2 ON t2.id = t1.id + 1
  WHERE t1.idotartam IS NULL
)
UPDATE kotode_status_log AS log SET idotartam = ido.sec, idotartam_perc = ido.sec / 60,  idotartam_ora = ido.sec / 3600
FROM ido WHERE ido.id = log.id
;
