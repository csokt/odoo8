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
    cikkdict[record[field]] = 1
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
        cikk = Cikk.create({'cikkszam': termekkod, 'cikknev': fej['megnevezes'], 'alkatresz_e': False})
#      bom  = Bom.search([('cikk_id', '=', cikk.id), ('alkatresz_e', '=', True)], limit=1)
#      if not len(bom):
#        bom = Bom.create({'cikk_id': cikk.id, 'verzio': 'alkatrész', 'gylap_default_e': False})
#        BomLine.create({'bom_id': bom.id, 'cikk_id': cikk.id, 'beepules': 1.0})
      for alk in gylap['darabjegyzek']:
        cikkszam = alk['cikkszam']
        if cikkszam == 'referencia': continue
        alk_cikk = Cikk.search([('cikkszam', 'ilike', cikkszam)], limit=1)
        if not len(alk_cikk):
          alk_cikk = Cikk.create({'cikkszam': cikkszam, 'cikknev': alk['megnevezes'], 'alkatresz_e': True, 'bekerulesi_ar': alk['bekerulesi_ar']})
#        bom  = Bom.search([('cikk_id', '=', alk_cikk.id), ('alkatresz_e', '=', True)], limit=1)
#        if not len(bom):
#          bom = Bom.create({'cikk_id': alk_cikk.id, 'verzio': 'alkatrész', 'gylap_default_e': False})
#          BomLine.create({'bom_id': bom.id, 'cikk_id': alk_cikk.id, 'beepules': 1.0})

      # muvelet feltöltés #####################################################
      if not javitas_e:
        muv_ids = Muvelet.search([('cikk_id', '=', cikk.id)])
        if not len(muv_ids):
          for muv in gylap['muveleti_utasitas']:
            if muv['muveleti_szam'] == 'msz': continue
            muv_row = {
              'cikk_id'         : cikk.id,
              'muveletszam'     : muv['muveleti_szam'],
              'muveletnev'      : muv['megnevezes'],
              'fajlagos_db'     : 1,
              'normaora'        : muv['ossz_ido'] / fej['rendelt_db'],
              'beall_ido'       : muv['beall_ido'],
            }
            Muvelet.create(muv_row)

      # Ha nincs anyagjegyzék, vagy javításra adták, akkor anyagjegyzéket készítünk
      bom  = Bom.search([('cikk_id', '=', cikk.id), ('gylap_default_e', '=', True)], limit=1)
      if not len(bom) or javitas_e:
        verzio = '['+fej['rendelesszam']+']' if javitas_e else 'késztermék'
        bom = Bom.create({'cikk_id': cikk.id, 'verzio': verzio, 'gylap_default_e': not javitas_e})
        for alk in gylap['darabjegyzek']:
          cikkszam = alk['cikkszam']
          if cikkszam != 'referencia':
            bom_cikk = Cikk.search([('cikkszam', 'ilike', cikkszam)], limit=1)
            beepules = alk['ossz_beepules']/fej['rendelt_db']
            BomLine.create({'bom_id': bom.id, 'cikk_id': bom_cikk.id, 'beepules': beepules})

      # gyartasi_lap létrehozása ##############################################
      gyartlap_row = {
#        'mongo_id'      : gylap['_id'],
#        'counter'       : gylap['counter'],
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
        'cikkek_uid'    : calc_cikkek_uid(gylap['darabjegyzek'], 'cikkszam'),
        'bom_id'        : bom.id,
        'javitas_e'     : javitas_e,
      }
      gyartlap = Gyartlap.create(gyartlap_row)
#      gyartlap_row['hatarido'] = str(hatarido)
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
            'gyartasi_lap_id' : gyartlap.id,
            'muveletszam'     : muv['muveleti_szam'],
            'muveletnev'      : muv['megnevezes'],
            'fajlagos_db'     : 1,
            'normaora'        : muv['ossz_ido'] / fej['rendelt_db'],
            'beall_ido'       : muv['beall_ido'],
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
#    for fej in self.env['legrand.mozgasfej'].search([('state','!=','konyvelt')]):
      if fej.state   == 'terv':     megjegyzes = 'A szállítólevelet véglegesíteni kell.'
      elif fej.state == 'szallit':  megjegyzes = 'A szállítólevél átvételét rögzíteni kell.'
      else:                         megjegyzes = 'A szállítólevél másodpéldányát be kell küldeni könyvelésre.'
      impex_row = {
        'sorszam'     : fej.id,
        'hely_id'     : fej.forrashely_id.id if fej.state == 'terv' else fej.celallomas_id.id,
        'megjegyzes'  : megjegyzes,
      }
      Impex.create(impex_row)
    return True
