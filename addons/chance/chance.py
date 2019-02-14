# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions
from chance_proc import pub, log

############################################################################################################################  Hely  ###
class ChanceHely(models.Model):
  _name               = 'chance.hely'
  _order              = 'sorrend'
  name                = fields.Char(u'Megnevezés')
  nev                 = fields.Char(u'Név')
  telepules           = fields.Char(u'Település')
  cim                 = fields.Char(u'Cím')
  azonosito           = fields.Char(u'Belső azonosító')
  sorrend             = fields.Integer(u'Sorrend')
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?')        # A SZEFO készletbe beszámít-e ez a hely?
  keszaru_e           = fields.Boolean(u'Készáru raktár?')                # Késztermék bevételezésnél jelenjen-e meg?
  cikk_ar_felvesz_e   = fields.Boolean(u'Cikk árat felvegye?')            # A cikkar táblába automatikus insert/update legyen-e?
  active              = fields.Boolean(u'Aktív?', default=True)

############################################################################################################################  Partner  ###
class ChancePartner(models.Model):
  _name               = 'chance.partner'
  name                = fields.Char(u'Megnevezés',  required=True)
  nev                 = fields.Char(u'Név',         required=True)
  telepules           = fields.Char(u'Település')
  cim                 = fields.Char(u'Cím')
  active              = fields.Boolean(u'Aktív?',   default=True)

############################################################################################################################  Cikk  ###
class ChanceCikk(models.Model):
  _name               = 'chance.cikk'
  _order              = 'cikkszam'
  name                = fields.Char(u'Cikkazonosító',   compute='_compute_name', store=True)
  cikkszam            = fields.Char(u'Cikkszám',        required=True)
  osztaly             = fields.Char(u'Osztály',         required=True)
  meret               = fields.Char(u'Méret',           required=True)
  szin                = fields.Char(u'Szín',            required=True)
  megnevezes          = fields.Char(u'Megnevezés',      required=True)
  onkoltseg           = fields.Float(u'Önköltség',      digits=(16, 0))
  indulo_keszlet      = fields.Float(u'Induló készlet', digits=(16, 0))
  vonalkod            = fields.Char(u'Vonalkód',        required=False)
  active              = fields.Boolean(u'Aktív?',       default=True)
  # virtual fields
  feljegyzes_ids      = fields.One2many('chance.feljegyzes', 'cikk_id', u'Feljegyzések')

  @api.model
  def create(self, vals):
    new = super(ChanceCikk, self).create(vals)
    new.vonalkod = str(oct(new.id + 4096))[1:].replace('0','8')
    return new

  @api.one
  @api.depends('cikkszam', 'osztaly', 'meret', 'szin', 'megnevezes')
  def _compute_name(self):
    if self.cikkszam and self.osztaly and self.meret and self.szin and self.megnevezes:
      self.name = self.cikkszam+'-'+self.osztaly+'-'+self.meret+'-'+self.szin+' '+self.megnevezes

############################################################################################################################  Cikkar  ###
class ChanceCikkar(models.Model):
  _name               = 'chance.cikkar'
  _order              = 'hely_id, cikkszam'
  hely_id             = fields.Many2one('chance.hely', u'Raktárhely')
  hely_azonosito      = fields.Char(u'Hely azonosító',    related='hely_id.azonosito', store=True)
  cikkszam            = fields.Char(u'Cikkszám',          required=True)
  osztaly             = fields.Char(u'Osztály',           required=True)
  megnevezes          = fields.Char(u'Megnevezés',        required=True)
  nyilvantartasi_ar   = fields.Float(u'Nyilvántartási ár',required=True, digits=(16, 0))

############################################################################################################################  Mozgásfej  ###
class ChanceMozgasfej(models.Model):
  _name               = 'chance.mozgasfej'
  _order              = 'id desc'
  _rec_name           = 'id'
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                        u'Állapot', default='terv', readonly=False )
  mozgasnem           = fields.Selection([('bevet',u'Bevételezés'),('elad',u'Értékesítés'),('belso',u'Belső szállítás'), ('korrekcio',u'Készlethelyesbítés'),
                                          ('selejt',u'Selejtezés'),('indulo',u'Induló készlet'),('rendel',u'Rendelés'),('sajat',u'Saját felhasználás')],
                                          u'Mozgásnem', required=True, default=lambda self: self.env.context.get('mozgasnem', ''))
  forrashely_id       = fields.Many2one('chance.hely', u'Forráshely', index=True)
  celallomas_id       = fields.Many2one('chance.hely', u'Célállomás helye', index=True)
  vevo_id             = fields.Many2one('chance.partner', u'Vevő')
  forrasdokumentum    = fields.Char(u'Forrásdokumentum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  mozgastorzs_id      = fields.Many2one('chance.mozgastorzs', u'Mozgás')
  # virtual fields
  mozgassor_ids       = fields.One2many('chance.mozgassor', 'mozgasfej_id', u'Tételek')

  @api.model
  def create(self, vals):
    forrdict = {'bevet': 'gyartas', 'selejt': 'selejt'}
    celdict  = {'bevet': 'keszaru', 'selejt': 'korrekcio'}
    if vals['mozgasnem']   == 'elad':
      vals['celallomas_id'] = self.env['chance.hely'].search([('azonosito', '=', 'vevo')]).id
    elif vals['mozgasnem']   == 'sajat':
      vals['celallomas_id'] = self.env['chance.hely'].search([('azonosito', '=', 'sajat')]).id
    elif vals['mozgasnem']   == 'bevet':
      vals['forrashely_id'] = self.env['chance.hely'].search([('azonosito', '=', 'gyartas')]).id
    elif vals['mozgasnem']   == 'korrekcio':
      vals['forrashely_id'] = self.env['chance.hely'].search([('azonosito', '=', 'korrekcio')]).id
    elif vals['mozgasnem']   == 'indulo':
      vals['forrashely_id'] = self.env['chance.hely'].search([('azonosito', '=', 'indulo')]).id
    elif vals['mozgasnem']   == 'rendel':
      vals['forrashely_id'] = self.env['chance.hely'].search([('azonosito', '=', 'keszaru')]).id
    elif vals['mozgasnem'] != 'belso':
      forr_id = self.env['chance.hely'].search([('azonosito', '=', forrdict[vals['mozgasnem']])]).id
      cel_id  = self.env['chance.hely'].search([('azonosito', '=', celdict[vals['mozgasnem']])]).id
      vals['forrashely_id'], vals['celallomas_id'] = forr_id, cel_id
    return super(ChanceMozgasfej, self).create(vals)

  @api.multi
  def write(self, vals):
    super(ChanceMozgasfej, self).write(vals)
    self.env.cr.execute('REFRESH MATERIALIZED VIEW chance_keszlet')
    return True

  @api.one
  def veglegesites(self):
    if not self.mozgassor_ids:
      raise exceptions.Warning(u'Nincs véglegesíthető mozgás!')
    if self.forrashely_id == self.celallomas_id:
      raise exceptions.Warning(u'A forrás és célállomás helye megegyezik!')
    self.state = 'szallit' if self.mozgasnem in ('belso','rendel') else 'kesz'
    log(self.env, {'name': u'Mozgás véglegesítés', 'table': 'mozgasfej', 'value': self.forrashely_id.name+' -> '+self.celallomas_id.name, 'rowid': self.id})
    return True

  @api.one
  def state2elter(self):
    self.state  = 'elter'
    log(self.env, {'name': u'Állapot -> Átszállítva eltérésekkel', 'table': 'mozgasfej', 'value': self.forrashely_id.name+' -> '+self.celallomas_id.name, 'rowid': self.id})
    return True

  @api.one
  def state2kesz(self):
    self.state  = 'kesz'
    log(self.env, {'name': u'Állapot -> Átszállítva', 'table': 'mozgasfej', 'value': self.forrashely_id.name+' -> '+self.celallomas_id.name, 'rowid': self.id})
    return True

  @api.one
  def state2konyvelt(self):
    self.state  = 'konyvelt'
    log(self.env, {'name': u'Állapot -> Könyvelve', 'table': 'mozgasfej', 'value': self.forrashely_id.name+' -> '+self.celallomas_id.name, 'rowid': self.id})
    return True

############################################################################################################################  Mozgássor  ###
class ChanceMozgassor(models.Model):
  _name               = 'chance.mozgassor'
  _order              = 'id'
  _rec_name           = 'cikk_id'
  mozgasfej_id        = fields.Many2one('chance.mozgasfej',  u'Sz.lev.', index=True)
  vonalkod            = fields.Char(u'Vonalkód')
  cikk_id             = fields.Many2one('chance.cikk', u'Cikkazonosító', required=True, index=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 0), required=True)
  egysegar            = fields.Float(u'Egységár',  digits=(16, 0), required=False)
  megjegyzes          = fields.Char(u'Megjegyzés')
  mozgasfej_sorszam   = fields.Integer(u'Sz.lev.')
  # virtual fields
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                                        u'Állapot', related='mozgasfej_id.state', readonly=True)
  forrashely_id       = fields.Many2one('chance.hely', u'Forráshely',       related='mozgasfej_id.forrashely_id', readonly=True)
  celallomas_id       = fields.Many2one('chance.hely', u'Célállomás helye', related='mozgasfej_id.celallomas_id', readonly=True)
  raktaron            = fields.Float(u'Raktáron',   digits=(16, 0), compute='_compute_raktaron')
  cikkszam            = fields.Char(u'Cikkszám',    related='cikk_id.cikkszam',   readonly=True)
  osztaly             = fields.Char(u'Osztály',     related='cikk_id.osztaly',    readonly=True)
  meret               = fields.Char(u'Méret',       related='cikk_id.meret',      readonly=True)
  szin                = fields.Char(u'Szín',        related='cikk_id.szin',       readonly=True)
  megnevezes          = fields.Char(u'Megnevezés',  related='cikk_id.megnevezes', readonly=True)
  ertek               = fields.Float(u'Érték',      compute='_compute_ertek',     digits=(16, 0))
  mozgaskod           = fields.Char(u'Mozgáskód',   related='mozgasfej_id.mozgastorzs_id.mozgaskod', readonly=True)

  @api.model
  def create(self, vals):
    new = super(ChanceMozgassor, self).create(vals)
    new.mozgasfej_sorszam = new.mozgasfej_id.id
    if not new.celallomas_id.cikk_ar_felvesz_e:
      return new
    Cikkar = self.env['chance.cikkar']
    cikkar = Cikkar.search([('hely_id', '=', new.celallomas_id.id), ('cikkszam', '=', new.cikk_id.cikkszam), ('osztaly', '=', new.cikk_id.osztaly)], limit=1, order='id desc')
    if cikkar:
      if new.egysegar != cikkar.nyilvantartasi_ar:
        cikkar.nyilvantartasi_ar = new.egysegar
    else:
      cikkar_row = {
        'hely_id'           : new.celallomas_id.id,
        'cikkszam'          : new.cikk_id.cikkszam,
        'osztaly'           : new.cikk_id.osztaly,
        'megnevezes'        : new.cikk_id.megnevezes,
        'nyilvantartasi_ar' : new.egysegar
      }
      Cikkar.create(cikkar_row)
    return new

  @api.one
  @api.depends('cikk_id')
  def _compute_raktaron(self):
    self.raktaron = self.env['chance.keszlet'].search([('hely_id', '=', self.forrashely_id.id), ('cikk_id', '=', self.cikk_id.id)], limit=1).raktaron

  @api.one
  @api.depends('mennyiseg', 'egysegar')
  def _compute_ertek(self):
    self.ertek = self.mennyiseg * self.egysegar

  @api.onchange('vonalkod')
  def onchange_vonalkod(self):
    self.cikk_id = self.env['chance.cikk'].search([('vonalkod', '=', self.vonalkod)], order='id desc', limit=1).id
    self.mennyiseg = 1 if self.vonalkod else 0

  @api.onchange('cikk_id')
  def onchange_cikk_id(self):
    self.egysegar = self.env['chance.cikkar'].search([ ('hely_id', '=', self.celallomas_id.id), ('cikkszam', '=', self.cikk_id.cikkszam), ('osztaly', '=', self.cikk_id.osztaly)], order='id desc', limit=1).nyilvantartasi_ar
    self.raktaron = self.env['chance.keszlet'].search([('hely_id', '=', self.forrashely_id.id), ('cikk_id', '=', self.cikk_id.id)], limit=1).raktaron
    self.vonalkod = self.cikk_id.vonalkod

############################################################################################################################  Készlet  ###
class ChanceKeszlet(models.Model):
  _name               = 'chance.keszlet'
  _auto               = False
  _rec_name           = 'id'
  _order              = 'hely_id, cikk_id, osztaly, meret, szin'
  cikk_id             = fields.Many2one('chance.cikk', string=u'Cikkazonosító', readonly=True)
  hely_id             = fields.Many2one('chance.hely', u'Raktárhely', readonly=True)
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?', readonly=True)
  raktaron            = fields.Float(string=u'Raktáron', digits=(16, 0), readonly=True)
  varhato             = fields.Float(string=u'Előrejelzés', digits=(16, 0), readonly=True)
  cikkszam            = fields.Char(u'Cikkszám')
  osztaly             = fields.Char(u'Osztály')
  meret               = fields.Char(u'Méret')
  szin                = fields.Char(u'Szín')
  megnevezes          = fields.Char(u'Megnevezés')
  onkoltseg           = fields.Float(u'Önköltség', digits=(16, 0))
  ertek               = fields.Float(u'Érték',     digits=(16, 0))
  vonalkod            = fields.Char(u'Vonalkód')

  def init(self, cr):
    return
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
#      """CREATE or REPLACE VIEW %s as (
      """CREATE MATERIALIZED VIEW %s as (
      SELECT
        row_number() over() AS id,
        keszlet.*, cikk.cikkszam, cikk.osztaly, cikk.meret, cikk.szin, cikk.megnevezes, cikk.onkoltseg, raktaron * cikk.onkoltseg AS ertek, cikk.vonalkod
      FROM (
        SELECT
          cikk_id,
          hely_id,
          szefo_e,
          sum(CASE WHEN raktaron_e THEN mennyiseg ELSE 0.0 END) AS raktaron,
          sum(mennyiseg) AS varhato
        FROM (
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM chance_mozgassor AS sor
          JOIN chance_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN chance_hely      AS hely ON hely.id = fej.celallomas_id
          UNION ALL
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM chance_mozgassor AS sor
          JOIN chance_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN chance_hely      AS hely ON hely.id = fej.forrashely_id
        ) AS move
        GROUP BY cikk_id, hely_id, szefo_e
      ) AS keszlet
      JOIN chance_cikk AS cikk ON cikk.id  = keszlet.cikk_id

      )"""
      % (self._table)
    )

  @api.one
  @api.depends('raktaron', 'cikk_id.onkoltseg')
  def _compute_ertek(self):
    self.ertek = self.raktaron * self.cikk_id.onkoltseg

class ChanceKeszletCikk(models.Model):
  _name               = 'chance.keszlet_cikk'
  _auto               = False
  _rec_name           = 'cikk_id'
  _order              = 'cikk_id'
  cikk_id             = fields.Many2one('chance.cikk', string=u'Cikkazonosító', readonly=True)
  szefo_keszlet       = fields.Float(string=u'Készlet', digits=(16, 0), readonly=True)
  # virtual fields
  cikkszam            = fields.Char(u'Cikkszám',    related='cikk_id.cikkszam')
  osztaly             = fields.Char(u'Osztály',     related='cikk_id.osztaly')
  meret               = fields.Char(u'Méret',       related='cikk_id.meret')
  szin                = fields.Char(u'Szín',        related='cikk_id.szin')
  megnevezes          = fields.Char(u'Megnevezés',  related='cikk_id.megnevezes')
  onkoltseg           = fields.Float(u'Önköltség',  related='cikk_id.onkoltseg', digits=(16, 0))
  ertek               = fields.Float(u'Érték',      compute='_compute_ertek',    digits=(16, 0))
  vonalkod            = fields.Char(u'Vonalkód',    related='cikk_id.vonalkod')

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          row_number() over() AS id,
          cikk_id,
          sum(CASE WHEN szefo_e   AND raktaron_e THEN  mennyiseg ELSE 0.0 END) AS szefo_keszlet
        FROM (
          SELECT sor.cikk_id, hely.szefo_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM chance_mozgassor AS sor
          JOIN chance_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN chance_hely      AS hely ON hely.id = fej.celallomas_id
          WHERE mozgasnem != 'belso'
          UNION ALL
          SELECT sor.cikk_id, hely.szefo_e, fej.state NOT IN ('terv', 'szallit') AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM chance_mozgassor AS sor
          JOIN chance_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN chance_hely      AS hely ON hely.id = fej.forrashely_id
          WHERE mozgasnem != 'belso'
        ) AS move
        GROUP BY cikk_id
      )"""
      % (self._table)
    )

  @api.one
  @api.depends('szefo_keszlet', 'cikk_id.onkoltseg')
  def _compute_ertek(self):
    self.ertek = self.szefo_keszlet * self.cikk_id.onkoltseg

############################################################################################################################  Feljegyzések  ###
class ChanceFeljegyzes(models.Model):
  _name               = 'chance.feljegyzes'
  _order              = 'id desc'
  cikk_id             = fields.Many2one('chance.cikk',  u'Cikkazonosító', required=True)
  feljegyzes          = fields.Char(u'Feljegyzés', required=True)
  # virtual fields

############################################################################################################################  Mozgástörzs  ###
# Matrix-ból átemelve
class ChanceMozgastorzs(models.Model):
  _name               = 'chance.mozgastorzs'
  _order              = 'mozgaskod'
  name                = fields.Char(u'Mozgás',    compute='_compute_name', store=True)
  mozgaskod           = fields.Char(u'Mozgáskód', required=True)
  mozgasnev           = fields.Char(u'Mozgásnév', required=True)

  @api.one
  @api.depends('mozgaskod', 'mozgasnev')
  def _compute_name(self):
    if self.mozgaskod and self.mozgasnev:
      self.name = self.mozgaskod+' '+self.mozgasnev

############################################################################################################################  Impex  ###
class ChanceImpex(models.Model):
  _name               = 'chance.impex'
  _order              = 'id'
  cikkszam            = fields.Char(u'Cikkszám')
