# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import datetime, hashlib, pymongo
from raktar_proc import calc_cikkek_uid

class RaktarProduct(models.Model):
  _inherit  = 'product.product'
  cikkszam            = fields.Char(u'Cikkszám')
  anyag               = fields.Boolean(u'Anyag?',  default=False)
  termek              = fields.Boolean(u'Termék?', default=False)
  # virtual fields
  uzem_keszlet_ids    = fields.One2many('raktar.uzem_keszlet', 'product_id', u'Üzem készlet', readonly=True,
                        domain=[('hely_id.uzem_helyi_raktar','=',True)])
  uzem_move_ids       = fields.One2many('raktar.uzem_move',    'product_id', u'Üzem mozgás',  readonly=True)

############################################################################################################################  Gyártási lap  ###
class RaktarGyartasiLap(models.Model):
  _name               = 'raktar.gyartasi_lap'
  _order              = 'id'
  state               = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], u'Állapot', default='uj')
  name                = fields.Char(u'Rendelés', compute='_compute_name', store=True)
  mongo_id            = fields.Char(u'Mongodb id', readonly=True)
  counter             = fields.Integer(u'Counter', required=True, readonly=True)
  rendelesszam        = fields.Char(u'Rendelésszám', required=True, readonly=True)
  jegyzet             = fields.Char(u'Jegyzet', readonly=True)
  termekcsalad        = fields.Char(u'Termékcsalád', readonly=True)
  termekkod           = fields.Char(u'Termékkód', required=True, readonly=True)
  rendelt_db          = fields.Integer(u'Rendelt db', required=True, readonly=True)
  modositott_db       = fields.Integer(u'Módosított rendelés')
  kiadas_ideje        = fields.Char(u'Kiadás ideje', readonly=True)
  hatarido_str        = fields.Char(u'Határidő (eredeti)', required=True, readonly=True)
  hatarido            = fields.Date(u'Határidő')
  teljesitett_db      = fields.Integer(u'Teljesített db', default=0)
  vir_teljesitett_db  = fields.Integer(u'VIR teljesített db ', default=0)
  szamlazott_db       = fields.Integer(u'Számlázott db', default=0)
  szamlazhato_db      = fields.Integer(u'Számlázható db', compute='_compute_szamlazhato_db', store=True)
  hatralek_db         = fields.Integer(u'Hátralék db', compute='_compute_hatralek_db', store=True)
  eltol               = fields.Integer(u'Eltol (nap)', default=1)
  product_id          = fields.Many2one('product.product',  u'Termék', required=True, readonly=True)
  cikkek_uid          = fields.Char(u'Összes cikk uid', readonly=True)
  muveletterv_id      = fields.Many2one('raktar.muveletterv',  u'Műveletterv', domain="[('product_id','=',product_id)]")
  picking_id          = fields.Many2one('stock.picking',  u'Anyag beszállítás', readonly=True)
  gyartasi_hely_ids   = fields.Many2many('raktar.mozgasnem', string=u'Fő gyártási helyek', domain=[('gyartas', '=', True)])
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  rendelt_ora         = fields.Float(u'Rendelt óra', digits=(16, 2), compute='_compute_rendelt_ora')
  teljesitett_ora     = fields.Float(u'Teljesített óra', digits=(16, 2), compute='_compute_teljesitett_ora')
  check_cikkek_uid    = fields.Char(u'Ellenőrzés', compute='_compute_check_cikkek_uid')
  count_gyartas_ids   = fields.Integer(u'Gyártási műveletek', compute='_compute_count_gyartas_ids')
  count_fuggo_gyartas = fields.Integer(u'Függő gyártási műveletek', compute='_compute_count_fuggo_gyartas', store=True)
  count_befejezetlen  = fields.Integer(u'Befejezetlen gyártási műveletek', compute='_compute_count_befejezetlen', store=True)
  count_cikkhiany     = fields.Integer(u'Cikkhiány', compute='_compute_count_cikkhiany')
  gyartas_ids         = fields.One2many('raktar.gyartas',       'gyartasi_lap_id', u'Gyártás',                states={'kesz': [('readonly', True)]})
  gyartas_cikk_ids    = fields.One2many('raktar.gyartas_cikk',  'gyartasi_lap_id', u'Gyártás darabjegyzék',   readonly=True)
  darabjegyzek_ids    = fields.One2many('raktar.darabjegyzek',  'gyartasi_lap_id', u'Legrand darabjegyzék',   readonly=True)
  gylap_muvelet_ids   = fields.One2many('raktar.gylap_muvelet', 'gyartasi_lap_id', u'Műveleti utasítás',      readonly=True)
  homogen_ids         = fields.One2many('raktar.homogen',       'gyartasi_lap_id', u'Homogén',                states={'kesz': [('readonly', True)]})

  @api.one
  @api.depends('modositott_db', 'teljesitett_db')
  def _compute_hatralek_db(self):
    self.hatralek_db = self.modositott_db - self.teljesitett_db

  @api.one
  @api.depends('homogen_ids')
  def _compute_rendelt_ora(self):
    self.rendelt_ora = sum(map(lambda r: r.ossz_ido+r.beall_ido, self.homogen_ids.filtered('sajat')))

  @api.one
  @api.depends('rendelt_ora', 'teljesitett_db', 'rendelt_db')
  def _compute_teljesitett_ora(self):
    self.teljesitett_ora = self.rendelt_ora * self.teljesitett_db / self.rendelt_db

  @api.onchange('muveletterv_id')
  def onchange_muveletterv_id(self):
    if not self.muveletterv_id: self.state = 'uj'

  @api.one
  @api.depends('teljesitett_db', 'szamlazott_db')
  def _compute_szamlazhato_db(self):
    self.szamlazhato_db = self.teljesitett_db - self.szamlazott_db

  @api.multi
  def write(self, vals):
    super(RaktarGyartasiLap, self).write(vals)
    if self.state in ('uj', 'mterv'):
      self.calc_gyartas_anyag()
    return True

  @api.one
  @api.depends('rendelesszam', 'product_id')
  def _compute_name(self):
    self.name = self.rendelesszam+' -> '+self.product_id.name_template

  @api.one
  @api.depends('muveletterv_id')
  def _compute_check_cikkek_uid(self):
    if len(self.muveletterv_id):
      if self.cikkek_uid == self.muveletterv_id.cikkek_uid:
        self.check_cikkek_uid = 'OK'
      else:
#        self.check_cikkek_uid = u'A darabjegyzék és a műveletterv anyaglista eltér!'
        self.check_cikkek_uid = u'Eltér!'

  @api.one
  @api.depends('gyartas_ids')
  def _compute_count_gyartas_ids(self):
    self.count_gyartas_ids = len(self.gyartas_ids)

  @api.one
  @api.depends('gyartas_ids')
  def _compute_count_fuggo_gyartas(self):
    self.count_fuggo_gyartas = len(self.gyartas_ids.filtered(lambda r: not r.production_id))

  @api.one
  @api.depends('gyartas_ids')
  def _compute_count_befejezetlen(self):
    gyartasban = self.gyartas_ids.filtered(lambda r: r.production_id)
    if len(gyartasban):
      befejezetlen = len(gyartasban.filtered(lambda r: r.production_state not in ('done', 'cancel')))
    else:
      befejezetlen = -1
    if self.count_befejezetlen != befejezetlen:
      self.count_befejezetlen = befejezetlen
      if befejezetlen == 0: self.state = 'gykesz'

  @api.one
  @api.depends('gyartas_cikk_ids')
  def _compute_count_cikkhiany(self):
    self.count_cikkhiany = len(self.gyartas_cikk_ids.filtered(lambda r: r.ossz_beepules > r.elerheto))

#  @api.one
#  def set_state2javit(self):
#    Log = self.env['szefo.log']
#    Log.create({'loglevel': 'info', 'name': u'Állapot -> Javítás', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
#    self.state = 'javit'
#    return True

  @api.one
  def set_state2mterv(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Állapot -> Műveletterv', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    if not self.muveletterv_id.muvelet_homogen_ids:
      raise exceptions.Warning(u'A művelettervhez a homogének nincsenek kiszámolva!')
    self.state = 'mterv'
    return True

  @api.one
  def set_state2gyartas(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Állapot -> Gyártás', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'gyartas'
    return True

  @api.one
  def set_state2gykesz(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Állapot -> Gyártás kész', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'gykesz'
    return True

  @api.one
  def set_state2kesz(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Állapot -> Rendelés teljesítve', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'kesz'
    return True

  @api.one
  def create_muveletterv(self):
    if self.muveletterv_id:
      raise exceptions.Warning(u'Már létezik!')
    Bom         = self.env['mrp.bom']
    Bom_line    = self.env['mrp.bom.line']
    Muveletterv = self.env['raktar.muveletterv']
    Muvelet     = self.env['raktar.muvelet']
    Mozgnem     = self.env['raktar.mozgasnem']
    Log         = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Műveletterv készítés', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})

    bom_row = {
      'name': self.product_id.cikkszam+' [rsz: '+self.rendelesszam+']',
      'product_tmpl_id': self.product_id.product_tmpl_id.id
    }
    bom = Bom.create(bom_row)
    for anyag in self.darabjegyzek_ids:
      bom_line_row = {
        'product_id': anyag.product_id.id,
        'product_qty': max(anyag.beepules, 0.00001),
        'bom_id': bom.id
      }
      bom_line = Bom_line.create(bom_line_row)
    mterv_row = {
      'product_id': self.product_id.id,
      'valtozat'  : 'rsz: '+self.rendelesszam,
    }
    mterv = Muveletterv.create(mterv_row)
    mozgnem = Mozgnem.search([('azon', '=', 'szentes')], limit=1)
    muvelet_row = {
      'product_id': self.product_id.id,
      'muveletterv_id': mterv.id,
      'name': 'szerelés',
      'gyartasi_hely_id': mozgnem.id,
      'bom_id': bom.id,
    }
    muvelet = Muvelet.create(muvelet_row)
    mterv.calc_muvelet_cikkek_uid()
    self.muveletterv_id = mterv.id
#    self.state = 'mterv'
    return True

  @api.one
  def copy_muvelet(self):
    Gyartas = self.env['raktar.gyartas']
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Gyártási terv generálás', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    if len(self.gyartas_ids):
      raise exceptions.Warning(u'Már létezik!')
    for muv in self.muveletterv_id.muvelet_ids:
      ossz_ido = muv.ossz_ido * self.rendelt_db / self.muveletterv_id.gyartasi_lap_id.rendelt_db if self.muveletterv_id.gyartasi_lap_id else 0.0
      tervezett_datum = datetime.datetime.combine(datetime.date.today(), datetime.time(12)) + datetime.timedelta(days=self.eltol+muv.szint-1)
      gyartas_row = {
        'muveletterv_id'  : muv.muveletterv_id.id,
        'szint'           : muv.szint,
        'name'            : muv.name,
        'product_id'      : muv.product_id.id,
        'beepules'        : muv.beepules,
        'bom_id'          : muv.bom_id.id,
        'homogen_id'      : muv.homogen_id.id,
        'db_per_ora'      : muv.db_per_ora,
        'ossz_ido'        : ossz_ido,
        'beall_ido'       : muv.beall_ido,
        'gyartasi_hely_id': muv.gyartasi_hely_id.id,
        'tervezett_datum' : tervezett_datum,
        'rendelt_db'      : self.rendelt_db,
        'gyartasi_lap_id' : self.id,
      }
      Gyartas.create(gyartas_row)
      self.state = 'gyterv'
    return True

  @api.one
  def calc_gyartas_anyag(self):
    self.gyartas_cikk_ids.unlink()
    if not self.muveletterv_id:
#      raise exceptions.Warning(u'Nincs műveletterv!')
      return True
    Cikkek   = self.env['raktar.gyartas_cikk']

    legr_alk = {}
    for alk in self.darabjegyzek_ids:
      legr_alk[alk.product_id.id] = alk.ossz_beepules

    for mcikk in self.muveletterv_id.muvelet_cikk_ids.filtered(lambda r: r.termek_menny > 0.0):
      cikk_row = {
        'gyartasi_lap_id': self.id,
        'product_id': mcikk.product_id.id,
        'beepules': mcikk.termek_menny,
        'ossz_beepules': mcikk.termek_menny*self.rendelt_db,
        'legr_ossz_beepules': legr_alk.setdefault(mcikk.product_id.id, 0)
      }
      Cikkek.create(cikk_row)
      del legr_alk[mcikk.product_id.id]

    for prod_id in legr_alk.keys():
      cikk_row = {
        'gyartasi_lap_id': self.id,
        'product_id': prod_id,
        'beepules': 0.0,
        'ossz_beepules': 0.0,
        'legr_ossz_beepules': legr_alk[prod_id]
      }
      Cikkek.create(cikk_row)

    return True

  @api.one
  def gyartas_inditas(self):
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Gyártási előírások végrehajtása', 'module': 'raktar', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    gyartasok = self.gyartas_ids.filtered(lambda r: not r.production_id)
    for gyartas in gyartasok:
      # A kiválasztott félkésztermék/termék gyártásra adása.
      if not gyartas.gyartasi_hely_id.location_id:
        raise exceptions.Warning(gyartas.bom_id.name + u': Gyártási hely nincs megadva!')
      if gyartas.production_id:
        raise exceptions.Warning(u'Már létezik!')
      prod_row = {
        'product_id'      : gyartas.product_id.id,
        'bom_id'          : gyartas.bom_id.id,
        'product_qty'     : gyartas.rendelt_db*gyartas.beepules,
        'product_uom'     : gyartas.product_id.uom_id.id,
        'date_planned'    : gyartas.tervezett_datum,
        'origin'          : gyartas.gyartasi_lap_id.rendelesszam+' ['+str(gyartas.gyartasi_lap_id.id)+']',
        'location_src_id' : gyartas.gyartasi_hely_id.location_id.id,
        'location_dest_id': gyartas.gyartasi_hely_id.location_id.id
        }
      production = gyartas.env['mrp.production'].create(prod_row)
      production.signal_workflow('button_confirm')
      gyartas.production_id = production.id
    self._compute_count_fuggo_gyartas()
    self._compute_count_befejezetlen()
    self.state = 'kimer'
    return True

  @api.one
  def export_impex(self):
    self.env['raktar.impex'].search([]).unlink()
    for alk in self.darabjegyzek_ids.filtered(lambda r: r.ossz_beepules >= 0.01):
      impex_row = {
        'sorszam'         : self.id,
        'rendelesszam'    : self.rendelesszam,
        'termekkod'       : alk.product_id.cikkszam,
        'homogen'         : '',
#        'db'              : round(alk.ossz_beepules),
        'mennyiseg'       : round(alk.ossz_beepules, 2),
        'ertek'           : 0.0,
        'gyartasi_lap_id' : self.id,
        'product_id'      : alk.product_id.id,
        'homogen_id'      : False,
      }
      self.env['raktar.impex'].create(impex_row)
    return True

############################################################################################################################  Darabjegyzék  ###
class RaktarDarabjegyzek(models.Model):
  _name               = 'raktar.darabjegyzek'
  _order              = 'cikkszam'
  _rec_name           = 'cikkszam'
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap', readonly=True)
  product_id          = fields.Many2one('product.product',  u'Alkatrész', index=True, readonly=True)
  cikkszam            = fields.Char(u'Cikkszám', readonly=True)
  ossz_beepules       = fields.Float(u'Össz beépülés', digits=(16, 5), readonly=True)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3), readonly=True)
  # calculated fields
  rendelt_db          = fields.Integer(u'Rendelt termék db', related='gyartasi_lap_id.rendelt_db', readonly=True)
  beepules            = fields.Float(u'Beépülés', digits=(16, 6), compute='_compute_beepules', store=True)
  ossz_bekerules      = fields.Float(u'Össz bekerülés', digits=(16, 5), compute='_compute_ossz_bekerules', store=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('rendelt_db', 'ossz_beepules')
  def _compute_beepules(self):
    self.beepules = self.ossz_beepules / self.rendelt_db

  @api.one
  @api.depends('rendelt_db', 'bekerulesi_ar')
  def _compute_ossz_bekerules(self):
    self.ossz_bekerules = self.bekerulesi_ar * self.ossz_beepules

############################################################################################################################  Gylap művelet  ###
class RaktarGylapMuvelet(models.Model):
  _name               = 'raktar.gylap_muvelet'
  _order              = 'id'
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap', readonly=True)
  name                = fields.Char(u'Műveleti szám', readonly=True)
  homogen             = fields.Char(u'Homogén', readonly=True)
  megnevezes          = fields.Char(u'Megnevezés', readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 8), readonly=True, states={'uj': [('readonly', False)]})
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), readonly=True)
  homogen_id          = fields.Many2one('raktar.sajathomogen',  u'Homogén')
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

############################################################################################################################  Homogén  ###
class RaktarHomogen(models.Model):
  _name               = 'raktar.homogen'
  _order              = 'id'
  name                = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap', readonly=True)
  termekcsalad        = fields.Char(u'Termékcsalád', related='gyartasi_lap_id.termekcsalad', readonly=True, store=True)
  homogen             = fields.Char(u'Homogén', readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 5), readonly=True, states={'uj': [('readonly', False)]})
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 3), readonly=True)
  korrekcios_ido      = fields.Float(u'Korrekciós idő', digits=(16, 3))
  potido              = fields.Float(u'Pótidő', digits=(16, 3), readonly=True)
  sajat               = fields.Boolean(u'Saját homogén?', default=True, readonly=True)
  homogen_id          = fields.Many2one('raktar.sajathomogen',  u'sHomogén', readonly=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra', digits=(16, 5), compute='_compute_teljesitett_ora', store=True)
  szamlazhato_ora     = fields.Float(u'Számlázható óra', digits=(16, 5), compute='_compute_szamlazhato_ora', store=True)
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
#  gyartasi_lap_state  = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
#                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
#                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
  gyartasi_lap_sorsz  = fields.Integer(u'Sorszám', compute='_compute_gyartasi_lap_sorsz')
  rendelesszam        = fields.Char(u'Rendelésszám', related='gyartasi_lap_id.rendelesszam', readonly=True)
  termekkod           = fields.Char(u'Tételkód', related='gyartasi_lap_id.termekkod', readonly=True)
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True)
  szamlazhato_db      = fields.Integer(u'Számlázható', related='gyartasi_lap_id.szamlazhato_db', readonly=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('gyartasi_lap_id', 'homogen')
  def _compute_name(self):
    self.name = str(self.gyartasi_lap_id.id)+'/'+self.homogen

  @api.one
  @api.depends('ossz_ido', 'beall_ido', 'korrekcios_ido', 'potido', 'gyartasi_lap_id.rendelt_db', 'gyartasi_lap_id.teljesitett_db')
  def _compute_teljesitett_ora(self):
    ossz_ido  = self.ossz_ido * self.gyartasi_lap_id.teljesitett_db / self.gyartasi_lap_id.rendelt_db
    beall_ido = self.beall_ido if self.gyartasi_lap_id.teljesitett_db > 0 else 0.0
    self.teljesitett_ora = ossz_ido + beall_ido + self.korrekcios_ido + self.potido

  @api.one
  @api.depends('ossz_ido', 'beall_ido', 'korrekcios_ido', 'gyartasi_lap_id.rendelt_db', 'gyartasi_lap_id.szamlazhato_db', 'gyartasi_lap_id.szamlazott_db')
  def _compute_szamlazhato_ora(self):
    ossz_ido   = self.ossz_ido * self.gyartasi_lap_id.szamlazhato_db / self.gyartasi_lap_id.rendelt_db
    beall_ido  = self.beall_ido if self.gyartasi_lap_id.szamlazott_db == 0 else 0.0
    self.szamlazhato_ora = ossz_ido + beall_ido + self.korrekcios_ido

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_gyartasi_lap_sorsz(self):
    self.gyartasi_lap_sorsz = self.gyartasi_lap_id.id

  @api.one
  def toggle_sajat(self):
    self.sajat = not self.sajat
    return True

############################################################################################################################  Mozgásnem  ###
class RaktarMozgasnem(models.Model):
  _name               = 'raktar.mozgasnem'
  _order              = 'sorrend'
  name                = fields.Char(u'Megnevezés')
  azon                = fields.Char(u'Belső azonosító')
  partner_id          = fields.Many2one('res.partner',  u'Partner')
  picking_type_id     = fields.Many2one('stock.picking.type',  u'Picking type')
  location_src_id     = fields.Many2one('stock.location', u'Forráshely')
  location_dest_id    = fields.Many2one('stock.location', u'Célállomás helye')
  belso_szallitas     = fields.Boolean(u'Belső szállítás?')
  gyartas             = fields.Boolean(u'Gyártás?')
  beszallitas         = fields.Boolean(u'Beszállítás?')
  kiszallitas         = fields.Boolean(u'Kiszállítás?')
  selejt              = fields.Boolean(u'Selejt raktár?')
  veszteseg           = fields.Boolean(u'Veszteség raktár?')
  # új mezők
  location_id         = fields.Many2one('stock.location', u'Raktár helye')
  mozgas_be_forr      = fields.Boolean(u'Anyag beszállítás forráshely?')
  mozgas_be_cel       = fields.Boolean(u'Anyag beszállítás célállomás?')
  mozgas_ki_forr      = fields.Boolean(u'Termék kiszállítás forráshely?')
  mozgas_ki_cel       = fields.Boolean(u'Termék kiszállítás célállomás?')
  mozgas_belso_forr   = fields.Boolean(u'Belső szállítás forráshely?')
  mozgas_belso_cel    = fields.Boolean(u'Belső szállítás célállomás?')
  mozgas_vissza_forr  = fields.Boolean(u'Alkatrész visszaszállítás forráshely?')
  mozgas_vissza_cel   = fields.Boolean(u'Alkatrész visszaszállítás célállomás?')
  mozgas_selejt_forr  = fields.Boolean(u'Selejt kiszállítás forráshely?')
  mozgas_selejt_cel   = fields.Boolean(u'Selejt kiszállítás célállomás?')
  mozgas_szall_forr   = fields.Boolean(u'Szállítólevél forráshely?')
  mozgas_szall_cel    = fields.Boolean(u'Szállítólevél célállomás?')
  uzem_raktar_valaszt = fields.Boolean(u'Üzem raktár választás?')
  uzem_helyi_raktar   = fields.Boolean(u'Üzem helyi raktár?')
  sorrend             = fields.Integer(u'Sorrend')
  active              = fields.Boolean(u'Aktív?', default=True)

############################################################################################################################  Műveletterv  ###
class RaktarMuveletterv(models.Model):
  _name               = 'raktar.muveletterv'
  _order              = 'id desc'
  name                = fields.Char(u'Megnevezés', compute='_compute_name', store=True)
  product_id          = fields.Many2one('product.product',  u'Termék')
  valtozat            = fields.Char(u'Változat')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap', domain="[('product_id','=',product_id)]")
  maxszint            = fields.Integer(u'Utolsó szint')
  cikkek_uid          = fields.Char(u'Összes cikk uid')
  rejt_muvelet_cikkek = fields.Boolean(u'Alkatrészlista elrejtése?', default=False)
  mod_gyartasi_lap_id = fields.Boolean(u'Gyártási lap módosult?', default=False)
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  rendelt_db          = fields.Integer(u'Rendelt db', related='gyartasi_lap_id.rendelt_db', readonly=True)
  muvelet_ids         = fields.One2many('raktar.muvelet', 'muveletterv_id', u'Tételek')
  muvelet_cikk_ids    = fields.One2many('raktar.muvelet_cikk', 'muveletterv_id', u'Alkatrészek')
  muvelet_homogen_ids = fields.One2many('raktar.muvelet_homogen', 'muveletterv_id', u'Homogének')

  @api.multi
  def write(self, vals):
    if 'mod_gyartasi_lap_id' in vals:
      mod_gyartasi_lap_id = True
      vals['mod_gyartasi_lap_id'] = False
    else:
      mod_gyartasi_lap_id = False
    super(RaktarMuveletterv, self).write(vals)
    if mod_gyartasi_lap_id:
      for tmuv in self.muvelet_ids:
        if tmuv.muv_szam_ids:
          tmuv.muv_szam_ids = [(5,)]
#    self.muvelet_ids.write({'db_per_ora': 0.0, 'ossz_ido': 0.0, 'beall_ido': 0.0})
#    self.muvelet_homogen_ids.unlink()
    return True

  @api.one
  @api.depends('product_id', 'valtozat')
  def _compute_name(self):
    if self.product_id and self.valtozat:
      self.name = self.product_id.name_template.split('|')[0]+' ['+self.valtozat+']'

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.mod_gyartasi_lap_id = True

  @api.one
  def toggle_muvelet_cikkek(self):
    self.rejt_muvelet_cikkek = not self.rejt_muvelet_cikkek
    return True

  @api.one
  def calc_muvelet_cikkek_uid(self):
    # Alkatrészlista és beépülés számítás
    if not self.muvelet_ids:
      raise exceptions.Warning(u'Nincs művelet!')
    Cikkek = self.env['raktar.muvelet_cikk']
    muvelet_ids = self.muvelet_ids.sorted(key=lambda r: -r.szint)
    self.maxszint = muvelet_ids[0].szint
    muvelet_ids.write({'beepules': 1.0})
    cikkdict = {}
    for muvelet in muvelet_ids:
      if muvelet.product_id.id not in cikkdict:
        if muvelet.szint != self.maxszint: raise exceptions.Warning(muvelet.product_id.name + u' cikk nem épül be sehova!')
      elif cikkdict[muvelet.product_id.id] != 0.0:
        muvelet.beepules = cikkdict[muvelet.product_id.id]
      cikkdict[muvelet.product_id.id] = cikkdict.setdefault(muvelet.product_id.id, 0) - muvelet.beepules
      bom_qty   = muvelet.bom_id.product_qty
      for bom_line in muvelet.bom_id.bom_line_ids:
        cikkdict[bom_line.product_id.id] = cikkdict.setdefault(bom_line.product_id.id, 0) + muvelet.beepules*bom_line.product_qty/bom_qty
    self.muvelet_cikk_ids.unlink()
    for product_id in cikkdict.keys():
      Cikkek.create({'muveletterv_id': self.id, 'product_id': product_id, 'termek_menny': cikkdict[product_id]})
    products =  Cikkek.search([('muveletterv_id', '=', self.id), ('termek_menny', '>', 0.0)]).mapped('product_id')
    self.cikkek_uid = calc_cikkek_uid(products, 'cikkszam')
    return True

  @api.one
  def calc_muvelet_homogen(self):
    if not self.gyartasi_lap_id:
      raise exceptions.Warning(u'Nincs gyártási lap megadva!')
    if not self.muvelet_ids:
      raise exceptions.Warning(u'Nincs művelet létrehozva!')
    for muvelet in self.muvelet_ids:
      if not muvelet.homogen_id:
        raise exceptions.Warning('A '+muvelet.name+' '+u'homogén nincs megadva!')
      if not muvelet.muv_szam_ids:
        for gymuv in self.gyartasi_lap_id.gylap_muvelet_ids.filtered(lambda r: r.homogen_id == muvelet.homogen_id):
          muvelet.muv_szam_ids = [(4,gymuv.id)]
    # Homogének számolás
    self.muvelet_ids.write({'db_per_ora': 0.0, 'ossz_ido': 0.0, 'beall_ido': 0.0})
    self.muvelet_homogen_ids.unlink()
    for gymuv in self.gyartasi_lap_id.gylap_muvelet_ids:
      tmuv = self.muvelet_ids.filtered(lambda r: len(r.muv_szam_ids.filtered(lambda rr: rr.id == gymuv.id))>0)
      beep = sum(map(lambda r: r.beepules, tmuv))
      for tm in tmuv:
        tm.ossz_ido  += gymuv.ossz_ido * tm.beepules / beep
        tm.beall_ido += gymuv.beall_ido / len(tmuv)
    for tmuv in self.muvelet_ids.filtered(lambda r: r.ossz_ido > 0.0):
      tmuv.db_per_ora = tmuv.beepules * self.rendelt_db / tmuv.ossz_ido

    homdict = {}
    for hom in self.gyartasi_lap_id.homogen_ids.filtered('homogen_id'):
      homdict[hom.homogen_id.id] = [0.0, 0.0, hom.ossz_ido, hom.beall_ido]
    for muvelet in self.muvelet_ids:
      homlist = homdict.setdefault(muvelet.homogen_id.id, [0.0, 0.0, 0.0, 0.0])
      homlist[0] += muvelet.ossz_ido
      homlist[1] += muvelet.beall_ido
      homdict[muvelet.homogen_id.id] = homlist
    for homogen_id in sorted(homdict.keys()):
      homlist = homdict[homogen_id]
      homogen_row = {
        'muveletterv_id'  : self.id,
        'homogen_id'      : homogen_id,
        'ossz_ido'        : homlist[0],
        'beall_ido'       : homlist[1],
        'ossz_ido_legr'   : homlist[2],
        'beall_ido_legr'  : homlist[3],
      }
      self.env['raktar.muvelet_homogen'].create(homogen_row)
    return True

############################################################################################################################  Művelet  ###
class RaktarMuvelet(models.Model):
  _name               = 'raktar.muvelet'
  _order              = 'muveletterv_id, szint, name'
  muveletterv_id      = fields.Many2one('raktar.muveletterv',  u'Műveletterv')
  szint               = fields.Integer(u'Szint', default=1)
  name                = fields.Char(u'Megnevezés', default='címkenyomtatás')
  product_id          = fields.Many2one('product.product',  u'Termék')
  beepules            = fields.Float(u'Beépülés', digits=(16, 5), default=0.0)
  bom_id              = fields.Many2one('mrp.bom',  u'Anyagjegyzék')
  homogen_id          = fields.Many2one('raktar.sajathomogen',  u'Homogén')
  edit_muv_szam_ids   = fields.Boolean(u' ', default=False)
  muv_szam_ids        = fields.Many2many('raktar.gylap_muvelet', string=u'Műv.számok')
  db_per_ora          = fields.Float(u'db/óra', digits=(16, 2), readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 8))   #A művelethez tartozó összes idő, felosztás előtt
  beall_ido           = fields.Float(u'Beáll. idő', digits=(16, 5))   #A művelethez tartozó beállítási idő, felosztás előtt
  gyartasi_hely_id    = fields.Many2one('raktar.mozgasnem', u'Gyártási hely', default=5, domain=[('gyartas', '=', True)])

  @api.model
  def create(self, vals):
    vals['edit_muv_szam_ids'] = False
    return super(RaktarMuvelet, self).create(vals)

  @api.multi
  def write(self, vals):
    vals['edit_muv_szam_ids'] = False
    super(RaktarMuvelet, self).write(vals)
    return True

  @api.onchange('product_id')
  def onchange_product_id(self):
    if self.product_id:
      Bom = self.env['mrp.bom']
      domain = [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)]
      self.bom_id = Bom.search(domain, limit=1, order='id').id
      return {'domain': {'bom_id': domain}}

  @api.onchange('homogen_id')
  def onchange_homogen_id(self):
    self.edit_muv_szam_ids = True
    self.muv_szam_ids = False

  @api.onchange('edit_muv_szam_ids','homogen_id')
  def onchange_edit_muv_szam_ids(self):
    if self.homogen_id:
      domain = [('gyartasi_lap_id', '=', self.muveletterv_id.gyartasi_lap_id.id),('homogen_id', '=', self.homogen_id.id)]
    else:
      domain = [('gyartasi_lap_id', '=', 0)]
    return {'domain': {'muv_szam_ids': domain}}

############################################################################################################################  Művelet cikk  ###
class RaktarMuveletCikk(models.Model):
  _name               = 'raktar.muvelet_cikk'
  _order              = 'product_id'
  _rec_name           = 'product_id'
  muveletterv_id      = fields.Many2one('raktar.muveletterv',  u'Műveletterv')
  product_id          = fields.Many2one('product.product',  u'Termék')
  termek_menny        = fields.Float(u'Mennyiség', digits=(16, 6))

############################################################################################################################  Művelet homogén  ###
class RaktarMuveletHomogen(models.Model):
  _name               = 'raktar.muvelet_homogen'
  _order              = 'id'
  muveletterv_id      = fields.Many2one('raktar.muveletterv',  u'Műveletterv')
  homogen_id          = fields.Many2one('raktar.sajathomogen',  u'Homogén')
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 5))
  ossz_ido_legr       = fields.Float(u'Legr.össz.idő', digits=(16, 5))
  beall_ido           = fields.Float(u'Beáll. idő', digits=(16, 3))
  beall_ido_legr      = fields.Float(u'Legr.beáll.idő', digits=(16, 3))
  # virtual fields
  ossz_ido_elter      = fields.Float(u'Összidő eltér', digits=(16, 5), compute='_compute_ossz_ido_elter')
  beall_ido_elter     = fields.Float(u'Beáll.idő eltér', digits=(16, 3), compute='_compute_beall_ido_elter')

  @api.one
  @api.depends('ossz_ido', 'ossz_ido_legr')
  def _compute_ossz_ido_elter(self):
    self.ossz_ido_elter = self.ossz_ido - self.ossz_ido_legr

  @api.one
  @api.depends('beall_ido', 'beall_ido_legr')
  def _compute_beall_ido_elter(self):
    self.beall_ido_elter = self.beall_ido - self.beall_ido_legr

############################################################################################################################  Gyártás  ###
class RaktarGyartas(models.Model):
  _name               = 'raktar.gyartas'
  _inherit            = 'raktar.muvelet'
  _order              = 'gyartasi_lap_id, tervezett_datum, gyartasi_hely_id, name, production_id desc'
  _rec_name           = 'bom_id'
  potido              = fields.Float(u'Pótidő', digits=(16, 3), default=0.0)
  tervezett_datum     = fields.Datetime(u'Tervezett dátum')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap')
  production_id       = fields.Many2one('mrp.production',  u'Gyártási rendelés')
  rendelt_db          = fields.Integer(u'Rendelt db')                                                                   #A gyártási helyhez leosztott rendelési darabszám
  feloszt             = fields.Float(u'Felosztás',      digits=(16, 5), compute='_compute_feloszt',     store=False)
  rendelt_ora         = fields.Float(u'Rendelt óra',    digits=(16, 5), compute='_compute_rendelt_ora', store=True) #A rendelt darabhoz kiszámolt óra
  gyartando_db        = fields.Integer(u'Gyártandó db',                  compute='_compute_gyartas',    store=True)
  gyartando_ora       = fields.Float(u'Gyártandó óra',   digits=(16, 5), compute='_compute_gyartas',    store=True)
  gyartott_db         = fields.Integer(u'Gyártott db',                   compute='_compute_gyartas',    store=True)
  gyartott_ora        = fields.Float(u'Gyártott óra',    digits=(16, 5), compute='_compute_gyartas',    store=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra',digits=(16, 5), compute='_compute_teljesites',  store=True) #A gyártási lapon teljesített darabszámhoz arányosított óra
  szamlazhato_ora     = fields.Float(u'Számlázható óra',digits=(16, 5), compute='_compute_teljesites',  store=True) #A gyártási lapon számlázható darabszámhoz arányosított óra
  elerheto_db         = fields.Integer(u'Elérhető db')                                                              #Nem használt
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
#  gyartasi_lap_state  = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
#                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
#                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
  production_state    = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'), ('ready', 'Ready to Produce'),
                                          ('in_production', 'Production Started'), ('done', 'Done')], u'Gy.rend állapot', related='production_id.state')
  gyartasi_lap_sorsz  = fields.Integer(u'Sorszám', compute='_compute_gyartasi_lap_sorsz')
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.multi
  def write(self, vals):
    super(RaktarGyartas, self).write(vals)
    if 'potido' in vals:
      homogen = self.env['raktar.homogen'].search([('gyartasi_lap_id', '=', self.gyartasi_lap_id.id), ('homogen_id', '=', self.homogen_id.id)], limit=1)
      homogen.write({'potido': vals['potido']})
    return True

  @api.one
  @api.depends('rendelt_db')
  def _compute_feloszt(self):
    self.feloszt = 1.0 * self.rendelt_db / self.gyartasi_lap_id.rendelt_db

  @api.one
  @api.depends('rendelt_db')
  def _compute_rendelt_ora(self):
    self.rendelt_ora = self.feloszt * (self.ossz_ido + self.beall_ido)

  @api.one
#  @api.depends('production_id.state', 'production_id.move_created_ids', 'production_id.move_created_ids2', 'rendelt_ora', 'rendelt_db')
  @api.depends('production_id.state', 'production_id.move_created_ids2')
  def _compute_gyartas(self):
    self.gyartando_db  = sum(map(lambda r: r.product_uom_qty, self.production_id.move_created_ids)) / self.beepules
    self.gyartando_ora = self.gyartando_db * self.rendelt_ora / self.rendelt_db
    self.gyartott_db   = sum(map(lambda r: r.product_uom_qty, self.production_id.move_created_ids2.filtered(lambda r: r.state == 'done'))) / self.beepules
    self.gyartott_ora  = self.gyartott_db * self.rendelt_ora / self.rendelt_db

  @api.one
  @api.depends('potido', 'gyartasi_lap_id.teljesitett_db', 'gyartasi_lap_id.szamlazott_db')
  def _compute_teljesites(self):
    egysegido = self.feloszt * self.ossz_ido / self.gyartasi_lap_id.rendelt_db
    beall_ido = self.feloszt * self.beall_ido if self.gyartasi_lap_id.szamlazott_db > 0 else 0.0
    self.teljesitett_ora = egysegido * self.gyartasi_lap_id.teljesitett_db + beall_ido + self.potido
    self.szamlazhato_ora = egysegido * self.gyartasi_lap_id.szamlazhato_db + beall_ido + self.potido

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_gyartasi_lap_sorsz(self):
    self.gyartasi_lap_sorsz = self.gyartasi_lap_id.id

  @api.one
  def dec_tervezett_datum(self):
    self.tervezett_datum = fields.Datetime.from_string(self.tervezett_datum) - datetime.timedelta(days=1)
    if self.tervezett_datum < fields.Datetime.now():
      raise exceptions.Warning(u'Nem lehet kisebb, mint az aktuális idő!')
    return True

  @api.one
  def inc_tervezett_datum(self):
    self.tervezett_datum = fields.Datetime.from_string(self.tervezett_datum) + datetime.timedelta(days=1)
    return True

  @api.multi
  def felosztas(self):
    self.ensure_one()
    self.rendelt_db  = self.rendelt_db / 2
    copy = self.copy()

#    return {'type': 'ir.actions.client', 'tag': 'reload' }
    return  {
      'type': 'ir.actions.act_window',
      'res_model':  self.gyartasi_lap_id._name,
      'res_id': self.gyartasi_lap_id.id,
      'view_type': 'form',
      'view_mode':  'form',
      'target': 'current',
    }

  @api.one
  def export_impex(self):
    self.env['raktar.impex'].search([]).unlink()
    for bom_line in self.bom_id.bom_line_ids:
      mennyiseg = self.rendelt_db*self.beepules*bom_line.product_qty/self.bom_id.product_qty
      impex_row = {
        'sorszam'         : self.gyartasi_lap_id.id,
        'rendelesszam'    : self.gyartasi_lap_id.rendelesszam,
        'termekkod'       : bom_line.product_id.cikkszam,
        'homogen'         : self.homogen_id.homogen,
        'hely'            : self.gyartasi_hely_id.azon,
#        'db'              : round(mennyiseg),
        'mennyiseg'       : round(mennyiseg, 2),
        'ertek'           : 0.0,
        'gyartasi_lap_id' : self.gyartasi_lap_id.id,
        'product_id'      : bom_line.product_id.id,
        'homogen_id'      : self.homogen_id.id,
        'hely_id'         : self.gyartasi_hely_id.id,
        'production_id'   : self.production_id.id,
      }
      if impex_row['mennyiseg'] >= 0.01: self.env['raktar.impex'].create(impex_row)
    return True

############################################################################################################################  Gyártás cikk  ###
class RaktarGyartasCikk(models.Model):
  _name               = 'raktar.gyartas_cikk'
  _order              = 'product_id'
  _rec_name           = 'product_id'
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap')
  product_id          = fields.Many2one('product.product',  u'Termék')
  beepules            = fields.Float(u'Beépülés', digits=(16, 6))
  ossz_beepules       = fields.Float(u'Össz beépülés', digits=(16, 5))
  legr_ossz_beepules  = fields.Float(u'Legrand beépülés', digits=(16, 5))
  # virtual fields
  elteres             = fields.Float(u'Eltérés', digits=(16, 5), compute='_compute_elteres')
#  depoban             = fields.Float(u'Depóban', digits=(16, 5), compute='_compute_depoban')
  elerheto            = fields.Float(u'Elérhető', digits=(16, 3), related='product_id.virtual_available')

  @api.one
  @api.depends('ossz_beepules', 'legr_ossz_beepules')
  def _compute_elteres(self):
    self.elteres = self.legr_ossz_beepules - self.ossz_beepules

#  @api.one
#  @api.depends('product_id')
#  def _compute_depoban(self):
#    depoban = 0
##    quants = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('location_id', '=', 19)])
##    for quant in quants: depoban += quant.qty
#    self.env.cr.execute("""SELECT SUM(qty) FROM stock_quant WHERE product_id = %s AND location_id = 19
#                           GROUP BY product_id""", [self.product_id.id])
#    qty_list = self.env.cr.fetchall()
#    if len(qty_list): depoban += qty_list[0][0]
##    mterv = self.env['raktar.mozgasterv'].search([('picking_id','=',False),('product_id', '=', self.product_id.id), ('forrashely_id', '=', 3)])
##    for mozg in mterv: depoban -= mozg.product_uom_qty
#    self.env.cr.execute("""SELECT SUM(product_uom_qty) FROM raktar_mozgasterv
#                           WHERE picking_id IS NULL AND forrashely_id = 3 AND product_id = %s
#                           GROUP BY product_id""", [self.product_id.id])
#    qty_list = self.env.cr.fetchall()
#    if len(qty_list): depoban -= qty_list[0][0]
#    self.depoban = depoban

############################################################################################################################  Mozgásterv  ###
class RaktarMozgasterv(models.Model):
  _name               = 'raktar.mozgasterv'
  _order              = 'date_planned, forrashely_id, celallomas_id, origin, product_id'
  origin              = fields.Char(u'Rendelésszám')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap')
  product_id          = fields.Many2one('product.product',  u'Termék', required=True)
  product_uom_qty     = fields.Float(u'Mennyiség', digits=(16, 5), required=True)
  forrashely_id       = fields.Many2one('raktar.mozgasnem', u'Forráshely', domain=[('belso_szallitas', '=', True)])
  celallomas_id       = fields.Many2one('raktar.mozgasnem', u'Célállomás helye', domain=[('belso_szallitas', '=', True)])
  date_planned        = fields.Datetime(u'Tervezett dátum')
  kivalaszt           = fields.Boolean(u'Kiválaszt?', default=False)
  picking_id          = fields.Many2one('stock.picking',  u'Belső szállítás')
  # virtual fields
  gyartasi_lap_sorsz  = fields.Integer(u'Sorszám', compute='_compute_gyartasi_lap_sorsz')

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_gyartasi_lap_sorsz(self):
    self.gyartasi_lap_sorsz = self.gyartasi_lap_id.id


  @api.one
  def kivalaszt_valt(self):
    self.kivalaszt = not self.kivalaszt
    return True

############################################################################################################################  Saját homogén  ###
class RaktarSajatHomogen(models.Model):
  _name               = 'raktar.sajathomogen'
  _order              = 'homogen'
  name                = fields.Char(u'Megnevezés', compute='_compute_name', store=True)
  homogen             = fields.Char(u'Homogén', required=True)
  nev                 = fields.Char(u'Név')
  active              = fields.Boolean(u'Aktív?', default=True)

#  @api.one
#  @api.depends('homogen', 'nev')
#  def _compute_name(self):
#    if self.homogen and self.nev:
#      self.name = self.homogen+' - '+self.nev

  @api.one
  @api.depends('homogen')
  def _compute_name(self):
    self.name = self.homogen

############################################################################################################################  Picking  ###
class RaktarPicking(models.Model):
  _name               = 'raktar.picking'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')], 'Állapot',
                        default='terv', readonly=True )
  mozgas              = fields.Selection([('be',u'Anyag beszállítás'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt kiszállítás'),('szall',u'Szállítólevél')],
                                          u'Mozgás', required=True, default=lambda self: self.env.context.get('mozgas', ''))
  forrashely_id       = fields.Many2one('raktar.mozgasnem', u'Forráshely')
  celallomas_id       = fields.Many2one('raktar.mozgasnem', u'Célállomás helye')
  forrasdokumentum    = fields.Char(u'Forrásdokumentum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  picking_id          = fields.Many2one('stock.picking',  u'Kiszedés', readonly=True)
  picking2_id         = fields.Many2one('stock.picking',  u'Kiszedés 2', readonly=True)
  # virtual fields
  picking_state       = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('waiting', 'Waiting Another Operation'), ('confirmed', 'Waiting Availability'),
                                          ('partially_available', 'Partially Available'), ('assigned', 'Ready to Transfer'), ('done', 'Transferred')],
                                          u'Kiszedés állapot', related='picking_id.state', readonly=True)
  forrashely_azon     = fields.Char(u'Forráshely azonosító', related='forrashely_id.azon', readonly=True)
  celallomas_azon     = fields.Char(u'Célállomás azonosító', related='celallomas_id.azon', readonly=True)
  raktar_move_ids     = fields.One2many('raktar.move', 'raktar_picking_id', u'Tételek')

  @api.model
  def create(self, vals):
    forrdict = {'be': 'legr_besz', 'ki': 'legr_kisz', 'vissza': 'legr_vissza', 'selejt': 'legr_selejt'}
    celdict  = {'be': 'legr_depo', 'ki': 'legr_vevo', 'vissza': 'legr_vevo',   'selejt': 'legr_vevo'}
    if vals['mozgas'] not in ('belso','szall'):
      forr_id = self.env['raktar.mozgasnem'].search([('azon', '=', forrdict[vals['mozgas']])]).id
      cel_id  = self.env['raktar.mozgasnem'].search([('azon', '=', celdict[vals['mozgas']])]).id
      vals['forrashely_id'], vals['celallomas_id'] = forr_id, cel_id
    return super(RaktarPicking, self).create(vals)

  @api.one
  def import_impex(self):
    for impex in self.env['raktar.impex'].search([]):
      move_row = {
        'raktar_picking_id' : self.id,
#        'gyartasi_lap_id'   : impex.gyartasi_lap_id.id,
        'gyartasi_lap_sorsz': impex.sorszam,
        'product_id'        : impex.product_id.id,
        'product_uom_qty'   : impex.mennyiseg,
        'hibakod_id'        : impex.hibakod_id.id,
        'megjegyzes'        : impex.megjegyzes,
      }
      self.env['raktar.move'].create(move_row)
    return True

  @api.one
  def export_impex(self):
    self.env['raktar.impex'].search([]).unlink()
    for move in self.raktar_move_ids:
      impex_row = {
        'sorszam'         : move.gyartasi_lap_id.id,
        'rendelesszam'    : move.gyartasi_lap_id.rendelesszam,
        'termekkod'       : move.product_id.cikkszam,
        'homogen'         : '',
#        'db'              : round(move.product_uom_qty),
        'mennyiseg'       : round(move.product_uom_qty, 2),
        'ertek'           : 0.0,
        'gyartasi_lap_id' : move.gyartasi_lap_id.id,
        'product_id'      : move.product_id.id,
        'homogen_id'      : False,
        'hibakod_id'      : move.hibakod_id.id,
        'megjegyzes'      : move.megjegyzes,
      }
      self.env['raktar.impex'].create(impex_row)
    return True

  @api.one
  def state2elter(self):
    self.state  = 'elter'
    return True

  @api.one
  def state2kesz(self):
    self.state  = 'kesz'
    return True

  @api.one
  def state2konyvelt(self):
    self.state  = 'konyvelt'
    return True

  @api.one
  def veglegesites(self):
    if self.picking_id: return True
    if self.mozgas == 'szall':
      self.state  = 'szallit'
    else:
      picking_id = self.mozgas_veglegesites(self.forrashely_id, self.celallomas_id)
      self.picking_id  = picking_id[0]
      self.state  = 'szallit' if self.mozgas == 'belso' else 'kesz'
    return True

  @api.one
  def selejt_kiszallitas(self):
    legr_selejt = self.env['raktar.mozgasnem'].search([('azon', '=', 'legr_selejt')])
#    legr_kisz   = self.env['raktar.mozgasnem'].search([('azon', '=', 'legr_kisz')])
    legr_vevo   = self.env['raktar.mozgasnem'].search([('azon', '=', 'legr_vevo')])
    picking_id  = self.mozgas_veglegesites(legr_selejt, legr_vevo)
    self.picking2_id  = picking_id[0]
    return True

  @api.one
  def mozgas_veglegesites(self, forrashely_id, celallomas_id):
    if not self.raktar_move_ids:
      raise exceptions.Warning(u'Nincs véglegesíthető mozgás!')
    if forrashely_id == celallomas_id and self.mozgas == 'belso':
      raise exceptions.Warning(u'A forrás és célállomás helye megegyezik!')

    Picking   = self.env['stock.picking']
    Move      = self.env['stock.move']
    Log       = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Szállítás véglegesítés', 'module': 'raktar', 'table': 'picking', 'value': forrashely_id.name+' -> '+celallomas_id.name, 'rowid': self.id})

    picking_row = {
      'picking_type_id' : forrashely_id.picking_type_id.id,
      'partner_id'      : celallomas_id.partner_id.id,
      'origin'          : self.forrasdokumentum,
      'move_type'       : 'direct',
    }
    picking = Picking.create(picking_row)

    for anyag in self.raktar_move_ids:
      origin = anyag.gyartasi_lap_id.rendelesszam+' ['+str(anyag.gyartasi_lap_id.id)+']' if anyag.gyartasi_lap_id else False
      move_row = {
        'picking_id'      : picking.id,
        'origin'          : origin,
        'product_id'      : anyag.product_id.id,
        'name'            : anyag.product_id.name,
        'product_uom'     : anyag.product_id.uom_id.id,
        'product_uom_qty' : anyag.product_uom_qty,
#        'location_id'     : forrashely_id.location_src_id.id,
#        'location_dest_id': celallomas_id.location_dest_id.id
        'location_id'     : forrashely_id.location_id.id,
        'location_dest_id': celallomas_id.location_id.id
      }
      Move.create(move_row)
      if self.mozgas == 'ki' and anyag.gyartasi_lap_id and anyag.gyartasi_lap_id.state != 'kesz':
        anyag.gyartasi_lap_id.teljesitett_db     += anyag.product_uom_qty
        anyag.gyartasi_lap_id.vir_teljesitett_db += anyag.product_uom_qty

    picking.action_confirm()
#    self.picking_id  = picking.id
#    return True
    return picking.id

############################################################################################################################  Move  ###
class RaktarMove(models.Model):
  _name               = 'raktar.move'
  _order              = 'id'
  _rec_name           = 'product_id'
  raktar_picking_id   = fields.Many2one('raktar.picking',  u'Belső szállítás')
  gyartasi_lap_sorsz  = fields.Integer(u'Sorszám')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap',
                        compute='_compute_gyartasi_lap_id', store=True,
                        readonly=True
                        )
  product_id          = fields.Many2one('product.product',  u'Termék', required=True)
  product_uom_qty     = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  hibakod_id          = fields.Many2one('raktar.hibakod', u'Hibakód')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  mozgas              = fields.Selection([('be',u'Anyag beszállítás'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt kiszállítás'),('szall',u'Szállítólevél')],
                                          u'Mozgás', related='raktar_picking_id.mozgas', readonly=True)
  picking_id          = fields.Integer(u'Picking id', compute='_compute_picking_id')
  forrashelyen        = fields.Float(u'Készlet', digits=(16, 2), compute='_compute_forrashelyen')
  modositott_db       = fields.Integer(u'Rendelt db', related='gyartasi_lap_id.modositott_db', readonly=True)


  @api.one
  @api.depends('gyartasi_lap_sorsz')
  def _compute_gyartasi_lap_id(self):
    self.gyartasi_lap_id = self.gyartasi_lap_sorsz

  @api.onchange('gyartasi_lap_sorsz')
  def onchange_gyartasi_lap_sorsz(self):
    self.product_id = False
    ids = self.gyartasi_lap_id.muveletterv_id.muvelet_cikk_ids.mapped('product_id.id')
    domain = [('id','in',ids)] if self.gyartasi_lap_sorsz else []
    return {'domain': {'product_id': domain}}

  @api.one
  @api.depends('raktar_picking_id')
  def _compute_picking_id(self):
    self.picking_id = self.raktar_picking_id.picking_id.id

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_gyartasi_lap_sorsz(self):
    self.gyartasi_lap_sorsz = self.gyartasi_lap_id.id

  @api.one
  @api.depends('product_id')
  def _compute_forrashelyen(self):
#    quants = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('location_id', '=', self.raktar_picking_id.forrashely_id.location_src_id.id)])
    quants = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('location_id', '=', self.raktar_picking_id.forrashely_id.location_id.id)])
    self.forrashelyen = sum(map(lambda r: r.qty, quants))

############################################################################################################################  Bont  ###
class RaktarBont(models.Model):
  _name               = 'raktar.bont'
  _order              = 'id desc'
  _rec_name           = 'sorszam'
  sorszam             = fields.Integer(u'Sorszám', required=True)
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap', compute='_compute_gyartasi_lap_id', store=True, readonly=True )
  gyartas_id          = fields.Many2one('raktar.gyartas',  u'Gyártás', required=True, domain="[('gyartasi_lap_id','=',sorszam)]")
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  picking_id          = fields.Many2one('stock.picking',  u'Kiszedés', readonly=True)
  picking2_id         = fields.Many2one('stock.picking',  u'Kiszedés 2', readonly=True)
  # virtual fields
  hely                = fields.Char(u'Üzem', related='gyartas_id.gyartasi_hely_id.name', readonly=True)
  product             = fields.Char(u'Félkész/termék', related='gyartas_id.bom_id.product_tmpl_id.name', readonly=True)

  @api.one
  @api.depends('sorszam')
  def _compute_gyartasi_lap_id(self):
    self.gyartasi_lap_id = self.sorszam

  @api.one
  def szetszerel(self):
    if self.picking_id: return True
    selejt    = self.env['raktar.mozgasnem'].search([('azon', '=', 'selejt')])
    termeles  = self.env['raktar.mozgasnem'].search([('azon', '=', 'termeles')])
    picking_row = {
      'picking_type_id' : selejt.picking_type_id.id,
      'origin'          : self.gyartas_id.production_id.name,
      'move_type'       : 'direct',
    }
    picking = self.env['stock.picking'].create(picking_row)
    move_row = {
      'picking_id'      : picking.id,
      'product_id'      : self.gyartas_id.product_id.id,
      'name'            : self.gyartas_id.product_id.name,
      'product_uom'     : self.gyartas_id.product_id.uom_id.id,
      'product_uom_qty' : self.mennyiseg,
      'location_id'     : self.gyartas_id.gyartasi_hely_id.location_id.id,
      'location_dest_id': termeles.location_id.id
    }
    self.env['stock.move'].create(move_row)
    picking.action_confirm()
    picking.force_assign()
    self.picking_id  = picking.id

    picking_row = {
      'picking_type_id' : selejt.picking_type_id.id,
      'origin'          : self.gyartas_id.production_id.name,
      'move_type'       : 'direct',
    }
    picking2 = self.env['stock.picking'].create(picking_row)
    for bom_line in self.gyartas_id.bom_id.bom_line_ids:
      qty = round(self.mennyiseg*bom_line.product_qty/self.gyartas_id.bom_id.product_qty, 5)
      move_row = {
        'picking_id'      : picking2.id,
        'product_id'      : bom_line.product_id.id,
        'name'            : bom_line.product_id.name,
        'product_uom'     : bom_line.product_id.uom_id.id,
        'product_uom_qty' : qty,
        'location_id'     : termeles.location_id.id,
        'location_dest_id': self.gyartas_id.gyartasi_hely_id.location_id.id
      }
      if qty > 0.0: self.env['stock.move'].create(move_row)
    picking2.action_confirm()
    self.picking2_id  = picking2.id
    return True

############################################################################################################################  Lézer, tampon  ###
class RaktarLezerTampon(models.Model):
  _name               = 'raktar.lezer_tampon'
  _order              = 'id'
  _rec_name           = 'termek_id'
  muvelet             = fields.Char(u'Művelet')
  termekkod           = fields.Char(u'Termékkód')
  termek_id           = fields.Many2one('product.product',  u'Termék')
  alkatresz           = fields.Char(u'Alkatrészkód')
  alkatresz_id        = fields.Many2one('product.product',  u'Alkatrész')
  pozicio             = fields.Char(u'Pozíció')
  rajz_felirat        = fields.Char(u'Rajz/Felirat')
  muvelet_db          = fields.Integer(u'Művelet db')
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  Impex  ###
class RaktarImpex(models.Model):
  _name               = 'raktar.impex'
  _order              = 'id'
  sorszam             = fields.Integer(u'Sorszám')
  rendelesszam        = fields.Char(u'Rendelésszám')
  termekkod           = fields.Char(u'Termékkód')
  homogen             = fields.Char(u'Homogén')
  hely                = fields.Char(u'Hely')
  db                  = fields.Integer(u'db')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 3))
  ertek               = fields.Float(u'Érték', digits=(16, 8))
  datum               = fields.Datetime(u'Dátum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap id')
  product_id          = fields.Many2one('product.product',  u'Termék id')
  homogen_id          = fields.Many2one('raktar.sajathomogen',  u'Homogén id')
  hely_id             = fields.Many2one('raktar.mozgasnem', u'Hely id')
  production_id       = fields.Many2one('mrp.production',  u'Gyártási rendelés')
  hibakod_id          = fields.Many2one('raktar.hibakod', u'Hibakód')
  # computed fields
  ora                 = fields.Float(u'Óra', digits=(16, 2), compute='_compute_ora', store=True)
  price               = fields.Float(u'Price', digits=(16, 3), compute='_compute_price', store=True)
  raktaron            = fields.Float(u'Raktáron', digits=(16, 3), related='product_id.product_tmpl_id.qty_available', store=True)
  # virtual fields
  gylap_state         = fields.Selection([('uj',u'Új'),('javit',u'Javítás'),('mterv',u'Műveletterv'),('gyterv',u'Gyártási terv'),('kimer',u'Kimérés'),
                                          ('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], string=u'Gy.lap állapot', related='gyartasi_lap_id.state')
  gyartasi_hely_ids   = fields.Many2many('raktar.mozgasnem', string=u'Gyártási helyek', related='gyartasi_lap_id.gyartasi_hely_ids')
  production_state    = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'), ('ready', 'Ready to Produce'),
                                          ('in_production', 'Production Started'), ('done', 'Done')], 'Gy.rend állapot', related='production_id.state')

  @api.one
  @api.depends('mennyiseg', 'gyartasi_lap_id')
  def _compute_ora(self):
    self.ora = self.gyartasi_lap_id.rendelt_ora * self.mennyiseg / self.gyartasi_lap_id.rendelt_db if self.gyartasi_lap_id else 0.0

  @api.one
  @api.depends('product_id')
  def _compute_price(self):
    self.price = self.env['raktar.darabjegyzek'].search([('product_id', '=', self.product_id.id)], order='id desc', limit=1).bekerulesi_ar

class RaktarImpexBeepul(models.TransientModel):
  _name               = 'raktar.impex_beepul'
  product_id          = fields.Many2one('product.template',  u'Alkatrész', required=True)

  @api.multi
  def impex_beepul(self):

    def calc_beepul(product_id, level=0, prev_id=0, prev_name='', beepul=0.0):
      if product_id.id == prev_id or level > 5: return
      self.env['raktar.impex'].create({'sorszam': level, 'ertek': beepul, 'product_id': product_id.id, 'megjegyzes': prev_name})
      bom_line_ids = self.env['mrp.bom.line'].search([('product_id', '=', product_id.id)])
      for bom_line in bom_line_ids:
        calc_beepul(bom_line.bom_id.product_tmpl_id, level+1, product_id.id, product_id.name.split(' ')[0], bom_line.product_qty/bom_line.bom_id.product_qty)

    self.ensure_one()
    self.env['raktar.impex'].search([]).unlink()
    calc_beepul(self.product_id)
    return {
      'type':       'ir.actions.act_window',
      'res_model':  'raktar.impex',
      'view_mode':  'tree',
    }

class RaktarImpexInput(models.TransientModel):
  _name               = 'raktar.impex_input'
  szamlalo            = fields.Float(u'Számláló', digits=(16, 2), default=1)
  nevezo              = fields.Float(u'Nevező',   digits=(16, 2), default=1)
  arany               = fields.Float(u'Arány',    digits=(16, 8))

  @api.onchange('szamlalo', 'nevezo')
  def onchange_szamlalo_nevezo(self):
    if self.nevezo: self.arany = self.szamlalo / self.nevezo

  @api.multi
  def impex_aranyit(self):
#    if not self.arany: raise exceptions.Warning(u'Az arány nem lehet nulla!')
    self.ensure_one()
    for impex in self.env['raktar.impex'].search([]):
      impex.write({'mennyiseg' : impex.mennyiseg * self.arany})
    return {
      'type':       'ir.actions.act_window',
      'res_model':  'raktar.impex',
      'view_mode':  'tree',
    }

