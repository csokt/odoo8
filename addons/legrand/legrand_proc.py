# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import time, datetime, json, yaml, hashlib, pymongo
import paho.mqtt.publish as publish

def pub(env, message):
  if type(message) is dict:
    message['database'] = env.cr.dbname
    message['utc']      = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    message['user']     = env.user.name
    if 'name' in message:
      message['event']  = message.pop('name')
    # topic: /log/program/database
  elif type(message) is int:
    message = {'timestamp': time.time(), 'state': message}
  else:
    message = {'timestamp': time.time(), 'message': message}
  topic   = "log/vir/"+env.cr.dbname
  try:
    payload = json.dumps(message).encode('utf-8')
  except Exception, e:
#    payload = json.dumps(u'json.dumps exception').encode('utf-8')
    payload = json.dumps(str(type(message))).encode('utf-8')
  publish.single(topic, payload, hostname='mqtt.szefo.local')

def log(env, message):
  if 'loglevel' not in message: message['loglevel'] = 'info'
  message['module'] = 'raktar'
  env['szefo.log'].create(message)
#  pub(env, message)

def trim(list):
  ret = []
  for elem in list:
    if type(elem)==unicode or type(elem)==str: ret.append(elem.strip())
    else: ret.append(elem)
  return ret

def calc_cikkek_uid(recordset, field):
  cikkdict = {}
  for record in recordset:
    cikkdict[record[field].upper()] = 1
  cikkek = ' '.join(sorted(cikkdict.keys()))
  return hashlib.md5(cikkek.encode()).hexdigest()

############################################################################################################################  Paraméter  ###
class LegrandParameter(models.Model):
  _name  = 'legrand.parameter'

############################################################################################################################  Legrand scheduler  ###
  @api.model
  def process_legrand_scheduler_queue(self):
    for gylap in self.env['legrand.gyartasi_lap'].search([('state', '=', 'gyartas'), ('muveletek_elvegezve', '=', True)]):
      gylap.state = 'gykesz'

############################################################################################################################  Gyártási lap import  ###
  @api.one
  def gyartasi_lap_import(self):
#    raise exceptions.Warning(u'Nincs művelet!')
#    pub(self.env, {'event': u'Gyártási lapok import elkezdése'})

    Cikk      = self.env['legrand.cikk']
    Gyartlap  = self.env['legrand.gyartasi_lap']
    Dbjegyzek = self.env['legrand.gylap_dbjegyzek']
    GyMuvelet = self.env['legrand.gylap_legrand_muvelet']
    SzMuvelet = self.env['legrand.gylap_szefo_muvelet']
    Muvelet   = self.env['legrand.muvelet']
    GyHomogen = self.env['legrand.gylap_homogen']
    SzHomogen = self.env['legrand.homogen']
    Bom       = self.env['legrand.bom']
    BomLine   = self.env['legrand.bom_line']

    # gyartasi_lapok létrehozása ##############################################
    count, maxcount = 0, 60
    for doc in self.env['datawh.documents'].search([('doctype', '=', u'Gyártási lap'), ('reject', '=', False), ('imported', '=', False)]):
#    for doc in self.env['datawh.documents'].search([]):
      gylap = yaml.load(doc.document)

      # fej alapadatok ########################################################
      fej = gylap['fej'][0]
#      pub(self.env, {'event': u'Gyártási lap import', 'rendelesszam': fej['rendelesszam']})
      javitas_e = fej['rendelesszam'][0] in ('j','J')
      termekkod = fej['termekkod']
      try:
        hatarido = datetime.datetime.strptime(fej['hatarido_str'], "%y/%m/%d").date()
      except:
        hatarido = False

      # cikk, bom, bom_line feltöltés #########################################
      cikk = Cikk.search([('cikkszam', 'ilike', termekkod)], limit=1)
      if not len(cikk):
        cikk = Cikk.create({'cikkszam': termekkod, 'cikknev': fej['megnevezes'], 'kesztermek_e': True})
      for alk in gylap['darabjegyzek']:
        cikkszam = alk['cikkszam']
        if cikkszam == 'referencia': continue
        alk_cikk = Cikk.search([('cikkszam', 'ilike', cikkszam)], limit=1)
        if not len(alk_cikk):
          alk_cikk = Cikk.create({'cikkszam': cikkszam, 'cikknev': alk['megnevezes'], 'alkatresz_e': True, 'bekerulesi_ar': alk['bekerulesi_ar']})

      # muvelet feltöltés #####################################################
      if not javitas_e:
        muv_ids = Muvelet.search([('cikk_id', '=', cikk.id)])
        if not len(muv_ids):
          for muv in gylap['muveleti_utasitas']:
            if muv['muveleti_szam'] == 'msz': continue
            muv_row = {
              'cikk_id'           : cikk.id,
              'muveletszam'       : muv['muveleti_szam'],
              'muveletnev'        : muv['megnevezes'],
              'fajlagos_db'       : 1,
              'normaora'          : muv['ossz_ido'] / fej['rendelt_db'],
              'beall_ido'         : muv['beall_ido'],
              'legrand_normaora'  : muv['ossz_ido'] / fej['rendelt_db'],
              'legrand_beall_ido' : muv['beall_ido'],
            }
            Muvelet.create(muv_row)

      # Ha nincs anyagjegyzék, vagy javításra adták, akkor anyagjegyzéket készítünk
      gylap_cikkek_uid = calc_cikkek_uid(gylap['darabjegyzek'], 'cikkszam')
      bom  = Bom.search([('cikk_id', '=', cikk.id), ('cikkek_uid', '=', gylap_cikkek_uid)], limit=1)
      if not len(bom) or javitas_e:
        verzio = '['+fej['rendelesszam']+']' if javitas_e else 'késztermék'
#        bom = Bom.create({'cikk_id': cikk.id, 'verzio': verzio, 'gylap_default_e': not javitas_e})
        bom = Bom.create({'cikk_id': cikk.id, 'verzio': verzio})
        for alk in gylap['darabjegyzek']:
          cikkszam = alk['cikkszam']
          if cikkszam != 'referencia':
            bom_cikk = Cikk.search([('cikkszam', 'ilike', cikkszam)], limit=1)
            beepules = alk['ossz_beepules']/fej['rendelt_db']
            BomLine.create({'bom_id': bom.id, 'cikk_id': bom_cikk.id, 'beepules': beepules})

      # gyartasi_lap létrehozása ##############################################
      gyartlap_row = {
        'cikk_id'       : cikk.id,
        'rendelesszam'  : fej['rendelesszam'],
        'termekcsalad'  : fej['termekcsalad'],
        'termekkod'     : termekkod,
        'rendelt_db'    : fej['rendelt_db'],
        'modositott_db' : fej['rendelt_db'],
        'kiadas_ideje'  : fej['kiadas_ideje'],
        'hatarido_str'  : fej['hatarido_str'],
        'hatarido'      : hatarido,
        'jegyzet'       : fej['jegyzet'],
        'raklap'        : fej['raklap'],
        'raklap_min'    : fej['raklap_min'],
        'raklap_max'    : fej['raklap_max'],
        'rakat_tipus'   : fej['rakat_tipus'],
        'keu_szam'      : fej['keu_szam'],
        'raktar'        : fej['raktar'],
        'cikkek_uid'    : gylap_cikkek_uid,
        'bom_id'        : bom.id,
        'javitas_e'     : javitas_e,
      }
      gyartlap = Gyartlap.create(gyartlap_row)
#      pub(self.env, gyartlap_row)

      # gylap_dbjegyzek feltöltés ###############################################
      for alk in gylap['darabjegyzek']:
        cikkszam = alk['cikkszam']
        if cikkszam != 'referencia':
          alk_cikk = Cikk.search([('cikkszam', 'ilike', cikkszam)], limit=1)
          ossz_beepules = alk['ossz_beepules']
          Dbjegyzek.create({'gyartasi_lap_id': gyartlap.id, 'cikk_id': alk_cikk.id, 'ossz_beepules': ossz_beepules, 'bekerulesi_ar': alk['bekerulesi_ar']})

      # gylap_legrand_muvelet feltöltés #######################################
      for muv in gylap['muveleti_utasitas']:
        if muv['muveleti_szam'] == 'msz': continue
        szhom   = SzHomogen.search([('homogen', '=', muv['homogen'])])
        if not len(szhom):
          szhom = SzHomogen.create({'homogen': muv['homogen'], 'sajat_homogen': False})
        muv_row = {
          'gyartasi_lap_id' : gyartlap.id,
          'muveleti_szam'   : muv['muveleti_szam'],
          'megnevezes'      : muv['megnevezes'],
          'ossz_ido'        : muv['ossz_ido'],
          'beall_ido'       : muv['beall_ido'],
          'homogen_id'      : szhom.id,
        }
        GyMuvelet.create(muv_row)

      # gylap_homogen feltöltés ###############################################
      for hom in gylap['homogen']:
        szhom   = SzHomogen.search([('homogen', '=', hom['homogen'])])
        if not len(szhom):
          szhom = SzHomogen.create({'homogen': hom['homogen'], 'sajat_homogen': False})
        hom_row = {
          'gyartasi_lap_id' : gyartlap.id,
#          'homogen'         : hom['homogen'],
          'ossz_ido'        : hom['ossz_ido'],
          'beall_ido'       : hom['beall_ido'],
          'sajat'           : szhom.sajat_homogen,
          'homogen_id'      : szhom.id,
        }
        GyHomogen.create(hom_row)

      # gylap_szefo_muvelet feltöltés ###############################################
      if not javitas_e:
        for muv in Muvelet.search([('cikk_id', '=', gyartlap.cikk_id.id)]):
          muv_row = muv.read()[0]
          muv_row['gyartasi_lap_id'] = gyartlap.id
          SzMuvelet.create(muv_row)
      else:
        for muv in gylap['muveleti_utasitas']:
          if muv['muveleti_szam'] == 'msz': continue
          muv_row = {
            'gyartasi_lap_id'   : gyartlap.id,
            'muveletszam'       : muv['muveleti_szam'],
            'muveletnev'        : muv['megnevezes'],
            'fajlagos_db'       : 1,
            'normaora'          : muv['ossz_ido'] / fej['rendelt_db'],
            'beall_ido'         : muv['beall_ido'],
            'legrand_normaora'  : muv['ossz_ido'] / fej['rendelt_db'],
            'legrand_beall_ido' : muv['beall_ido'],
          }
          SzMuvelet.create(muv_row)
      doc.imported = True
      count += 1
      if count == maxcount:
        log(self.env, {'loglevel': 'info', 'module': 'legrand', 'name': u'Gyártási lapok import kész'})
        return True
    log(self.env, {'loglevel': 'info', 'module': 'legrand', 'name': u'Gyártási lapok import kész'})
    return True

############################################################################################################################  Számlamelléklet nullázás  ###
  @api.one
  def szla_mell_nulla(self):
    Gyartlap = self.env['legrand.gyartasi_lap']

    for gylap in Gyartlap.search([('state','!=','kesz'),('szamlazhato_db','>',0)]):
      gylap.szamlazott_db += gylap.szamlazhato_db
      if not gylap.hatralek_db: gylap.state = 'kesz'

    for gylap in Gyartlap.search([('state','!=','kesz'),('hatralek_db','=',0)]):
      if gylap.modositott_db == gylap.szamlazott_db: gylap.state = 'kesz'
    log(self.env, {'loglevel': 'info', 'name': u'Számlamelléklet alaphelyzetbe állítás', 'module': 'legrand'})
    return True

############################################################################################################################  Impex id keres  ###
  @api.one
  def calc_impex(self):
    for impex in self.env['legrand.impex'].search([]):
      gylap = self.env['legrand.gyartasi_lap'].search([('rendelesszam', '=', impex.rendelesszam)], limit=1)
      cikk  = self.env['legrand.cikk'].search([('cikkszam', 'ilike', impex.cikkszam)], limit=1)
      hom   = self.env['legrand.homogen'].search([('homogen', '=', impex.homogen)], limit=1)
      impex.write({'sorszam': gylap.id, 'gyartasi_lap_id': gylap.id, 'cikk_id': cikk.id, 'homogen_id': hom.id})
    return True

############################################################################################################################  Gyártási lap ellenőrzés  ###
  @api.one
  def gylap_ellenorzes(self):
    Impex = self.env['legrand.impex']
    Impex.search([]).unlink()

    for gylap in self.env['legrand.gyartasi_lap'].search([('state', '!=', 'kesz')]):
      megjegyzes = ''
      if gylap.teljesitett_db > 0 and gylap.state in ('mterv', 'uj'): megjegyzes = 'Teljesítés történt, a gyártást el kell elindítani.'
      if megjegyzes:
        impex_row = {
          'sorszam'       : gylap.id,
          'rendelesszam'  : gylap.rendelesszam,
          'termekkod'     : gylap.cikk_id.cikkszam,
          'db'            : gylap.teljesitett_db,
          'megjegyzes'    : megjegyzes,
        }
        Impex.create(impex_row)

    datum = fields.Datetime.to_string(datetime.datetime.combine(datetime.date.today(), datetime.time(0)) - datetime.timedelta(days=0))
    for fej in self.env['legrand.mozgasfej'].search([('mozgasnem','=','belso'), ('state','!=','konyvelt'), ('write_date','<',datum)]):
      if fej.state   == 'terv':
        hely_id    = fej.forrashely_id.id
        megjegyzes = 'A szállítólevelet véglegesíteni kell.'
      elif fej.state == 'szallit':
        hely_id    = fej.celallomas_id.id
        megjegyzes = 'A szállítólevél átvételét rögzíteni kell.'
      else:
        hely_id    = False
        megjegyzes = 'A szállítólevél nincs könyvelve.'
      impex_row = {
        'sorszam'     : fej.id,
        'hely_id'     : hely_id,
        'megjegyzes'  : megjegyzes,
      }
      Impex.create(impex_row)

    for cikk in self.env['legrand.vall_keszlet'].search([('szefo_keszlet', '<', 0.0)], order='szefo_keszlet'):
      impex_row = {
        'cikk_id'     : cikk.cikk_id.id,
        'mennyiseg'   : cikk.szefo_keszlet,
        'megjegyzes'  : 'Vállalati készlet negatív',
      }
      Impex.create(impex_row)

    return True

############################################################################################################################  Impex - Üzem készlet  ###
  @api.one
  def impex_uzem_keszlet(self):
    Impex  = self.env['legrand.impex']
    hely_id = Impex.search([], limit=1).hely_id.id
    if not hely_id:
     raise exceptions.Warning(u'Az impex első sorában a Hely id nincs kitöltve!')
    Impex.search([]).write({'hely_id': hely_id, 'ertek': 0.0, 'megjegyzes': ''})
    self.env.cr.execute("""
      WITH uzemi AS
      ( SELECT keszlet.cikk_id, keszlet.raktaron AS keszlet FROM legrand_impex AS impex JOIN legrand_keszlet AS keszlet ON impex.cikk_id = keszlet.cikk_id AND impex.hely_id = keszlet.hely_id )
      UPDATE legrand_impex AS impex SET ertek = uzemi.keszlet FROM uzemi WHERE impex.cikk_id = uzemi.cikk_id
      """)
    self.env.cr.execute("""UPDATE legrand_impex SET megjegyzes = 'hiány' WHERE mennyiseg > ertek""")
    return True

############################################################################################################################  Anyagjegyzék ellenőrzése  ###
  @api.one
  def anyagj_ellenorzes(self):
    Impex = self.env['legrand.impex']
    Impex.search([]).unlink()

    self.env.cr.execute("""
      WITH list AS (
      SELECT DISTINCT cikk.id AS termek_id, line.cikk_id AS anyag_id, round(beepules, 3) AS beepules FROM legrand_bom_line AS line
      JOIN legrand_bom AS head on line.bom_id = head.id
      JOIN legrand_cikk AS cikk on head.cikk_id = cikk.id
      ),
      ossz AS (
      SELECT termek_id, anyag_id, count(*) AS count FROM list
      GROUP BY termek_id, anyag_id
      HAVING count(*) > 1
      )
      SELECT termek.cikkszam AS termek, anyag.cikkszam AS anyag, anyag.cikknev AS anyagnev, ossz.count FROM ossz
      JOIN legrand_cikk AS termek on ossz.termek_id = termek.id
      JOIN legrand_cikk AS anyag on ossz.anyag_id = anyag.id
      ORDER BY termek, anyag
      """)
    rows = self.env.cr.fetchall()
    Impex.create({ 'megjegyzes': 'Referencia|Cikkszám|Cikknév|Számosság' })
    for row in rows:
      Impex.create({ 'megjegyzes': "%s|%s|%s|%s" % tuple(row) })
    return True
