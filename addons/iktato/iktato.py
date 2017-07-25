# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions

import logging
_logger = logging.getLogger(__name__)

class IktatoKonyv(models.Model):
  _name               = 'iktato.konyv'
  _inherit            = 'mail.thread'
  _order              = 'id desc'
  name                = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  irany               = fields.Selection([('be',u'BE'), ('ki','KI')], u'Irány', required=True, default=lambda self: self.env.context.get('irany', ''))
  tipus               = fields.Selection([('level',u'levél'), ('szamla',u'számla'), ('szerz',u'szerződés')], u'Típus', required=True, default=lambda self: self.env.context.get('tipus', ''))
  iratszam_be         = fields.Char(u'Bejövő irat száma', default='')
  iratszam_ki         = fields.Char(u'Kimenő irat száma', compute='_compute_iratszam_ki', store=True)
  iratszam            = fields.Char(u'Irat száma', compute='_compute_iratszam', store=True)
  elozmeny_id         = fields.Many2one('iktato.konyv', u'Előzmény')
  targy               = fields.Text(u'Tárgy', default='',  required=True)
  partner_id          = fields.Many2one('res.partner',   u'Partner', required=True,  auto_join=False)
  osztaly_id          = fields.Many2one('hr.department', u'Osztály', required=False, auto_join=False)
  eloado_id           = fields.Many2one('hr.employee',   u'Előadó',  required=False, auto_join=False)
  melleklet           = fields.Integer(u'Mellékletek')
  kezeles_mod         = fields.Char(u'Kezelés módja', default='')
  megjegyzes          = fields.Text(u'Megjegyzés', default='')
  irat_kelte          = fields.Date(u'Irat kelte')
  regi_sorszam        = fields.Char(u'Régi sorszám', default='')
  ugy_id              = fields.Many2one('iktato.ugy',  u'Ügy',  required=False, auto_join=False)
  szerzodes_id        = fields.Many2one('iktato.szerzodes', u'Szerződés')
  megtekintes         = fields.Integer(u'Megtekintési szint', default=0, compute='_compute_megtekintes', store=True, track_visibility='onchange')
  # virtual fields
  megtekintes_novelheto = fields.Boolean(u'Megtekintési szint növelheto',  compute='_compute_megtekintes_novelheto')
  osztaly_ids         = fields.Many2many('hr.department', string=u'Másolatot kap')
  ugysorszam          = fields.Integer('Ügy', related='ugy_id.ugysorszam' )

  @api.one
  @api.depends('ugy_id')
  def _compute_megtekintes(self):
    if self.ugy_id:
      self.megtekintes = self.ugy_id.megtekintes

  @api.one
  @api.depends('ugy_id')
  def _compute_iratszam_ki(self):
    if self.irany == 'ki':
      if not isinstance(self.id, models.NewId):
        if self.ugy_id:
          Konyv = self.env['iktato.konyv']
          konyv_count = Konyv.search_count([('ugy_id', '=', self.ugy_id.id), ('irany', '=', 'ki')])
          self.iratszam_ki = str(self.id)+'/'+str(self.ugy_id.ugysorszam)+'-'+str(konyv_count)
        else:
          self.iratszam_ki = str(self.id)
      else:
        self.iratszam_ki = 'Mentés után kap értéket!'

  @api.one
  @api.depends('iratszam_be', 'iratszam_ki')
  def _compute_iratszam(self):
    if self.irany == 'be':
      self.iratszam = self.iratszam_be
    else:
      self.iratszam = self.iratszam_ki

  @api.one
  @api.depends('megtekintes')
  def _compute_megtekintes_novelheto(self):
    self.megtekintes_novelheto = self.megtekintes < self.env.user.security_clearance

  @api.one
  @api.depends('iratszam', 'targy', 'partner_id')
  def _compute_name(self):
    if not isinstance(self.id, models.NewId):
      self.name = str(self.id)+' | '+self.iratszam+' - '+self.partner_id.name[:20]+' - '+self.targy[:30]

  @api.one
  def megtekintesi_szint_csokkentes(self):
    self.megtekintes = self.megtekintes - 1

  @api.one
  def megtekintesi_szint_noveles(self):
    self.megtekintes = self.megtekintes + 1

  @api.onchange('elozmeny_id')
  def on_change_elozmeny_id(self):
    self.targy      = self.elozmeny_id.targy
    self.partner_id = self.elozmeny_id.partner_id

  @api.one
  def ugygeneralas(self):
    Ugy = self.env['iktato.ugy']
    ugy_id = Ugy.create({'ugysorszam': self.id, 'targy': self.targy, 'osztaly_id': self.osztaly_id.id, 'partner_id': self.partner_id.id, 'megtekintes': self.megtekintes})
    self.ugy_id = ugy_id
    return True

class Ugy(models.Model):
  _name       = 'iktato.ugy'
  _inherit    = 'mail.thread'
  _order      = 'ugysorszam desc'
  ugysorszam  = fields.Integer(u'Ügy')
  name        = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  targy       = fields.Text(u'Tárgy',  required=False)
  partner_id  = fields.Many2one('res.partner',   u'Partner', required=True, auto_join=False)
  osztaly_id  = fields.Many2one('hr.department', u'Osztály', required=False, auto_join=False)
  eloado_id   = fields.Many2one('hr.employee',   u'Előadó',  required=False, auto_join=False)
  megjegyzes  = fields.Text(u'Megjegyzés')
  megtekintes = fields.Integer(u'Megtekintési szint', default=0, track_visibility='onchange')
  # virtual fields
  megtekintes_novelheto = fields.Boolean(u'Megtekintési szint növelheto',  compute='_compute_megtekintes_novelheto')
  konyv_ids             = fields.One2many('iktato.konyv', 'ugy_id', u'Ügyhöz tartozó levelek')

  @api.one
  @api.depends('megtekintes')
  def _compute_megtekintes_novelheto(self):
    self.megtekintes_novelheto = self.megtekintes < self.env.user.security_clearance

  @api.one
  def megtekintesi_szint_noveles(self):
    self.megtekintes = self.megtekintes + 1
    Konyv  = self.env['iktato.konyv']
    iratok = Konyv.search([('ugy_id', '=', self.id)])
    iratok.write({'megtekintes': self.megtekintes})

  @api.one
  def megtekintesi_szint_csokkentes(self):
    self.megtekintes = self.megtekintes - 1
    Konyv  = self.env['iktato.konyv']
    iratok = Konyv.search([('ugy_id', '=', self.id)])
    iratok.write({'megtekintes': self.megtekintes})

  @api.one
  @api.depends('targy', 'partner_id')
  def _compute_name(self):
    self.name = str(self.ugysorszam)+' - '+self.partner_id.name[:20]+' - '+self.targy[:30]

class SzerzodesTipus(models.Model):
  _name               = 'iktato.szerz_tipus'
  _order              = 'id'
  name                = fields.Char(u'Szerződés típus')

class SzerzodesUtem(models.Model):
  _name               = 'iktato.szerz_utem'
  _order              = 'id'
  name                = fields.Char(u'Szerződés ütemezés')

class SzerzodesTemplate(models.AbstractModel):
  _name               = 'iktato.szerzodes_template'
  name                = fields.Char(u'Azonosító', compute='_compute_name', store=True)
  szerzodesszam       = fields.Char(u'Szerződés száma')
  szerz_tipus_id      = fields.Many2one('iktato.szerz_tipus', u'Szerződés típusa', required=True)
  targy               = fields.Char(u'Szerződés tárgya', required=True)
  partner_id          = fields.Many2one('res.partner',   u'Partner', required=True)
  penznem             = fields.Selection([('huf',u'HUF'), ('eur','EUR')], u'Pénznem', required=True, default='huf')
  osszeg              = fields.Char(u'Szerződött összeg', required=True)
  utem_osszeg         = fields.Char(u'Ütemezés szerinti összeg')
  kelte               = fields.Date(u'Szerződés kelte', required=True)
  kezdete             = fields.Date(u'Szerződés kezdete')
  vege                = fields.Date(u'Szerződés vége')
  szerz_utem_id       = fields.Many2one('iktato.szerz_utem', u'Teljesítés ütemezése')
  hatarido            = fields.Date(u'Teljesítési határidő')
  megjegyzes          = fields.Char(u'Megjegyzés')
  megtekintes         = fields.Integer(u'Megtekintési szint', default=0, track_visibility='onchange')

  @api.one
  @api.depends('szerzodesszam', 'targy', 'partner_id')
  def _compute_name(self):
    if not isinstance(self.id, models.NewId):
      szerzodesszam = self.szerzodesszam+' - ' if self.szerzodesszam else ''
      self.name = str(self.id)+' | '+szerzodesszam+self.partner_id.name[:20]+' - '+self.targy[:30]

class Szerzodes(models.Model):
  _name               = 'iktato.szerzodes'
  _inherit            = ['iktato.szerzodes_template', 'mail.thread']
  _order              = 'id desc'
  iktatokonyv_ids     = fields.One2many('iktato.konyv', 'szerzodes_id', u'Levelek', readonly=True)
  szerzodes_log_ids   = fields.One2many('iktato.szerzodes_log', 'szerzodes_id', u'Szerződés történet', readonly=True)
  # virtual fields
  megtekintes_novelheto = fields.Boolean(u'Megtekintési szint növelheto',  compute='_compute_megtekintes_novelheto')

  @api.multi
  def write(self, vals):
    if 'megtekintes' not in vals:
      old = self.read()[0]
      del old['id']
      old['partner_id']     = self.partner_id.id
      old['szerz_tipus_id'] = self.szerz_tipus_id.id
      old['szerz_utem_id']  = self.szerz_utem_id.id
      old['szerzodes_id']   = self.id
      old['rogzites']       = self.write_date
      self.env['iktato.szerzodes_log'].create(old)
    super(Szerzodes, self).write(vals)
    return True

  @api.one
  @api.depends('megtekintes')
  def _compute_megtekintes_novelheto(self):
    self.megtekintes_novelheto = self.megtekintes < self.env.user.security_clearance

  @api.one
  def megtekintesi_szint_csokkentes(self):
    self.megtekintes = self.megtekintes - 1

  @api.one
  def megtekintesi_szint_noveles(self):
    self.megtekintes = self.megtekintes + 1

class SzerzodesLog(models.Model):
  _name               = 'iktato.szerzodes_log'
  _inherit            = 'iktato.szerzodes_template'
  _order              = 'id desc'
  szerzodes_id        = fields.Many2one('iktato.szerzodes',   u'Szerződés', required=True)
  rogzites            = fields.Datetime(u'Rögzítés ideje')
