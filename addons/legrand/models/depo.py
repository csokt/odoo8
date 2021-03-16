# -*- coding: utf-8 -*-

# from odoo import tools, models, fields, api, exceptions
from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Depó raktáros bevételezés  ###
class LegrandDepobevet(models.Model):
  _name               = 'legrand.depobevet'
  _order              = 'id'
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám', required=True)
  cikkszam            = fields.Char(u'Cikkszám',   related='cikk_id.cikkszam', store=True)
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2), required=True)
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

############################################################################################################################  Bevételezés összesítő  ###
class LegrandDepobevetOssz(models.Model):
  _name = 'legrand.depobevetossz'
  _auto = False
  _rec_name = 'cikk_id'
  _order = 'cikk_id'
  cikk_id             = fields.Many2one('legrand.cikk', string=u'Cikkszám')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2))
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT
          cikk_id AS id,
          cikk_id,
          sum(mennyiseg) AS mennyiseg
        FROM legrand_depobevet
        GROUP BY cikk_id
      )"""
      % (self._table)
    )

############################################################################################################################  Depó kimérés  ###
class LegrandDepokimer(models.Model):
  _name               = 'legrand.depokimer'
  _order              = 'id desc'
  name                = fields.Char(u'Megnevezés', compute='_compute_name', store=True)
  state               = fields.Selection([('terv',u'Tervezet'),('kimer',u'Kimérés'),('kesz',u'Lezárva')],u'Állapot', default='terv')
  hely_id             = fields.Many2one('legrand.hely', u'Üzem', domain=[('belso_szallitas_e', '=', True)], readonly=True, states={'terv': [('readonly', False)]}, required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  mozgasfej_id        = fields.Many2one('legrand.mozgasfej',  u'Szállítólevél', readonly=True)
  # virtual fields
  kimergylap_ids      = fields.One2many('legrand.kimergylap', 'depokimer_id', u'Gyártási lapok')
  kimercikk_ids       = fields.One2many('legrand.kimercikk', 'depokimer_id', u'Alkatrészek')

  @api.one
  @api.depends('hely_id', 'kimergylap_ids')
  def _compute_name(self):
    if self.hely_id:
      self.name = self.hely_id.name+' ('+', '.join(self.kimergylap_ids.mapped(lambda r: str(r.gyartasi_lap_id.id)))+')'

  @api.one
  def alkatresz_lista(self):
    self.kimercikk_ids.unlink()
    for kimergylap in self.kimergylap_ids:
      for alk in kimergylap.gyartasi_lap_id.bom_id.bom_line_ids:
        row = {
          'depokimer_id'    : self.id,
          'cikk_id'         : alk.cikk_id.id,
          'mennyiseg'       : kimergylap.gyartasi_lap_id.modositott_db * alk.beepules,
        }
        self.kimercikk_ids.create(row)
    return True

  @api.one
  def kimeres_indit(self):
    self.alkatresz_lista()
    self.state = 'kimer'
    return True

  @api.one
  def szallitolevel(self):
    return True

  @api.one
  def state2terv(self):
    self.state = 'terv'
    return True

############################################################################################################################  Kimérés gyártási lap  ###
class LegrandKimergylap(models.Model):
  _name               = 'legrand.kimergylap'
  _order              = 'id'
  _rec_name           = 'gyartasi_lap_id'
  depokimer_id        = fields.Many2one('legrand.depokimer',  u'Kimér')
  gyartasi_lap_id     = fields.Many2one('legrand.gyartasi_lap',  u'Gyártási lap')
  # virtual fields

############################################################################################################################  Kimérés cikkek  ###
class LegrandKimercikk(models.Model):
  _name               = 'legrand.kimercikk'
  _order              = 'id'
  _rec_name           = 'cikk_id'
  depokimer_id        = fields.Many2one('legrand.depokimer',  u'Kimér')
  cikk_id             = fields.Many2one('legrand.cikk', u'Cikkszám')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2))
  kimerve_e           = fields.Boolean(u'Kimérve?')
  # virtual fields
  cikknev             = fields.Char(u'Cikknév', related='cikk_id.cikknev', readonly=True)
  # virtual fields

