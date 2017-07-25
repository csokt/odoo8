# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions
import datetime, hashlib, pymongo
from legrand_proc import pub, log, calc_cikkek_uid

############################################################################################################################  Hely  ###
class LegrandHely(models.Model):
  _name               = 'legrand.hely'
  _order              = 'sorrend'
  name                = fields.Char(u'Megnevezés')
  nev                 = fields.Char(u'Név')
  telepules           = fields.Char(u'Település')
  cim                 = fields.Char(u'Cím')
  azonosito           = fields.Char(u'Belső azonosító')
  sorrend             = fields.Integer(u'Sorrend')
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?')        # A SZEFO készletbe beszámít-e ez a hely?
  legrand_e           = fields.Boolean(u'Legrand készletbe számít?')      # A Legrand készletbe beszámít-e ez a hely?
  szefo_szallitas_e   = fields.Boolean(u'Legrand-SZEFO szállítás?')       # A Legrand és a SZEFO közötti a mozgás?
  belso_szallitas_e   = fields.Boolean(u'SZEFO belső szállítás?')         # SZEFO-n belüli a mozgás?

  uzem_raktar_e       = fields.Boolean(u'Üzem raktár választás?')
  uzem_helyi_raktar_e = fields.Boolean(u'Üzem helyi raktár?')
  active              = fields.Boolean(u'Aktív?', default=True)

############################################################################################################################  Cikk  ###
class LegrandCikk(models.Model):
  _name               = 'legrand.cikk'
  _order              = 'cikkszam'
  _rec_name           = 'cikkszam'
#  name                = fields.Char(u'Név',      compute='_compute_name', store=True)
  cikkszam            = fields.Char(u'Cikkszám', required=True)
  cikknev             = fields.Char(u'Cikknév',  required=True)
  alkatresz_e         = fields.Boolean(u'Alkatrész?',   default=False)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár',  digits=(16, 3))
  beepulok_ids        = fields.Many2many('legrand.bom', string=u'Beépülők', domain=[('beepul_e', '=', True)])
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  keszlet             = fields.Float(u'Készlet',   digits=(16, 2), compute='_compute_keszlet')
  lefoglalt           = fields.Float(u'Lefoglalt', digits=(16, 2), compute='_compute_lefoglalt')
  muvelet_ids         = fields.One2many('legrand.muvelet',      'cikk_id',    u'Műveletek')
  lezer_tampon_ids    = fields.One2many('legrand.lezer_tampon', 'termek_id',  u'Lézer, tampon')
  feljegyzes_ids      = fields.One2many('legrand.feljegyzes',   'cikk_id',    u'Feljegyzések')

  @api.one
  @api.depends()
  def _compute_keszlet(self):
    self.keszlet = self.env['legrand.vall_keszlet'].search([('cikk_id', '=', self.id)], limit=1).szefo_keszlet

  @api.one
  @api.depends()
  def _compute_lefoglalt(self):
    self.lefoglalt = self.env['legrand.lefoglalt'].search([('cikk_id', '=', self.id)], limit=1).lefoglalt

############################################################################################################################  Bom  ###
class LegrandBom(models.Model):
  _name               = 'legrand.bom'
  _order              = 'name'
  name                = fields.Char(u'Név',           compute='_compute_name', store=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikkszám', index=True, required=True)
  verzio              = fields.Char(u'Verzió',        required=True)
  gylap_default_e     = fields.Boolean(u'Gy.lap alapértelmezett?', default=False)
  beepul_e            = fields.Boolean(u'Beépül?',    default=False)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)
  cikkek_uid          = fields.Char(u'Összes alkatrész uid', compute='_compute_cikkek_uid')
  bom_line_ids        = fields.One2many('legrand.bom_line', 'bom_id', u'Anyagjegyzék sorok')
  mozgassor_ids       = fields.One2many('legrand.mozgassor', 'bom_id', u'Szállítás sorok', readonly=True)
  count_mozgassor_ids = fields.Integer(u'Szállítás sorok db', compute='_compute_count_mozgassor_ids')
  admin_e             = fields.Boolean(u'Admin?', compute='_check_user_group')
  legrand_admin_e     = fields.Boolean(u'Legrand admin?', compute='_check_user_group')
  # temporary fields
  raktar_gylap_id     = fields.Integer(u'Gyártási lap sorszám')


  @api.one
  @api.depends('cikk_id', 'verzio')
  def _compute_name(self):
    if self.cikk_id and self.verzio:
      self.name = self.cikk_id.cikkszam+' '+self.verzio

  @api.one
  @api.depends('bom_line_ids')
  def _compute_cikkek_uid(self):
    self.cikkek_uid = calc_cikkek_uid(self.bom_line_ids, 'cikkszam')

  @api.one
  @api.depends('mozgassor_ids')
  def _compute_count_mozgassor_ids(self):
    self.count_mozgassor_ids = len(self.mozgassor_ids)

  @api.one
  def _check_user_group(self):
    self.admin_e = self.env.user.has_group('base.group_system')
    self.legrand_admin_e = self.env.user.has_group('legrand.group_legrand_admin')

  @api.one
  def import_impex(self):
    for impex in self.env['legrand.impex'].search([]):
      sor_row = {
        'bom_id'            : self.id,
        'cikk_id'           : impex.cikk_id.id,
        'beepules'          : impex.ertek,
      }
      self.env['legrand.bom_line'].create(sor_row)
    return True

  @api.one
  def export_impex(self):
    self.env['legrand.impex'].search([]).unlink()
    for alk in self.bom_line_ids:
      impex_row = {
        'cikk_id'         : alk.cikk_id.id,
        'ertek'           : alk.beepules,
      }
      self.env['legrand.impex'].create(impex_row)
    return True

############################################################################################################################  Bom line  ###
class LegrandBomLine(models.Model):
  _name               = 'legrand.bom_line'
  _order              = 'id'
  _rec_name           = 'cikk_id'
#  name                = fields.Char(u'Név',      compute='_compute_name', store=True)
  bom_id              = fields.Many2one('legrand.bom',  u'BOM', index=True, required=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', index=True, required=True)
  beepules            = fields.Float(u'Beépülés', digits=(16, 8), required=True)
  # virtual fields
  cikkszam            = fields.Char(u'Cikkszám',        related='cikk_id.cikkszam', readonly=True)
  cikknev             = fields.Char(u'Alkatrész neve',  related='cikk_id.cikknev',  readonly=True)

#  @api.one
#  @api.depends('bom_id', 'cikk_id')
#  def _compute_name(self):
#    if self.bom_id and self.cikk_id:
#      self.name = self.cikk_id.cikkszam+' ('+self.bom_id.name+')'

############################################################################################################################  Hibakód  ###
class LegrandHibakod(models.Model):
  _name               = 'legrand.hibakod'
  _order              = 'kod'
  name                = fields.Char(u'Megnevezés', compute='_compute_name', store=True)
  kod                 = fields.Char(u'Hibakód', required=True)
  nev                 = fields.Char(u'Név', required=True)
  active              = fields.Boolean(u'Aktív?', default=True)

  @api.one
  @api.depends('kod', 'nev')
  def _compute_name(self):
    if self.kod and self.nev: self.name = self.kod+' - '+self.nev

############################################################################################################################  Mozgásfej  ###
class LegrandMozgasfej(models.Model):
  _name               = 'legrand.mozgasfej'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                        u'Állapot', default='terv', readonly=False )
  mozgasnem           = fields.Selection([('be',u'Alkatrész bevételezés'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('helyesbit',u'Készlethelyesbítés'),('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt visszaszállítás')],
                                          u'Mozgásnem', required=True, default=lambda self: self.env.context.get('mozgasnem', ''))
  forrashely_id       = fields.Many2one('legrand.hely', u'Forráshely', index=True)
  celallomas_id       = fields.Many2one('legrand.hely', u'Célállomás helye', index=True)
  forrasdokumentum    = fields.Char(u'Forrásdokumentum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  mozgassor_ids       = fields.One2many('legrand.mozgassor', 'mozgasfej_id', u'Tételek')

  @api.model
  def create(self, vals):
    forrdict = {'be': 'legrand', 'ki': 'depo',    'vissza': 'depo',    'selejt': 'selejt'}
    celdict  = {'be': 'depo',    'ki': 'legrand', 'vissza': 'legrand', 'selejt': 'legrand'}
    if vals['mozgasnem']   == 'helyesbit':
      vals['forrashely_id'] = self.env['legrand.hely'].search([('azonosito', '=', 'legrand')]).id
    elif vals['mozgasnem'] != 'belso':
      forr_id = self.env['legrand.hely'].search([('azonosito', '=', forrdict[vals['mozgasnem']])]).id
      cel_id  = self.env['legrand.hely'].search([('azonosito', '=', celdict[vals['mozgasnem']])]).id
      vals['forrashely_id'], vals['celallomas_id'] = forr_id, cel_id
    return super(LegrandMozgasfej, self).create(vals)

  @api.one
  def import_impex(self):
    for impex in self.env['legrand.impex'].search([]):
      sor_row = {
        'mozgasfej_id'      : self.id,
        'gyartasi_lap_id'   : impex.gyartasi_lap_id.id,
        'cikk_id'           : impex.cikk_id.id,
        'bom_id'            : impex.bom_id.id,
        'mennyiseg'         : impex.mennyiseg,
        'hibakod_id'        : impex.hibakod_id.id,
        'megjegyzes'        : impex.megjegyzes,
      }
      self.env['legrand.mozgassor'].create(sor_row)
    return True

  @api.one
  def export_impex(self):
    self.env['legrand.impex'].search([]).unlink()
    for sor in self.mozgassor_ids:
      impex_row = {
        'gyartasi_lap_id' : sor.gyartasi_lap_id.id,
        'cikk_id'         : sor.cikk_id.id,
        'bom_id'          : sor.bom_id.id,
        'mennyiseg'       : sor.mennyiseg,
        'hibakod_id'      : sor.hibakod_id.id,
        'megjegyzes'      : sor.megjegyzes,
      }
      self.env['legrand.impex'].create(impex_row)
    return True

  @api.one
  def veglegesites(self):
    if not self.mozgassor_ids:
      raise exceptions.Warning(u'Nincs véglegesíthető mozgás!')
    if self.forrashely_id == self.celallomas_id:
      raise exceptions.Warning(u'A forrás és célállomás helye megegyezik!')
    self.state = 'szallit' if self.mozgasnem == 'belso' else 'kesz'
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
    if self.mozgasnem == 'ki':
      for sor in self.mozgassor_ids:
        if sor.gyartasi_lap_id and sor.gyartasi_lap_id.state != 'konyvelt':
          sor.gyartasi_lap_id.teljesitett_db += sor.mennyiseg
          if sor.gyartasi_lap_id.teljesitett_db >= sor.gyartasi_lap_id.modositott_db:
            sor.gyartasi_lap_id.state = 'gykesz'
    self.state  = 'konyvelt'
    return True

############################################################################################################################  Mozgássor  ###
class LegrandMozgassor(models.Model):
  _name               = 'legrand.mozgassor'
  _order              = 'id'
  _rec_name           = 'cikk_id'
  mozgasfej_id        = fields.Many2one('legrand.mozgasfej',  u'Mozgásfej', index=True)
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám', index=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', index=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  hibakod_id          = fields.Many2one('legrand.hibakod', u'Hibakód')
  megjegyzes          = fields.Char(u'Megjegyzés', default=lambda self: 'helyesbít' if self.env.context.get('mozgasnem', '') == 'helyesbit' else '')
  # computed fields
  mozgasfej_sorszam   = fields.Integer(u'Sz.lev.')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', compute='_compute_cikknev')
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                                        u'Állapot',  related='mozgasfej_id.state')
  mozgasnem           = fields.Selection([('be',u'Alkatrész bevételezés'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('helyesbit',u'Készlethelyesbítés'),('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt visszaszállítás')],
                                          u'Mozgásnem',  related='mozgasfej_id.mozgasnem')
  forrashely_id       = fields.Many2one('legrand.hely', u'Forráshely',       related='mozgasfej_id.forrashely_id')
  celallomas_id       = fields.Many2one('legrand.hely', u'Célállomás helye', related='mozgasfej_id.celallomas_id')

  @api.model
  def create(self, vals):
    new = super(LegrandMozgassor, self).create(vals)
    new.mozgasfej_sorszam = new.mozgasfej_id.id
    return new

  @api.multi
  def unlink(self):
    if self.state != 'terv':
      raise exceptions.Warning(u'Törölni csak Tervezet állapotban lehet!')
    return super(LegrandMozgassor, self).unlink()

  @api.one
  @api.depends('cikk_id', 'bom_id')
  def _compute_cikknev(self):
    self.cikknev = self.cikk_id.cikknev if self.cikk_id else self.bom_id.cikk_id.cikknev

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    if self.mozgasfej_id.mozgasnem == 'ki':
      self.bom_id = self.gyartasi_lap_id.bom_id
    else:
      self.cikk_id = False
      cikk_ids = self.gyartasi_lap_id.bom_id.bom_line_ids.mapped('cikk_id.id')
      bom_ids  = self.gyartasi_lap_id.bom_id.cikk_id.beepulok_ids.mapped('id')
      cikk_domain = [('id','in',cikk_ids)] if self.gyartasi_lap_id else []
      bom_domain  = [('id','in',bom_ids)]  if self.gyartasi_lap_id else []
      return {'domain': {'cikk_id': cikk_domain, 'bom_id': bom_domain}}

  @api.onchange('cikk_id')
  def onchange_cikk_id(self):
    self.bom_id = False

  @api.onchange('bom_id')
  def onchange_bom_id(self):
    self.cikk_id = False

############################################################################################################################  Anyagigénylés  ###
class LegrandAnyagigeny(models.Model):
  _name               = 'legrand.anyagigeny'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('uj',u'Új igény'),('nyugta',u'Nyugtázva')], u'Állapot', default='terv', readonly=True)
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám',                                                          readonly=True, states={'terv': [('readonly', False)]})
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap',                                             readonly=True, states={'terv': [('readonly', False)]})
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True,                                             readonly=True, states={'terv': [('readonly', False)]})
  hely_id             = fields.Many2one('legrand.hely', u'Üzem', domain=[('belso_szallitas_e', '=', True)],                   readonly=True, states={'terv': [('readonly', False)]}, required=True)
  igeny_ok            = fields.Selection([('hiany',u'hiánypótlás'),('selejt',u'selejtpótlás')], 'Kérés oka', default='hiany', readonly=True, states={'terv': [('readonly', False)]}, required=True)
  megjegyzes          = fields.Char(u'Megjegyzés',                                                                            states={'nyugta': [('readonly', True)]})
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.cikk_id = False
    ids = self.gyartasi_lap_id.bom_id.bom_line_ids.mapped('cikk_id.id')
    domain = [('id','in',ids)] if self.gyartasi_lap_id else []
    return {'domain': {'cikk_id': domain}}

  @api.one
  def veglegesites(self):
    self.state = 'uj'
    return True

  @api.one
  def state2nyugta(self):
    self.state = 'nyugta'
    return True

############################################################################################################################  Készlet  ###
class LegrandKeszlet(models.Model):
  _name = 'legrand.keszlet'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id, hely_id'
#  bom_id              = fields.Many2one('legrand.bom',  u'Termék', readonly=True)
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True)
  hely_id             = fields.Many2one('legrand.hely', u'Raktárhely', readonly=True)
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?', readonly=True)
  legrand_e           = fields.Boolean(u'Legrand készletbe számít?', readonly=True)
  raktaron            = fields.Float(string=u'Raktáron', readonly=True)
  varhato             = fields.Float(string=u'Előrejelzés', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          row_number() over() AS id,
          cikk_id,
          hely_id,
          szefo_e,
          legrand_e,
          sum(CASE WHEN raktaron_e THEN mennyiseg ELSE 0.0 END) AS raktaron,
          sum(mennyiseg) AS varhato
        FROM (
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          WHERE cikk_id > 0
          UNION ALL
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          WHERE cikk_id > 0
          UNION ALL
          SELECT line.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg*line.beepules AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0
          UNION ALL
          SELECT line.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg*line.beepules AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0
        ) AS move
        GROUP BY cikk_id, hely_id, szefo_e, legrand_e
      )"""
      % (self._table)
    )

############################################################################################################################  Vállalati készlet  ###
class LegrandVallKeszlet(models.Model):
  _name = 'legrand.vall_keszlet'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True)
  szefo_keszlet       = fields.Float(string=u'SZEFO készlet', readonly=True)
  legrand_keszlet     = fields.Float(string=u'Legrand készlet', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          cikk_id AS id,
          cikk_id,
          sum(CASE WHEN szefo_e   AND raktaron_e THEN  mennyiseg ELSE 0.0 END) AS szefo_keszlet,
          sum(CASE WHEN legrand_e AND raktaron_e THEN -mennyiseg ELSE 0.0 END) AS legrand_keszlet
        FROM (
          SELECT sor.cikk_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          WHERE cikk_id > 0 AND mozgasnem != 'belso'
          UNION ALL
          SELECT sor.cikk_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          WHERE cikk_id > 0 AND mozgasnem != 'belso'
          UNION ALL
          SELECT line.cikk_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg*line.beepules AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0 AND mozgasnem != 'belso'
          UNION ALL
          SELECT line.cikk_id, hely.szefo_e, hely.legrand_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg*line.beepules AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0 AND mozgasnem != 'belso'
        ) AS move
        GROUP BY cikk_id
      )"""
      % (self._table)
    )

############################################################################################################################  Lefoglalt  ###
class LegrandLefoglalt(models.Model):
  _name = 'legrand.lefoglalt'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True)
  lefoglalt           = fields.Float(string=u'Lefoglalt', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          cikk_id AS id,
          cikk_id,
          sum(mennyiseg) AS lefoglalt
        FROM (
          SELECT
            line.cikk_id,
            gylap.hatralek_db * line.beepules AS mennyiseg
          FROM legrand_gyartasi_lap AS gylap
          JOIN legrand_bom_line     AS line ON line.bom_id = gylap.bom_id
          WHERE gylap.state = 'gyartas' AND gylap.hatralek_db != 0
        ) AS gyartas
        GROUP BY cikk_id
      )"""
      % (self._table)
    )

############################################################################################################################  Cikk készlet  ###
class LegrandCikkKeszlet(models.Model):
  _name = 'legrand.cikk_keszlet'
  _auto = False
  _rec_name = 'cikkszam'
  _order = 'cikkszam'
  cikkszam            = fields.Char(u'Cikkszám', required=True)
  cikknev             = fields.Char(u'Cikknév',  required=True)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3))
  keszlet             = fields.Float(u'Készlet',   digits=(16, 2))
  lefoglalt           = fields.Float(u'Lefoglalt', digits=(16, 2))
  elerheto            = fields.Float(u'Elérhető',  digits=(16, 2))

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          cikk.id,
          cikk.id AS cikk_id,
          cikkszam,
          cikknev,
          bekerulesi_ar,
          szefo_keszlet AS keszlet,
          lefoglalt,
          CASE WHEN szefo_keszlet IS NULL THEN 0 ELSE szefo_keszlet END - CASE WHEN lefoglalt IS NULL THEN 0 ELSE lefoglalt END AS elerheto
        FROM legrand_cikk AS cikk
        LEFT JOIN legrand_vall_keszlet AS keszlet ON keszlet.cikk_id = cikk.id
        LEFT JOIN legrand_lefoglalt AS foglalt ON foglalt.cikk_id = cikk.id
        WHERE active
      )"""
      % (self._table)
    )

############################################################################################################################  Homogén  ###
class LegrandHomogen(models.Model):
  _name               = 'legrand.homogen'
  _rec_name           = 'homogen'
  _order              = 'homogen'
  homogen             = fields.Char(u'Homogén', required=True, readonly=True)
  homogennev          = fields.Char(u'Név')
  sajat_homogen       = fields.Boolean(u'Saját homogén?', default=False)

############################################################################################################################  Művelet  ###
class LegrandMuvelet(models.Model):
  _name               = 'legrand.muvelet'
  _order              = 'cikk_id, muveletszam'
  name                = fields.Char(u'Művelet', compute='_compute_name', store=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Termék', readonly=True)
  muveletszam         = fields.Integer(u'Műveletszám', required=True)
  muveletnev          = fields.Char(u'Műveletnév', required=True)
  fajlagos_db         = fields.Integer(u'Fajlagos db', default = 1, required=True)
  normaora            = fields.Float(u'Normaóra', digits=(16, 8), required=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), required=True)
  # virtual fields

  @api.one
  @api.depends('cikk_id', 'muveletszam')
  def _compute_name(self):
    if self.cikk_id and self.muveletszam and self.muveletnev:
      self.name = str(self.cikk_id.cikkszam)+' '+str(self.muveletszam)+' '+self.muveletnev

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
  modositott_db       = fields.Integer(u'Módosított rendelés')
  kiadas_ideje        = fields.Char(u'Kiadás ideje', readonly=True)
  hatarido_str        = fields.Char(u'Határidő (eredeti)', required=True, readonly=True)
  hatarido            = fields.Date(u'Határidő')
  teljesitett_db      = fields.Integer(u'Teljesített db', default=0)
  szamlazott_db       = fields.Integer(u'Számlázott db', default=0)
  szamlazhato_db      = fields.Integer(u'Számlázható db', compute='_compute_szamlazhato_db', store=True)
  hatralek_db         = fields.Integer(u'Hátralék db', compute='_compute_hatralek_db', store=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Termék', required=True, readonly=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', required=False, domain="[('cikk_id', '=', cikk_id)]")
  cikkek_uid          = fields.Char(u'Összes cikk uid', readonly=False)
  gyartasi_hely_ids   = fields.Many2many('legrand.hely', string=u'Fő gyártási helyek', domain=[('szefo_e', '=', True)])
  javitas_e           = fields.Boolean(u'Javítás?', default=False)
  raklap              = fields.Char(u'raklap',      readonly=True)
  raklap_min          = fields.Char(u'raklap_min',  readonly=True)
  raklap_max          = fields.Char(u'raklap_max',  readonly=True)
  rakat_tipus         = fields.Char(u'rakat_tipus', readonly=True)
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  rendelt_ora         = fields.Float(u'Rendelt óra', digits=(16, 2), compute='_compute_rendelt_ora')
  teljesitett_ora     = fields.Float(u'Teljesített óra', digits=(16, 2), compute='_compute_teljesitett_ora')
  utolso_feljegyzes   = fields.Char(u'Utolsó feljegyzés', compute='_compute_utolso_feljegyzes')
  check_cikkek_uid    = fields.Char(u'Ellenőrzés', compute='_compute_check_cikkek_uid')
  cikkhiany           = fields.Char(u'Cikkhiány', compute='_compute_cikkhiany')
  cikkhiany_count     = fields.Integer(u'Cikkhiány', compute='_compute_cikkhiany')
  szefo_muvelet_ids   = fields.One2many('legrand.gylap_szefo_muvelet',  'gyartasi_lap_id', u'Szefo műveletek',      readonly=True,  states={'uj': [('readonly', False)]})
  lezer_tampon_ids    = fields.One2many('legrand.lezer_tampon',         'termek_id',       u'Lézer, tampon',        readonly=True,  related='cikk_id.lezer_tampon_ids')
  gylap_homogen_ids   = fields.One2many('legrand.gylap_homogen',        'gyartasi_lap_id', u'Homogén',              states={'kesz': [('readonly', True)]})
  gylap_dbjegyzek_ids = fields.One2many('legrand.gylap_dbjegyzek',      'gyartasi_lap_id', u'Legrand darabjegyzék', readonly=True)
  gylap_muvelet_ids   = fields.One2many('legrand.gylap_legrand_muvelet','gyartasi_lap_id', u'Műveleti utasítás',    readonly=True)

  @api.one
  @api.depends('rendelesszam', 'cikk_id')
  def _compute_name(self):
    self.name = str(self.id)+' '+self.rendelesszam+' -> '+self.cikk_id.cikkszam

  @api.one
  @api.depends('teljesitett_db', 'szamlazott_db')
  def _compute_szamlazhato_db(self):
    self.szamlazhato_db = self.teljesitett_db - self.szamlazott_db

  @api.one
  @api.depends('modositott_db', 'teljesitett_db')
  def _compute_hatralek_db(self):
    self.hatralek_db = self.modositott_db - self.teljesitett_db

  @api.one
  @api.depends('gylap_homogen_ids')
  def _compute_rendelt_ora(self):
    self.rendelt_ora = sum(map(lambda r: r.ossz_ido+r.beall_ido, self.gylap_homogen_ids.filtered('sajat')))

  @api.one
  @api.depends('rendelt_ora', 'teljesitett_db', 'rendelt_db')
  def _compute_teljesitett_ora(self):
    self.teljesitett_ora = self.rendelt_ora * self.teljesitett_db / self.rendelt_db

  @api.one
  @api.depends('cikk_id')
  def _compute_utolso_feljegyzes(self):
    self.utolso_feljegyzes = self.env['legrand.feljegyzes'].search([('gyartasi_lap_id', '=', self.id)], limit=1, order='id desc').feljegyzes

  @api.one
  @api.depends('bom_id')
  def _compute_check_cikkek_uid(self):
    if len(self.bom_id):
      if self.cikkek_uid == self.bom_id.cikkek_uid:
        self.check_cikkek_uid = 'OK'
      else:
#        self.check_cikkek_uid = u'A darabjegyzék és a műveletterv anyaglista eltér!'
        self.check_cikkek_uid = u'Eltér!'

  @api.one
  @api.depends()
  def _compute_cikkhiany(self):
    hiany, count = '', 0
    ids = self.bom_id.bom_line_ids.mapped('cikk_id.id')
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

############################################################################################################################  Gylap darabjegyzék  ###
class LegrandGylapDbjegyzek(models.Model):
  _name               = 'legrand.gylap_dbjegyzek'
  _order              = 'cikk_id'
  _rec_name           = 'cikk_id'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', readonly=True)
#  cikkszam            = fields.Char(u'Cikkszám', readonly=True)
  ossz_beepules       = fields.Float(u'Össz beépülés', digits=(16, 6), readonly=True)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3), readonly=True)
  # calculated fields
  beepules            = fields.Float(u'Beépülés', digits=(16, 6), compute='_compute_beepules', store=True)
  ossz_bekerules      = fields.Float(u'Össz bekerülés', digits=(16, 5), compute='_compute_ossz_bekerules', store=True)
  # virtual fields
  cikknev             = fields.Char(u'Megnevezés', related='cikk_id.cikknev', readonly=True)
  rendelt_db          = fields.Integer(u'Rendelt termék db', related='gyartasi_lap_id.rendelt_db', readonly=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('rendelt_db', 'ossz_beepules')
  def _compute_beepules(self):
    self.beepules = self.ossz_beepules / self.rendelt_db

  @api.one
  @api.depends('rendelt_db', 'bekerulesi_ar')
  def _compute_ossz_bekerules(self):
    self.ossz_bekerules = self.bekerulesi_ar * self.ossz_beepules

############################################################################################################################  Gylap Legrand művelet  ###
class LegrandGylapMuvelet(models.Model):
  _name               = 'legrand.gylap_legrand_muvelet'
  _order              = 'id'
  _rec_name           = 'muveleti_szam'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True)
#  name                = fields.Char(u'Művelet', readonly=True)
  muveleti_szam       = fields.Integer(u'Műveleti szám', readonly=True)
  megnevezes          = fields.Char(u'Megnevezés', readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 8), readonly=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), readonly=True)
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén', readonly=True)
  # virtual fields
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

############################################################################################################################  Gylap homogén  ###
class LegrandGylapHomogen(models.Model):
  _name               = 'legrand.gylap_homogen'
  _order              = 'id'
  name                = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True)
  termekcsalad        = fields.Char(u'Termékcsalád', related='gyartasi_lap_id.termekcsalad', readonly=True, store=True)
#  homogen             = fields.Char(u'sHomogén', readonly=True)
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén', readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 5), readonly=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 3), readonly=True)
  korrekcios_ido      = fields.Float(u'Korrekciós idő', digits=(16, 3))
  potido              = fields.Float(u'Pótidő', digits=(16, 3), readonly=True)
  sajat               = fields.Boolean(u'Saját homogén?', default=True, readonly=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra', digits=(16, 5), compute='_compute_teljesitett_ora', store=True)
  szamlazhato_ora     = fields.Float(u'Számlázható óra', digits=(16, 5), compute='_compute_szamlazhato_ora', store=True)
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True)
  rendelesszam        = fields.Char(u'Rendelésszám', related='gyartasi_lap_id.rendelesszam', readonly=True)
  termekkod           = fields.Char(u'Tételkód', related='gyartasi_lap_id.termekkod', readonly=True)
  szamlazhato_db      = fields.Integer(u'Számlázható', related='gyartasi_lap_id.szamlazhato_db', readonly=True)
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('gyartasi_lap_id', 'homogen_id')
  def _compute_name(self):
    self.name = str(self.gyartasi_lap_id.id)+'/'+self.homogen_id.homogen

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
  def toggle_sajat(self):
    self.sajat = not self.sajat
    return True

############################################################################################################################  Gylap Szefo művelet  ###
class LegrandSzefoMuvelet(models.Model):
  _name               = 'legrand.gylap_szefo_muvelet'
  _order              = 'gyartasi_lap_id, muveletszam'
  name                = fields.Char(u'Művelet', compute='_compute_name', store=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True)
  muveletszam         = fields.Integer(u'Műveletszám', required=True)
  muveletnev          = fields.Char(u'Műveletnév', required=True)
  fajlagos_db         = fields.Integer(u'Fajlagos db', default = 1, required=True)
  normaora            = fields.Float(u'Normaóra', digits=(16, 8), required=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), required=True)
  # virtual fields
  muveletvegzes_ids   = fields.One2many('legrand.muveletvegzes',  'szefo_muvelet_id', u'Műveletvégzés')
  osszes_ido          = fields.Float(u'Összes idő', digits=(16, 8), compute='_compute_ossz_ido', store=False)
  osszes_db           = fields.Integer(u'Összes db', compute='_compute_osszes_db', store=False)
  kesz_db             = fields.Integer(u'Kész db',   compute='_compute_kesz_db', store=False)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('gyartasi_lap_id', 'muveletszam')
  def _compute_name(self):
    self.name = str(self.gyartasi_lap_id.id)+' '+str(self.muveletszam)+' '+self.muveletnev

  @api.one
  @api.depends('gyartasi_lap_id.modositott_db', 'fajlagos_db', 'normaora')
  def _compute_ossz_ido(self):
    self.osszes_ido = self.gyartasi_lap_id.modositott_db * self.fajlagos_db * self.normaora

  @api.one
  @api.depends('gyartasi_lap_id.modositott_db', 'fajlagos_db')
  def _compute_osszes_db(self):
    self.osszes_db = self.gyartasi_lap_id.modositott_db * self.fajlagos_db

  @api.one
  @api.depends('muveletvegzes_ids')
  def _compute_kesz_db(self):
    self.kesz_db = sum(self.muveletvegzes_ids.mapped('mennyiseg'))

############################################################################################################################  Műveletvégzés  ###
class LegrandMuveletvegzes(models.Model):
  _name               = 'legrand.muveletvegzes'
  _order              = 'id desc'
  szefo_muvelet_id    = fields.Many2one('legrand.gylap_szefo_muvelet', u'Művelet', required=True)
  hely_id             = fields.Many2one('legrand.hely', string=u'Gyártási hely', domain=[('szefo_e', '=', True)], required=True)
  szemely_id          = fields.Many2one('nexon.szemely', u'Dolgozó', required=True)
  mennyiseg           = fields.Integer(u'Mennyiség', required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  nexon_azon          = fields.Integer(u'Személy Id')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', related='szefo_muvelet_id.gyartasi_lap_id', readonly=True)
  muveletnev          = fields.Char(u'Műveletnév',   related='szefo_muvelet_id.muveletnev', readonly=True)
  osszes_db           = fields.Integer(u'Összes db', related='szefo_muvelet_id.osszes_db', readonly=True)
  kesz_db             = fields.Integer(u'Kész db',   related='szefo_muvelet_id.kesz_db', readonly=True)

  @api.model
  def create(self, vals):
    vals['nexon_azon'] = self.env['nexon.szemely'].search([('id', '=', vals['szemely_id'])]).SzemelyId
    return super(LegrandMuveletvegzes, self).create(vals)

  @api.multi
  def write(self, vals):
    vals['nexon_azon'] = self.szemely_id.SzemelyId
    return super(LegrandMuveletvegzes, self).write(vals)

  @api.onchange('nexon_azon')
  def onchange_nexon_azon(self):
    self.szemely_id = self.env['nexon.szemely'].search([('SzemelyId', '=', self.nexon_azon)], limit=1, order='id').id

############################################################################################################################  Feljegyzések  ###
class LegrandFeljegyzes(models.Model):
  _name               = 'legrand.feljegyzes'
  _order              = 'id desc'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap')
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikkszám', required=True)
  feljegyzes          = fields.Char(u'Feljegyzés', required=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.cikk_id = self.gyartasi_lap_id.cikk_id.id

############################################################################################################################  MEO jegyzőkönyv  ###
class LegrandMeoJegyzokonyv(models.Model):
  _name               = 'legrand.meo_jegyzokonyv'
  _order              = 'id desc'
#  _rec_name           = 'muveleti_szam'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', required=True)
#  name                = fields.Char(u'Művelet', readonly=True)
  visszaadott_db      = fields.Integer(u'Visszaadott darabszám')
  ellenorizte_id      = fields.Many2one('nexon.szemely', u'Ellenőrizte', required=True)
  hiba_leirasa        = fields.Char(u'Hiba leírása', required=True)
  dolgozo_id          = fields.Many2one('nexon.szemely', u'Dolgozó', required=True)
  gylap_szefo_muv_id1 = fields.Many2one('legrand.gylap_szefo_muvelet', u'Művelet', required=True, domain="[('gyartasi_lap_id', '=', gyartasi_lap_id)]")
  gylap_szefo_muv_id2 = fields.Many2one('legrand.gylap_szefo_muvelet', u'2. Művelet', domain="[('gyartasi_lap_id', '=', gyartasi_lap_id)]")
  intezkedesek        = fields.Char(u'Intézkedések', required=True)
  javitasi_ido        = fields.Float(u'Javításra fordított idő', digits=(16, 2))
  dolgozo_megjegyzese = fields.Char(u'Dolgozó megjegyzése')
  muszakvezeto_id     = fields.Many2one('nexon.szemely', u'Műszakvezető')
  gyartaskozi_ell_id  = fields.Many2one('nexon.szemely', u'Gyártásközi ellenőr')
  keszaru_ell_id      = fields.Many2one('nexon.szemely', u'Készáru ellenőr')
  fioktelep_vezeto_id = fields.Many2one('nexon.szemely', u'Fióktelep vezető')
  # virtual fields
  meo_jkv_selejt_ids  = fields.One2many('legrand.meo_jkv_selejt',  'meo_jegyzokonyv_id', u'Selejtezett alkatrészek')

############################################################################################################################  MEO jegyzőkönyv selejt  ###
class LegrandMeoJkvSelejt(models.Model):
  _name               = 'legrand.meo_jkv_selejt'
  _order              = 'id'
#  _rec_name           = 'muveleti_szam'
  meo_jegyzokonyv_id  = fields.Many2one('legrand.meo_jegyzokonyv',  u'MEO jegyzőkönyv', index=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', required=True)
  selejtezett_db      = fields.Integer(u'Selejtezett darabszám')
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3))
  # virtual fields
  cikknev             = fields.Char(u'Név', related='cikk_id.cikknev', readonly=True)
  osszertek           = fields.Float(u'Összérték', digits=(16, 2), compute='_compute_osszertek')

  @api.onchange('cikk_id')
  def onchange_cikk_id(self):
    self.bekerulesi_ar = self.cikk_id.bekerulesi_ar

  @api.one
  @api.depends('cikk_id', 'selejtezett_db')
  def _compute_osszertek(self):
    self.osszertek = self.selejtezett_db*self.bekerulesi_ar

############################################################################################################################  Lézer, tampon  ###
class LegrandLezerTampon(models.Model):
  _name               = 'legrand.lezer_tampon'
  _order              = 'id'
  _rec_name           = 'muvelet'
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
class LegrandImpex(models.Model):
  _name               = 'legrand.impex'
  _order              = 'id'
  sorszam             = fields.Integer(u'Sorszám')
  rendelesszam        = fields.Char(u'Rendelésszám')
  cikkszam            = fields.Char(u'Cikkszám')
  homogen             = fields.Char(u'Homogén')
  db                  = fields.Integer(u'db')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2))
  ertek               = fields.Float(u'Érték', digits=(16, 8))
  datum               = fields.Datetime(u'Dátum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási_lap id')
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikk id')
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék')
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén')
  hely_id             = fields.Many2one('legrand.hely', u'Hely id')
  hibakod_id          = fields.Many2one('legrand.hibakod', u'Hibakód')
#  # computed fields
  ora                 = fields.Float(u'Óra', digits=(16, 2), compute='_compute_ora', store=True)
#  # virtual fields
  gylap_state          = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], u'Állapot', related='gyartasi_lap_id.state')
  gyartasi_hely_ids   = fields.Many2many('legrand.hely', string=u'Gyártási helyek', related='gyartasi_lap_id.gyartasi_hely_ids')
  price               = fields.Float(u'Price', digits=(16, 3), related='cikk_id.bekerulesi_ar')

  @api.one
  @api.depends('mennyiseg', 'gyartasi_lap_id')
  def _compute_ora(self):
    self.ora = self.gyartasi_lap_id.rendelt_ora * self.mennyiseg / self.gyartasi_lap_id.rendelt_db if self.gyartasi_lap_id else 0.0
