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
  gyartasi_hely_e     = fields.Boolean(u'Gyártási hely?')                 # Folyik-e termelés ezen a helyen?
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
  termekcsoport       = fields.Char(u'Termékcsoport')
  kulso_dokumentum    = fields.Char(u'Külső dokumentum')
  alkatresz_e         = fields.Boolean(u'Alkatrész?',   default=False)
  kesztermek_e        = fields.Boolean(u'Késztermék?',  default=False)
  szefo_cikk_e        = fields.Boolean(u'SZEFO cikk?',  default=False)
  cimke_e             = fields.Boolean(u'Címke?',       default=False)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár',  digits=(16, 3))
  beepulok_ids        = fields.Many2many('legrand.bom', string=u'Beépülők', domain=[('beepul_e', '=', True)])
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  keszlet             = fields.Float(u'Készlet',   digits=(16, 2), compute='_compute_keszlet')
  lefoglalt           = fields.Float(u'Lefoglalt', digits=(16, 2), compute='_compute_lefoglalt')
  muvelet_ids         = fields.One2many('legrand.muvelet',      'cikk_id',    u'Műveletek', auto_join=True)
  lezer_tampon_ids    = fields.One2many('legrand.lezer_tampon', 'termek_id',  u'Lézer, tampon', auto_join=True)
  feljegyzes_ids      = fields.One2many('legrand.feljegyzes',   'cikk_id',    u'Feljegyzések', auto_join=True)

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
  name                = fields.Char(u'Név', compute='_compute_name', store=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikkszám', index=True, required=True, auto_join=True)
  verzio              = fields.Char(u'Verzió', required=True)
  beepul_e            = fields.Boolean(u'Beépül?', default=False)
  cikkek_uid          = fields.Char(u'Összes alkatrész uid', compute='_compute_cikkek_uid', store=True)
  active              = fields.Boolean(u'Aktív?', default=True, groups='legrand.group_legrand_director')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)
  bom_line_ids        = fields.One2many('legrand.bom_line', 'bom_id', u'Anyagjegyzék sorok', auto_join=True)
  mozgassor_ids       = fields.One2many('legrand.mozgassor', 'bom_id', u'Szállítás sorok', readonly=True, auto_join=True)
  count_mozgassor_ids = fields.Integer(u'Szállítás sorok db', compute='_compute_count_mozgassor_ids')
  admin_e             = fields.Boolean(u'Admin?',             compute='_check_user_group')
  legrand_director_e  = fields.Boolean(u'Legrand director?',  compute='_check_user_group')
  # temporary fields
  raktar_gylap_id     = fields.Integer(u'Gyártási lap sorszám')


  @api.one
  @api.depends('cikk_id', 'verzio')
  def _compute_name(self):
    if self.cikk_id and self.verzio:
      self.name = self.cikk_id.cikkszam+' '+self.verzio

  @api.one
  @api.depends('bom_line_ids', 'bom_line_ids.cikk_id')
  def _compute_cikkek_uid(self):
    self.cikkek_uid = calc_cikkek_uid(self.bom_line_ids, 'cikkszam')

  @api.one
  @api.depends('mozgassor_ids')
  def _compute_count_mozgassor_ids(self):
    self.count_mozgassor_ids = len(self.mozgassor_ids)

  @api.one
  def _check_user_group(self):
    self.admin_e = self.env.user.has_group('base.group_system')
    self.legrand_director_e = self.env.user.has_group('legrand.group_legrand_director')

  @api.one
  def import_impex(self):
    for impex in self.env['legrand.impex'].search([]):
      sor_row = {
        'bom_id'            : self.id,
        'cikk_id'           : impex.cikk_id.id,
        'beepules'          : impex.beepules,
      }
      self.env['legrand.bom_line'].create(sor_row)
    return True

  @api.one
  def export_impex(self):
    self.env['legrand.impex'].search([]).unlink()
    for alk in self.bom_line_ids:
      impex_row = {
        'cikk_id'         : alk.cikk_id.id,
        'beepules'        : alk.beepules,
      }
      self.env['legrand.impex'].create(impex_row)
    return True

############################################################################################################################  Bom line  ###
class LegrandBomLine(models.Model):
  _name               = 'legrand.bom_line'
  _order              = 'id'
  _rec_name           = 'cikk_id'
#  name                = fields.Char(u'Név',      compute='_compute_name', store=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', index=True, required=True, auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', index=True, required=True, auto_join=True)
  beepules            = fields.Float(u'Beépülés', digits=(16, 8), required=True)
  depo_felhasznalas   = fields.Boolean(u'Depó felhasználás?', default=False)
  # virtual fields
  active              = fields.Boolean(u'Aktív?',       related='bom_id.active',    readonly=True)
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
  forrashely_id       = fields.Many2one('legrand.hely', u'Forráshely', index=True, auto_join=True)
  celallomas_id       = fields.Many2one('legrand.hely', u'Célállomás helye', index=True, auto_join=True)
  kulso_dokumentum    = fields.Char(u'Külső dokumentum')
  forrasdokumentum    = fields.Char(u'Forrásdokumentum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  mozgassor_irhato_e  = fields.Boolean(u'Tételek írható?', compute='_compute_mozgassor_irhato_e')
  mozgassor_ids       = fields.One2many('legrand.mozgassor', 'mozgasfej_id', u'Tételek', auto_join=True)

  @api.one
  @api.depends('state')
  def _compute_mozgassor_irhato_e(self):
    self.mozgassor_irhato_e = self.state == 'terv' or (self.state == 'elter' and self.env.user.has_group('legrand.group_legrand_manager'))

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
    new = super(LegrandMozgasfej, self).create(vals)
    self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_keszlet')
    self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_vall_keszlet')
    return new

  @api.multi
  def write(self, vals):
    super(LegrandMozgasfej, self).write(vals)
    self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_keszlet')
    self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_vall_keszlet')
    return True

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
      beepules = 0
      if sor.gyartasi_lap_id and sor.cikk_id:
        bom_line_ids = sor.gyartasi_lap_id.bom_id.bom_line_ids.filtered(lambda r: r.cikk_id == sor.cikk_id)
        if len(bom_line_ids):
          beepules = bom_line_ids[0].beepules
      impex_row = {
        'sorszam'         : sor.gyartasi_lap_id.id,
        'gyartasi_lap_id' : sor.gyartasi_lap_id.id,
        'db'              : sor.gyartasi_lap_id.modositott_db,
        'cikk_id'         : sor.cikk_id.id,
        'bom_id'          : sor.bom_id.id,
        'mennyiseg'       : sor.mennyiseg,
        'hibakod_id'      : sor.hibakod_id.id,
        'rendelesszam'    : sor.gyartasi_lap_id.rendelesszam,
        'cikkszam'        : sor.gyartasi_lap_id.termekkod,
        'megjegyzes'      : sor.megjegyzes,
        'beepules'        : beepules,
      }
      self.env['legrand.impex'].create(impex_row)
    return True

  @api.one
  def import_bevet(self):
    for bevet in self.env['legrand.depobevetossz'].search([]):
      sor_row = {
        'mozgasfej_id'      : self.id,
        'cikk_id'           : bevet.cikk_id.id,
        'mennyiseg'         : bevet.mennyiseg,
      }
      self.env['legrand.mozgassor'].create(sor_row)
    self.env['legrand.depobevet'].search([]).unlink()
    return True

  @api.one
  def veglegesites(self):
    if not self.mozgassor_ids:
      raise exceptions.Warning(u'Nincs véglegesíthető mozgás!')
    if self.forrashely_id == self.celallomas_id:
      raise exceptions.Warning(u'A forrás és célállomás helye megegyezik!')
    if self.mozgasnem == 'be':
      depo_id = self.env['legrand.hely'].search([('azonosito','=','depo')]).id
      ossz_uj_igeny_ids = self.env['legrand.anyagigeny'].search([('state', '=', 'uj'), ('forrashely_id', '=', depo_id)])
      for sor in self.mozgassor_ids:
        cikk_uj_igeny_ids = ossz_uj_igeny_ids.filtered(lambda r: r.cikk_id == sor.cikk_id)
        if cikk_uj_igeny_ids:
          for cikk_uj_igeny in cikk_uj_igeny_ids:
            cikk_uj_igeny.write({'erkezett': cikk_uj_igeny.erkezett + sor.mennyiseg})
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
  mozgasfej_id        = fields.Many2one('legrand.mozgasfej',  u'Mozgásfej', index=True, readonly=True, auto_join=True)
#  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám', domain="[('szefo_cikk_e', '=', False)]", index=True)
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám', index=True, auto_join=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', index=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', auto_join=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  hibakod_id          = fields.Many2one('legrand.hibakod', u'Hibakód', auto_join=True)
  megjegyzes          = fields.Char(u'Megjegyzés', default=lambda self: 'helyesbít' if self.env.context.get('mozgasnem', '') == 'helyesbit' else '')
  # computed fields
  mozgasfej_sorszam   = fields.Integer(u'Sz.lev.')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', compute='_compute_cikknev', required=True)
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                                        u'Állapot',  related='mozgasfej_id.state', readonly=True)
  mozgasnem           = fields.Selection([('be',u'Alkatrész bevételezés'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('helyesbit',u'Készlethelyesbítés'),('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt visszaszállítás')],
                                          u'Mozgásnem',  related='mozgasfej_id.mozgasnem', readonly=True)
  forrashely_id       = fields.Many2one('legrand.hely', u'Forráshely',       related='mozgasfej_id.forrashely_id', readonly=True, auto_join=True)
  celallomas_id       = fields.Many2one('legrand.hely', u'Célállomás helye', related='mozgasfej_id.celallomas_id', readonly=True, auto_join=True)
  forrashelyen        = fields.Float(u'Készlet', digits=(16, 2), compute='_compute_forrashelyen')

  @api.model
  def create(self, vals):
    new = super(LegrandMozgassor, self).create(vals)
    new.mozgasfej_sorszam = new.mozgasfej_id.id
    if new.mozgasnem == 'ki' and new.mennyiseg > new.forrashelyen:
      raise exceptions.Warning(u'A kiszállítás nagyobb mint a hátralék!')
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
    cikk_domain = [('alkatresz_e', '=', True)]
    bom_domain  = [('beepul_e', '=', True)]
    if self.mozgasfej_id.mozgasnem == 'be':
      self.bom_id = False
      cikk_domain = [('szefo_cikk_e', '=', False)]
    if self.mozgasfej_id.mozgasnem == 'ki':
      self.bom_id = self.gyartasi_lap_id.bom_id.id
      bom_domain  = [('id','=',self.bom_id.id)]
    else:
      self.cikk_id = False
      self.bom_id = False
      if self.gyartasi_lap_id:
        cikk_ids = self.gyartasi_lap_id.bom_id.bom_line_ids.mapped('cikk_id.id')
        bom_ids  = self.gyartasi_lap_id.bom_id.cikk_id.beepulok_ids.mapped('id')
        bom_ids.append(self.gyartasi_lap_id.bom_id.id)
        cikk_domain = [('id','in',cikk_ids)]
        bom_domain  = [('id','in',bom_ids)]
    return {'domain': {'cikk_id': cikk_domain, 'bom_id': bom_domain}}

  @api.onchange('cikk_id')
  def onchange_cikk_id(self):
    self.bom_id = False

  @api.onchange('bom_id')
  def onchange_bom_id(self):
    self.cikk_id = False

  @api.one
  @api.depends('cikk_id', 'forrashely_id', 'mozgasnem')
  def _compute_forrashelyen(self):
    if self.mozgasnem == 'ki':
      self.forrashelyen = self.gyartasi_lap_id.hatralek_db
    else:
      self.forrashelyen = self.env['legrand.keszlet'].search([('cikk_id', '=', self.cikk_id.id), ('hely_id', '=', self.forrashely_id.id)]).raktaron

############################################################################################################################  Előszerelés  ###
class LegrandEloszereles(models.Model):
  _name               = 'legrand.eloszereles'
  _order              = 'id desc'
  hely_id             = fields.Many2one('legrand.hely', string=u'Gyártási hely', domain=[('gyartasi_hely_e', '=', True)], required=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', auto_join=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', required=True, auto_join=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='bom_id.cikk_id.cikknev', readonly=True)
  akcio               = fields.Char(u'Akció', compute='_compute_akcio')

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    bom_domain  = [('beepul_e', '=', True)]
    self.bom_id = False
    if self.gyartasi_lap_id:
      bom_ids  = self.gyartasi_lap_id.bom_id.cikk_id.beepulok_ids.mapped('id')
      bom_domain  = [('id','in',bom_ids)]
    return {'domain': {'bom_id': bom_domain}}

  @api.one
  @api.depends('mennyiseg')
  def _compute_akcio(self):
    if self.mennyiseg > 0: self.akcio = u'előgyártás'
    elif self.mennyiseg < 0: self.akcio = u'felhasználás'
    else: self.akcio = ''

############################################################################################################################  Cikk mozgás  ###
class LegrandCikkMozgas(models.Model):
  _name = 'legrand.cikk_mozgas'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'mozgasfej_id desc, datum'
  state               = fields.Selection([('terv',u'Tervezet'),('szallit',u'Szállítás'),('elter',u'Átszállítva eltérésekkel'),('kesz',u'Átszállítva'),('konyvelt',u'Könyvelve')],
                        u'Állapot', readonly=True)
  mozgasnem           = fields.Selection([('be',u'Alkatrész bevételezés'),('ki',u'Termék kiszállítás'),('belso',u'Belső szállítás'),
                                          ('helyesbit',u'Készlethelyesbítés'),('vissza',u'Alkatrész visszaszállítás'),('selejt',u'Selejt visszaszállítás')],
                                          u'Mozgásnem', readonly=True)
  mozgasfej_id        = fields.Integer(u'Mozgásfej')
  forrashely_id       = fields.Many2one('legrand.hely',       u'Forráshely',        readonly=True, auto_join=True)
  celallomas_id       = fields.Many2one('legrand.hely',       u'Célállomás helye',  readonly=True, auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',       u'Cikkszám',          readonly=True, auto_join=True)
  bom_id              = fields.Many2one('legrand.bom',        u'Anyagjegyzék',      readonly=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap', u'Gyártási lap',    readonly=True, auto_join=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 5), readonly=True)
  datum               = fields.Date(u'Létrehozás ideje', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          row_number() over() AS id,
          state,
          mozgasnem,
          mozgasfej_id,
          forrashely_id,
          celallomas_id,
          cikk_id,
          bom_id,
          gyartasi_lap_id,
          mennyiseg,
          datum
        FROM (
          SELECT fej.id AS mozgasfej_id, fej.forrashely_id, fej.celallomas_id, sor.cikk_id, sor.bom_id, sor.gyartasi_lap_id, sor.mennyiseg AS mennyiseg, fej.state, fej.mozgasnem, sor.create_date AS datum
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          WHERE cikk_id > 0
          UNION ALL
          SELECT fej.id AS mozgasfej_id, fej.forrashely_id, fej.celallomas_id, line.cikk_id, sor.bom_id, sor.gyartasi_lap_id, sor.mennyiseg*line.beepules AS mennyiseg, fej.state, fej.mozgasnem, sor.create_date
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0
        ) AS move
      )"""
      % (self._table)
    )

############################################################################################################################  Anyagigénylés  ###
class LegrandAnyagigeny(models.Model):
  _name               = 'legrand.anyagigeny'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('uj',u'Új igény'),('nyugta',u'Nyugtázva')], u'Állapot', default='terv', readonly=True)
  #!!!                                                                                                            Depo bedrótozva
  forrashely_id       = fields.Many2one('legrand.hely', u'Forráshely', domain=[('belso_szallitas_e', '=', True)], default=4,  readonly=True, states={'terv': [('readonly', False)]}, required=True)
  hely_id             = fields.Many2one('legrand.hely', u'Célállomás', domain=[('belso_szallitas_e', '=', True)],             readonly=True, states={'terv': [('readonly', False)]}, required=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap',                                             readonly=True, states={'terv': [('readonly', False)]})
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám',                                                          readonly=True, states={'terv': [('readonly', False)]}, required=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2),                                                            readonly=True, states={'terv': [('readonly', False)]}, required=True)
  igeny_ok            = fields.Selection([('hiany',u'hiánypótlás'),('selejt',u'selejtpótlás')], 'Kérés oka', default='hiany', readonly=True, states={'terv': [('readonly', False)]}, required=True)
  megjegyzes          = fields.Char(u'Megjegyzés',                                                                                           states={'nyugta': [('readonly', True)]})
  erkezett            = fields.Float(u'Érkezett', digits=(16, 2),                                                             readonly=True, states={'uj': [('readonly', False)]})
  hatralek            = fields.Float(u'Hátralék', digits=(16, 2), compute='_compute_hatralek', store=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.cikk_id = False
    ids = self.gyartasi_lap_id.bom_id.bom_line_ids.mapped('cikk_id.id')
    domain = [('id','in',ids)] if self.gyartasi_lap_id else []
    return {'domain': {'cikk_id': domain}}

  @api.one
  @api.depends('mennyiseg', 'erkezett')
  def _compute_hatralek(self):
    self.hatralek = 0 if self.mennyiseg - self.erkezett < 0 else self.mennyiseg - self.erkezett

  @api.one
  def state2uj(self):
    self.state = 'uj'
    return True

  @api.one
  def state2nyugta(self):
    self.state = 'nyugta'
    return True

  @api.one
  def state2terv(self):
    self.state = 'terv'
    return True

############################################################################################################################  Készlet  ###
class LegrandKeszlet(models.Model):
  _name = 'legrand.keszlet'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id, hely_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True, auto_join=True)
  hely_id             = fields.Many2one('legrand.hely', u'Raktárhely', readonly=True, auto_join=True)
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?', readonly=True)
  legrand_e           = fields.Boolean(u'Legrand készletbe számít?', readonly=True)
  terv                = fields.Float(string=u'Terv',        readonly=True)
  szallitason         = fields.Float(string=u'Szállításon', readonly=True)
  megerkezett         = fields.Float(string=u'Megérkezett', readonly=True)
  raktaron            = fields.Float(string=u'Raktáron',    readonly=True)
  varhato             = fields.Float(string=u'Előrejelzés', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár',  digits=(16, 3), related='cikk_id.bekerulesi_ar', readonly=True)
  alkatresz_e         = fields.Boolean(u'Alkatrész',  related='cikk_id.alkatresz_e',  readonly=True)
  kesztermek_e        = fields.Boolean(u'Késztermék', related='cikk_id.kesztermek_e', readonly=True)

  def init(self, cr):
    return
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
#      """CREATE or REPLACE VIEW %s as (
      """CREATE MATERIALIZED VIEW %s as (
        SELECT
          row_number() over() AS id,
          cikk_id,
          hely_id,
          szefo_e,
          legrand_e,
          sum(CASE WHEN state = 'terv' THEN mennyiseg ELSE 0.0 END) AS terv,
          sum(CASE WHEN state = 'szallit' THEN mennyiseg ELSE 0.0 END) AS szallitason,
          sum(CASE WHEN state NOT IN ('terv', 'szallit') THEN mennyiseg ELSE 0.0 END) AS megerkezett,
          sum(CASE WHEN raktaron_e THEN mennyiseg ELSE 0.0 END) AS raktaron,
          sum(mennyiseg) AS varhato
        FROM (
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          WHERE cikk_id > 0
          UNION ALL
          SELECT sor.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state != 'terv' AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          WHERE cikk_id > 0
          UNION ALL
          SELECT line.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,
            CASE WHEN line.depo_felhasznalas THEN CASE WHEN hely.legrand_e THEN sor.mennyiseg*line.beepules ELSE 0.0 END ELSE sor.mennyiseg*line.beepules END AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          JOIN legrand_bom_line  AS line ON sor.bom_id = line.bom_id
          WHERE sor.bom_id > 0
          UNION ALL
          SELECT line.cikk_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state != 'terv' AS raktaron_e,
            CASE WHEN line.depo_felhasznalas THEN CASE WHEN cel.legrand_e THEN -sor.mennyiseg*line.beepules ELSE 0.0 END ELSE -sor.mennyiseg*line.beepules END AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          JOIN legrand_hely      AS cel  ON cel.id  = fej.celallomas_id
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
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True, auto_join=True)
  szefo_keszlet       = fields.Float(string=u'SZEFO készlet', readonly=True)
  legrand_keszlet     = fields.Float(string=u'Legrand készlet', readonly=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    return
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
#      """CREATE or REPLACE VIEW %s as (
      """CREATE MATERIALIZED VIEW %s as (
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

############################################################################################################################  Anyagjegyzék készlet  ###
class LegrandAnyagjegyzekKeszlet(models.Model):
  _name = 'legrand.anyagjegyzek_keszlet'
  _auto = False
  _rec_name = 'bom_id'
  _order = 'bom_id, hely_id'
  bom_id              = fields.Many2one('legrand.bom', string=u'Anyagjegyzék', readonly=True, auto_join=True)
  hely_id             = fields.Many2one('legrand.hely', u'Raktárhely', readonly=True, auto_join=True)
  szefo_e             = fields.Boolean(u'SZEFO készletbe számít?', readonly=True)
  legrand_e           = fields.Boolean(u'Legrand készletbe számít?', readonly=True)
  terv                = fields.Float(string=u'Terv',        readonly=True)
  szallitason         = fields.Float(string=u'Szállításon', readonly=True)
  megerkezett         = fields.Float(string=u'Megérkezett', readonly=True)
  raktaron            = fields.Float(string=u'Raktáron',    readonly=True)
  varhato             = fields.Float(string=u'Előrejelzés', readonly=True)
  # virtual fields

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          row_number() over() AS id,
          bom_id,
          hely_id,
          szefo_e,
          legrand_e,
          sum(CASE WHEN state = 'terv' THEN mennyiseg ELSE 0.0 END) AS terv,
          sum(CASE WHEN state = 'szallit' THEN mennyiseg ELSE 0.0 END) AS szallitason,
          sum(CASE WHEN state NOT IN ('terv', 'szallit') THEN mennyiseg ELSE 0.0 END) AS megerkezett,
          sum(CASE WHEN raktaron_e THEN mennyiseg ELSE 0.0 END) AS raktaron,
          sum(mennyiseg) AS varhato
        FROM (
          SELECT sor.bom_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state NOT IN ('terv', 'szallit') AS raktaron_e,  sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.celallomas_id
          WHERE bom_id > 0
          UNION ALL
          SELECT sor.bom_id, hely.id AS hely_id, hely.szefo_e, hely.legrand_e, fej.state, fej.state != 'terv' AS raktaron_e, -sor.mennyiseg AS mennyiseg
          FROM legrand_mozgassor AS sor
          JOIN legrand_mozgasfej AS fej  ON fej.id  = sor.mozgasfej_id
          JOIN legrand_hely      AS hely ON hely.id = fej.forrashely_id
          WHERE bom_id > 0
        ) AS move
        GROUP BY bom_id, hely_id, szefo_e, legrand_e
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
  cikk_id             = fields.Many2one('legrand.cikk',  u'Termék', readonly=True, auto_join=True)
  muveletszam         = fields.Integer(u'Műveletszám', required=True)
  muveletnev          = fields.Char(u'Műveletnév', required=True)
  fajlagos_db         = fields.Integer(u'Fajlagos db', default = 1, required=True)
  normaora            = fields.Float(u'SZEFO normaóra', digits=(16, 8))
  beall_ido           = fields.Float(u'SZEFO beállítási idő', digits=(16, 5))
  legrand_normaora    = fields.Float(u'Legrand normaóra', digits=(16, 8))
  legrand_beall_ido   = fields.Float(u'Legrand beállítási idő', digits=(16, 5))
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

############################################################################################################################  Gylap darabjegyzék  ###
class LegrandGylapDbjegyzek(models.Model):
  _name               = 'legrand.gylap_dbjegyzek'
  _order              = 'gyartasi_lap_id, cikk_id'
  _rec_name           = 'cikk_id'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True, auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', readonly=True, auto_join=True)
#  cikkszam            = fields.Char(u'Cikkszám', readonly=True)
  ossz_beepules       = fields.Float(u'Össz beépülés', digits=(16, 6), readonly=True)
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3), readonly=True)
  kesz_e              = fields.Boolean(u'Kész?', readonly=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  # calculated fields
  beepules            = fields.Float(u'Beépülés', digits=(16, 6), compute='_compute_beepules', store=True)
  ossz_bekerules      = fields.Float(u'Össz bekerülés', digits=(16, 5), compute='_compute_ossz_bekerules', store=True)
  cikk_ar             = fields.Float(u'Cikktörzs ár',  digits=(16, 3), related='cikk_id.bekerulesi_ar', store=True)
  arelteres           = fields.Float(u'Eltérés', digits=(16, 3), compute='_compute_arelteres', store=True)
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                        u'Állapot', related='gyartasi_lap_id.state', readonly=True)
  cimke_e             = fields.Boolean(u'Címke?',  related='cikk_id.cimke_e', readonly=True)
  homogen_7127_van_e  = fields.Boolean(u'7127 van benne?', related='gyartasi_lap_id.homogen_7127_van_e', readonly=True)
  cikknev             = fields.Char(u'Megnevezés', related='cikk_id.cikknev', readonly=True)
  rendelt_db          = fields.Integer(u'Rendelt termék db', related='gyartasi_lap_id.rendelt_db', readonly=True)
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True)
  gyartasi_hely_id    = fields.Many2one('legrand.hely',  u'Fő gyártási hely', related='gyartasi_lap_id.gyartasi_hely_id', auto_join=True, readonly=True)
  hatralek_ora        = fields.Float(u'Hátralék óra', digits=(16, 2), compute='_compute_hatralek_ora')
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('rendelt_db', 'ossz_beepules')
  def _compute_beepules(self):
    self.beepules = self.ossz_beepules / self.rendelt_db

  @api.one
  @api.depends('rendelt_db', 'bekerulesi_ar')
  def _compute_ossz_bekerules(self):
    self.ossz_bekerules = self.bekerulesi_ar * self.ossz_beepules

  @api.one
  @api.depends('cikk_id.bekerulesi_ar', 'bekerulesi_ar')
  def _compute_arelteres(self):
    self.arelteres = self.bekerulesi_ar - self.cikk_id.bekerulesi_ar

  @api.one
  @api.depends('gyartasi_lap_id', 'cimke_e')
  def _compute_hatralek_ora(self):
    if self.kesz_e:
      self.hatralek_ora = 0
    else:
      ora_osszes = sum(self.gyartasi_lap_id.gylap_homogen_ids.filtered(lambda r: r.homogen_id.homogen == '7127').mapped('rendelt_ora'))
      count = len(self.env['legrand.gylap_dbjegyzek'].search([('gyartasi_lap_id', '=', self.gyartasi_lap_id.id), ('cimke_e','=',True)]))
      self.hatralek_ora = ora_osszes / count if count else 0

  @api.one
  def kesz(self):
    self.kesz_e  = True
    return True

############################################################################################################################  Gylap Legrand művelet  ###
class LegrandGylapMuvelet(models.Model):
  _name               = 'legrand.gylap_legrand_muvelet'
  _order              = 'id'
  _rec_name           = 'muveleti_szam'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True, auto_join=True)
#  name                = fields.Char(u'Művelet', readonly=True)
  muveleti_szam       = fields.Integer(u'Műveleti szám', readonly=True)
  megnevezes          = fields.Char(u'Megnevezés', readonly=True)
  ossz_ido            = fields.Float(u'Összes idő', digits=(16, 8), readonly=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), readonly=True)
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén', readonly=True, auto_join=True)
  # virtual fields
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

############################################################################################################################  Gylap homogén  ###
class LegrandGylapHomogen(models.Model):
  _name               = 'legrand.gylap_homogen'
  _order              = 'id'
  name                = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True, auto_join=True)
  termekcsalad        = fields.Char(u'Termékcsalád', related='gyartasi_lap_id.termekcsalad', readonly=True, store=True)
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén', readonly=True, auto_join=True)
  ossz_ido            = fields.Float(u'Összes idő',       digits=(16, 5), readonly=True)
  beall_ido           = fields.Float(u'Beállítási idő',   digits=(16, 3), readonly=True)
  korrekcios_ido      = fields.Float(u'Korrekciós idő',   digits=(16, 3))
  sajat               = fields.Boolean(u'Saját homogén?', default=True,   readonly=True)
  gyartasi_hely_id    = fields.Many2one('legrand.hely', u'Gyártási hely', domain=[('szefo_e', '=', True)], states={'kesz': [('readonly', True)]})
  rendelt_ora         = fields.Float(u'Rendelt óra',      digits=(16, 5), compute='_compute_rendelt_ora',     store=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra',  digits=(16, 5), compute='_compute_teljesitett_ora', store=True)
  hatralek_ora        = fields.Float(u'Hátralék óra',     digits=(16, 5), compute='_compute_hatralek_ora',    store=True)
  szamlazott_ora      = fields.Float(u'Számlázott óra',   digits=(16, 5), compute='_compute_szamlazott_ora',  store=True)
  szamlazhato_ora     = fields.Float(u'Számlázható óra',  digits=(16, 5), compute='_compute_szamlazhato_ora', store=True)
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                                        u'Gy.lap állapot', related='gyartasi_lap_id.state', readonly=True, store=True)
  # virtual fields
  sorszam             = fields.Integer(u'Sorszám', compute='_compute_sorszam')
  rendelesszam        = fields.Char(u'Rendelésszám', related='gyartasi_lap_id.rendelesszam', readonly=True)
  termekkod           = fields.Char(u'Tételkód', related='gyartasi_lap_id.termekkod', readonly=True)
  termeknev           = fields.Char(u'Terméknév', related='gyartasi_lap_id.cikknev', readonly=True)
  termekcsoport       = fields.Char(u'Termékcsoport', related='gyartasi_lap_id.termekcsoport', readonly=True)
  rendelt_db          = fields.Integer(u'Rendelt db', related='gyartasi_lap_id.rendelt_db', readonly=True)
  szamlazhato_db      = fields.Integer(u'Számlázható', related='gyartasi_lap_id.szamlazhato_db', readonly=True)
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True)
  dummy               = fields.Char(u'Dummy', compute='_compute_dummy')
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_sorszam(self):
    self.sorszam = self.gyartasi_lap_id.id

  @api.one
  @api.depends('gyartasi_lap_id', 'homogen_id')
  def _compute_name(self):
    self.name = str(self.gyartasi_lap_id.id)+'/'+self.homogen_id.homogen

  @api.one
  @api.depends('ossz_ido', 'beall_ido', 'korrekcios_ido', 'gyartasi_lap_id.rendelt_db', 'gyartasi_lap_id.modositott_db')
  def _compute_rendelt_ora(self):
    ossz_ido        = self.ossz_ido * self.gyartasi_lap_id.modositott_db / self.gyartasi_lap_id.rendelt_db
    korrekcios_ido  = self.korrekcios_ido * self.gyartasi_lap_id.modositott_db / self.gyartasi_lap_id.rendelt_db
    beall_ido       = self.beall_ido if self.gyartasi_lap_id.modositott_db > 0 else 0.0
    self.rendelt_ora = ossz_ido + beall_ido + korrekcios_ido

  @api.one
  @api.depends('ossz_ido', 'beall_ido', 'korrekcios_ido', 'gyartasi_lap_id.rendelt_db', 'gyartasi_lap_id.teljesitett_db')
  def _compute_teljesitett_ora(self):
    ossz_ido        = self.ossz_ido * self.gyartasi_lap_id.teljesitett_db / self.gyartasi_lap_id.rendelt_db
    korrekcios_ido  = self.korrekcios_ido * self.gyartasi_lap_id.teljesitett_db / self.gyartasi_lap_id.rendelt_db
    beall_ido       = self.beall_ido if self.gyartasi_lap_id.teljesitett_db > 0 else 0.0
    self.teljesitett_ora = ossz_ido + beall_ido + korrekcios_ido

  @api.one
  @api.depends('rendelt_ora', 'teljesitett_ora')
  def _compute_hatralek_ora(self):
    self.hatralek_ora = self.rendelt_ora - self.teljesitett_ora

  @api.one
  @api.depends('ossz_ido', 'beall_ido', 'korrekcios_ido', 'gyartasi_lap_id.rendelt_db', 'gyartasi_lap_id.szamlazott_db')
  def _compute_szamlazott_ora(self):
    ossz_ido        = self.ossz_ido * self.gyartasi_lap_id.szamlazott_db / self.gyartasi_lap_id.rendelt_db
    korrekcios_ido  = self.korrekcios_ido * self.gyartasi_lap_id.szamlazott_db / self.gyartasi_lap_id.rendelt_db
    beall_ido       = self.beall_ido if self.gyartasi_lap_id.szamlazott_db > 0 else 0.0
    self.szamlazott_ora = ossz_ido + beall_ido + korrekcios_ido

  @api.one
  @api.depends('szamlazott_ora', 'teljesitett_ora')
  def _compute_szamlazhato_ora(self):
    self.szamlazhato_ora = self.teljesitett_ora - self.szamlazott_ora

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_dummy(self):
    self.dummy = ''

  @api.one
  def toggle_sajat(self):
    self.sajat = not self.sajat
    return True

############################################################################################################################  Gylap Szefo művelet  ###
class LegrandSzefoMuvelet(models.Model):
  _name               = 'legrand.gylap_szefo_muvelet'
  _order              = 'gyartasi_lap_id, muveletszam'
  name                = fields.Char(u'Művelet', compute='_compute_name', store=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', readonly=True, auto_join=True)
  muveletszam         = fields.Integer(u'Műveletszám', required=True)
  muveletnev          = fields.Char(u'Műveletnév', required=True)
  fajlagos_db         = fields.Integer(u'Fajlagos db', default = 1, required=True)
  normaora            = fields.Float(u'Normaóra', digits=(16, 8), required=True)
  beall_ido           = fields.Float(u'Beállítási idő', digits=(16, 5), required=True)
  osszes_db           = fields.Integer(u'Összes db',                compute='_compute_osszes_db',   store=True)
  kesz_db             = fields.Integer(u'Kész db',                  compute='_compute_kesz_db',     store=True)
  hiany_db            = fields.Integer(u'Hiány db',                 compute='_compute_hiany',       store=True)
  osszes_ido          = fields.Float(u'Összes idő', digits=(16, 5), compute='_compute_osszes_ido',  store=True)
  osszes_ora          = fields.Float(u'Összes óra', digits=(16, 2), compute='_compute_osszes_ora',  store=True)
  kesz_ora            = fields.Float(u'Kész óra',   digits=(16, 2), compute='_compute_kesz_ora',    store=True)
  hiany_ora           = fields.Float(u'Hiány óra',  digits=(16, 2), compute='_compute_hiany',       store=True)
  # virtual fields
  muveletvegzes_ids   = fields.One2many('legrand.muveletvegzes',  'szefo_muvelet_id', u'Műveletvégzés', auto_join=True)
  active              = fields.Boolean(u'Aktív?', related='gyartasi_lap_id.active', readonly=True)

  @api.one
  @api.depends('gyartasi_lap_id', 'muveletszam')
  def _compute_name(self):
    self.name = str(self.gyartasi_lap_id.id)+' '+str(self.muveletszam)+' '+self.muveletnev

  @api.one
  @api.depends('gyartasi_lap_id.modositott_db', 'fajlagos_db')
  def _compute_osszes_db(self):
    self.osszes_db = self.gyartasi_lap_id.modositott_db * self.fajlagos_db

  @api.one
  @api.depends('muveletvegzes_ids', 'muveletvegzes_ids.mennyiseg')
  def _compute_kesz_db(self):
    self.kesz_db = sum(self.muveletvegzes_ids.mapped('mennyiseg'))

  @api.one
  @api.depends('osszes_db', 'kesz_db', 'osszes_ora', 'kesz_ora')
  def _compute_hiany(self):
    self.hiany_db  = self.osszes_db - self.kesz_db
    self.hiany_ora = self.osszes_ora - self.kesz_ora

  @api.one
  @api.depends('osszes_db', 'normaora')
  def _compute_osszes_ido(self):
    self.osszes_ido = self.osszes_db * self.normaora

  @api.one
  @api.depends('osszes_ido', 'beall_ido')
  def _compute_osszes_ora(self):
    self.osszes_ora = self.osszes_ido + self.beall_ido

  @api.one
  @api.depends('osszes_ora', 'osszes_db', 'kesz_db')
  def _compute_kesz_ora(self):
    if self.osszes_db:
      self.kesz_ora = self.osszes_ora * self.kesz_db / self.osszes_db
    else:
      self.kesz_ora = 0

############################################################################################################################  Műveletvégzés  ###
class LegrandMuveletvegzes(models.Model):
  _name               = 'legrand.muveletvegzes'
  _order              = 'id desc'
  szefo_muvelet_id    = fields.Many2one('legrand.gylap_szefo_muvelet', u'Művelet', required=True, auto_join=True)
  hely_id             = fields.Many2one('legrand.hely', string=u'Gyártási hely', domain=[('szefo_e', '=', True)], required=True, auto_join=True)
  szemely_id          = fields.Many2one('nexon.szemely', u'Dolgozó', required=True, auto_join=True)
  mennyiseg           = fields.Integer(u'Mennyiség', required=True)
  teljesitett_ora     = fields.Float(u'Teljesített óra', digits=(16, 5), compute='_compute_teljesitett_ora', store=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  nexon_azon          = fields.Integer(u'Személy Id')
  felvette_id         = fields.Many2one('res.users', u'Felvette', readonly=True, auto_join=True)
  ellenorizte_id      = fields.Many2one('res.users', u'Ellenőrizte', readonly=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', related='szefo_muvelet_id.gyartasi_lap_id', readonly=True, auto_join=True, store=True)
  gyartasi_hely_id    = fields.Many2one('legrand.hely',  u'Fő gyártási hely', related='szefo_muvelet_id.gyartasi_lap_id.gyartasi_hely_id', readonly=True, auto_join=True, store=True)
  minoseg             = fields.Char(u'Minőség', readonly=True)
  # virtual fields
  muveletnev          = fields.Char(u'Műveletnév',   related='szefo_muvelet_id.muveletnev', readonly=True)
  osszes_db           = fields.Integer(u'Összes db', related='szefo_muvelet_id.osszes_db', readonly=True)
  kesz_db             = fields.Integer(u'Kész db',   related='szefo_muvelet_id.kesz_db', readonly=True)

  @api.model
  def create(self, vals):
    vals['nexon_azon'] = self.env['nexon.szemely'].search([('id', '=', vals['szemely_id'])]).SzemelyId
    if 'felvette_id' not in vals:
      vals['felvette_id'] = self.env.user.id
    return super(LegrandMuveletvegzes, self).create(vals)

  @api.multi
  def write(self, vals):
    vals['nexon_azon'] = self.szemely_id.SzemelyId
    return super(LegrandMuveletvegzes, self).write(vals)

  @api.onchange('nexon_azon')
  def onchange_nexon_azon(self):
    self.szemely_id = self.env['nexon.szemely'].search([('SzemelyId', '=', self.nexon_azon)], limit=1, order='id').id

  @api.one
  @api.depends('mennyiseg', 'szefo_muvelet_id.osszes_db', 'szefo_muvelet_id.osszes_ido', 'szefo_muvelet_id.beall_ido')
  def _compute_teljesitett_ora(self):
    if self.szefo_muvelet_id and self.szefo_muvelet_id.osszes_db:
      self.teljesitett_ora = (self.szefo_muvelet_id.osszes_ido + self.szefo_muvelet_id.beall_ido) * self.mennyiseg / self.szefo_muvelet_id.osszes_db

  @api.one
  def jo(self):
    self.ellenorizte_id = self.env.user.id
    self.minoseg = 'jó'
    return True

  @api.one
  def rossz(self):
    self.ellenorizte_id = self.env.user.id
    self.minoseg = 'rossz'
    self.megjegyzes = self.megjegyzes = u'hibás ' + self.megjegyzes if self.megjegyzes else u'hibás'
    return True

############################################################################################################################  Feljegyzések  ###
class LegrandFeljegyzes(models.Model):
  _name               = 'legrand.feljegyzes'
  _order              = 'id desc'
  tema                = fields.Selection([('napi',u'Napi jelentés'),('egyeb',u'Egyéb')], u'Téma', default='napi', required=True)
  hely_id             = fields.Many2one('legrand.hely', u'Üzem', domain=[('belso_szallitas_e', '=', True)], auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikkszám', auto_join=True)
  feljegyzes          = fields.Char(u'Feljegyzés', required=True)
  gyartas_szunetel_e  = fields.Boolean(u'Gyártás szünetel?')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  @api.model
  def create(self, vals):
    felj = super(LegrandFeljegyzes, self).create(vals)
    if felj.gyartas_szunetel_e:
      # felj.gyartasi_lap_id.gyartas_szunetel_e = felj.gyartas_szunetel_e
      self.env.cr.execute("UPDATE legrand_gyartasi_lap SET gyartas_szunetel_e = true WHERE id = " + str(felj.gyartasi_lap_id.id))
    return felj

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.cikk_id = self.gyartasi_lap_id.cikk_id.id

############################################################################################################################  Jelenléti ív fej ###
class LegrandJelenletFej(models.Model):
  _name               = 'legrand.jelenletfej'
  _order              = 'ev desc, ho desc, nap desc, telephely_id'
  telephely_id        = fields.Many2one('szefo.telephely',  u'Telephely', required=True, domain=[('legrand_e', '=', True)])
  ev                  = fields.Char(u'Év')
  ho                  = fields.Char(u'Hónap')
  nap                 = fields.Char(u'Nap')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  jelenlet_ids        = fields.One2many('legrand.jelenlet',  'jelenletfej_id', u'Jelenlét', auto_join=True)
  count_jelenlet_ids  = fields.Integer(u'Jelenlét sorok db', compute='_compute_count_jelenlet_ids')
  director_e          = fields.Boolean(u'Director?', compute='_check_user_group')

  @api.model
  def create(self, vals):
    fej = super(LegrandJelenletFej, self).create(vals)
    for dolgozo in self.env['nexon.szemely'].search([('telephely_id', '=', fej.telephely_id.id)]):
      jelenlet_row = {
        'jelenletfej_id'    : fej.id,
        'dolgozo_id'        : dolgozo.id,
      }
      self.env['legrand.jelenlet'].create(jelenlet_row)
    return fej

  @api.one
  @api.depends('jelenlet_ids')
  def _compute_count_jelenlet_ids(self):
    self.count_jelenlet_ids = len(self.jelenlet_ids)

  @api.one
  def _check_user_group(self):
    self.director_e = self.env.user.has_group('legrand.group_legrand_director')

############################################################################################################################  Jelenléti ív  ###
class LegrandJelenlet(models.Model):
  _name               = 'legrand.jelenlet'
  _order              = 'id'
  jelenletfej_id      = fields.Many2one('legrand.jelenletfej',  u'Jelenlét fej', index=True, auto_join=True)
  telephely_id        = fields.Many2one('szefo.telephely',  u'Telephely', related='jelenletfej_id.telephely_id', readonly=True, store=True, auto_join=True)
  ev                  = fields.Char(u'Év',    related='jelenletfej_id.ev',  readonly=True, store=True)
  ho                  = fields.Char(u'Hónap', related='jelenletfej_id.ho',  readonly=True, store=True)
  nap                 = fields.Char(u'Nap',   related='jelenletfej_id.nap', readonly=True, store=True)
  dolgozo_id          = fields.Many2one('nexon.szemely', u'Dolgozó', required=True, domain="[('telephely_id', '=', telephely_id)]", auto_join=True)
  ora                 = fields.Float(u'Óra', digits=(16, 2))
  jogcim              = fields.Selection([('ledolgozott',u'Ledolgozott idő'),('szabadsag',u'Szabadság'),('rendkivuli',u'Rendkívüli szabadság'),('fizetesnelkuli',u'Fizetésnélküli szabadság'),('verado',u'Véradó szabadság'),
                                        ('betegseg',u'Betegség'),('igazolt',u'Igazolt távollét'),('igazolatlan',u'Igazolatlan távollét'),('pihenonap',u'Pihenőnap'),('keszenlet',u'Készenlét')],
                                        u'Jogcím', default='ledolgozott', required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  MEO jegyzőkönyv  ###
class LegrandMeoJegyzokonyv(models.Model):
  _name               = 'legrand.meo_jegyzokonyv'
  _order              = 'id desc'
#  _rec_name           = 'muveleti_szam'
  hely_id             = fields.Many2one('legrand.hely', string=u'Telephely', domain=[('szefo_e', '=', True)], required=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', required=True, auto_join=True)
#  name                = fields.Char(u'Művelet', readonly=True)
  visszaadott_db      = fields.Integer(u'Visszaadott darabszám')
  ellenorizte_id      = fields.Many2one('nexon.szemely', u'Ellenőrizte', auto_join=True)
  hiba_leirasa        = fields.Char(u'Hiba leírása', required=True)
  dolgozo_id          = fields.Many2one('nexon.szemely', u'Dolgozó', auto_join=True)
  gylap_szefo_muv_id1 = fields.Many2one('legrand.gylap_szefo_muvelet', u'Művelet', domain="[('gyartasi_lap_id', '=', gyartasi_lap_id)]", auto_join=True)
  gylap_szefo_muv_id2 = fields.Many2one('legrand.gylap_szefo_muvelet', u'2. Művelet', domain="[('gyartasi_lap_id', '=', gyartasi_lap_id)]", auto_join=True)
  intezkedesek        = fields.Char(u'Intézkedések')
  javitasi_ido        = fields.Float(u'Javításra fordított idő', digits=(16, 2))
  dolgozo_megjegyzese = fields.Char(u'Dolgozó megjegyzése')
  megjegyzes          = fields.Char(u'Megjegyzés')
  kulso_dokumentum    = fields.Char(u'Külső dokumentum')
  aql_megfelelo_e     = fields.Boolean(u'AQL szerint megfelelő?')
  logisztikai_hiba_e  = fields.Boolean(u'Logisztikai hiba?')
  szerelesi_hiba_e    = fields.Boolean(u'Szerelési hiba?')
  muszakvezeto_id     = fields.Many2one('nexon.szemely', u'Műszakvezető', auto_join=True)
  gyartaskozi_ell_id  = fields.Many2one('nexon.szemely', u'Gyártásközi ellenőr', auto_join=True)
  keszaru_ell_id      = fields.Many2one('nexon.szemely', u'Készáru ellenőr', auto_join=True)
  fioktelep_vezeto_id = fields.Many2one('nexon.szemely', u'Fióktelep vezető', auto_join=True)
  # virtual fields
  selejt_osszertek    = fields.Float(u'Selejt érték összesen', digits=(16, 0), compute='_compute_selejt_osszertek')
  meo_jkv_selejt_ids  = fields.One2many('legrand.meo_jkv_selejt',  'meo_jegyzokonyv_id', u'Selejtezett alkatrészek', auto_join=True)
  legrand_manager_e   = fields.Boolean(u'Legrand Manager?',   compute='_check_user_group')
  legrand_director_e  = fields.Boolean(u'Legrand director?',  compute='_check_user_group')

  @api.one
  @api.depends('meo_jkv_selejt_ids')
  def _compute_selejt_osszertek(self):
#    self.selejt_osszertek = sum(map(lambda r: r.ertek, self.meo_jkv_selejt_ids))
    self.selejt_osszertek = sum(self.meo_jkv_selejt_ids.mapped('ertek'))

  @api.one
  def _check_user_group(self):
    self.legrand_manager_e = self.env.user.has_group('legrand.group_legrand_manager')
    self.legrand_director_e = self.env.user.has_group('legrand.group_legrand_director')

############################################################################################################################  MEO jegyzőkönyv selejt  ###
class LegrandMeoJkvSelejt(models.Model):
  _name               = 'legrand.meo_jkv_selejt'
  _order              = 'id'
#  _rec_name           = 'muveleti_szam'
  meo_jegyzokonyv_id  = fields.Many2one('legrand.meo_jegyzokonyv',  u'MEO jegyzőkönyv', index=True, auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Alkatrész', required=True, auto_join=True)
  selejtezett_db      = fields.Integer(u'Selejtezett darabszám')
  bekerulesi_ar       = fields.Float(u'Bekerülési ár', digits=(16, 3))
  # virtual fields
  cikknev             = fields.Char(u'Név', related='cikk_id.cikknev', readonly=True)
  ertek               = fields.Float(u'Érték', digits=(16, 0), compute='_compute_ertek')

  @api.onchange('cikk_id')
  def onchange_cikk_id(self):
    self.bekerulesi_ar = self.cikk_id.bekerulesi_ar

  @api.one
  @api.depends('cikk_id', 'selejtezett_db')
  def _compute_ertek(self):
    self.ertek = self.selejtezett_db*self.bekerulesi_ar

############################################################################################################################  Legrand jegyzőkönyv  ###
class LegrandLgrJegyzokonyv(models.Model):
  _name               = 'legrand.lgr_jegyzokonyv'
  _order              = 'id desc'
  _rec_name           = 'jegyzokonyv_szama'
  jegyzokonyv_szama   = fields.Char(u'Jegyzőkönyv száma', required=True)
  hely_id             = fields.Many2one('legrand.hely', string=u'Gyártási hely', domain=[('szefo_e', '=', True)], required=True, auto_join=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', required=True, auto_join=True)
  sorozat             = fields.Integer(u'Sorozat', required=True)
#  name                = fields.Char(u'Művelet', readonly=True)
  normaora            = fields.Float(u'Normaóra', digits=(16, 2))
  vizsgalatok         = fields.Char(u'Vizsgálatok', required=True)
  eszrevetelek        = fields.Char(u'Észrevételek')
  megjegyzes          = fields.Char(u'Megjegyzés')
  kelt                = fields.Date(u'Kelt')
  # virtual fields
  termeknev           = fields.Char(u'Termék megnevezés', related='gyartasi_lap_id.cikk_id.cikknev', readonly=True)

############################################################################################################################  Lézer, tampon  ###
class LegrandLezerTampon(models.Model):
  _name               = 'legrand.lezer_tampon'
  _order              = 'id'
  _rec_name           = 'alkatresz_id'
  muvelet             = fields.Char(u'Művelet')
  termekkod           = fields.Char(u'Termékkód')
  termek_id           = fields.Many2one('legrand.cikk',  u'Termék', auto_join=True)
  alkatresz           = fields.Char(u'Alkatrészkód')
  alkatresz_id        = fields.Many2one('legrand.cikk',  u'Alkatrész', auto_join=True)
  pozicio             = fields.Char(u'Pozíció')
  rajz_felirat        = fields.Char(u'Rajz/Felirat')
  muvelet_db          = fields.Integer(u'Művelet db')
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  Gylap lézer, tampon  ###
class LegrandGylapLezerTampon(models.Model):
  _name               = 'legrand.gylap_lezer_tampon'
  _order              = 'gyartasi_lap_id, lezer_tampon_id'
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap', u'Gyártási lap', required=True,  auto_join=True)
  lezer_tampon_id     = fields.Many2one('legrand.lezer_tampon', u'Alkatrész', required=True, domain="[('termek_id', '=', cikk_id)]", auto_join=True)
  utasitas            = fields.Char(u'Utasítás')
  mennyiseg           = fields.Integer(u'Mennyiség')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                        u'Állapot', related='gyartasi_lap_id.state', readonly=True)
  gylap_lezer_sor_ids = fields.One2many('legrand.gylap_lezer_tampon_sor', 'gylap_lezer_tampon_id', u'Gylap lézer, tampon sor')

  cikk_id             = fields.Many2one('legrand.cikk',  u'Termék', related='gyartasi_lap_id.cikk_id', readonly=True, auto_join=True)
  modositott_db       = fields.Integer(u'Késztermék rendelt db', related='gyartasi_lap_id.modositott_db', readonly=True)
  carnet_e            = fields.Boolean(u'Carnet?', related='gyartasi_lap_id.carnet_e', readonly=True)
  hatarido            = fields.Date(u'Határidő', related='gyartasi_lap_id.hatarido', readonly=True, store=True)
  gyartasi_hely_id    = fields.Many2one('legrand.hely',  u'Fő gyártási hely', related='gyartasi_lap_id.gyartasi_hely_id', readonly=True, auto_join=True)

  muvelet             = fields.Char(u'Művelet', related='lezer_tampon_id.muvelet', readonly=True)
  pozicio             = fields.Char(u'Pozíció', related='lezer_tampon_id.pozicio', readonly=True)
  rajz_felirat        = fields.Char(u'Rajz/ felirat', related='lezer_tampon_id.rajz_felirat', readonly=True)
  muvelet_db          = fields.Integer(u'Művelet db', related='lezer_tampon_id.muvelet_db', readonly=True)
  egyeb_info          = fields.Char(u'Egyéb info', related='lezer_tampon_id.megjegyzes', readonly=True)

  osszes_db           = fields.Integer(u'Összes db', compute='_compute_db', store=True)
  kesz_db             = fields.Integer(u'Kész db',   compute='_compute_db', store=True)
  hiany_db            = fields.Integer(u'Hiány db',  compute='_compute_db', store=True)

  hatralek_ora        = fields.Float(u'Hátralék óra', digits=(16, 2), compute='_compute_ora')

  legrand_manager_e   = fields.Boolean(u'Legrand Manager?',   compute='_check_user_group')
  legrand_director_e  = fields.Boolean(u'Legrand director?',  compute='_check_user_group')

  @api.multi
  def write(self, vals):
    if 'mennyiseg' in vals and vals['mennyiseg']:
      sor_row = {
        'gylap_lezer_tampon_id' : self.id,
        'mennyiseg'             : vals['mennyiseg'],
        'megjegyzes'            : vals['megjegyzes'] if 'megjegyzes' in vals else False
      }
      self.env['legrand.gylap_lezer_tampon_sor'].create(sor_row)
    vals['mennyiseg']  = 0
    # vals['megjegyzes'] = False
    return super(LegrandGylapLezerTampon, self).write(vals)

  @api.one
  @api.depends('gyartasi_lap_id.modositott_db', 'lezer_tampon_id.muvelet_db', 'gylap_lezer_sor_ids.mennyiseg')
  def _compute_db(self):
    self.osszes_db = self.modositott_db * self.muvelet_db
    self.kesz_db   = sum(self.gylap_lezer_sor_ids.mapped('mennyiseg'))
    self.hiany_db  = self.osszes_db - self.kesz_db

  @api.one
  @api.depends('gyartasi_lap_id')
  def _compute_ora(self):
    if self.hiany_db:
      ora_osszes = sum(self.gyartasi_lap_id.gylap_homogen_ids.filtered(lambda r: r.homogen_id.homogen == '7121').mapped('rendelt_ora'))
      count = len(self.env['legrand.gylap_lezer_tampon'].search([('gyartasi_lap_id', '=', self.gyartasi_lap_id.id), ('muvelet','like','lézer')]))
      rendelt_ora = ora_osszes / count if count else 0
      self.hatralek_ora = rendelt_ora * self.hiany_db / self.osszes_db if self.osszes_db else 0
    else:
      self.hatralek_ora = 0

  @api.one
  def _check_user_group(self):
    self.legrand_manager_e = self.env.user.has_group('legrand.group_legrand_manager')
    self.legrand_director_e = self.env.user.has_group('legrand.group_legrand_director')

############################################################################################################################  Gylap lézer, tampon sor  ###
class LegrandGylapLezerTamponSor(models.Model):
  _name               = 'legrand.gylap_lezer_tampon_sor'
  gylap_lezer_tampon_id = fields.Many2one('legrand.gylap_lezer_tampon', u'Gylap lézer, tampon',  readonly=True, auto_join=True)
  mennyiseg           = fields.Integer(u'Mennyiség')
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  Lefoglalt  ###
class LegrandLefoglalt(models.Model):
  _name = 'legrand.lefoglalt'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám', readonly=True, auto_join=True)
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

############################################################################################################################  Anyagszükséglet  ###
class LegrandAnyagszukseglet(models.Model):
  _name = 'legrand.anyagszukseglet'
  _auto = False
  _order = 'gyartasi_lap_id, cikk_id'
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], u'Állapot')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Alkatrész', auto_join=True)
  rendelt             = fields.Float(u'Rendelt', digits=(16, 5))
  hatralek            = fields.Float(u'Hátralék',  digits=(16, 5))
  # virtual fields

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          row_number() over() AS id,
          gylap.state,
          gylap.id AS gyartasi_lap_id,
          line.cikk_id,
          gylap.modositott_db * line.beepules AS rendelt,
          gylap.hatralek_db * line.beepules AS hatralek
        FROM legrand_gyartasi_lap AS gylap
        JOIN legrand_bom_line     AS line ON line.bom_id = gylap.bom_id
        WHERE gylap.active AND gylap.state != 'kesz'
      )"""
      % (self._table)
    )

############################################################################################################################  Anyaghiány  ###
class LegrandAnyaghiany(models.Model):
  _name = 'legrand.anyaghiany'
  _auto = False
  _order = 'cikk_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Alkatrész', auto_join=True)
  szefo_keszlet       = fields.Float(u'SZEFO készlet', digits=(16, 2))
  mterv_igeny         = fields.Float(u'Műveletterv igénye',  digits=(16, 2))
  gyartas_igeny       = fields.Float(u'Gyártás igénye',  digits=(16, 2))
  mterv_gyartas_elter = fields.Float(u'Műveletterv + gyártás eltérés',  digits=(16, 2))
  gyartas_elter       = fields.Float(u'Gyártás eltérés',  digits=(16, 2))
  # virtual fields

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        WITH
        anyag AS (
          SELECT state, cikk_id, SUM(hatralek) AS hatralek FROM legrand_anyagszukseglet GROUP BY state, cikk_id
        ),
        igeny AS (
          SELECT keszlet.cikk_id, keszlet.szefo_keszlet,
            CASE WHEN gyartas.state IS NULL THEN 0.0 ELSE gyartas.hatralek END AS gyartas_igeny,
            CASE WHEN mterv.state   IS NULL THEN 0.0 ELSE mterv.hatralek   END AS mterv_igeny
          FROM legrand_vall_keszlet AS keszlet
          LEFT JOIN anyag AS gyartas ON gyartas.cikk_id = keszlet.cikk_id AND gyartas.state = 'gyartas'
          LEFT JOIN anyag AS mterv ON mterv.cikk_id = keszlet.cikk_id AND mterv.state = 'mterv'
        ),
        elter AS (
          SELECT cikk_id, szefo_keszlet, gyartas_igeny, mterv_igeny, szefo_keszlet - gyartas_igeny AS gyartas_elter , szefo_keszlet - gyartas_igeny - mterv_igeny AS mterv_gyartas_elter FROM igeny
        )
--        SELECT row_number() over() AS id, elter.* FROM elter WHERE mterv_gyartas_elter < 0 AND gyartas_igeny + mterv_igeny > 0
        SELECT row_number() over() AS id, elter.* FROM elter WHERE gyartas_igeny + mterv_igeny > 0
      )"""
      % (self._table)
    )

############################################################################################################################  Anyaghiány log  ###
class LegrandAnyaghianyLog(models.Model):
  _name               = 'legrand.anyaghiany_log'
  _order              = 'datum desc, cikk_id'
  datum               = fields.Date(u'Dátum')
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Alkatrész', auto_join=True)
  szefo_keszlet       = fields.Float(u'SZEFO készlet', digits=(16, 2))
  mterv_igeny         = fields.Float(u'Műveletterv igénye',  digits=(16, 2))
  gyartas_igeny       = fields.Float(u'Gyártás igénye',  digits=(16, 2))
  mterv_gyartas_elter = fields.Float(u'Műveletterv + gyártás eltérés',  digits=(16, 2))
  gyartas_elter       = fields.Float(u'Gyártás eltérés',  digits=(16, 2))
  # virtual fields

############################################################################################################################  Gyártási lap log  ###
class LegrandGyartasiLapLog(models.Model):
  _name               = 'legrand.gyartasi_lap_log'
  _order              = 'datum desc, gyartasi_lap_id'
  datum               = fields.Date(u'Dátum')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap', auto_join=True)
  state               = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')], u'Állapot', default='uj')
  gyartasi_hely_id    = fields.Many2one('legrand.hely',  u'Fő gyártási hely', auto_join=True)
  rendelesszam        = fields.Char(u'Rendelésszám')
  termekkod           = fields.Char(u'Termékkód')
  hatarido            = fields.Date(u'Határidő')
  hatralek_db         = fields.Integer(u'Hátralék db')
  rendelt_ora         = fields.Float(u'Rendelt óra',      digits=(16, 2))
  teljesitett_ora     = fields.Float(u'Teljesített óra',  digits=(16, 2))
  hatralek_ora        = fields.Float(u'Nyitott óra',      digits=(16, 2))
  szamlazott_ora      = fields.Float(u'Számlázott óra',   digits=(16, 2))
  szamlazhato_ora     = fields.Float(u'Számlázható óra',  digits=(16, 2))
  termekcsoport       = fields.Char(u'Termékcsoport')
  leallas_ok          = fields.Char(u'Gyártás leállásának oka')
  aktivitas           = fields.Char(u'Gyártás aktivitás')
  leallas_felelos     = fields.Char(u'Felelős')
  # virtual fields

############################################################################################################################  LIR users  ###
class LegrandLirUser(models.Model):
  _name               = 'legrand.lir_user'
  _order              = 'name'
  user_id             = fields.Many2one('res.users', u'User', required=True)
  qr                  = fields.Integer(u'QR kód', required=True)
  pin                 = fields.Integer(u'PIN kód', required=True)
  role                = fields.Selection([('kodolo',u'Kódoló'),('admin',u'Admin')], u'Szerepkör', default='kodolo', required=True)
  hely_id             = fields.Many2one('legrand.hely', string=u'Gyártási hely', domain=[('szefo_e', '=', True)], required=True, auto_join=True)
  # computed fields
  name                = fields.Char(u'Név',  related='user_id.partner_id.name', readonly=True, store=True)
  hely                = fields.Char(u'Hely', related='hely_id.name', readonly=True, store=True)

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
  ertek               = fields.Float(u'Érték', digits=(16, 2))
  datum               = fields.Datetime(u'Dátum')
  beepules            = fields.Float(u'Beépülés', digits=(16, 8))
  megjegyzes          = fields.Char(u'Megjegyzés')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási_lap id', auto_join=True)
  cikk_id             = fields.Many2one('legrand.cikk',  u'Cikk id', auto_join=True)
  bom_id              = fields.Many2one('legrand.bom',  u'Anyagjegyzék', auto_join=True)
  homogen_id          = fields.Many2one('legrand.homogen',  u'Homogén', auto_join=True)
  hely_id             = fields.Many2one('legrand.hely', u'Hely id', auto_join=True)
  hibakod_id          = fields.Many2one('legrand.hibakod', u'Hiba', auto_join=True)
#  # computed fields
  ora                 = fields.Float(u'Óra', digits=(16, 2), compute='_compute_ora', store=True)
#  # virtual fields
  carnet_e            = fields.Boolean(u'Carnet?', related='gyartasi_lap_id.carnet_e', readonly=True)
  gylap_state         = fields.Selection([('uj',u'Új'),('mterv',u'Műveletterv'),('gyartas',u'Gyártás'),('gykesz',u'Gyártás kész'),('kesz',u'Rendelés teljesítve')],
                        u'Állapot', related='gyartasi_lap_id.state', readonly=True)
  cikknev             = fields.Char(u'Cikknév', compute='_compute_cikknev')
  price               = fields.Float(u'Price', digits=(16, 3), compute='_compute_price')
  gyartasi_hely_id    = fields.Many2one('legrand.hely',  u'Fő gyártási hely', related='gyartasi_lap_id.gyartasi_hely_id', readonly=True)
  termekcsoport       = fields.Char(u'Termékcsoport', related='gyartasi_lap_id.termekcsoport', readonly=True)
  hibakod             = fields.Char(u'Hiba kódja',    related='hibakod_id.kod', readonly=True)
  hibanev             = fields.Char(u'Hiba leírása',  related='hibakod_id.nev', readonly=True)

  @api.one
  @api.depends('mennyiseg', 'gyartasi_lap_id')
  def _compute_ora(self):
    self.ora = self.gyartasi_lap_id.rendelt_ora * self.mennyiseg / self.gyartasi_lap_id.modositott_db if self.gyartasi_lap_id else 0.0

  @api.one
  @api.depends('cikk_id', 'bom_id')
  def _compute_cikknev(self):
    self.cikknev = self.cikk_id.cikknev if self.cikk_id else self.bom_id.cikk_id.cikknev

  @api.one
  @api.depends('cikk_id')
  def _compute_price(self):
#    if self.gyartasi_lap_id:
#      self.price = self.env['legrand.gylap_dbjegyzek'].search([('cikk_id', '=', self.cikk_id.id), ('gyartasi_lap_id', '=', self.gyartasi_lap_id.id)]).bekerulesi_ar
#    else:
      self.price = self.cikk_id.bekerulesi_ar
