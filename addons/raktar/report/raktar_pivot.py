# -*- coding: utf-8 -*-
# © 2016 Lorenzo Battistini - Agile Business Group
# © 2016 Csók Tibor - SZEFO Zrt.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import tools
from openerp import models, fields

class RaktarKeszletErtekel(models.Model):
  _name = 'raktar.keszlet_ertekel'
  _auto = False
  _rec_name = 'product_id'
  product_id          = fields.Many2one('product.product', string=u'Termék', readonly=True)
  location_id         = fields.Many2one('stock.location', string=u'Hely', readonly=True)
  qty                 = fields.Float(string=u'Mennyiség', readonly=True)
  in_date             = fields.Datetime(u'Érkezés ideje', readonly=True)
  sale_ok             = fields.Boolean(u'Értékesíthető?', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
      SELECT
          quant.id AS id,
          quant.product_id AS product_id,
          quant.location_id AS location_id,
          quant.qty AS qty,
          quant.in_date AS in_date,
          template.sale_ok AS sale_ok
      FROM stock_quant AS quant
      JOIN product_product prod ON prod.id = quant.product_id
      JOIN product_template template
          ON template.id = prod.product_tmpl_id
      )"""
      % (self._table)
    )
