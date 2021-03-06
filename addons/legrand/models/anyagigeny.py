# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Anyagigénylés  ###
class LegrandAnyagigeny(models.Model):
  _name               = 'legrand.anyagigeny'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('uj',u'Új igény'),('nyugta',u'Nyugtázva')], u'Állapot', default='terv', readonly=True)
  #!!!                                                                                                            Depo bedrótozva
  forrashely_id       = fields.Many2one('legrand.hely', u'Honnan',     domain=[('belso_szallitas_e', '=', True)], default=4,  readonly=True, states={'terv': [('readonly', False)]}, required=True)
  hely_id             = fields.Many2one('legrand.hely', u'Hova',       domain=[('belso_szallitas_e', '=', True)],             readonly=True, states={'terv': [('readonly', False)]}, required=True)
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap',                                             readonly=True, states={'terv': [('readonly', False)]})
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám',                                                          readonly=True, states={'terv': [('readonly', False)]}, required=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2),                                                            readonly=True, states={'terv': [('readonly', False)]}, required=True)
  igeny_ok            = fields.Selection([('hiany',u'hiánypótlás'),('selejt',u'selejtpótlás')], 'Kérés oka', default='hiany', readonly=True, states={'terv': [('readonly', False)]}, required=True)
  megjegyzes          = fields.Char(u'Megjegyzés',                                                                                           states={'nyugta': [('readonly', True)]})
  erkezett            = fields.Float(u'Érkezett', digits=(16, 2),                                                             readonly=True, states={'uj': [('readonly', False)]})
  kuldott             = fields.Float(u'Küldött', digits=(16, 2),                                                              readonly=True, states={'uj': [('readonly', False)]})
  hatralek            = fields.Float(u'Hátralék', digits=(16, 2), compute='_compute_hatralek', store=True)
  megkerve_e          = fields.Boolean(u'Megkérve?',                                                                          readonly=True, states={'uj': [('readonly', False)]})
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  @api.model
  def create(self, vals):
    if 'mennyiseg' not in vals or vals['mennyiseg'] <= 0:
      raise exceptions.Warning(u'A mennyiség legyen nagyobb nullánál!')
    return super(LegrandAnyagigeny, self).create(vals)

  @api.multi
  def write(self, vals):
    if 'mennyiseg' in vals and vals['mennyiseg'] <= 0:
      raise exceptions.Warning(u'A mennyiség legyen nagyobb nullánál!')
    mennyiseg = vals['mennyiseg'] if 'mennyiseg' in vals else self.mennyiseg
    kuldott   = vals['kuldott']   if 'kuldott' in vals   else self.kuldott
    if kuldott >= mennyiseg:
      vals['state'] = 'nyugta'
    return super(LegrandAnyagigeny, self).write(vals)

  @api.onchange('gyartasi_lap_id')
  def onchange_gyartasi_lap_id(self):
    self.cikk_id = False
    ids = self.gyartasi_lap_id.bom_id.bom_line_ids.mapped('cikk_id.id')
    domain = [('id','in',ids)] if self.gyartasi_lap_id else []
    return {'domain': {'cikk_id': domain}}

  @api.one
  @api.depends('mennyiseg', 'kuldott')
  def _compute_hatralek(self):
    self.hatralek = 0 if self.mennyiseg - self.kuldott < 0 else self.mennyiseg - self.kuldott

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

  @api.one
  def megkerve(self):
    self.megkerve_e = True
    return True
