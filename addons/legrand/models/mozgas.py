# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Mozgásfej  ###
class LegrandMozgasfej(models.Model):
  _name               = 'legrand.mozgasfej'
  _order              = 'id desc'
  _rec_name           = 'id'
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
    # self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_keszlet')
    # self.env.cr.execute('REFRESH MATERIALIZED VIEW legrand_vall_keszlet')
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
      ossz_uj_igeny_ids = self.env['legrand.anyagigeny'].search([('state', '=', 'uj'), ('forrashely_id', '=', depo_id)], order='id')
      for sor in self.mozgassor_ids:
        cikk_uj_igeny_ids = ossz_uj_igeny_ids.filtered(lambda r: r.cikk_id == sor.cikk_id)
        if cikk_uj_igeny_ids:
          mennyiseg = sor.mennyiseg
          for cikk_uj_igeny in cikk_uj_igeny_ids:
            hatralek = 0 if cikk_uj_igeny.mennyiseg - cikk_uj_igeny.erkezett <= 0 else cikk_uj_igeny.mennyiseg - cikk_uj_igeny.erkezett
            if hatralek == 0:
              continue
            erkezhet = mennyiseg if mennyiseg <= hatralek else hatralek
            cikk_uj_igeny.write({'erkezett': cikk_uj_igeny.erkezett + erkezhet})
            mennyiseg = mennyiseg - erkezhet
            if mennyiseg <= 0:
              break
    if self.mozgasnem == 'belso':
      ossz_uj_igeny_ids = self.env['legrand.anyagigeny'].search([('state', '=', 'uj'), ('forrashely_id', '=', self.forrashely_id.id), ('hely_id', '=', self.celallomas_id.id)], order='id')
      for sor in self.mozgassor_ids:
        cikk_uj_igeny_ids = ossz_uj_igeny_ids.filtered(lambda r: r.cikk_id == sor.cikk_id)
        if cikk_uj_igeny_ids:
          mennyiseg = sor.mennyiseg
          for cikk_uj_igeny in cikk_uj_igeny_ids:
            kuldheto = mennyiseg if mennyiseg <= cikk_uj_igeny.hatralek else cikk_uj_igeny.hatralek
            cikk_uj_igeny.write({'kuldott': cikk_uj_igeny.kuldott + kuldheto})
            mennyiseg = mennyiseg - kuldheto
            if mennyiseg <= 0:
              break
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
  raktar              = fields.Char(u'Raktár',      related='gyartasi_lap_id.raktar',     readonly=True)
  raklap_min          = fields.Char(u'Raklap min',  related='gyartasi_lap_id.raklap_min', readonly=True)
  raklap_max          = fields.Char(u'Raklap max',  related='gyartasi_lap_id.raklap_max', readonly=True)

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

