# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions
import logging, re
_logger = logging.getLogger(__name__)

def trim(list):
  ret = []
  for elem in list:
    if type(elem)==unicode or type(elem)==str: ret.append(elem.strip())
    else: ret.append(elem)
  return ret

############################################################################################################################  Paraméter  ###
class LeltarParameter(models.Model):
  _inherit  = 'szefo.parameter'

  @api.one
  def import_gyartasi_szam(self):
    import pymssql
    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='DominoSoft')
    Eszkoz = self.env['leltar.eszkoz']
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Gyártási szám import', 'module': 'leltar'})

    cursor = mssql_conn.cursor()
    cursor.execute("""SELECT bf_lelt, bf_gyszam
                      FROM DominoSoft.dbo.beftorzs WHERE targyev = 2019 AND status = 0 AND bf_kiido IS NULL AND bf_gyszam IS NOT NULL order by hivszam""")
    row = cursor.fetchone()
    while row:
      leltari_szam, gyartasi_szam = trim(row)
      eszkoz = Eszkoz.search([('leltari_szam', '=', leltari_szam)])
      if eszkoz and not eszkoz.gyartasi_szam:
        eszkoz.write({'gyartasi_szam': gyartasi_szam})
      row = cursor.fetchone()
    return True

  @api.one
  def import_netto_ertek(self):
    import pymssql
    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='DominoSoft')
    Eszkoz = self.env['leltar.eszkoz']
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Nettó érték import', 'module': 'leltar'})

    self.env.cr.execute("""UPDATE leltar_eszkoz SET netto_ertek = -1""")
    self.env.invalidate_all()
    cursor = mssql_conn.cursor()
    cursor.execute("""SELECT bf_lelt, bf_brutto-bf_ecs AS netto FROM ( SELECT MAX(hivszam) AS lasthsz FROM DominoSoft.dbo.beftorzs GROUP BY bf_lelt ) AS last
                      INNER JOIN DominoSoft.dbo.beftorzs AS torzs ON torzs.hivszam = lasthsz""")
    row = cursor.fetchone()
    while row:
      leltari_szam, netto_ertek = trim(row)
      eszkoz = Eszkoz.search([('leltari_szam', '=', leltari_szam)])
      if eszkoz:
        eszkoz.write({'netto_ertek': netto_ertek})
      row = cursor.fetchone()
    return True

  @api.one
  def import_eszkoz(self):
    import pymssql
    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='DominoSoft')

    Eszkoz  = self.env['leltar.eszkoz']
    Csoport = self.env['leltar.csoport']
    Korzet  = self.env['leltar.korzet']
    Log     = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Eszköz import', 'module': 'leltar'})

    cursor = mssql_conn.cursor()
    cursor.execute("""SELECT hivszam, bf_lelt, bf_megnev, bf_ltkorzet, bf_ltfelelos, bf_ltcsoport, bf_gyszam, bf_param, bf_vonalkod
                      FROM DominoSoft.dbo.beftorzs WHERE targyev = 2019 AND status = 0 AND bf_kiido IS NULL order by hivszam""")
    row = cursor.fetchone()
    while row:
      leltarcsoport_id    = None
      leltarkorzet_kod    = None
      akt_hasznalo_id     = None
      akt_leltarkorzet_id = None
      hivszam, leltari_szam, megnevezes, ds_leltarkorzet, ds_leltarfelelos, csoportkod, gyartasi_szam, megjegyzes, leltari_szam_vonalkod = trim(row)
      if not Eszkoz.search_count(['|', ('active', '=', True), ('active', '=', False), ('leltari_szam', '=', leltari_szam)]):

        csoport_ids = Csoport.search_read([('csoportkod', '=', csoportkod)])
        if csoport_ids: leltarcsoport_id = csoport_ids[0]['id']

        korzet_ids = Korzet.search_read([('ds_leltarkorzet', '=', ds_leltarkorzet)])
        if len(korzet_ids) == 1:
          akt_leltarkorzet_id = korzet_ids[0]['id']
          leltarkorzet_kod    = korzet_ids[0]['leltarkorzet_kod']

        Eszkoz.create({'name': leltari_szam+' - '+megnevezes, 'hivszam': hivszam, 'leltari_szam': leltari_szam, 'megnevezes': megnevezes,
          'leltarcsoport_id': leltarcsoport_id, 'akt_leltarkorzet_id': akt_leltarkorzet_id, 'akt_hasznalo_id': akt_hasznalo_id,
          'leltarkorzet_kod': leltarkorzet_kod, 'csoportkod': csoportkod, 'leltari_szam_vonalkod': leltari_szam_vonalkod, 'gyartasi_szam': gyartasi_szam,
          'megjegyzes': megjegyzes, 'ds_leltarkorzet': ds_leltarkorzet, 'ds_leltarfelelos': ds_leltarfelelos, 'idegen_e': False })
      row = cursor.fetchone()
    return True

  @api.one
  def leltariv_generalas(self):
    for korzet in self.env['leltar.korzet'].search([('leltarozni', '=', True)]):
      self.env['leltar.leltariv'].create({'leltarkorzet_id': korzet.id})
    return True

  @api.one
  def leltar_lezaras(self):
    if self.env['leltar.leltariv_dupla'].search([]):
      raise exceptions.Warning(u'Többszörösen felvett új eszközök!')
    if self.env['leltar.leltariv_hiany'].search([]):
      raise exceptions.Warning(u'Nincs minden eszköz leltározva!')
    if self.env['leltar.eszkoz'].search([('zarolva', '=', True)]):
      raise exceptions.Warning(u'Eszköz nem lehet zárolva!')
    if self.env['leltar.korzet'].search([('zarolva', '=', True)]):
      raise exceptions.Warning(u'Körzet nem lehet zárolva!')
    if self.env['leltar.leltariv'].search([('state', '=', 'terv')]):
      raise exceptions.Warning(u'Leltárív nem lehet Tervezet állapotban!')
    if self.env['leltar.leltariv_osszes'].search([('selejtezni','=',True), '|', ('megjegyzes','=',''), ('megjegyzes','=',False)]):
      raise exceptions.Warning(u'Selejtezéshez meg kell jelölni az okot!')

    for selejt in self.env['leltar.leltariv_osszes'].search([('selejtezni','=',True)]):
      selejt.eszkoz_id.write({'selejt_ok': selejt.megjegyzes, 'selejtezni': True})

    for mozgas in self.env['leltar.leltariv_mozgas'].search([]):
      if mozgas.akt_leltarkorzet_id.id != mozgas.leltariv_id.leltarkorzet_id.id:
        self.env['leltar.eszkozmozgas'].create({'eszkoz_id': mozgas.eszkoz_id.id, 'hova_leltarkorzet_id': mozgas.leltariv_id.leltarkorzet_id.id, 'megerkezett': True, 'megjegyzes': u'leltár' })

    self.env['leltar.leltariv'].search([('state', '!=', 'konyvelt')]).write({'state': 'konyvelt'})

    return True

############################################################################################################################  DsFelelos  ###
class LeltarDsFelelos(models.Model):
  _name       = 'leltar.ds_felelos'
  bl_kod      = fields.Char(u'Kód',  required=True)
  bl_megnev   = fields.Char(u'Megnevezés',  required=True)
  SzemelyId   = fields.Integer(u'SzemelyId',  required=True)
  employee_id = fields.Integer(u'Employee id')

############################################################################################################################  Csoport  ###
class LeltarCsoport(models.Model):
  _name       = 'leltar.csoport'
  name        = fields.Char(u'Leltárcsoport név',  required=True)
  csoportkod  = fields.Char(u'Leltárcsoport kód',  required=True)
  active      = fields.Boolean(u'Aktív?',  default=True)

############################################################################################################################  Tulajdonság  ###
class LeltarTulajdonsag(models.Model):
  _name       = 'leltar.tulajdonsag'
  name        = fields.Char(u'Tulajdonság',  required=True)

############################################################################################################################  Körzet  ###
class LeltarKorzet(models.Model):
  _name               = 'leltar.korzet'
  _order              = 'leltarkorzet_kod'
  name                = fields.Char(u'Leltárkörzet', compute='_compute_name', store=True)
  leltarkorzet_kod    = fields.Char(u'Leltárkörzet kód',   required=True)
  leltarfelelos_id    = fields.Many2one('hr.employee',  u'Leltárfelelős',  required=False, auto_join=True)
  telephely_id        = fields.Many2one('szefo.telephely',  u'Telephely',  required=True,  auto_join=True)
  szobaszam           = fields.Char(u'Szobaszám',   required=True)
  megnevezes          = fields.Char(u'Leltárkörzet név',   required=True)
  zarolva             = fields.Boolean(u'Zárolva?', default=False)
  leltarozni          = fields.Boolean(u'Leltározni?', default=True)
  ds_leltarkorzet     = fields.Char(u'DS Leltárkörzet',  required=True)
  ds_korzet_vonalkod  = fields.Char(u'DS Leltárkörzet vonalkód',   required=True)
  hianyzo_eszk_gyujto = fields.Boolean(u'Hiányzó eszközök gyűjtő', default=False)
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  eszkozok_ids        = fields.One2many('leltar.eszkoz', 'akt_leltarkorzet_id', u'Eszközök a leltárkörzetben')

  @api.one
  @api.depends('leltarkorzet_kod', 'telephely_id', 'szobaszam', 'megnevezes')
  def _compute_name(self):
    if self.leltarkorzet_kod and self.telephely_id and self.szobaszam and self.megnevezes:
      self.name = self.leltarkorzet_kod+' - '+self.telephely_id.name+', '+self.szobaszam+': '+self.megnevezes

  @api.one
  def zarolva_valt(self):
    self.zarolva = not self.zarolva
    return True

  @api.one
  def leltarozni_valt(self):
    self.leltarozni = not self.leltarozni
    return True

############################################################################################################################  Szett  ###
class LeltarSzett(models.Model):
  _name                 = 'leltar.szett'
  name                  = fields.Char(u'Szett név', required=True)
  leltarkorzet_id       = fields.Many2one('leltar.korzet',  u'Leltárkörzet',  required=True)
  hasznalo_id           = fields.Many2one('hr.employee',    u'Felhasználó')
  megjegyzes            = fields.Char(u'Megjegyzés')
  count_korzet_elter    = fields.Integer(u'Leltárkörzet eltér', compute='_compute_count_korzet_elter', store=True)
  count_hasznalo_elter  = fields.Integer(u'Felhasználó eltér',  compute='_compute_count_hasznalo_elter', store=True)
  # virtual fields
  eszkozok_ids          = fields.One2many('leltar.eszkoz', 'szett_id', u'Eszközök a szettben')

  @api.one
  @api.depends('leltarkorzet_id', 'eszkozok_ids.akt_leltarkorzet_id')
  def _compute_count_korzet_elter(self):
    self.count_korzet_elter = len(self.eszkozok_ids.filtered(lambda r: self.leltarkorzet_id.id != r.akt_leltarkorzet_id.id))

  @api.one
  @api.depends('hasznalo_id', 'eszkozok_ids.akt_hasznalo_id')
  def _compute_count_hasznalo_elter(self):
    self.count_hasznalo_elter = len(self.eszkozok_ids.filtered(lambda r: self.hasznalo_id.id != r.akt_hasznalo_id.id))

  @api.one
  def szett_eszkoz_mozgas(self):
    for eszkoz in self.eszkozok_ids.filtered(lambda r: self.leltarkorzet_id.id != r.akt_leltarkorzet_id.id):
      self.env['leltar.eszkozmozgas'].create({'eszkoz_id': eszkoz.id, 'honnan_leltarkorzet_id': eszkoz.akt_leltarkorzet_id.id,
                    'hova_leltarkorzet_id': self.leltarkorzet_id.id, 'megjegyzes': 'szett eszköz' })
    return True

  @api.one
  def szett_eszkoz_hasznal(self):
    for eszkoz in self.eszkozok_ids.filtered(lambda r: self.hasznalo_id.id != r.akt_hasznalo_id.id):
      self.env['leltar.eszkozatvetel'].create({'eszkoz_id': eszkoz.id, 'uj_hasznalo_id': self.hasznalo_id.id, 'megjegyzes': self.megjegyzes})
    return True

############################################################################################################################  Eszköz  ###
class LeltarEszkoz(models.Model):
  _name                 = 'leltar.eszkoz'
  _inherit              = 'mail.thread'
  name                  = fields.Char(u'Eszköz',        compute='_compute_name', store=True)
  hivszam               = fields.Integer(u'Hiv.szám',   readonly=True)
  leltari_szam          = fields.Char(u'Leltári szám',  required=True, index=True)
  megnevezes            = fields.Char(u'Eszköz név',    required=True)
  akt_leltarkorzet_id   = fields.Many2one('leltar.korzet',  u'Aktuális leltárkörzet')
  akt_hasznalo_id       = fields.Many2one('hr.employee',    u'Aktuális használó')
  leltarcsoport_id      = fields.Many2one('leltar.csoport', u'Leltárcsoport')
  szett_id              = fields.Many2one('leltar.szett', u'Eszköz szett')
  csoportkod            = fields.Char(u'Leltárcsoport kód')
  leltari_szam_vonalkod = fields.Char(u'Leltári szám vonalkód')
  gyartasi_szam         = fields.Char(u'Gyártási szám')
  megjegyzes            = fields.Char(u'Megjegyzés')
  leltarkorzet_kod      = fields.Char(u'DS <-> Leltárkörzet kód')
  ds_leltarkorzet       = fields.Char(u'DS Leltárkörzet')
  ds_leltarfelelos      = fields.Char(u'DS Leltárfelelős')
  netto_ertek           = fields.Integer(u'Nettó érték')
  selejt_ok             = fields.Char(u'Selejtezés oka')
  selejtezni            = fields.Boolean(u'Selejtezni', default=False)
  zarolva               = fields.Boolean(u'Zárolva?',   default=False)
  idegen_e              = fields.Boolean(u'Idegen eszköz?', default=True)
  active                = fields.Boolean(u'Aktív?',     default=True)
  # virtual fields
  not_active            = fields.Boolean(u'Nem aktív?', compute='_compute_not_active')
  mozgas_ids            = fields.One2many('leltar.eszkozmozgas', 'eszkoz_id', u'Eszköz mozgások')
  atvetel_ids           = fields.One2many('leltar.eszkozatvetel', 'eszkoz_id', u'Eszköz átvételek')
  tulajdonsag_ids       = fields.Many2many('leltar.tulajdonsag', string=u'Tulajdonságok')

  @api.one
  @api.depends('leltari_szam', 'megnevezes')
  def _compute_name(self):
    if self.leltari_szam and self.megnevezes:
      self.name = self.leltari_szam+' - '+self.megnevezes

  @api.one
  @api.depends('active')
  def _compute_not_active(self):
    self.not_active = not self.active

  @api.multi
  def write(self, vals):
    super(LeltarEszkoz, self).write(vals)
    if 'netto_ertek' not in vals:
      Log = self.env['szefo.log']
      Log.create({'loglevel': 'notice', 'name': 'modify', 'value': vals, 'module': 'leltar', 'table': 'eszkoz', 'rowid': self.id})
    return True

  @api.onchange('selejt_ok')
  def on_change_elozmeny_id(self):
    if self.selejt_ok:  self.selejtezni = True
    else:               self.selejtezni = False; self.active = True

  @api.one
  def selejtezni_valt(self):
    self.selejtezni = not self.selejtezni
    return True

  @api.one
  def zarolva_valt(self):
    self.zarolva = not self.zarolva
    return True

  @api.one
  def do_toggle_active(self):
    self.active = not self.active
    return True

############################################################################################################################  Eszközmozgás  ###
class LeltarEszkozmozgas(models.Model):
  _name                 = 'leltar.eszkozmozgas'
  _order                = 'id desc'
  eszkoz_id             = fields.Many2one('leltar.eszkoz', u'Eszköz',  required=True, auto_join=True)
  honnan_leltarkorzet_id= fields.Many2one('leltar.korzet', u'Honnan leltárkörzet', readonly=True)
  hova_leltarkorzet_id  = fields.Many2one('leltar.korzet', u'Hova leltárkörzet',   required=True)
  megerkezett           = fields.Boolean(u'Megérkezett', default=False)
  megjegyzes            = fields.Char(u'Megjegyzés')
  # virtual fields
  akt_leltarkorzet_id   = fields.Many2one('leltar.korzet',  u'Aktuális leltárkörzet',  related='eszkoz_id.akt_leltarkorzet_id' )

  @api.model
  def create(self, vals):
    eszkoz_id = vals['eszkoz_id']
    eszkoz    = self.env['leltar.eszkoz'].search([('id', '=', eszkoz_id)])
    honnan_id = eszkoz.akt_leltarkorzet_id.id
    hova_id   = vals['hova_leltarkorzet_id']
    honnan    = self.env['leltar.korzet'].search([('id', '=', honnan_id)])
    hova      = self.env['leltar.korzet'].search([('id', '=', hova_id)])
    if honnan_id == hova_id:
      raise exceptions.Warning(u'A hova és honnan leltárkörzet megegyezik!')
    if eszkoz.zarolva:
      raise exceptions.Warning(u'Eszköz zárolva!')
    if honnan.zarolva:
      raise exceptions.Warning(u'Honnan leltárkörzet ('+ honnan.name + u') zárolva!')
    if hova.zarolva:
      raise exceptions.Warning(u'Hova leltárkörzet zárolva!')
    vals['honnan_leltarkorzet_id'] = honnan_id
    vals['akt_leltarkorzet_id'] = hova_id
    return super(LeltarEszkozmozgas, self).create(vals)

  @api.multi
  def write(self, vals):
    super(LeltarEszkozmozgas, self).write(vals)
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'notice', 'name': 'modify', 'value': vals, 'module': 'leltar', 'table': 'eszkozmozgas', 'rowid': self.id})
    return True

  @api.one
  def megerkezett_valt(self):
    self.megerkezett = not self.megerkezett
    return True

  @api.one
  def sztorno(self):
    megjegyzes = u'sztornó ID:'+str(self.id)
    if not self.honnan_leltarkorzet_id:
      raise exceptions.Warning(u'Honnan leltárkörzet üres, nem lehet sztornózni!')
    if self.megerkezett:
      raise exceptions.Warning(u'Már sztornózva van!')
    Mozgas = self.env['leltar.eszkozmozgas']
    Mozgas.create({'eszkoz_id': self.eszkoz_id.id, 'honnan_leltarkorzet_id': self.hova_leltarkorzet_id.id, 'hova_leltarkorzet_id': self.honnan_leltarkorzet_id.id,
                  'megerkezett': True, 'megjegyzes': megjegyzes })
    self.megerkezett = True
    self.megjegyzes = megjegyzes
    return True

############################################################################################################################  Körzetmozgás  ###
class LeltarKorzetmozgas(models.Model):
  _name                 = 'leltar.korzetmozgas'
  _order                = 'id desc'
  honnan_leltarkorzet_id= fields.Many2one('leltar.korzet', u'Honnan leltárkörzet',  required=True)
  hova_leltarkorzet_id  = fields.Many2one('leltar.korzet', u'Hova leltárkörzet',  required=True)
  megjegyzes            = fields.Char(u'Megjegyzés')

  @api.model
  def create(self, vals):
    Eszkoz = self.env['leltar.eszkoz']
    Mozgas = self.env['leltar.eszkozmozgas']
    honnan_id = vals['honnan_leltarkorzet_id']
    hova_id   = vals['hova_leltarkorzet_id']
    eszkozok  = Eszkoz.search([('akt_leltarkorzet_id', '=', honnan_id)])
    for eszkoz in eszkozok:
      Mozgas.create({'eszkoz_id': eszkoz.id, 'honnan_leltarkorzet_id': honnan_id, 'hova_leltarkorzet_id': hova_id,
                     'megerkezett': True, 'megjegyzes': u'Körzet mozgatás' })
    return super(LeltarKorzetmozgas, self).create(vals)

############################################################################################################################  Eszközátvétel  ###
class LeltarEszkozatvetel(models.Model):
  _name                 = 'leltar.eszkozatvetel'
  _order                = 'id desc'
  eszkoz_id             = fields.Many2one('leltar.eszkoz', u'Eszköz',  required=True, auto_join=True)
  regi_hasznalo_id      = fields.Many2one('hr.employee',   u'Régi használó', readonly=True)
  uj_hasznalo_id        = fields.Many2one('hr.employee',   u'Új használó',  required=False )
  hr_bevette            = fields.Boolean(u'HR bevette', default=False)
  megjegyzes            = fields.Char(u'Megjegyzés')
  eszkoz_megjegyzes     = fields.Char(u'Eszköz megjegyzés',  related='eszkoz_id.megjegyzes' )
  # virtual fields
  akt_hasznalo_id       = fields.Many2one('hr.employee',   u'Aktuális használó',  related='eszkoz_id.akt_hasznalo_id' )

  @api.model
  def create(self, vals):
    eszkoz_id = vals['eszkoz_id']
    eszkoz    = self.env['leltar.eszkoz'].search([('id', '=', eszkoz_id)])
    regi_id   = eszkoz.akt_hasznalo_id.id
    uj_id     = vals['uj_hasznalo_id']
    if regi_id == uj_id:
      raise exceptions.Warning(u'A régi és az új használó megegyezik!')
    vals['regi_hasznalo_id'] = regi_id
    vals['akt_hasznalo_id']   = uj_id
    if vals['megjegyzes']: vals['eszkoz_megjegyzes'] = vals['megjegyzes']
    return super(LeltarEszkozatvetel, self).create(vals)

  @api.one
  def hr_bevette_valt(self):
    self.hr_bevette = not self.hr_bevette
    return True

############################################################################################################################  Leltár  ###
class LeltarLeltar(models.Model):
  _name                 = 'leltar.leltar'
  eszkoz_id             = fields.Many2one('leltar.eszkoz', u'Eszköz',  required=False, auto_join=True)
  leltarkorzet_id       = fields.Many2one('leltar.korzet', u'Leltárkörzet',  required=False)
  hivszam               = fields.Integer(u'Hiv.szám',  required=True, index=True)
  targyev               = fields.Integer(u'Tárgyév',   required=True)
  targyho               = fields.Integer(u'Tárgyhó',   required=True)
  leltari_szam_vonalkod = fields.Char(u'Leltári szám vonalkód',   required=True)
  leltarkorzet_vonalkod = fields.Char(u'Leltárkörzet vonalkód',   required=True)
  szobaszam             = fields.Char(u'Szobaszám')
  ervenyesseg_kezdete   = fields.Datetime(u'Érvényesség kezdete')
  # virtual fields
  leltari_szam          = fields.Char(u'Leltári szám',  related='eszkoz_id.leltari_szam')

############################################################################################################################  Vonalkódolvas  ###
class LeltarVonalkodolvas(models.Model):
  _name   = 'leltar.vonalkodolvas'
  _order  = 'id desc'
  vonalkod            = fields.Char(u'Kód bevitel')
  vonalkod_save       = fields.Char(u'Olvasott vonalkód')
  leltarkorzet_id     = fields.Many2one('leltar.korzet', u'Leltárkörzet', required=True)
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz')
  akt_leltarkorzet_id = fields.Many2one('leltar.korzet',  u'Aktuális leltárkörzet')
  uzenet              = fields.Char(u'Üzenet')
  leltar              = fields.Boolean(u'Leltár?', default=lambda self: self.env.context.get('leltar', False))
  dummy               = fields.Char(u'Dummy')
  uj_eszkoz_ids       = fields.Many2many('leltar.eszkoz', relation='leltar_eszkoz_vonalkodolvas_uj_rel',  string='Új eszközök')
  ell_eszkoz_ids      = fields.Many2many('leltar.eszkoz', relation='leltar_eszkoz_vonalkodolvas_ell_rel', string='Ellenőrzendő eszközök')
  akt_eszkoz_ids      = fields.Many2many('leltar.eszkoz', relation='leltar_eszkoz_vonalkodolvas_akt_rel', string='Aktuális eszközök')
#  # virtual fields
#  leltarkorzet_id_dup = fields.Many2one('leltar.korzet', u'Leltárkörzet', compute='_compute_leltarkorzet_id_dup')
#
#  @api.one
#  @api.depends('leltarkorzet_id')
#  def _compute_leltarkorzet_id_dup(self):
#    self.leltarkorzet_id_dup = self.leltarkorzet_id

  @api.model
  def create(self, vals):
    Mozgas = self.env['leltar.eszkozmozgas']
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': vals, 'module': 'leltar'})
    if vals['leltar']:
      megerkezett, megjegyzes = True,  u'leltár'
    else:
      megerkezett, megjegyzes = False, u'vonalkód'
      del vals['ell_eszkoz_ids']
      del vals['akt_eszkoz_ids']
    new = super(LeltarVonalkodolvas, self).create(vals)
    for eszkoz in new.uj_eszkoz_ids:
      Mozgas.create({'eszkoz_id': eszkoz.id, 'honnan_leltarkorzet_id': eszkoz.akt_leltarkorzet_id.id, 'hova_leltarkorzet_id': new.leltarkorzet_id.id,
                     'megerkezett': megerkezett, 'megjegyzes': megjegyzes})
    return new

  @api.one
  def do_mass_insert_mozgas(self):
    return True

  @api.onchange('vonalkod')
  def on_change_leltarkorzet(self):

    def ean_cut(s):
      if re.match('^0?000100\d{6}|^0?000001\d{6}', s): return s[s.index('1'):-1]
      else: return s

    if not self.vonalkod: return
    self.vonalkod = ean_cut(self.vonalkod)
    Eszkoz        = self.env['leltar.eszkoz']
    Korzet        = self.env['leltar.korzet']

    self.vonalkod_save = self.vonalkod
    korzet_ids = Korzet.search([('leltarkorzet_kod', '=', self.vonalkod)])
    eszkoz_ids = Eszkoz.search([('leltari_szam_vonalkod', '=', self.vonalkod)])
    if not eszkoz_ids:
      eszkoz_ids = Eszkoz.search([('leltari_szam', '=', self.vonalkod)])

    self.eszkoz_id = False
    self.akt_leltarkorzet_id = False
    if korzet_ids:
      if not self.leltarkorzet_id:
        self.leltarkorzet_id = korzet_ids[0]
        eszkoz_ids = Eszkoz.search([('akt_leltarkorzet_id', '=', self.leltarkorzet_id.id)])
        self.uj_eszkoz_ids  = False
        self.ell_eszkoz_ids = eszkoz_ids
        self.akt_eszkoz_ids = eszkoz_ids
        self.uzenet = u'Leltárkörzet'
      else:
        self.uzenet = u'Leltárkörzet módosítása nem lehetséges!'
    elif eszkoz_ids:
      self.eszkoz_id = eszkoz_ids[0]
      self.akt_leltarkorzet_id = self.eszkoz_id.akt_leltarkorzet_id.id
      if self.eszkoz_id not in self.akt_eszkoz_ids:
        self.uj_eszkoz_ids  += self.eszkoz_id
      self.ell_eszkoz_ids -= self.eszkoz_id
      self.uzenet = u'Leltári szám'
    else:
      self.uzenet = u'Nincs találat'

    self.vonalkod = ''

############################################################################################################################  Leltárív  ###
class LeltarLeltariv(models.Model):
  _name               = 'leltar.leltariv'
  _order              = 'leltarkorzet_kod, id desc'
  name                = fields.Char(u'Leltárív', compute='_compute_name', store=True)
  state               = fields.Selection([('terv',u'Tervezet'),('kesz',u'Kész'),('konyvelt',u'Könyvelt')], u'Állapot', default='terv' )
  leltarkorzet_id     = fields.Many2one('leltar.korzet',  u'Leltárkörzet',  required=True)
  letrehozva          = fields.Date(u'Létrehozva',  readonly=True)
  leltarvezeto_id     = fields.Many2one('hr.employee',  u'Leltárvezető',  auto_join=True, states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  leltarozo_id        = fields.Many2one('hr.employee',  u'Leltározó',  auto_join=True, states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  leltarozo2_id       = fields.Many2one('hr.employee',  u'Leltározó2', auto_join=True, states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  leltarozo3_id       = fields.Many2one('hr.employee',  u'Leltározó3', auto_join=True, states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  leltarkorzet_kod    = fields.Char(u'Leltárkörzet kód', related='leltarkorzet_id.leltarkorzet_kod', readonly=True, store=True)
  hianyzo_eszk_gyujto = fields.Boolean(u'Hiányzó eszközök gyűjtő', related='leltarkorzet_id.hianyzo_eszk_gyujto', readonly=True, store=True)
  # virtual fields
  ujeszkozok_ids      = fields.One2many('leltar.leltariv_ujeszkoz', 'leltariv_id', u'Új eszközök a leltáríven', states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  eszkozok_ids        = fields.One2many('leltar.leltariv_eszkoz', 'leltariv_id', u'Eszközök a leltáríven', states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  ismeretlen_ids      = fields.One2many('leltar.leltariv_ismeretlen', 'leltariv_id', u'Ismeretlen eszközök a leltáríven', states={'kesz': [('readonly', True)], 'konyvelt': [('readonly', True)]})
  leltariv_osszes_ids = fields.One2many('leltar.leltariv_osszes', 'leltariv_id', u'Összes eszköz a leltáríven', readonly=True)

  @api.model
  def create(self, vals):
    vals['letrehozva'] = fields.Date.today()
    leltarkorzet_id = vals['leltarkorzet_id']
    elozo_leltariv = self.env['leltar.leltariv'].search([('leltarkorzet_id', '=', leltarkorzet_id), ('state', '!=', 'konyvelt')])
    if elozo_leltariv:
      raise exceptions.Warning(elozo_leltariv.leltarkorzet_id.name + u' leltárkörzet már fel van véve!')
    leltariv = super(LeltarLeltariv, self).create(vals)

    eszkozok  = self.env['leltar.eszkoz'].search([('akt_leltarkorzet_id', '=', leltarkorzet_id)])
    for eszkoz in eszkozok:
      self.env['leltar.leltariv_eszkoz'].create({'leltariv_id': leltariv.id, 'eszkoz_id': eszkoz.id})
    return leltariv

  @api.one
  @api.depends('leltarkorzet_id')
  def _compute_name(self):
    self.name = self.leltarkorzet_id.name

  @api.one
  def state2kesz(self):
    if not self.leltarvezeto_id or not self.leltarozo_id:
      raise exceptions.Warning(u'A leltárfelelősöket fel kell venni!')
    self.state  = 'kesz'
    return True

  @api.one
  def state2terv(self):
    self.state  = 'terv'
    return True

############################################################################################################################  Leltárív eszközök  ###
class LeltarLeltarivEszkoz(models.Model):
  _name               = 'leltar.leltariv_eszkoz'
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     readonly=True, auto_join=True)
  fellelheto          = fields.Boolean(u'Fellelhető', default=False)
  serult_cimke        = fields.Boolean(u'Sérült címke', default=False)
  selejtezni          = fields.Boolean(u'Selejtezni', default=False)
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  Leltárív új eszközök  ###
class LeltarLeltarivUjeszkoz(models.Model):
  _name               = 'leltar.leltariv_ujeszkoz'
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     required=True, auto_join=True)
  serult_cimke        = fields.Boolean(u'Sérült címke', default=False)
  selejtezni          = fields.Boolean(u'Selejtezni', default=False)
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  akt_leltarkorzet_id = fields.Many2one('leltar.korzet',  u'Nyilvántartás szerinti leltárkörzet',  related='eszkoz_id.akt_leltarkorzet_id' )

############################################################################################################################  Leltárív leltári számmal nem azonosítható eszközök  ###
class LeltarLeltarivIsmeretlen(models.Model):
  _name               = 'leltar.leltariv_ismeretlen'
  name                = fields.Char(u'Eszköz', compute='_compute_name', store=True)
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)
  kod                 = fields.Char(u'Kód', required=True)
  megnevezes          = fields.Char(u'Megnevezes', required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  state               = fields.Selection([('terv',u'Tervezet'),('kesz',u'Kész'),('konyvelt',u'Könyvelt')], u'Állapot', related='leltariv_id.state' )

  @api.one
  @api.depends('kod', 'megnevezes', 'megjegyzes')
  def _compute_name(self):
    megjegyzes = ', ' + self.megjegyzes if self.megjegyzes else ''
    if self.kod and self.megnevezes:
      self.name = self.kod + ' - ' + self.megnevezes + megjegyzes

############################################################################################################################  Leltárív összes eszköz (generált és új)  ###
class LeltarLeltarivOsszes(models.Model):
  _name               = 'leltar.leltariv_osszes'
  _auto               = False
  _order              = 'eszkoz_id'
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', auto_join=True)
  hianyzo_eszk_gyujto = fields.Boolean(u'Hiányzó eszközök gyűjtő')
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     auto_join=True)
  fellelheto          = fields.Boolean(u'Fellelhető')
  hiany               = fields.Boolean(u'Hiány')
  serult_cimke        = fields.Boolean(u'Sérült címke')
  selejtezni          = fields.Boolean(u'Selejtezni')
  megjegyzes          = fields.Char(u'Megjegyzés')
  leltariv_eszkoz_id  = fields.Integer(u'Leltárív eszköz id')
  leltariv_ujeszkoz_id= fields.Integer(u'Leltárív új eszköz id')
  write_date          = fields.Datetime(u'Módosítás ideje')

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        WITH
          osszes AS (
            SELECT eszkoz.leltariv_id, iv.hianyzo_eszk_gyujto, eszkoz.eszkoz_id, eszkoz.fellelheto, eszkoz.serult_cimke, eszkoz.selejtezni, eszkoz.megjegyzes,
              eszkoz.id AS leltariv_eszkoz_id, 0 AS leltariv_ujeszkoz_id, eszkoz.write_date
            FROM leltar_leltariv_eszkoz AS eszkoz
            JOIN leltar_leltariv AS iv ON iv.id = leltariv_id AND iv.state != 'konyvelt'
            UNION ALL
            SELECT eszkoz.leltariv_id, iv.hianyzo_eszk_gyujto, eszkoz.eszkoz_id, true AS fellelheto, eszkoz.serult_cimke, eszkoz.selejtezni, eszkoz.megjegyzes,
              0 AS leltariv_eszkoz_id, eszkoz.id AS leltariv_ujeszkoz_id, eszkoz.write_date
            FROM leltar_leltariv_ujeszkoz AS eszkoz
            JOIN leltar_leltariv AS iv ON iv.id = leltariv_id AND iv.state != 'konyvelt'
          ),
          talalt AS (
            SELECT DISTINCT eszkoz_id FROM osszes WHERE fellelheto AND NOT hianyzo_eszk_gyujto
          )
        SELECT row_number() over() AS id, osszes.*, NOT EXISTS (SELECT eszkoz_id from talalt WHERE talalt.eszkoz_id = osszes.eszkoz_id) as hiany FROM osszes
      )"""
      % (self._table)
    )

############################################################################################################################  Leltárív új eszközök duplikátumok  ###
class LeltarLeltarivDupla(models.Model):
  _name               = 'leltar.leltariv_dupla'
  _auto               = False
  _order              = 'eszkoz_id'
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     required=True, auto_join=True)
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        WITH
          -- szűrés a generált és fellelhető táblában egyúttal az új táblában is szereplő eszközökre
          dupla AS (
            SELECT eszkoz_id, count(*) FROM leltar_leltariv_osszes WHERE fellelheto GROUP BY eszkoz_id HAVING count(*) > 1
          ),
          -- szűrés az egyazon leltáríven szereplő, generált táblában és az új táblában is szereplő eszközökre
          -- az előző szűrés eredményét kivonjuk
          dupla2 AS (
            SELECT eszkoz_id, leltariv_id, count(*) FROM leltar_leltariv_osszes
            WHERE eszkoz_id NOT IN (SELECT eszkoz_id FROM dupla)
            GROUP BY eszkoz_id, leltariv_id HAVING count(*) > 1
          ),
          result AS (
            SELECT osszes.eszkoz_id, osszes.leltariv_id FROM leltar_leltariv_osszes AS osszes JOIN dupla ON dupla.eszkoz_id = osszes.eszkoz_id
            UNION ALL
            SELECT eszkoz_id, leltariv_id FROM dupla2
          )
          SELECT row_number() over() AS id, eszkoz_id, leltariv_id FROM result
      )"""
      % (self._table)
    )

############################################################################################################################  Leltárív nem fellelhető eszközök  ###
class LeltarLeltarivHiany(models.Model):
  _name               = 'leltar.leltariv_hiany'
  _auto               = False
  _order              = 'eszkoz_id'
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     required=True, auto_join=True)
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        WITH
          -- generált, nem könyvelt és nem fellelhető leltárív eszközök szűrése
          nem_fellelt AS (
            SELECT gen.id, gen.eszkoz_id, gen.leltariv_id FROM leltar_leltariv_eszkoz AS gen
            JOIN leltar_leltariv AS iv ON iv.id = gen.leltariv_id AND iv.state != 'konyvelt'
            WHERE NOT gen.fellelheto
          ),
          -- új és nem könyvelt leltárív eszközök szűrése
          ujak AS (
            SELECT uj.id, uj.eszkoz_id, uj.leltariv_id FROM leltar_leltariv_ujeszkoz AS uj
            JOIN leltar_leltariv AS iv ON iv.id = uj.leltariv_id AND iv.state != 'konyvelt'
          )
          -- a nem fellelt de újak között sem található eszközök szűrése
          SELECT gen.id, gen.eszkoz_id, gen.leltariv_id FROM nem_fellelt AS gen
          LEFT JOIN ujak AS uj ON uj.eszkoz_id = gen.eszkoz_id
          WHERE uj.id IS NULL
      )"""
      % (self._table)
    )

############################################################################################################################  Leltárív új mozgások  ###
class LeltarLeltarivMozgas(models.Model):
  _name               = 'leltar.leltariv_mozgas'
  _auto               = False
  _order              = 'eszkoz_id'
  eszkoz_id           = fields.Many2one('leltar.eszkoz', u'Eszköz',     required=True, auto_join=True)
  leltariv_id         = fields.Many2one('leltar.leltariv', u'Leltárív', required=True, auto_join=True)
  # virtual fields
  akt_leltarkorzet_id = fields.Many2one('leltar.korzet',  u'Nyilvántartás szerinti leltárkörzet',  related='eszkoz_id.akt_leltarkorzet_id' )

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        WITH
          ujak AS (
            SELECT uj.id, uj.eszkoz_id, uj.leltariv_id, iv.create_date FROM leltar_leltariv_ujeszkoz AS uj
            JOIN leltar_leltariv AS iv ON iv.id = uj.leltariv_id AND iv.state != 'konyvelt'
          ),
          kihagy AS (
            SELECT DISTINCT uj.eszkoz_id from ujak AS uj
            JOIN leltar_eszkozmozgas AS mozgas ON mozgas.eszkoz_id = uj.eszkoz_id
            WHERE mozgas.create_date > uj.create_date
          )
        SELECT id, eszkoz_id, leltariv_id from ujak WHERE eszkoz_id NOT IN (SELECT id from kihagy)
      )"""
      % (self._table)
    )
