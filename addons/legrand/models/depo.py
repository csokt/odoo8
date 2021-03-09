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

