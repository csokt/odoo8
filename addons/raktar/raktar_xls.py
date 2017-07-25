# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Üzem picking  ###
class RaktarUzemPicking(models.Model):
  def sajat_raktar(self):
    return self.env.user.sajat_raktar_id.id

  _name               = 'raktar.uzem_picking'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('kesz',u'Rögzítve')], 'Állapot',
                        default='terv',
                        readonly=True
                        )
  uzem_id             = fields.Many2one('raktar.mozgasnem', u'Üzem',
                        default=sajat_raktar,
                        required=True
                        )
  forrashely_id       = fields.Many2one('raktar.mozgasnem', u'Forráshely',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True,
                        domain="[('uzem_raktar_valaszt','=',True)]"
                        )
  celallomas_id       = fields.Many2one('raktar.mozgasnem', u'Célállomás helye',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True,
                        domain="[('uzem_raktar_valaszt','=',True)]"
                        )
  forrasdokumentum    = fields.Char(u'Forrásdokumentum')
  megjegyzes          = fields.Char(u'Megjegyzés')
  # virtual fields
  name                = fields.Integer(u'ID', compute='_compute_name')
  uzem_move_ids       = fields.One2many('raktar.uzem_move', 'uzem_picking_id', u'Tételek',
                        readonly=True, states={'terv': [('readonly', False)]}
                        )

  @api.one
  @api.depends()
  def _compute_name(self):
#    self.name = str(self.id)
    self.name = self.id

  @api.one
  def import_impex(self):
    for impex in self.env['raktar.impex'].search([]):
      move_row = {
        'uzem_picking_id'   : self.id,
#        'gyartasi_lap_id' : impex.gyartasi_lap_id.id,
        'gyartasi_lap_sorsz': impex.sorszam,
        'product_id'        : impex.product_id.id,
        'mennyiseg'         : impex.mennyiseg,
      }
      self.env['raktar.uzem_move'].create(move_row)
    return True

  @api.one
  def export_impex(self):
    self.env['raktar.impex'].search([]).unlink()
    for move in self.uzem_move_ids:
      impex_row = {
        'sorszam'         : move.gyartasi_lap_id.id,
        'rendelesszam'    : move.gyartasi_lap_id.rendelesszam,
        'termekkod'       : move.product_id.cikkszam,
        'homogen'         : '',
#        'db'              : move.mennyiseg,
        'mennyiseg'       : move.mennyiseg,
        'ertek'           : 0.0,
        'gyartasi_lap_id' : move.gyartasi_lap_id.id,
        'product_id'      : move.product_id.id,
        'homogen_id'      : False,
      }
      self.env['raktar.impex'].create(impex_row)
    return True

  @api.one
  def state2kesz(self):
    self.state  = 'kesz'
    return True

############################################################################################################################  Üzem move  ###
class RaktarUzemMove(models.Model):
  def sajat_raktar(self):
    return self.env.user.sajat_raktar_id.id

  _name               = 'raktar.uzem_move'
  _order              = 'id desc'
  _rec_name           = 'product_id'
  uzem_picking_id     = fields.Many2one('raktar.uzem_picking',  u'Fej ID')
  state               = fields.Selection([('terv',u'Tervezet'),('kesz',u'Rögzítve')], 'Állapot',
                        related='uzem_picking_id.state', store=True,
                        readonly=True
                        )
  uzem_id             = fields.Many2one('raktar.mozgasnem', u'Üzem',
                        default=sajat_raktar,
                        required=True
                        )
  forrashely_id       = fields.Many2one('raktar.mozgasnem', u'Forráshely',
                        compute='_compute_forrashely_id', store=True,
                        readonly=True
                        )
  celallomas_id       = fields.Many2one('raktar.mozgasnem', u'Célállomás helye',
                        compute='_compute_celallomas_id', store=True,
                        readonly=True
                        )
  gyartasi_lap_sorsz  = fields.Integer(u'Sorszám')
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap',
                        compute='_compute_gyartasi_lap_id', store=True,
                        readonly=True
                        )
  product_id          = fields.Many2one('product.product',  u'Termék',
                        required=True
                        )
  valtozat            = fields.Char(u'Változat', default='')
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2),
                        required=True
                        )

  @api.one
  @api.depends('uzem_picking_id')
  def _compute_forrashely_id(self):
    self.forrashely_id = self.uzem_picking_id.forrashely_id.id

  @api.one
  @api.depends('uzem_picking_id')
  def _compute_celallomas_id(self):
    self.celallomas_id = self.uzem_picking_id.celallomas_id.id

  @api.one
  @api.depends('gyartasi_lap_sorsz')
  def _compute_gyartasi_lap_id(self):
    self.gyartasi_lap_id = self.gyartasi_lap_sorsz

  @api.onchange('gyartasi_lap_sorsz')
  def onchange_gyartasi_lap_sorsz(self):
    self.product_id = False
    ids = self.gyartasi_lap_id.muveletterv_id.muvelet_cikk_ids.mapped('product_id.id')
    domain = [('id','in',ids)] if self.gyartasi_lap_sorsz else []
    return {'domain': {'product_id': domain}}

############################################################################################################################  Üzem készlet  ###
class RaktarUzemKeszlet(models.Model):
  _name = 'raktar.uzem_keszlet'
  _auto = False
  _rec_name = 'product_id'
  _order = 'uzem_id, product_id, valtozat, hely_id'
  uzem_id             = fields.Many2one('raktar.mozgasnem', u'Üzem', readonly=True)
  hely_id             = fields.Many2one('raktar.mozgasnem', u'Raktárhely', readonly=True)
  product_id          = fields.Many2one('product.product', string=u'Termék', readonly=True)
  valtozat            = fields.Char(u'Változat', readonly=True)
  raktaron            = fields.Float(string=u'Raktáron', readonly=True)
  tervezett           = fields.Float(string=u'Várható', readonly=True)
  false               = fields.Boolean(u'Hamis', readonly=True)

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
      SELECT
        row_number() over() AS id,
        uzem_id,
        hely_id,
        product_id,
        valtozat,
        sum(raktaron) AS raktaron,
        sum(tervezett) AS tervezett,
        FALSE AS false
      FROM (
        SELECT uzem_id,celallomas_id AS hely_id, product_id, valtozat, sum(CASE WHEN state='kesz' THEN mennyiseg ELSE 0 END) AS raktaron, sum(mennyiseg) AS tervezett
        FROM raktar_uzem_move
        GROUP BY uzem_id,product_id,valtozat,celallomas_id
        UNION ALL
        SELECT uzem_id,forrashely_id hely_id, product_id, valtozat, sum(CASE WHEN state='kesz' THEN -mennyiseg ELSE 0 END) AS raktaron, sum(-mennyiseg) AS tervezett
        FROM raktar_uzem_move
        GROUP BY uzem_id,product_id,valtozat,forrashely_id
      ) AS move
      GROUP BY uzem_id,product_id,valtozat,hely_id
      )"""
      % (self._table)
    )
############################################################################################################################  Anyagigénylés  ###
class RaktarIgenyTemplate(models.AbstractModel):
  _name               = 'raktar.igeny_template'
  _order              = 'id desc'
  tipus               = fields.Selection([('igeny',u'Igénylés'), ('selejt',u'Selejtküldés')], u'Típus',
                        default=lambda self: self.env.context.get('tipus', ''),
                        required=True
                        )
  state               = fields.Selection([('terv',u'Tervezet'),('uj',u'Új igény'),('nyugta',u'Nyugtázva'),('szallit',u'Szállítás'),('kesz',u'Lezárt')], u'Állapot',
                        default='terv',
                        readonly=True
                        )
  sorszam             = fields.Integer(u'Sorszám',
                        readonly=True, states={'terv': [('readonly', False)]}
                        )
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap',
                        compute='_compute_gyartasi_lap_id', store=True,
                        readonly=True
                        )
  product_id          = fields.Many2one('product.product',  u'Termék',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  darab               = fields.Integer(u'Darab',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  kuldott_db          = fields.Integer(u'Küldött',
                        readonly=True, states={'szallit': [('readonly', False)], 'nyugta': [('readonly', False)]}
                        )
  kapott_db           = fields.Integer(u'Kapott',
                        readonly=True, states={'szallit': [('readonly', False)]}
                        )
  kuldott_ossz_db     = fields.Integer(u'Küldött összes',
                        readonly=True
                        )
  kapott_ossz_db      = fields.Integer(u'Kapott összes',
                        readonly=True
                        )
  hely_id             = fields.Many2one('raktar.mozgasnem', u'Üzem',
                        domain=[('belso_szallitas', '=', True)],
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  igeny_ok            = fields.Selection([('hiany',u'hiánypótlás'),('selejt',u'selejtpótlás')], 'Kérés oka',
                        default='hiany',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  selejt_ok_id        = fields.Many2one('raktar.hibakod', u'Hibakód',
                        states={'kesz': [('readonly', True)]}
                        )
  megjegyzes          = fields.Char(u'Megjegyzés',
                        states={'kesz': [('readonly', True)]}
                        )
  # virtual fields
  rendelesszam        = fields.Char(u'Rendelésszám', related='gyartasi_lap_id.rendelesszam',
                        readonly=True,
                        required=True
                        )
  termekkod           = fields.Char(u'Termékkód',    related='gyartasi_lap_id.termekkod',
                        readonly=True,
                        required=True
                        )

  @api.one
  @api.depends('sorszam')
  def _compute_gyartasi_lap_id(self):
    self.gyartasi_lap_id = self.sorszam

  @api.onchange('sorszam')
  def onchange_sorszam(self):
    self.product_id = False
    ids = self.gyartasi_lap_id.muveletterv_id.muvelet_cikk_ids.mapped('product_id.id')
#    ids = self.gyartasi_lap_id.gyartas_cikk_ids.filtered(lambda r: r.beepules > 0.0).mapped('product_id.id')
    domain = [('id','in',ids)] if self.sorszam else []
    return {'domain': {'product_id': domain}}

  @api.onchange('kuldott_db')
  def onchange_kuldott_db(self):
    if self.kuldott_db > 0: self.kapott_db = 0

  @api.onchange('kapott_db')
  def onchange_kapott_db(self):
    if self.kapott_db > 0: self.kuldott_db = 0

  @api.one
  def rogzit(self):
    if self.tipus == 'igeny':
#      if self.igeny_ok == 'selejt':
#        copy = self.copy({'tipus': 'selejt', 'state': 'terv', 'megjegyzes': False})
      self.state = 'uj'
    elif self.tipus == 'selejt':
      self.state = 'nyugta'
    return True

  @api.one
  def state2nyugta(self):
    self.state = 'nyugta'
    return True

  @api.one
  def state2kesz(self):
    if self.kuldott_ossz_db != self.kapott_ossz_db:
      raise exceptions.Warning(u'A küldött és kapott darabszámoknak egyeznie kell!')
    self.state = 'kesz'
    return True


class RaktarIgeny(models.Model):
  _name               = 'raktar.igeny'
  _inherit            = 'raktar.igeny_template'
  igeny_log_ids       = fields.One2many('raktar.igeny_log', 'igeny_id', u'Anyagigénylés történet', readonly=True)

  @api.multi
  def write(self, vals):
#    if 'kuldott_db' in vals and 'kapott_db' in vals:
#      raise exceptions.Warning(u'Küldés és fogadás egyszerre nem lehetséges!')
    old = self.read()[0]
    del old['id']
    old['igeny_id']           = self.id
    old['gyartasi_lap_id']    = self.gyartasi_lap_id.id
    old['product_id']         = self.product_id.id
    old['hely_id']            = self.hely_id.id
    old['selejt_ok_id']       = self.selejt_ok_id.id
    old['rogzitesi_ido']      = self.write_date
    old['rogzito_uid']        = self.write_uid.id
    kuld_ossz, kap_ossz       = self.kuldott_ossz_db, self.kapott_ossz_db
    if 'kuldott_db' in vals and vals['kuldott_db'] != 0:
      vals['kuldott_ossz_db'] = kuld_ossz = self.kuldott_ossz_db + vals['kuldott_db']
      if self.darab           < vals['kuldott_ossz_db']:  raise exceptions.Warning(u'Az összes küldött darab meghaladja az eredeti mennyiséget!')
      vals['kapott_db']       = 0
      vals['state']           = 'szallit'
    elif 'kapott_db' in vals and vals['kapott_db'] != 0:
      vals['kapott_ossz_db']  = kap_ossz = self.kapott_ossz_db + vals['kapott_db']
      if self.darab           < vals['kapott_ossz_db']:   raise exceptions.Warning(u'Az összes kapott darab meghaladja az eredeti mennyiséget!')
      vals['kuldott_db']      = 0
      vals['state']           = 'szallit'
    if kuld_ossz > 0 and kuld_ossz == kap_ossz:
      vals['state']           = 'nyugta'
      if self.darab           == kuld_ossz:  vals['state'] = 'kesz'
    if self.state != 'terv':
      self.env['raktar.igeny_log'].create(old)
    super(RaktarIgeny, self).write(vals)
    return True

class RaktarIgenyLog(models.Model):
  _name               = 'raktar.igeny_log'
  _inherit            = 'raktar.igeny_template'
  igeny_id            = fields.Many2one('raktar.igeny',   u'Anyagigénylés', required=True)
  rogzitesi_ido       = fields.Datetime(u'Rögzítés ideje')
  rogzito_uid         = fields.Many2one('res.users', u'Rögzítette')

############################################################################################################################  Selejtkövet fej  ###
class RaktarSelejtkovet(models.Model):
  _name               = 'raktar.selejtkovet'
  _order              = 'id desc'
  state               = fields.Selection([('terv',u'Tervezet'),('folytat',u'Folyamatban'),('zarhat',u'Lezárható'),('kesz',u'Lezárt')], 'Állapot',
                        default='terv',
                        readonly=True
                        )
  sorszam             = fields.Integer(u'Sorszám',
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  gyartasi_lap_id     = fields.Many2one('raktar.gyartasi_lap',  u'Gyártási lap',
                        compute='_compute_gyartasi_lap_id', store=True,
                        readonly=True
                        )
  gyartas_id          = fields.Many2one('raktar.gyartas',  u'Gyártási művelet',
                        domain="[('gyartasi_lap_id','=',sorszam)]",
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True,
                        )
  product_id          = fields.Many2one('product.product',  u'Szétszerelt alkatrész',
                        related='gyartas_id.product_id', store=True,
                        readonly=True
                        )
  gyartasi_hely_id    = fields.Many2one('raktar.mozgasnem', u'Gyártási hely',
                        related='gyartas_id.gyartasi_hely_id', store=True,
                        readonly=True
                        )
  mennyiseg           = fields.Float(u'Mennyiség', digits=(16, 2),
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  szamolt             = fields.Float(u'Számolt', digits=(16, 2),
                        readonly=True
                        )
  hely_id             = fields.Many2one('raktar.mozgasnem', u'Üzem',
                        readonly=True
                        )
  bontasi_hely_id     = fields.Many2one('raktar.mozgasnem', u'Szétszerelési hely',
                        domain=[('belso_szallitas', '=', True)],
                        readonly=True, states={'terv': [('readonly', False)]},
                        required=True
                        )
  munka               = fields.Selection([('szet',u'Szétszerelés'), ('ujra','Újragyártás')], u'Munka',
                        readonly=True, states={'terv': [('readonly', False)]}
                        )
  megjegyzes          = fields.Char(u'Megjegyzés',
                        states={'kesz': [('readonly', True)]}
                        )
  picking_id          = fields.Many2one('stock.picking',  u'Kiszedés',    readonly=True)
  picking2_id         = fields.Many2one('stock.picking',  u'Kiszedés 2',  readonly=True)
  production_id       = fields.Many2one('mrp.production', u'Újragyártás', readonly=True)
  # virtual fields
  rendelesszam        = fields.Char(u'Rendelésszám', related='gyartasi_lap_id.rendelesszam',
                        readonly=True,
                        required=True
                        )
  termekkod           = fields.Char(u'Termékkód',    related='gyartasi_lap_id.termekkod',
                        readonly=True,
                        required=True
                        )
  selejtkovet_tet_ids = fields.One2many('raktar.selejtkovet_tet', 'selejtkovet_id', u'Tételek',
                        readonly=True, states={'folytat': [('readonly', False)]}
                        )
  picking_state       = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('waiting', 'Waiting Another Operation'), ('confirmed', 'Waiting Availability'),
                                          ('partially_available', 'Partially Available'), ('assigned', 'Ready to Transfer'), ('done', 'Transferred')],
                                          u'Kiszedés állapot', related='picking_id.state', readonly=True)
  picking2_state      = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('waiting', 'Waiting Another Operation'), ('confirmed', 'Waiting Availability'),
                                          ('partially_available', 'Partially Available'), ('assigned', 'Ready to Transfer'), ('done', 'Transferred')],
                                          u'Kiszedés 2 állapot', related='picking2_id.state', readonly=True)
  production_state    = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'), ('ready', 'Ready to Produce'),
                                          ('in_production', 'Production Started'), ('done', 'Done')], 'Újragyártás állapot', related='production_id.state')

  @api.one
  @api.depends('sorszam')
  def _compute_gyartasi_lap_id(self):
    self.gyartasi_lap_id, self.gyartas_id = self.sorszam, False

  @api.one
  def rogzit(self):
    if self.state == 'folytat': return True
    for bom_line in self.gyartas_id.bom_id.bom_line_ids:
      qty = self.mennyiseg*bom_line.product_qty/self.gyartas_id.bom_id.product_qty
      tetel_row = {
        'selejtkovet_id'  : self.id,
        'product_id'      : bom_line.product_id.id,
        'max_mennyiseg'   : round(qty, 0),
        'mennyiseg'       : round(qty, 0),
      }
      if qty >= 1.0: self.env['raktar.selejtkovet_tet'].create(tetel_row)
    self.state = 'folytat'
    return True

  @api.one
  def veglegesites(self):
    if self.state == 'zarhat': return True
    Log = self.env['szefo.log']
    Log.create({'loglevel': 'info', 'name': u'Szétszerelés végrehajtása', 'module': 'raktar', 'table': 'selejtkovet', 'rowid': self.id})
    selejt    = self.env['raktar.mozgasnem'].search([('azon', '=', 'selejt')])
    termeles  = self.env['raktar.mozgasnem'].search([('azon', '=', 'termeles')])
    picking_row = {
      'picking_type_id' : selejt.picking_type_id.id,
      'origin'          : u'Szétszerelés ID: '+str(self.id),
      'move_type'       : 'direct',
    }
    picking = self.env['stock.picking'].create(picking_row)
    move_row = {
      'picking_id'      : picking.id,
      'product_id'      : self.gyartas_id.product_id.id,
      'name'            : self.gyartas_id.product_id.name,
      'product_uom'     : self.gyartas_id.product_id.uom_id.id,
      'product_uom_qty' : self.mennyiseg,
      'location_id'     : self.bontasi_hely_id.location_id.id,
      'location_dest_id': termeles.location_id.id
    }
    self.env['stock.move'].create(move_row)
    picking.action_confirm()
    picking.force_assign()
    self.picking_id  = picking.id

    picking_row = {
      'picking_type_id' : selejt.picking_type_id.id,
      'origin'          : u'Szétszerelés ID: '+str(self.id),
      'move_type'       : 'direct',
    }
    picking2 = self.env['stock.picking'].create(picking_row)
    for tetel in self.selejtkovet_tet_ids:
      move_row = {
        'picking_id'      : picking2.id,
        'product_id'      : tetel.product_id.id,
        'name'            : tetel.product_id.name,
        'product_uom'     : tetel.product_id.uom_id.id,
        'product_uom_qty' : tetel.mennyiseg,
        'location_id'     : termeles.location_id.id,
        'location_dest_id': self.bontasi_hely_id.location_id.id,
      }
      if tetel.mennyiseg >0.0: self.env['stock.move'].create(move_row)
    picking2.action_confirm()
    self.picking2_id  = picking2.id

    # A kiválasztott félkésztermék/termék gyártásra adása.
    prod_row = {
      'product_id'      : self.gyartas_id.product_id.id,
      'bom_id'          : self.gyartas_id.bom_id.id,
      'product_qty'     : self.mennyiseg,
      'product_uom'     : self.gyartas_id.product_id.uom_id.id,
#      'date_planned'    : self.gyartas_id.tervezett_datum,
#      'origin'          : self.gyartas_id.gyartasi_lap_id.rendelesszam+' ['+str(gyartas.gyartasi_lap_id.id)+']',
      'origin'          : u'Szétszerelés ID: '+str(self.id),
      'location_src_id' : self.gyartas_id.gyartasi_hely_id.location_id.id,
      'location_dest_id': self.gyartas_id.gyartasi_hely_id.location_id.id
      }
    production = self.env['mrp.production'].create(prod_row)
    production.signal_workflow('button_confirm')
    self.production_id = production.id

    self.state = 'zarhat'
    return True

  @api.one
  def export_impex(self):
    self.env['raktar.impex'].search([]).unlink()
    for tetel in self.selejtkovet_tet_ids:
      impex_row = {
        'sorszam'         : tetel.selejtkovet_id.gyartasi_lap_id.id,
        'rendelesszam'    : tetel.selejtkovet_id.gyartasi_lap_id.rendelesszam,
        'termekkod'       : tetel.product_id.cikkszam,
        'homogen'         : '',
        'mennyiseg'       : tetel.mennyiseg,
        'ertek'           : 0.0,
        'gyartasi_lap_id' : tetel.selejtkovet_id.gyartasi_lap_id.id,
        'product_id'      : tetel.product_id.id,
        'homogen_id'      : False,
      }
      self.env['raktar.impex'].create(impex_row)
    return True

############################################################################################################################  Selejtkövet tétel  ###
class RaktarSelejtkovetTet(models.Model):
  _name               = 'raktar.selejtkovet_tet'
  _order              = 'id'
  _rec_name           = 'product_id'
  selejtkovet_id      = fields.Many2one('raktar.selejtkovet',  u'Fej ID')
  product_id          = fields.Many2one('product.product',  u'Termék',
                        readonly=True
                        )
  max_mennyiseg       = fields.Float(u'Visszanyerhető', digits=(16, 2),
                        readonly=True
                        )
  mennyiseg           = fields.Float(u'Visszanyert', digits=(16, 2),
                        required=True
                        )
  # virtual fields

############################################################################################################################  Hibakód  ###
class RaktarHibakod(models.Model):
  _name               = 'raktar.hibakod'
  _order              = 'kod'
  name                = fields.Char(u'Megnevezés', compute='_compute_name', store=True)
  kod                 = fields.Char(u'Hibakód', required=True)
  nev                 = fields.Char(u'Név', required=True)
  active              = fields.Boolean(u'Aktív?', default=True)

  @api.one
  @api.depends('kod', 'nev')
  def _compute_name(self):
    if self.kod and self.nev: self.name = self.kod+' - '+self.nev

