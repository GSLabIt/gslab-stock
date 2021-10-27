import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)


class OoopsStockQuantityReportDifference(models.Model):
    _name = 'ooops.report.stock.quantity.difference'
    _description = 'Ooops Stock Quantity Difference Report'

    product_id = fields.Many2one(
        string='Product',
        comodel_name='product.product',
        ondelete='cascade',
        readonly=True
    )
    name = fields.Char(string='Name', related='product_id.display_name')
    incoming = fields.Float('Qty Incoming', default=0, readonly=True)
    outgoing = fields.Float('Qty Outgoing', default=0, readonly=True)
    supposed_stock = fields.Float('Supposed Stock', default=0, readonly=True)
    quant_stock_ontable = fields.Float('Stock Qty on Table', default=0, readonly=True)
    difference = fields.Float('Difference', default=0, readonly=True)
    float_compare = fields.Integer('Float compare', default=0, readonly=True)

    @api.model
    def action_stock_difference(self, check_picking_type=False):
        _logger.warn('Start stock quantity difference report ..')
        start = time.time()
        action = self.env.ref(
            'ooops_stock_quantity_difference.action_stock_quantity_difference'
        ).read()[0]

        self._fill_products()

        if check_picking_type:
            self._fill_incoming_picking_type()
            self._fill_outgoing_picking_type()
            action['display_name'] = "Stock Qty - Picking Type Discrepancy"
        else:
            self._fill_incoming()
            self._fill_outgoing()

        self._fill_supposed_stock()
        self._sql_quant_stock_ontable()
        self._fill_diffrence()
        self._fill_float_compare()
        _logger.warn(
            'Check quantity done in {} sec.'.format(round(time.time() - start))
        )

        return action

    def _fill_products(self):
        self._cr.execute(
            """
            INSERT INTO ooops_report_stock_quantity_difference (
                product_id, incoming, outgoing, supposed_stock,
                quant_stock_ontable, create_uid,create_date)
                SELECT DISTINCT product_id, 0, 0, 0, 0, %s, %s
                FROM stock_move_line AS sml
                INNER JOIN product_product AS pp ON sml.product_id = pp.id
                INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                WHERE pt.type = 'product' AND pp.active = true
                ORDER BY product_id
            ON CONFLICT (product_id)
            DO UPDATE SET
                incoming = 0,
                outgoing = 0,
                supposed_stock = 0,
                quant_stock_ontable = 0,
                difference = 0,
                float_compare = 0,
                write_uid = %s,
                write_date = %s;
                """,
            (
                self.env.user.id,
                fields.Datetime.now(),
                self.env.user.id,
                fields.Datetime.now(),
            )
        )

    def _fill_incoming_picking_type(self):
        _sql_incoming = """
            UPDATE ooops_report_stock_quantity_difference
            SET incoming = incoming.qty_done
            FROM (
                SELECT sml.product_id,
                SUM(sml.qty_done) AS qty_done
                FROM stock_move_line AS sml, stock_move AS sm
                WHERE
                    sml.move_id = sm."id" AND
                    sml."state"='done' AND (
                        sml.location_id in (
                            SELECT "id" FROM stock_location
                            WHERE "usage" in ('inventory', 'production')
                        )
                        OR sm.picking_id in (
                            SELECT id FROM stock_picking AS sp WHERE
                            sp.picking_type_id IN (
                                SELECT "id" FROM stock_picking_type WHERE code = 'incoming'
                            )
                        )
                    )
                GROUP BY sml.product_id
            ) AS incoming
            WHERE incoming.product_id = ooops_report_stock_quantity_difference.product_id;
        """
        self._cr.execute(_sql_incoming)

    def _fill_outgoing_picking_type(self):
        _sql_outgoing = """
            UPDATE ooops_report_stock_quantity_difference
            SET outgoing = outgoing.qty_done
            FROM (
                SELECT sml.product_id,
                SUM(sml.qty_done) AS qty_done
                FROM stock_move_line AS sml, stock_move AS sm
                WHERE
                    sml.move_id = sm."id" AND
                    sml."state"='done' AND (
                        sml.location_dest_id in (
                            SELECT "id" FROM stock_location
                            WHERE "usage" in ('inventory', 'production')
                        )
                        OR sm.picking_id in (
                            SELECT id FROM stock_picking AS sp WHERE
                            sp.picking_type_id IN (
                                SELECT "id" FROM stock_picking_type WHERE code = 'outgoing'
                            )
                        )
                    )
                GROUP BY sml.product_id
            ) AS outgoing
            WHERE outgoing.product_id = ooops_report_stock_quantity_difference.product_id;
        """
        self._cr.execute(_sql_outgoing)

    def _fill_incoming(self):
        _sql_outgoing = """
            UPDATE ooops_report_stock_quantity_difference
            SET incoming = incoming.qty_done
            FROM (
                SELECT sml.product_id,
                SUM(sml.qty_done) AS qty_done
                FROM stock_move_line AS sml
                WHERE
                    sml."state"='done' AND
                    sml.location_dest_id in (
                        SELECT "id" FROM stock_location
                        WHERE "usage" = 'internal'
                    )
                GROUP BY sml.product_id
            ) AS incoming
            WHERE
                incoming.product_id = ooops_report_stock_quantity_difference.product_id;
        """
        self._cr.execute(_sql_outgoing)

    def _fill_outgoing(self):
        _sql_incoming = """
            UPDATE ooops_report_stock_quantity_difference
            SET outgoing = outgoing.qty_done
            FROM (
                SELECT sml.product_id,
                SUM(sml.qty_done) AS qty_done
                FROM stock_move_line AS sml
                WHERE
                    sml."state"='done' AND
                    sml.location_id in (
                        SELECT "id" FROM stock_location
                        WHERE "usage" = 'internal'
                    )
                GROUP BY sml.product_id
            ) AS outgoing
            WHERE outgoing.product_id = ooops_report_stock_quantity_difference.product_id;
        """
        self._cr.execute(_sql_incoming)

    def _fill_supposed_stock(self):
        _sql_fill_supposed_stock = """
            UPDATE ooops_report_stock_quantity_difference
            SET supposed_stock = incoming - outgoing;
        """
        self._cr.execute(_sql_fill_supposed_stock)

    def _sql_quant_stock_ontable(self):
        _sql_quant_stock_ontable = """
            UPDATE ooops_report_stock_quantity_difference SET quant_stock_ontable = sq.qty
            FROM (
                SELECT product_id, sum(stock_quant.quantity) as qty
                FROM stock_quant
                WHERE
                location_id in (SELECT "id" FROM stock_location WHERE "usage" in ('internal'))
                GROUP BY product_id
            ) AS sq
            WHERE sq.product_id = ooops_report_stock_quantity_difference.product_id;
        """
        self._cr.execute(_sql_quant_stock_ontable)

    def _fill_diffrence(self):
        _sql_fill_diffrence = """
            UPDATE ooops_report_stock_quantity_difference
            SET difference = supposed_stock - quant_stock_ontable;
        """
        self._cr.execute(_sql_fill_diffrence)

    def _fill_float_compare(self):
        for rec in self.search([('difference', '!=', 0)]):
            rec.write({
                'float_compare':
                    float_compare(
                        rec.supposed_stock,
                        rec.quant_stock_ontable,
                        precision_rounding=rec.product_id.uom_id.rounding,
                    )
            })

    def action_balance_qty(self):
        product_ids = self.search([('float_compare', '!=', 0)]).mapped('product_id.id')
        if not product_ids:
            raise ValidationError(_('No stock quant to fix'))

        self.with_delay()._action_balance_qty(product_ids)

        self.env.user.notify_info(
            message="Job: Fix stock quant queued.", title=None, sticky=False
        )
        return self._context

    @job
    def _action_balance_qty(self, product_ids):
        _logger.warn('Start stock quantity fix ..')
        start = time.time()
        _stock_move_to_fix = (
            "select product_id,location_id,location_dest_id,qty_done,lot_id "
            "from stock_move_line "
            "where state='done' AND product_id in %s;"
        )
        self._cr.execute(_stock_move_to_fix, [tuple(product_ids)])
        stock_move_lines = self._cr.dictfetchall()
        _logger.warn('Found {} products to fix'.format(len(product_ids)))

        stock_quants = self.env['stock.quant'].search([
            ('product_id', 'in', product_ids)
        ])
        if stock_quants:
            stock_quants.write({'quantity': 0})

        for line in stock_move_lines:
            product_id = line['product_id']
            location_id = line['location_id']
            location_dest_id = line['location_dest_id']
            lot_id = line.get('lot_id')
            qty_done = line['qty_done']

            quant = self.env['stock.quant'].search(
                [
                    ('product_id', '=', product_id),
                    ('location_id', '=', location_id),
                    ('lot_id', '=', lot_id),
                ],
                limit=1,
            )
            if quant:
                quant.write({'quantity': quant.quantity - qty_done})
            else:
                self.env['stock.quant'].create({
                    'product_id': product_id,
                    'location_id': location_id,
                    'lot_id': lot_id,
                    'quantity': -qty_done
                })

            quant = self.env['stock.quant'].search(
                [
                    ('product_id', '=', product_id),
                    ('location_id', '=', location_dest_id),
                    ('lot_id', '=', lot_id),
                ],
                limit=1,
            )
            if quant:
                quant.write({'quantity': quant.quantity + qty_done})
            else:
                self.env['stock.quant'].create({
                    'product_id': product_id,
                    'location_id': location_dest_id,
                    'lot_id': lot_id,
                    'quantity': qty_done
                })

        _logger.warn('Fix quantity done in {} sec.'.format(round(time.time() - start)))

        self.action_stock_difference()

        self.env.user.notify_success(
            message="Job: Fix stock quant, sucessfully done.", title=None, sticky=True
        )

    _sql_constraints = [
        ('product_id_uniq', 'unique(product_id)', 'Product already in table'),
    ]
