# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import logging, re
_logger = logging.getLogger(__name__)

def trim(list):
  ret = []
  for elem in list:
    if type(elem)==unicode or type(elem)==str: ret.append(elem.strip())
    else: ret.append(elem)
  return ret

class LeltarParameter(models.Model):
  _inherit  = 'szefo.parameter'

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
      if eszkoz: eszkoz.write({'netto_ertek': netto_ertek})
      row = cursor.fetchone()
    return True

#  @api.one
#  def import_eszkoz(self):
#    import pymssql
#    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='DominoSoft')
#
#    Eszkoz  = self.env['leltar.eszkoz']
#    Csoport = self.env['leltar.csoport']
#    Korzet  = self.env['leltar.korzet']
#    Log     = self.env['szefo.log']
#    Log.create({'loglevel': 'info', 'name': u'Eszköz import', 'module': 'leltar'})
#
#    ut_hivszam = Eszkoz.search([], limit=1, order='hivszam desc').hivszam
#    if not ut_hivszam: ut_hivszam = 0
#    cursor = mssql_conn.cursor()
#    cursor.execute("""SELECT hivszam, bf_lelt, bf_megnev, bf_ltkorzet, bf_ltfelelos, bf_ltcsoport, bf_param, bf_vonalkod FROM DominoSoft.dbo.beftorzs
#                      WHERE hivszam > %s AND targyev = 2015 AND bf_vonalkod > 0 AND status = 0 order by hivszam""" % ut_hivszam)
#    row = cursor.fetchone()
#    while row:
#      leltarcsoport_id    = None
#      leltarkorzet_kod    = None
#      akt_hasznalo_id     = None
#      akt_leltarkorzet_id = None
#      hivszam, leltari_szam, megnevezes, ds_leltarkorzet, ds_leltarfelelos, csoportkod, megjegyzes, leltari_szam_vonalkod = trim(row)
#
#      csoport_ids = Csoport.search_read([('csoportkod', '=', csoportkod)])
#      if csoport_ids: leltarcsoport_id = csoport_ids[0]['id']
#
#      korzet_ids = Korzet.search_read([('ds_leltarkorzet', '=', ds_leltarkorzet)])
#      if len(korzet_ids) == 1:
#        akt_leltarkorzet_id = korzet_ids[0]['id']
#        leltarkorzet_kod    = korzet_ids[0]['leltarkorzet_kod']
#
#      Eszkoz.create({'name': leltari_szam+' - '+megnevezes, 'hivszam': hivszam, 'leltari_szam': leltari_szam, 'megnevezes': megnevezes,
#        'leltarcsoport_id': leltarcsoport_id, 'akt_leltarkorzet_id': akt_leltarkorzet_id, 'akt_hasznalo_id': akt_hasznalo_id,
#        'leltarkorzet_kod': leltarkorzet_kod, 'csoportkod': csoportkod, 'leltari_szam_vonalkod': leltari_szam_vonalkod, 'megjegyzes': megjegyzes,
#        'ds_leltarkorzet': ds_leltarkorzet, 'ds_leltarfelelos': ds_leltarfelelos })
#      row = cursor.fetchone()
#
#    return True

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
    cursor.execute("""SELECT hivszam, bf_lelt, bf_megnev, bf_ltkorzet, bf_ltfelelos, bf_ltcsoport, bf_param, bf_vonalkod
                      FROM DominoSoft.dbo.beftorzs WHERE targyev = 2017 AND status = 0 AND bf_kiido IS NULL order by hivszam""")
    row = cursor.fetchone()
    while row:
      leltarcsoport_id    = None
      leltarkorzet_kod    = None
      akt_hasznalo_id     = None
      akt_leltarkorzet_id = None
      hivszam, leltari_szam, megnevezes, ds_leltarkorzet, ds_leltarfelelos, csoportkod, megjegyzes, leltari_szam_vonalkod = trim(row)
      if not Eszkoz.search_count(['|', ('active', '=', True), ('active', '=', False), ('leltari_szam', '=', leltari_szam)]):

        csoport_ids = Csoport.search_read([('csoportkod', '=', csoportkod)])
        if csoport_ids: leltarcsoport_id = csoport_ids[0]['id']

        korzet_ids = Korzet.search_read([('ds_leltarkorzet', '=', ds_leltarkorzet)])
        if len(korzet_ids) == 1:
          akt_leltarkorzet_id = korzet_ids[0]['id']
          leltarkorzet_kod    = korzet_ids[0]['leltarkorzet_kod']

        Eszkoz.create({'name': leltari_szam+' - '+megnevezes, 'hivszam': hivszam, 'leltari_szam': leltari_szam, 'megnevezes': megnevezes,
          'leltarcsoport_id': leltarcsoport_id, 'akt_leltarkorzet_id': akt_leltarkorzet_id, 'akt_hasznalo_id': akt_hasznalo_id,
          'leltarkorzet_kod': leltarkorzet_kod, 'csoportkod': csoportkod, 'leltari_szam_vonalkod': leltari_szam_vonalkod, 'megjegyzes': megjegyzes,
          'ds_leltarkorzet': ds_leltarkorzet, 'ds_leltarfelelos': ds_leltarfelelos })
      row = cursor.fetchone()
    return True

  @api.one
  def import_felmeres(self):
    import pymssql
    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='DominoSoft')

    Leltar = self.env['leltar.leltar']
    Eszkoz = self.env['leltar.eszkoz']
    Korzet = self.env['leltar.korzet']
    Mozgas = self.env['leltar.eszkozmozgas']
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Leltár felmérés import', 'module': 'leltar'})

    ut_hivszam = Leltar.search([], limit=1, order='hivszam desc').hivszam
    if not ut_hivszam: ut_hivszam = 0
    cursor = mssql_conn.cursor()
    cursor.execute("""SELECT hsz, targyev, targyho, lt_bfvonalkod, lt_blvonalkod, lt_szobaszam, ervkezdet FROM DominoSoft.dbo.befleltar
                      WHERE hsz > %s ORDER BY hsz""" % ut_hivszam)
    row = cursor.fetchone()
    while row:
      eszkoz_id = None
      leltarkorzet_id = None
      hivszam, targyev, targyho, leltari_szam_vonalkod, leltarkorzet_vonalkod, szobaszam, ervenyesseg_kezdete = trim(row)
      eszkoz_ids = Eszkoz.search_read([('leltari_szam_vonalkod', '=', leltari_szam_vonalkod)])
      if eszkoz_ids:
        eszkoz_id = eszkoz_ids[0]['id']
        csoportkod = eszkoz_ids[0]['csoportkod']
        akt_leltarkorzet = eszkoz_ids[0]['akt_leltarkorzet_id']
        if akt_leltarkorzet:
          akt_leltarkorzet_id = akt_leltarkorzet[0]
        else:
          akt_leltarkorzet_id = False
      korzet_ids = Korzet.search_read([('leltarkorzet_kod', '=', leltarkorzet_vonalkod)])
#      korzet_ids = Korzet.search_read([('leltarkorzet_kod', '=', leltarkorzet_vonalkod), ('szobaszam', '=', szobaszam)])
      if korzet_ids: leltarkorzet_id = korzet_ids[0]['id']
      if eszkoz_id and leltarkorzet_id:
        Leltar.create({'eszkoz_id': eszkoz_id, 'leltarkorzet_id': leltarkorzet_id, 'hivszam': hivszam,
          'targyev': targyev, 'targyho': targyho, 'leltari_szam_vonalkod': leltari_szam_vonalkod,
          'leltarkorzet_vonalkod': leltarkorzet_vonalkod, 'szobaszam': szobaszam, 'ervenyesseg_kezdete': ervenyesseg_kezdete})
        if akt_leltarkorzet_id != leltarkorzet_id and csoportkod != '005':
          Mozgas.create({'eszkoz_id': eszkoz_id, 'honnan_leltarkorzet_id': akt_leltarkorzet_id,
                        'hova_leltarkorzet_id': leltarkorzet_id, 'megerkezett': True, 'megjegyzes': 'leltár' })
      else:
        Log.create({'loglevel': 'error', 'name': u'Sikertelen import', 'module': 'DominoSoft', 'table': 'befleltar', 'rowid': hivszam})
      row = cursor.fetchone()
    return True

class LeltarDsFelelos(models.Model):
  _name       = 'leltar.ds_felelos'
  bl_kod      = fields.Char(u'Kód',  required=True)
  bl_megnev   = fields.Char(u'Megnevezés',  required=True)
  SzemelyId   = fields.Integer(u'SzemelyId',  required=True)
  employee_id = fields.Integer(u'Employee id')

class LeltarCsoport(models.Model):
  _name       = 'leltar.csoport'
  name        = fields.Char(u'Leltárcsoport név',  required=True)
  csoportkod  = fields.Char(u'Leltárcsoport kód',  required=True)
  active      = fields.Boolean(u'Aktív?',  default=True)

class LeltarTulajdonsag(models.Model):
  _name       = 'leltar.tulajdonsag'
  name        = fields.Char(u'Tulajdonság',  required=True)

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
  ds_leltarkorzet     = fields.Char(u'DS Leltárkörzet',  required=True)
  ds_korzet_vonalkod  = fields.Char(u'DS Leltárkörzet vonalkód',   required=True)
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

class LeltarEszkoz(models.Model):
  _name                 = 'leltar.eszkoz'
  name                  = fields.Char(u'Eszköz',  required=True)
  hivszam               = fields.Integer(u'Hiv.szám',  required=True, index=True)
  leltari_szam          = fields.Char(u'Leltári szám',   required=True, index=True)
  megnevezes            = fields.Char(u'Eszköz név',   required=True)
  akt_leltarkorzet_id   = fields.Many2one('leltar.korzet',  u'Aktuális leltárkörzet')
  akt_hasznalo_id       = fields.Many2one('hr.employee',    u'Aktuális használó')
  leltarcsoport_id      = fields.Many2one('leltar.csoport', u'Leltárcsoport')
  szett_id              = fields.Many2one('leltar.szett', u'Eszköz szett')
  csoportkod            = fields.Char(u'Leltárcsoport kód',  required=True)
  leltari_szam_vonalkod = fields.Char(u'Leltári szám vonalkód',   required=True)
  megjegyzes            = fields.Char(u'Megjegyzés')
  leltarkorzet_kod      = fields.Char(u'DS <-> Leltárkörzet kód')
  ds_leltarkorzet       = fields.Char(u'DS Leltárkörzet',  required=True)
  ds_leltarfelelos      = fields.Char(u'DS Leltárfelelős')
  netto_ertek           = fields.Integer(u'Nettó érték')
  selejt_ok             = fields.Char(u'Selejtezés oka')
  selejtezni            = fields.Boolean(u'Selejtezni', default=False)
  zarolva               = fields.Boolean(u'Zárolva?', default=False)
  active                = fields.Boolean(u'Aktív?',  default=True)
  # virtual fields
  not_active            = fields.Boolean(u'Nem aktív?', compute='_compute_not_active')
  mozgas_ids            = fields.One2many('leltar.eszkozmozgas', 'eszkoz_id', u'Eszköz mozgások')
  tulajdonsag_ids       = fields.Many2many('leltar.tulajdonsag', string=u'Tulajdonságok')
#  selejtezni_dup        = fields.Boolean(u'Selejtezni', compute='_compute_selejtezni_dup')
#
#  @api.one
#  @api.depends('selejtezni')
#  def _compute_selejtezni_dup(self):
#    self.selejtezni_dup = self.selejtezni

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
    eszkoz    = self.env['leltar.eszkoz'].search([('id', '=', eszkoz_id)])[0]
    honnan_id = eszkoz.akt_leltarkorzet_id.id
    hova_id   = vals['hova_leltarkorzet_id']
    honnan    = self.env['leltar.korzet'].search([('id', '=', honnan_id)])[0]
    hova      = self.env['leltar.korzet'].search([('id', '=', hova_id)])[0]
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

class LeltarEszkozatvetel(models.Model):
  _name                 = 'leltar.eszkozatvetel'
  _order                = 'id desc'
  eszkoz_id             = fields.Many2one('leltar.eszkoz', u'Eszköz',  required=True, auto_join=True)
  akt_hasznalo_id       = fields.Many2one('hr.employee',   u'Aktuális használó',  related='eszkoz_id.akt_hasznalo_id' )
  uj_hasznalo_id        = fields.Many2one('hr.employee',   u'Új használó',  required=False )
  megjegyzes            = fields.Char(u'Megjegyzés')
  eszkoz_megjegyzes     = fields.Char(u'Eszköz megjegyzés',  related='eszkoz_id.megjegyzes' )

  def create(self, cr, uid, vals, context=None):
    vals['akt_hasznalo_id']   = vals['uj_hasznalo_id']
    if vals['megjegyzes']: vals['eszkoz_megjegyzes'] = vals['megjegyzes']
    return super(LeltarEszkozatvetel, self).create(cr, uid, vals, context=context)


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
