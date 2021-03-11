# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions
from utils import log

############################################################################################################################  Gyártási lap  ###
class LegrandGyartasiLap(models.Model):
  _name               = 'legrand.gyartasi_lap'
  _order              = 'id'
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], u'Állapot', default='uj')
  name                = fields.Char(u'Rendelés', compute='_compute_name', store=True)
  mongo_id            = fields.Char(u'Mongodb id', readonly=True)
  counter             = fields.Integer(u'Counter', readonly=True)
  rendelesszam        = fields.Char(u'Rendelésszám', required=True, readonly=True)
  jegyzet             = fields.Char(u'Jegyzet', readonly=True)
  termekcsalad        = fields.Char(u'Termékcsalád', readonly=True)
  termekkod           = fields.Char(u'Termékkód', required=True, readonly=True)
  rendelt_db          = fields.Integer(u'Rendelt db', required=True, readonly=True)
  modositott_db       = fields.Integer(u'Módosított rendelt db', states={'kesz': [('readonly', True)]})
  kiadas_ideje        = fields.Char(u'Kiadás ideje', readonly=True)
  hatarido_str        = fields.Char(u'Határidő (eredeti)', required=True, readonly=True)
  hatarido            = fields.Date(u'Határidő', states={'kesz': [('readonly', True)]})
  teljesitett_db      = fields.Integer(u'Teljesített db', default=0, states={'kesz': [('readonly', True)]})
  hatralek_db         = fields.Integer(u'Hátralék db', compute='_compute_hatralek_db', store=True)
  szamlazott_db       = fields.Integer(u'Számlázott db',  default=0, states={'kesz': [('readonly', True)]})
  szamlazhato_db      = fields.Integer(u'Számlázható db', compute='_compute_szamlazhato_db', store=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Termék', required=True, readonly=True, auto_join=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', required=False, domain="[('cikk_id', '=', cikk_id)]", auto_join=True, states={'kesz': [('readonly', True)]})
  cikkek_uid          = fields.Char(u'Összes cikk uid', readonly=False)
  gyartasi_hely_id    = fields.Many2one('legrand.hely', u'Fő gyártási hely', domain=[('szefo_e', '=', True)], states={'kesz': [('readonly', True)]})
  javitas_e           = fields.Boolean(u'Javítás?', default=False, states={'kesz': [('readonly', True)]})
  szallito            = fields.Char(u'Szállító',    readonly=True)
  raklap              = fields.Char(u'Raklap',      readonly=True)
  raklap_min          = fields.Char(u'Raklap min',  readonly=True)
  raklap_max          = fields.Char(u'Raklap max',  readonly=True)
  rakat_tipus         = fields.Char(u'Rakat tipus', readonly=True)
  keu_szam            = fields.Char(u'KEU szám',    readonly=True)
  raktar              = fields.Char(u'Raktár',      readonly=True)
  muveletek_elvegezve = fields.Boolean(u'Műveletek elvégezve?', compute='_compute_muveletek_elvegezve', store=True)
  carnet_db           = fields.Integer(u'Carnet db', states={'kesz': [('readonly', True)]})
  carnet_e            = fields.Boolean(u'Carnet?', compute='_compute_carnet_e', store=True)
  csokkentve_e        = fields.Boolean(u'Csökkentve/Visszavonva', default=False, states={'kesz': [('readonly', True)]})
  rendelt_ora         = fields.Float(u'Rendelt óra',      digits=(16, 2), compute='_compute_rendelt_ora',     store=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra',  digits=(16, 2), compute='_compute_teljesitett_ora', store=True)
  hatralek_ora        = fields.Float(u'Hátralék óra',     digits=(16, 2), compute='_compute_hatralek_ora',    store=True)
  szamlazott_ora      = fields.Float(u'Számlázott óra',   digits=(16, 2), compute='_compute_szamlazott_ora',  store=True)
  szamlazhato_ora     = fields.Float(u'Számlázható óra',  digits=(16, 2), compute='_compute_szamlazhato_ora', store=True)
  termekcsoport       = fields.Char(u'Termékcsoport',     related='cikk_id.termekcsoport',    readonly=True,  store=True)
  gyartas_szunetel_e  = fields.Boolean(u'Gyártás szünetel?', readonly=True, states={'gyartas': [('readonly', False)]})
  leallas_ok          = fields.Char(u'Gyártás leállásának oka', readonly=True, states={'gyartas': [('readonly', False)]})
  aktivitas           = fields.Char(u'Gyártás aktivitás', compute='_compute_aktivitas', store=True)
  leallas_felelos     = fields.Selection([('Szefo',u'Szefo'),('Legrand',u'Legrand'),('vis maior',u'vis maior')], u'Felelős', readonly=True, states={'gyartas': [('readonly', False)]})
  homogen_7127_van_e  = fields.Boolean(u'7127 van benne?', compute='_compute_homogen_7127_van_e', store=True)
  active              = fields.Boolean(u'Aktív?', default=True)
  # statistics
  elso_teljesites     = fields.Date(u'Első teljesítés napja')
  utolso_teljesites   = fields.Date(u'Utolsó teljesítés napja')
  hatarido_elott_db   = fields.Integer(u'Határidő előtt teljesített db')
  hatarido_utan_db    = fields.Integer(u'Határidő után teljesített db')
  hatarido_elott_ora  = fields.Float(u'Határidő előtt teljesített óra',  digits=(16, 2))
  hatarido_utan_ora   = fields.Float(u'Határidő után teljesített óra',   digits=(16, 2))
  elsoig_eltelt_nap   = fields.Integer(u'Első teljesítésig eltelt nap')
  utolsoig_eltelt_nap = fields.Integer(u'Utolsó teljesítésig eltelt nap')
  # virtual fields
  cikknev             = fields.Char(u'Terméknév', related='cikk_id.cikknev', readonly=True)
  utolso_feljegyzes   = fields.Char(u'Utolsó feljegyzés', compute='_compute_utolso_feljegyzes')
  feljegyzes_ideje    = fields.Char(u'Feljegyzés ideje',  compute='_compute_utolso_feljegyzes')
  feljegyzo_id        = fields.Many2one('res.users', u'Feljegyző', compute='_compute_utolso_feljegyzes')
  check_cikkek_uid    = fields.Char(u'Ellenőrzés', compute='_compute_check_cikkek_uid')
  cikkhiany           = fields.Char(u'Cikkhiány', compute='_compute_cikkhiany')
  cikkhiany_count     = fields.Integer(u'Cikkhiány db', compute='_compute_cikkhiany')
#  depo_db             = fields.Integer(u'Depó db', compute='_compute_depo_db')
  szefo_muvelet_ids   = fields.One2many('legrand.gylap_szefo_muvelet',  'gyartasi_lap_id', u'Szefo műveletek',      readonly=True,  states={'uj': [('readonly', False)]}, auto_join=True)
  lezer_tampon_ids    = fields.One2many('legrand.lezer_tampon',         'termek_id',       u'Lézer, tampon',        readonly=True,  related='cikk_id.lezer_tampon_ids', auto_join=True)
  gylap_homogen_ids   = fields.One2many('legrand.gylap_homogen',        'gyartasi_lap_id', u'Homogén',              states={'kesz': [('readonly', True)]}, auto_join=True)
  gylap_dbjegyzek_ids = fields.One2many('legrand.gylap_dbjegyzek',      'gyartasi_lap_id', u'Legrand darabjegyzék', readonly=True, auto_join=True)
  gylap_muvelet_ids   = fields.One2many('legrand.gylap_legrand_muvelet','gyartasi_lap_id', u'Műveleti utasítás',    readonly=True, auto_join=True)

  @api.multi
  def write(self, vals):
    if 'gyartasi_hely_id' in vals and vals['gyartasi_hely_id']:
      homogen_ids = self.gylap_homogen_ids.filtered(lambda r: not r.gyartasi_hely_id.id and r.sajat)
      homogen_ids.write({'gyartasi_hely_id': vals['gyartasi_hely_id']})
    if 'bom_id' in vals and vals['bom_id']:
      sor_ids = self.bom_id.mozgassor_ids.filtered(lambda r: r.gyartasi_lap_id.id == self.id)
      sor_ids.write({'bom_id': vals['bom_id']})
    return super(LegrandGyartasiLap, self).write(vals)

  @api.one
  @api.depends('state', 'leallas_ok')
  def _compute_aktivitas(self):
    if self.state == 'gyartas':
      self.aktivitas = u'áll' if self.leallas_ok else u'folyamatban'
      self.leallas_felelos = 'Szefo' if self.leallas_ok else ''
    else:
      self.aktivitas = ''
      self.leallas_felelos = ''

  @api.one
  @api.depends('gylap_homogen_ids.sajat')
  def _compute_homogen_7127_van_e(self):
    self.homogen_7127_van_e = len(self.gylap_homogen_ids.filtered(lambda r: r.homogen_id.homogen == '7127' and r.sajat)) > 0

  @api.one
  @api.depends('szefo_muvelet_ids', 'szefo_muvelet_ids.hiany_db')
  def _compute_muveletek_elvegezve(self):
    self.muveletek_elvegezve = len(self.szefo_muvelet_ids.filtered(lambda r: r.hiany_db > 0)) == 0

  @api.one
  @api.depends('rendelesszam', 'cikk_id')
  def _compute_name(self):
    self.name = str(self.id)+' '+self.rendelesszam+' -> '+self.cikk_id.cikkszam

  @api.one
  @api.depends('teljesitett_db', 'carnet_db')
  def _compute_carnet_e(self):
    self.carnet_e = self.teljesitett_db < self.carnet_db

  @api.one
  @api.depends('teljesitett_db', 'szamlazott_db')
  def _compute_szamlazhato_db(self):
    self.szamlazhato_db = self.teljesitett_db - self.szamlazott_db

  @api.one
  @api.depends('modositott_db', 'teljesitett_db')
  def _compute_hatralek_db(self):
    self.hatralek_db = self.modositott_db - self.teljesitett_db

  @api.one
  @api.depends('gylap_homogen_ids.sajat', 'gylap_homogen_ids.rendelt_ora')
  def _compute_rendelt_ora(self):
    self.rendelt_ora = sum(self.gylap_homogen_ids.filtered('sajat').mapped('rendelt_ora'))

  @api.one
  @api.depends('gylap_homogen_ids.sajat', 'gylap_homogen_ids.teljesitett_ora')
  def _compute_teljesitett_ora(self):
    self.teljesitett_ora = sum(self.gylap_homogen_ids.filtered('sajat').mapped('teljesitett_ora'))

  @api.one
  @api.depends('rendelt_ora', 'teljesitett_ora')
  def _compute_hatralek_ora(self):
    self.hatralek_ora = self.rendelt_ora - self.teljesitett_ora

  @api.one
  @api.depends('gylap_homogen_ids.sajat', 'gylap_homogen_ids.szamlazott_ora')
  def _compute_szamlazott_ora(self):
    self.szamlazott_ora = sum(self.gylap_homogen_ids.filtered('sajat').mapped('szamlazott_ora'))

  @api.one
  @api.depends('teljesitett_ora', 'szamlazott_ora')
  def _compute_szamlazhato_ora(self):
    self.szamlazhato_ora = self.teljesitett_ora - self.szamlazott_ora

  @api.one
  @api.depends('cikk_id')
  def _compute_utolso_feljegyzes(self):
    utolso = self.env['legrand.feljegyzes'].search([('gyartasi_lap_id', '=', self.id)], limit=1, order='id desc')
    self.utolso_feljegyzes = utolso.feljegyzes
    self.feljegyzes_ideje  = utolso.create_date
    self.feljegyzo_id      = utolso.create_uid

  @api.one
  @api.depends('bom_id')
  def _compute_check_cikkek_uid(self):
    if len(self.bom_id):
      if self.cikkek_uid == self.bom_id.cikkek_uid:
        self.check_cikkek_uid = 'OK'
      else:
        bom_cikkek    = self.bom_id.bom_line_ids.mapped('cikk_id')
        gylap_cikkek  = self.gylap_dbjegyzek_ids.mapped('cikk_id')
        bom_tobblet   = bom_cikkek - gylap_cikkek
        gylap_tobblet = gylap_cikkek - bom_cikkek
        uzenet = ''
        if len(bom_tobblet):
          uzenet += '+' +str([x.encode('UTF8') for x in bom_tobblet.mapped('cikkszam')])
        if len(gylap_tobblet):
          uzenet += ' -'+str([x.encode('UTF8') for x in gylap_tobblet.mapped('cikkszam')])
        self.check_cikkek_uid = uzenet

  @api.one
  @api.depends()
  def _compute_cikkhiany(self):
    hiany, count = '', 0
    ids = self.bom_id.bom_line_ids.mapped('cikk_id.id')
    if len(ids):
      query = 'SELECT id, elerheto FROM legrand_cikk_keszlet WHERE id in ({0})'.format(','.join(str(e) for e in ids))
      self.env.cr.execute(query)
      elerheto_dict = dict(self.env.cr.fetchall())
      for line in self.bom_id.bom_line_ids:
        ossz_beep = self.modositott_db * line.beepules
        elerheto  = max(elerheto_dict[line.cikk_id.id], 0.0)
        if ossz_beep > elerheto:
          hiany += '{0} ({1}), '.format(line.cikk_id.cikkszam, elerheto-ossz_beep)
          count += 1
    self.cikkhiany = hiany
    self.cikkhiany_count = count

#  @api.one
#  @api.depends()
#  def _compute_depo_db(self):
#    hely_id = self.env['legrand.hely'].search([('azonosito','=','depo')]).id
#    self.depo_db = self.env['legrand.anyagjegyzek_keszlet'].search([('bom_id', '=', self.bom_id.id),('hely_id','=',hely_id)]).raktaron

  @api.one
  def state2uj(self):
    log(self.env, {'name': u'Állapot -> Új', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'uj'
    return True

  @api.one
  def state2mterv(self):
    log(self.env, {'name': u'Állapot -> Műveletterv', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'mterv'
    return True

  @api.one
  def state2gyartas(self):
    log(self.env, {'name': u'Állapot -> Gyártás', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'gyartas'
    return True

  @api.one
  def state2gykesz(self):
    log(self.env, {'name': u'Állapot -> Gyártás kész', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'gykesz'
    return True

  @api.one
  def state2kesz(self):
    log(self.env, {'name': u'Állapot -> Rendelés teljesítve', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    self.state = 'kesz'
    return True

  @api.one
  def update_gylap_szefo_muvelet(self):
    if self.javitas_e:
      raise exceptions.Warning(u'Javítási munka, ez a funkció nem alkalmazható!')
    self.szefo_muvelet_ids.unlink()
    muv_ids = self.env['legrand.muvelet'].search([('cikk_id', '=', self.cikk_id.id)])
    for muv in muv_ids:
      muv_row = muv.read()[0]
      muv_row['gyartasi_lap_id'] = self.id
      self.szefo_muvelet_ids.create(muv_row)
    log(self.env, {'name': u'Műveletek frissítése', 'table': 'gyartasi_lap', 'value': self.name, 'rowid': self.id})
    return True

  @api.one
  def export_impex(self):
    self.env['legrand.impex'].search([]).unlink()
    for alk in self.gylap_dbjegyzek_ids:
      impex_row = {
        'mennyiseg'       : alk.ossz_beepules,
        'gyartasi_lap_id' : self.id,
        'cikk_id'         : alk.cikk_id.id,
      }
      self.env['legrand.impex'].create(impex_row)
    return True

