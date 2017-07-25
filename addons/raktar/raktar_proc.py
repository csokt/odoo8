# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import datetime, hashlib, pymongo

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
#  raise exceptions.Warning(str(cikkek))
  return hashlib.md5(cikkek.encode()).hexdigest()

############################################################################################################################  Paraméter  ###
class RaktarParameter(models.Model):
  _inherit  = 'szefo.parameter'
  cikktorzs_last_id = fields.Integer(u'Cikktörzs utolsó feldolgozott hivatkozási szám')

  @api.model
  def process_raktar_scheduler_queue(self):
    for gylap in self.env['raktar.gyartasi_lap'].search([('count_befejezetlen', '>', 0)]):
      gylap._compute_count_befejezetlen()
    for cikk in self.env['product.product'].search([('cikkszam', '=', False)]):
      cikk.cikkszam = cikk.name_template.split(' ')[0]
    for selkov in self.env['raktar.selejtkovet'].search([('state', '=', 'zarhat'),
        ('picking_state', 'in', ('cancel', 'done')), ('picking2_state', 'in', ('cancel', 'done')), ('production_state', 'in', ('cancel', 'done'))]):
      selkov.state = 'kesz'

  @api.one
  def import_gyartasi_lap(self):
    Product   = self.env['product.product']
    Gyartlap  = self.env['raktar.gyartasi_lap']
    Dbjegyzek = self.env['raktar.darabjegyzek']
    Homogen   = self.env['raktar.homogen']
    SHomogen  = self.env['raktar.sajathomogen']
    GyMuvelet = self.env['raktar.gylap_muvelet']
    Log       = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Gyártási lap import', 'module': 'raktar'})

    ut_counter = Gyartlap.search([], limit=1, order='counter desc').counter
    if not ut_counter: ut_counter = 2181
##########################################################################################################################################
##    ut_counter -= 5                                                                                                             # KIVENNI!
##########################################################################################################################################

    client = pymongo.MongoClient('intraweb.szefo.local')
    db = client.gyartas
#    gyartasi_lapok = db.gyartasilapok.find(filter={'counter': {'$gt': ut_counter}}).sort('counter', pymongo.ASCENDING).limit(1)
    gyartasi_lapok = db.gyartasilapok.find(filter={'counter': {'$gt': ut_counter}}, sort=[('counter', pymongo.ASCENDING)]).limit(100)
    for gylap in gyartasi_lapok:
      fej = gylap['fej']
      tetelkod = fej['tetelkod']
      try:
        hatarido = datetime.datetime.strptime(fej['hatarido'], "%y/%m/%d").date()
      except:
        hatarido = False
      product = Product.search([('cikkszam', 'ilike', tetelkod)], limit=1)
      if not len(product):
        name = tetelkod+' | '+fej['megnevezes']
        product = Product.create({'name': name, 'type': 'product', 'sale_ok': True, 'cikkszam': tetelkod, 'termek': True, 'list_price': 0.0})
      gyartlap_row = {
        'mongo_id'      : gylap['_id'],
        'counter'       : gylap['counter'],
        'product_id'    : product.id,
        'rendelesszam'  : fej['gyartasi_rend'],
        'termekcsalad'  : fej['termek_csalad'],
        'termekkod'     : tetelkod,
        'rendelt_db'    : fej['rendelt_db'],
        'modositott_db' : fej['rendelt_db'],
        'kiadas_ideje'  : fej['kiadas'],
        'hatarido_str'  : fej['hatarido'],
        'hatarido'      : hatarido,
        'jegyzet'       : fej['jegyzet'],
        'cikkek_uid'    : calc_cikkek_uid(gylap['darabjegyzek'], 'referencia'),
      }
      gyartlap = Gyartlap.create(gyartlap_row)
#      gyartlap.write({'cikkek_uid': calc_cikkek_uid(gylap['darabjegyzek'], 'referencia')})
      for alk in gylap['darabjegyzek']:
        referencia = alk['referencia']
        product = Product.search([('cikkszam', 'ilike', referencia)], limit=1)
        if not len(product):
          name = referencia+' | '+alk['megnevezes']+' '+alk['megnevezes2']
          product = Product.create({'name': name, 'type': 'product', 'sale_ok': False, 'cikkszam': referencia, 'anyag': True, 'list_price': 0.0})
#          product = Product.create({'name': name, 'type': 'product', 'sale_ok': False, 'cikkszam': referencia, 'anyag': True, 'list_price': 0.0, 'standard_price': alk['pri']})
        ossz_beepules = alk['beep']
        if ossz_beepules < 0.00001: ossz_beepules = 0.00001
        if referencia != 'referencia':
          Dbjegyzek.create({'gyartasi_lap_id': gyartlap.id, 'product_id': product.id, 'cikkszam': referencia,
                            'ossz_beepules': ossz_beepules, 'bekerulesi_ar': alk['pri']})
      for hom in gylap['homogen_osszesen']:
        shom    = SHomogen.search([('homogen', '=', hom['homogen'])])
        sajat   = len(shom) > 0
        hom_id  = shom.id if sajat else False
        hom_row = {
          'gyartasi_lap_id' : gyartlap.id,
          'homogen'         : hom['homogen'],
          'ossz_ido'        : hom['ossz'],
          'beall_ido'       : hom['beall_ido'],
          'sajat'           : sajat,
          'homogen_id'      : hom_id,
        }
        Homogen.create(hom_row)
      for muv in gylap['muveleti_utasitas']:
        if muv['msz'] == 'msz': continue
        shom    = SHomogen.search([('homogen', '=', muv['homogen'])])
        hom_id  = shom.id if shom else False
        muv_row = {
          'gyartasi_lap_id' : gyartlap.id,
          'name'            : muv['msz'],
          'homogen'         : muv['homogen'],
          'megnevezes'      : muv['megnevezes2'],
          'ossz_ido'        : muv['ossz'],
          'beall_ido'       : muv['beall_ido'],
          'homogen_id'      : hom_id,
        }
        GyMuvelet.create(muv_row)
    return True

  @api.one
  def mozgas_veglegesites_kiv(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Mozgásterv végrehajtás', 'module': 'raktar', 'value': 'Kiválasztott'})
    self.mozgas_veglegesites(-1)

  @api.one
  def mozgas_veglegesites_depo(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Mozgásterv végrehajtás', 'module': 'raktar', 'value': 'Forráshely=Depó'})
    self.mozgas_veglegesites(0)

  @api.one
  def mozgas_veglegesites_1(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Mozgásterv végrehajtás', 'module': 'raktar', 'value': 'Mai napra tervezett'})
    self.mozgas_veglegesites(1)

  @api.one
  def mozgas_veglegesites_2(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Mozgásterv végrehajtás', 'module': 'raktar', 'value': 'Ma és holnap'})
    self.mozgas_veglegesites(2)

  @api.one
  def mozgas_veglegesites_ossz(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Mozgásterv végrehajtás', 'module': 'raktar', 'value': 'Összes'})
    for i in range(10):
      self.mozgas_veglegesites(i)

  # Először az elosztóból szállítom ki az összes anyagot dátumra való tekintet nélkül
  # Másodszor a mai nap éjfélig esedékes mozgásokat veszem fel. (akt.dátum+1nap 00:00)
  @api.one
  def mozgas_veglegesites(self, timespan):
    Mozgasterv= self.env['raktar.mozgasterv']
    Product   = self.env['product.product']
    Mozgnem   = self.env['raktar.mozgasnem']
    Picking   = self.env['stock.picking']
    PType     = self.env['stock.picking.type']
    Move      = self.env['stock.move']
    # A locations lista (location_src_id, location_dest_id) párokat tartalmaz, date_last a date_planned szűrője, date_ship a szállítás napja
    def create_picking_and_move(locations, date_last, date_ship):
      def create_picking(origin=False, move_type='direct'):
        picking_row = {
          'picking_type_id':  for_mnem.picking_type_id.id,
          'partner_id':       cel_mnem.partner_id.id,
          'origin':           origin,
          'move_type':        move_type,
        }
        return Picking.create(picking_row)

      def create_move(qty, origin=False):
        move_row = {
          'picking_id': picking.id,
          'origin': origin,
          'product_id': product.id,
          'name': product.name,
          'product_uom': product.uom_id.id,
          'product_uom_qty': qty,
#          'location_id': for_mnem.location_src_id.id,
#          'location_dest_id': cel_mnem.location_dest_id.id
          'location_id': for_mnem.location_id.id,
          'location_dest_id': cel_mnem.location_id.id
        }
        Move.create(move_row)

      for loc in locations:
        forrashely_id, celallomas_id = loc
        for_mnem = Mozgnem.search([('id', '=', forrashely_id)])
        cel_mnem = Mozgnem.search([('id', '=', celallomas_id)])
        picking = create_picking()
        if timespan < 0:
          self.env.cr.execute("""SELECT product_id, SUM(product_uom_qty) FROM raktar_mozgasterv
                                 WHERE picking_id IS NULL AND forrashely_id = %s AND celallomas_id = %s AND kivalaszt
                                 GROUP BY product_id""", (forrashely_id, celallomas_id))
        else:
          self.env.cr.execute("""SELECT product_id, SUM(product_uom_qty) FROM raktar_mozgasterv
                                 WHERE picking_id IS NULL AND forrashely_id = %s AND celallomas_id = %s AND date_planned < %s
                                 GROUP BY product_id""", (forrashely_id, celallomas_id, date_last))
        product_qty = self.env.cr.fetchall()
        for pq in product_qty:
          product_id, qty = pq
          product = Product.search([('id', '=', product_id)])
          create_move(qty)
        picking.min_date = date_ship
        if timespan < 0:
          mterv = Mozgasterv.search([('picking_id', '=', False), ('forrashely_id.id', '=', forrashely_id),
                                     ('celallomas_id.id', '=', celallomas_id), ('kivalaszt', '=', True)])
        else:
          mterv = Mozgasterv.search([('picking_id', '=', False), ('forrashely_id.id', '=', forrashely_id),
                                     ('celallomas_id.id', '=', celallomas_id), ('date_planned', '<', date_last)])
        mterv.write({'picking_id': picking.id, 'kivalaszt': False})
        picking.action_confirm()

    soha        = fields.Datetime.to_string(datetime.datetime.max)
    holnap      = fields.Datetime.to_string(datetime.date.today() + datetime.timedelta(days=2))
    date_plan   = fields.Datetime.to_string(datetime.date.today() + datetime.timedelta(days=timespan))
    depo_mnem   = Mozgnem.search([('azon', '=', 'szent_depo')])
    if timespan < 0:
      self.env.cr.execute("SELECT DISTINCT forrashely_id, celallomas_id FROM raktar_mozgasterv WHERE picking_id IS NULL AND kivalaszt")
      create_picking_and_move(self.env.cr.fetchall(), soha, holnap)

    if timespan >= 0:
      self.env.cr.execute("SELECT DISTINCT forrashely_id, celallomas_id FROM raktar_mozgasterv WHERE picking_id IS NULL AND forrashely_id = %s", [depo_mnem.id])
      create_picking_and_move(self.env.cr.fetchall(), soha, min(date_plan, holnap))

    if timespan > 0:
      self.env.cr.execute("SELECT DISTINCT forrashely_id, celallomas_id FROM raktar_mozgasterv WHERE picking_id IS NULL AND date_planned < %s", [date_plan])
      create_picking_and_move(self.env.cr.fetchall(), date_plan, date_plan)

    for gylap in self.env['raktar.gyartasi_lap'].search([('count_befejezetlen', '>', 0)]):
      gylap._compute_count_befejezetlen()
    return True

  @api.one
  def mozgas_gen_ki(self):
    legr_kisz = self.env['raktar.mozgasnem'].search([('azon', '=', 'legr_kisz')])
#    quants    = self.env['stock.quant'].search([('location_id', '=', legr_kisz.location_src_id.id)])
    quants    = self.env['stock.quant'].search([('location_id', '=', legr_kisz.location_id.id)])
    if not len(quants):
      raise exceptions.Warning(u'Nincs kiszállításra váró termék a depóban!')
    picking_row = {
      'mozgas'        : 'ki',
#      'forrashely_id' : legr_kisz.id,
#      'celallomas_id' : legr_kisz.id,
    }
    raktar_picking = self.env['raktar.picking'].create(picking_row)

    gyrdict = {}
    for quant in quants:
      for qh in quant.history_ids.filtered('origin'):
        if qh.origin[:3]=='GyR': gyrdict[qh.origin] = quant.product_id.id

    counter = 0
    for gyrend in sorted(gyrdict.keys()):
      production  = self.env['mrp.production'].search([('name', '=', gyrend)])
      gyartas     = self.env['raktar.gyartas'].search([('production_id', '=', production.id)], limit=1)
      gylap       = gyartas.gyartasi_lap_id
#      gylap_id    = gyartas.gyartasi_lap_id.id if len(gyartas) else False
      quants_filt = quants.filtered(lambda r: len(r.history_ids.filtered(lambda rr: rr.origin == gyrend))>0 )
      qty = sum(map(lambda r: r.qty, quants_filt))
      if gylap.teljesitett_db < gylap.vir_teljesitett_db + qty:
        qty = gylap.teljesitett_db - gylap.vir_teljesitett_db
      if qty > 0:
        counter += 1
        move_row = {
          'raktar_picking_id' : raktar_picking.id,
          'gyartasi_lap_sorsz': gylap.id,
#          'gyartasi_lap_id'   : gylap.id,
          'product_id'        : gyrdict[gyrend],
          'product_uom_qty'   : qty,
        }
        self.env['raktar.move'].create(move_row)
    if not counter:
      raise exceptions.Warning(u'A depóban lévő termékeket még nem szállították ki!')
    return True

  @api.one
  def alkatresz_foglalas(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Alkatrész foglalás', 'module': 'raktar'})

    obj_list = []
    for production in self.env['mrp.production'].search([('state','=','confirmed')]):
      obj_list.append({'func': production.action_assign,  'datum': production.date_planned})
    for picking in self.env['stock.picking'].search([('state', 'in', ('waiting', 'partially_available')), ('pack_operation_exist','!=',True)]):
      obj_list.append({'func': picking.rereserve_pick,    'datum': picking.min_date})
    for picking in self.env['stock.picking'].search([('state','=','confirmed')]):
      obj_list.append({'func': picking.action_assign,     'datum': picking.min_date})
    obj_list.sort(key=lambda o: o['datum'])
    for obj in obj_list:
      obj['func']()

    for gylap in self.env['raktar.gyartasi_lap'].search([('count_befejezetlen', '>', 0)]):
      gylap._compute_count_befejezetlen()
    return True

  @api.one
  def szla_mell_nulla(self):
    Gyartlap = self.env['raktar.gyartasi_lap']
    Log      = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Számlamelléklet alaphelyzetbe állítás', 'module': 'raktar'})

    for gylap in Gyartlap.search([('state','!=','kesz'),('szamlazhato_db','>',0)]):
      gylap.szamlazott_db += gylap.szamlazhato_db
      if not gylap.hatralek_db: gylap.state = 'kesz'

    for gylap in Gyartlap.search([('state','!=','kesz'),('hatralek_db','=',0)]):
      if gylap.modositott_db == gylap.szamlazott_db: gylap.state = 'kesz'
    return True

  @api.one
  def gen_cikkszam(self):
    for cikk in self.env['product.product'].search([('cikkszam', '=', False)]):
      cikk.cikkszam = cikk.name_template.split(' ')[0]
    return True

  @api.one
  def calc_impex(self):
    Gyartlap  = self.env['raktar.gyartasi_lap']
    Product   = self.env['product.product']
    SHomogen  = self.env['raktar.sajathomogen']
    Mozgasnem = self.env['raktar.mozgasnem']
    for impex in self.env['raktar.impex'].search([]):
      gyartlap = Gyartlap.search([('rendelesszam', '=', impex.rendelesszam)], limit=1)
      product  = Product.search([('cikkszam', 'ilike', impex.termekkod)], limit=1)
      shom     = SHomogen.search([('homogen', '=', impex.homogen)], limit=1)
      hely     = Mozgasnem.search([('azon',   '=', impex.hely)], limit=1)
      impex.write({'sorszam': gyartlap.id, 'gyartasi_lap_id': gyartlap.id, 'product_id': product.id, 'homogen_id': shom.id, 'hely_id': hely.id})
    return True

  @api.one
  def legrand_keszlet(self):
    user_id = self.env.user.id
    self.env.cr.execute("""UPDATE raktar_impex SET mennyiseg = 0""")
    self.env.cr.execute("""
      UPDATE raktar_impex AS imp SET mennyiseg = keszlet.mennyiseg FROM (
        SELECT product_id, sum(menny) AS mennyiseg FROM (
          SELECT impex.product_id, quant.qty AS menny FROM raktar_impex AS impex, stock_quant AS quant, stock_location AS location
          WHERE impex.create_uid = %s AND impex.product_id = quant.product_id AND quant.location_id = location.id AND location.usage = 'internal'
          UNION ALL
          SELECT impex.product_id, move.product_uom_qty AS menny FROM raktar_impex AS impex, stock_move AS move, mrp_production AS production, raktar_gyartas AS gyartas, raktar_gyartasi_lap AS gylap
          WHERE impex.create_uid = %s AND impex.product_id = move.product_id AND move.state = 'done' AND move.raw_material_production_id = production.id
            AND production.id = gyartas.production_id AND gyartas.gyartasi_lap_id = gylap.id AND gylap.state != 'kesz'
          UNION ALL
          SELECT impex.product_id, -move.product_uom_qty AS menny FROM raktar_impex AS impex, stock_move AS move, mrp_production AS production, raktar_gyartas AS gyartas, raktar_gyartasi_lap AS gylap
          WHERE impex.create_uid = %s AND impex.product_id = move.product_id AND move.state = 'done' AND move.production_id = production.id
            AND production.id = gyartas.production_id AND gyartas.gyartasi_lap_id = gylap.id AND gylap.state != 'kesz'
          UNION ALL
          SELECT impex.product_id, -cikk.ossz_beepules*gylap.teljesitett_db/gylap.rendelt_db AS menny FROM raktar_impex AS impex, raktar_gyartas_cikk AS cikk, raktar_gyartasi_lap AS gylap
          WHERE impex.create_uid = %s AND impex.product_id = cikk.product_id AND cikk.gyartasi_lap_id = gylap.id AND gylap.state != 'kesz' AND gylap.teljesitett_db > 0
          UNION ALL
          SELECT impex.product_id, gylap.teljesitett_db AS menny FROM raktar_impex AS impex, raktar_gyartasi_lap AS gylap
          WHERE impex.create_uid = %s AND impex.product_id = gylap.product_id AND gylap.state != 'kesz' AND gylap.teljesitett_db > 0
          ) AS prod_qty
        GROUP BY product_id
        ) AS keszlet
      WHERE imp.product_id = keszlet.product_id
      """, (user_id, user_id, user_id, user_id, user_id))
    return True

#  @api.one
#  def telj_db_napijelent(self):
#    Log = self.env['szefo.log']
#    Log.create({'loglevel': 'info', 'name': u'Teljesített db napijelentésből', 'module': 'raktar'})
#    self.calc_impex()
#    for impex in self.env['raktar.impex'].search([]):
#      if impex.gyartasi_lap_id.state == 'kesz' :
#        raise exceptions.Warning(u'A(z) ' + impex.gyartasi_lap_id.rendelesszam + u' számú rendelés már le van zárva!')
#      impex.gyartasi_lap_id.teljesitett_db += impex.db
#      if impex.gyartasi_lap_id.teljesitett_db > impex.gyartasi_lap_id.modositott_db:
#        raise exceptions.Warning(u'A(z) ' + impex.gyartasi_lap_id.rendelesszam + u' számú rendelés már túl lenne teljesítve!')
#    return True
#
#  @api.one
#  def telj_db_szlamell(self):
#    Log = self.env['szefo.log']
#    Log.create({'loglevel': 'info', 'name': u'Teljesített db számlamellékletből', 'module': 'raktar'})
#    self.calc_impex()
#    for impex in self.env['raktar.impex'].search([]):
#      if impex.gyartasi_lap_id.state == 'kesz' :
#        raise exceptions.Warning(u'A(z) ' + impex.gyartasi_lap_id.rendelesszam + u' számú rendelés már le van zárva!')
#      if impex.gyartasi_lap_id.teljesitett_db != impex.gyartasi_lap_id.szamlazott_db + impex.db:
#        impex.gyartasi_lap_id.teljesitett_db = impex.gyartasi_lap_id.szamlazott_db + impex.db
#    return True

  @api.one
  def anyagjegyzek_keres(self):
    from sets import Set
    Impex = self.env['raktar.impex']
    Impex.search([]).unlink()
    for gylap in self.env['raktar.gyartasi_lap'].search([('state', '=', 'uj'), ('muveletterv_id', '=', False)]):
      gylfields = Set(gylap.darabjegyzek_ids.mapped(lambda r: r.product_id.id))
      for bom in self.env['mrp.bom'].search([]):
        bomfields = Set(bom.bom_line_ids.mapped(lambda r: r.product_id.id))
        if gylfields.issuperset(bomfields):
          impex_row = {
            'sorszam'         : gylap.id,
            'gyartasi_lap_id' : gylap.id,
            'product_id'      : bom.product_tmpl_id.id,
            'megjegyzes'      : bom.name,
          }
          Impex.create(impex_row)

  @api.one
  def gylap_ellenorzes(self):
    Impex = self.env['raktar.impex']
    Impex.search([]).unlink()
    for gylap in self.env['raktar.gyartasi_lap'].search([('state', '!=', 'kesz')]):
      megjegyzes         = ''
      if gylap.count_gyartas_ids != gylap.count_befejezetlen and gylap.state == 'kimer': megjegyzes = 'Gyártás részben megtörtént, de az alkatrészek nincsenek kimérve.'
      if gylap.teljesitett_db != gylap.vir_teljesitett_db and gylap.count_befejezetlen == 0: megjegyzes = 'Teljesített darabszámok eltérnek.'
      if gylap.teljesitett_db > 0 and gylap.state == 'kimer': megjegyzes = 'Teljesítés történt, de az alkatrészek nincsenek kimérve.'
      if gylap.teljesitett_db > 0 and gylap.state in ('mterv', 'gyterv'): megjegyzes = 'Teljesítés történt, de a gyártás nincs elindítva.'
      if megjegyzes:
        impex_row = {
          'sorszam'       : gylap.id,
          'rendelesszam'  : gylap.rendelesszam,
          'termekkod'     : gylap.product_id.cikkszam,
          'db'            : gylap.teljesitett_db,
          'megjegyzes'    : megjegyzes,
        }
        Impex.create(impex_row)
    for gyartas in self.env['raktar.gyartas'].search([('production_state','not in',('done', 'cancel')), ('gyartasi_lap_id.state', '!=', 'kesz')]):
      rendelt_db         = gyartas.gyartasi_lap_id.rendelt_db
      modositott_db      = gyartas.gyartasi_lap_id.modositott_db
      teljesitett_db     = gyartas.gyartasi_lap_id.teljesitett_db
      vir_teljesitett_db = gyartas.gyartasi_lap_id.vir_teljesitett_db
      szamlazott_db      = gyartas.gyartasi_lap_id.szamlazott_db
      szamlazhato_db     = gyartas.gyartasi_lap_id.szamlazhato_db
      hatralek_db        = gyartas.gyartasi_lap_id.hatralek_db
      state              = gyartas.gyartasi_lap_id.state
      megjegyzes         = ''
      if teljesitett_db > 0 and gyartas.production_state != 'in_production': megjegyzes = 'Teljesítés történt, de a gyártás nem "Termelés elindítva" állapotú.'
      if modositott_db == teljesitett_db: megjegyzes = 'A rendelés teljesítve, de a gyártás nem "Kész" állapotú.'
      if megjegyzes:
        impex_row ={
          'sorszam'       : gyartas.gyartasi_lap_id.id,
          'rendelesszam'  : gyartas.gyartasi_lap_id.rendelesszam,
          'termekkod'     : gyartas.gyartasi_lap_id.product_id.cikkszam,
#          'hely'          : gyartas.gyartasi_hely_id.azon,
          'db'            : teljesitett_db,
          'hely_id'       : gyartas.gyartasi_hely_id.id,
          'production_id' : gyartas.production_id.id,
          'megjegyzes'    : megjegyzes,
        }
        Impex.create(impex_row)
    datum = fields.Datetime.to_string(datetime.datetime.combine(datetime.date.today(), datetime.time(0)) - datetime.timedelta(days=0))
    for picking in self.env['raktar.picking'].search([('mozgas','=','belso'), ('state','!=','konyvelt'), ('write_date','<',datum)]):
      if picking.state   == 'terv':     megjegyzes = 'A szállítólevelet véglegesíteni kell.'
      elif picking.state == 'szallit':  megjegyzes = 'A szállítólevél átvételét rögzíteni kell.'
      else:                             megjegyzes = 'A szállítólevél másodpéldányát be kell küldeni könyvelésre.'
      impex_row = {
        'sorszam'     : picking.id,
        'hely_id'     : picking.forrashely_id.id if picking.state == 'terv' else picking.celallomas_id.id,
        'megjegyzes'  : megjegyzes,
      }
      Impex.create(impex_row)
    return True

  @api.one
  def homogen_ellenorzes(self):
    Gyartas = self.env['raktar.gyartas']
    Impex   = self.env['raktar.impex']
    Impex.search([]).unlink()
    for gylap in self.env['raktar.gyartasi_lap'].search([('state', 'in', ('gyterv','kimer','gyartas','gykesz'))], order='id'):
      for hom in gylap.homogen_ids.filtered('sajat'):
        gyartas   = gylap.gyartas_ids.filtered(lambda r: r.homogen_id.id == hom.homogen_id.id)
        ossz_ido  = sum(map(lambda r: r.feloszt*r.ossz_ido, gyartas))
        beall_ido = sum(map(lambda r: r.feloszt*r.beall_ido, gyartas))
        megjegyzes= ''
        if abs(hom.ossz_ido - ossz_ido) > 0.005: megjegyzes = 'Összes idő eltér!'
        if abs(hom.beall_ido - beall_ido) > 0.005: megjegyzes += ' Beállítási idő eltér!'
        if megjegyzes:
          impex_row = {
            'sorszam'           : gylap.id,
            'rendelesszam'      : gylap.rendelesszam,
            'termekkod'         : gylap.product_id.cikkszam,
            'homogen'           : hom.homogen_id.homogen,
            'db'                : gylap.modositott_db,
            'ertek'             : hom.ossz_ido - ossz_ido,
            'megjegyzes'        : megjegyzes,
          }
          Impex.create(impex_row)
    for gylap in self.env['raktar.gyartasi_lap'].search([('state', 'in', ('uj','mterv')), ('muveletterv_id', '!=', False)], order='id'):
      for hom in gylap.homogen_ids.filtered('sajat'):
#        muvelet   = gylap.muveletterv_id.muvelet_ids.filtered(lambda r: r.homogen_id.id == hom.homogen_id.id)
#        ossz_ido  = sum(map(lambda r: r.ossz_ido, muvelet))
#        ossz_ido  = ossz_ido * gylap.rendelt_db / gylap.muveletterv_id.gyartasi_lap_id.rendelt_db if gylap.muveletterv_id.gyartasi_lap_id else 0.0
#        beall_ido = sum(map(lambda r: r.beall_ido, muvelet))
        muv_hom   = gylap.muveletterv_id.muvelet_homogen_ids.filtered(lambda r: r.homogen_id.id == hom.homogen_id.id)
        ossz_ido  = muv_hom.ossz_ido if muv_hom else 0.0
        ossz_ido  = ossz_ido * gylap.rendelt_db / gylap.muveletterv_id.gyartasi_lap_id.rendelt_db if gylap.muveletterv_id.gyartasi_lap_id else 0.0
        beall_ido = muv_hom.beall_ido if muv_hom else 0.0
        megjegyzes= ''
        if abs(hom.ossz_ido - ossz_ido) > 0.005: megjegyzes = 'Összes idő eltér!'
        if abs(hom.beall_ido - beall_ido) > 0.005: megjegyzes += ' Beállítási idő eltér!'
        if megjegyzes:
          impex_row = {
            'sorszam'           : gylap.id,
            'rendelesszam'      : gylap.rendelesszam,
            'termekkod'         : gylap.product_id.cikkszam,
            'homogen'           : hom.homogen_id.homogen,
            'db'                : gylap.modositott_db,
            'ertek'             : hom.ossz_ido - ossz_ido,
            'megjegyzes'        : megjegyzes,
          }
          Impex.create(impex_row)
    return True

  """
  @api.one
  def upgrade_v1(self):
    Mozgasnem   = self.env['raktar.mozgasnem']
    Muvelet     = self.env['raktar.muvelet']
    Gyartas     = self.env['raktar.gyartas']
    Mozgasterv  = self.env['raktar.mozgasterv']
    for muv in Muvelet.search([]):
      muv.gyartasi_hely_id  = Mozgasnem.search([('location_src_id',   '=', muv.location_id.id),        ('gyartas',         '=', True)], limit=1).id
    for gyart in Gyartas.search([]):
      gyart.gyartasi_hely_id= Mozgasnem.search([('location_src_id',   '=', gyart.location_id.id),      ('gyartas',         '=', True)], limit=1).id
    for mterv in Mozgasterv.search([]):
      mterv.forrashely_id   =  Mozgasnem.search([('location_src_id',  '=', mterv.location_id.id),      ('belso_szallitas', '=', True)], limit=1).id
      mterv.celallomas_id   =  Mozgasnem.search([('location_dest_id', '=', mterv.location_dest_id.id), ('belso_szallitas', '=', True)], limit=1).id
    return True

  @api.one
  def upgrade_v2(self):
    Mozgasterv  = self.env['raktar.mozgasterv']
    Gyartlap    = self.env['raktar.gyartasi_lap']
    for mterv in Mozgasterv.search([]):
      mterv.gyartasi_lap_id =  Gyartlap.search([('rendelesszam', '=', mterv.origin)], limit=1).id
    return True

  @api.one
  def upgrade_v3(self):
    for gylap in self.env['raktar.gyartasi_lap'].search([]):
      if False:
        pass
      elif gylap.gyartas_ids:
        if gylap.count_befejezetlen == 0:
          gylap.state = 'gykesz'
        elif gylap.count_fuggo_gyartas == 0:
          gylap.state = 'gyartas'
        else:
          gylap.state = 'gyterv'
      elif gylap.muveletterv_id:
        gylap.state = 'mterv'
    return True

  @api.one
  def upgrade_v4(self):
    Gyartlap  = self.env['raktar.gyartasi_lap']
    SHomogen  = self.env['raktar.sajathomogen']
    GyMuvelet = self.env['raktar.gylap_muvelet']

    client = pymongo.MongoClient('intraweb.szefo.local')
    db = client.gyartas
    gyartlap  = Gyartlap.search([('gylap_muvelet_ids', '=', False)], order='id')
    for gylap in gyartlap:
      for hom in gylap.homogen_ids:
        shom = SHomogen.search([('homogen', '=', hom.homogen)])
        hom.homogen_id = shom.id if shom else False

      gyartasi_lap = db.gyartasilapok.find_one({'_id': gylap.mongo_id})
      for muv in gyartasi_lap['muveleti_utasitas']:
        if muv['msz'] == 'msz': continue
        shom    = SHomogen.search([('homogen', '=', muv['homogen'])])
        hom_id  = shom.id if shom else False
        muv_row = {
          'gyartasi_lap_id' : gylap.id,
          'name'            : muv['msz'],
          'homogen'         : muv['homogen'],
          'megnevezes'      : muv['megnevezes2'],
          'ossz_ido'        : muv['ossz'],
          'beall_ido'       : muv['beall_ido'],
          'homogen_id'      : hom_id,
        }
        GyMuvelet.create(muv_row)
    return True

  @api.one
  def upgrade_v5(self):
    Muvelet = self.env['raktar.muvelet']
    for impex in self.env['raktar.impex'].search([('gyartasi_lap_id', '!=', False)]):
#      for gyart in self.env['raktar.gyartas'].search([('ossz_ido', '=', 0.0)]):
      for gyart in impex.gyartasi_lap_id.gyartas_ids:
        muv = Muvelet.search([('muveletterv_id', '=', gyart.muveletterv_id.id), ('product_id', '=', gyart.product_id.id), ('bom_id', '=', gyart.bom_id.id,)], limit=1)
        ossz_ido = muv.ossz_ido * gyart.gyartasi_lap_id.rendelt_db / muv.muveletterv_id.gyartasi_lap_id.rendelt_db if muv.muveletterv_id.gyartasi_lap_id else 0.0
        gyartas_row = {
          'homogen_id'      : muv.homogen_id.id,
          'db_per_ora'      : muv.db_per_ora,
          'ossz_ido'        : ossz_ido,
          'beall_ido'       : muv.beall_ido,
        }
        gyart.write(gyartas_row)
    return True
    """

#  @api.one
#  def import_cikk(self):
#    import pymssql
#    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='SzentesModulKeszlet')
#    cursor  = mssql_conn.cursor()
#    Product = self.env['product.product']
#    Log     = self.env['szefo.log']
#    Log.create({'loglevel': 'info', 'name': 'Cikk import', 'module': 'raktar'})
#
#    start_id = self.cikktorzs_last_id + 1
#    cursor.execute("SELECT TOP 1 hsz FROM SzentesModulKeszlet.dbo.cikktorzs ORDER BY hsz desc")
#    row = cursor.fetchone()
#    if row: self.cikktorzs_last_id = trim(row)[0]
#    stop_id = self.cikktorzs_last_id
#
#    cursor.execute("""SELECT ct1.cikktipus, ct1.cikkszam, ct1.megnevezes, ct2.hsz FROM SzentesModulKeszlet.dbo.cikktorzs AS ct1
#      LEFT JOIN SzentesModulKeszlet.dbo.cikktorzs AS ct2 ON (ct2.cikkszam = ct1.cikkszam AND ct2.cikktipus = 'TERM')
#      WHERE ct1.hsz BETWEEN %s AND %s ORDER BY ct1.hsz""" % (start_id, stop_id))
#    row = cursor.fetchone()
#    while row:
#      cikktipus, cikkszam, megnevezes, ct2_hsz = trim(row)
#      megnevezes = cikkszam+' | '+' '.join(megnevezes.split())
#      row = cursor.fetchone()
#      sale_ok, anyag, termek = False, False, False
#      if cikktipus == 'TERM':
#        sale_ok, termek = True, True
#      if cikktipus == 'CIKK':
#        if ct2_hsz: continue
#        anyag = True
#      Product.create({'name': megnevezes, 'type': 'product', 'sale_ok': sale_ok, 'cikkszam': cikkszam, 'anyag': anyag, 'termek': termek, 'list_price': 0.0})
#    return True

#  @api.one
#  def init_db(self):
#    self.env['raktar.homogen'].search([]).unlink()
#    self.env['raktar.gyartas_cikk'].search([]).unlink()
#    self.env['raktar.darabjegyzek'].search([]).unlink()
#    self.env['raktar.gyartasi_lap'].search([]).unlink()
#    return True
