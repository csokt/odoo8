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
  state               = fields.Selection([('terv',u'Tervezet'),('kimer',u'Kimérés'),('kesz',u'Lezárva')],u'Állapot', default='terv')
  hely_id             = fields.Many2one('legrand.hely', u'Üzem', domain=[('belso_szallitas_e', '=', True)], readonly=True, states={'terv': [('readonly', False)]}, required=True)
  megjegyzes          = fields.Char(u'Megjegyzés')
  mozgasfej_id        = fields.Many2one('legrand.mozgasfej',  u'Szállítólevél', readonly=True)
  # virtual fields
  gyartasi_lapok      = fields.Char(u'Gyártási lapok', compute='_compute_gyartasi_lapok')
  kimergylap_ids      = fields.One2many('legrand.kimergylap', 'depokimer_id', u'Gyártási lapok')
  kimercikk_ids       = fields.One2many('legrand.kimercikk', 'depokimer_id', u'Alkatrészek')

  @api.one
  @api.depends('hely_id', 'kimergylap_ids')
  def _compute_gyartasi_lapok(self):
    self.gyartasi_lapok = ', '.join(self.kimergylap_ids.mapped(lambda r: str(r.gyartasi_lap_id.id)))

  @api.one
  def alkatresz_lista(self):
    cikkek = {}
    self.kimercikk_ids.unlink()
    for kimergylap in self.kimergylap_ids:
      for bom_line in kimergylap.gyartasi_lap_id.bom_id.bom_line_ids:
        cikkszam = bom_line.cikk_id.cikkszam
        mennyiseg = kimergylap.gyartasi_lap_id.modositott_db * bom_line.beepules
        if cikkszam in cikkek:
          cikkek[cikkszam]['mennyiseg'] += mennyiseg
        else:
          row = {
            'depokimer_id'    : self.id,
            'cikk_id'         : bom_line.cikk_id.id,
            'mennyiseg'       : mennyiseg,
          }
          cikkek[cikkszam] = row

    depo_id = self.env['legrand.hely'].search([('azonosito','=','depo')]).id
    ossz_uj_igeny_ids = self.env['legrand.anyagigeny'].search([('state', '=', 'uj'), ('forrashely_id', '=', depo_id), ('hely_id', '=', self.hely_id.id)])
    for cikk_uj_igeny in ossz_uj_igeny_ids:
      cikkszam = cikk_uj_igeny.cikk_id.cikkszam
      mennyiseg = cikk_uj_igeny.hatralek
      if cikkszam in cikkek:
        cikkek[cikkszam]['mennyiseg'] += mennyiseg
      else:
        row = {
          'depokimer_id'    : self.id,
          'cikk_id'         : cikk_uj_igeny.cikk_id.id,
          'mennyiseg'       : mennyiseg,
        }
        cikkek[cikkszam] = row

    for cikkszam in sorted(cikkek):
      self.kimercikk_ids.create(cikkek[cikkszam])
    return True

  @api.one
  def kimeres_indit(self):
    self.alkatresz_lista()
    self.state = 'kimer'
    return True

  @api.one
  def szallitolevel(self):
    depo_id = self.env['legrand.hely'].search([('azonosito','=','depo')]).id
    mozgasfej = {
      'mozgasnem'         : 'belso',
      'forrashely_id'     : depo_id,
      'celallomas_id'     : self.hely_id.id,
      'forrasdokumentum'  : u'Gy.lap(ok): '+self.gyartasi_lapok,
      'megjegyzes'        : self.megjegyzes,
    }
    mozgasfej_id = self.env['legrand.mozgasfej'].create(mozgasfej)

    for kimercikk in self.kimercikk_ids:
      mozgassor = {
        'mozgasfej_id'    : mozgasfej_id.id,
        'cikk_id'         : kimercikk.cikk_id.id,
        'mennyiseg'       : kimercikk.mennyiseg,
      }
      self.env['legrand.mozgassor'].create(mozgassor)

    self.mozgasfej_id = mozgasfej_id.id
    # raise exceptions.Warning(mozgasfej_id.id)
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

