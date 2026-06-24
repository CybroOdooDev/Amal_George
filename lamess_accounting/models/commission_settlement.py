# -*- coding: utf-8 -*-
"""Settlement mensile delle righe bonus M3."""

from collections import defaultdict

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.modules import module as odoo_module


class LamessCommissionSettlement(models.Model):
    _name = "lamess.commission.settlement"
    _description = "Lamess Commission Settlement"
    _order = "period_id desc, partner_id"
    _rec_name = "display_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    display_name = fields.Char(string="Riferimento", compute="_compute_display_name", store=True)
    period_id = fields.Many2one(
        "lamess.commission.period",
        string="Periodo",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Consulente",
        required=True,
        ondelete="restrict",
        index=True,
        domain=[("x_is_networker", "=", True)],
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Azienda",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
    )
    state = fields.Selection([
        ("draft", "Bozza"),
        ("confirmed", "Confermato"),
        ("posted", "Accreditato wallet"),
        ("cancelled", "Annullato"),
    ], string="Stato", default="draft", required=True, tracking=True, index=True)
    line_ids = fields.One2many(
        "lamess.commission.settlement.line",
        "settlement_id",
        string="Dettaglio bonus",
        copy=False,
    )
    gross_amount = fields.Float(
        string="Totale lordo bonus (€)",
        compute="_compute_totals",
        store=True,
        digits=(16, 2),
    )
    runtime_line_count = fields.Integer(string="Righe runtime", compute="_compute_totals", store=True)
    confirmed_at = fields.Datetime(string="Confermato il", readonly=True)
    posted_at = fields.Datetime(string="Accreditato il", readonly=True)
    posted_by_id = fields.Many2one("res.users", string="Accreditato da", readonly=True)
    payout_trace_line_ids = fields.One2many(
        "lamess.payout.request.settlement.line",
        "settlement_id",
        string="Tracciabilita payout",
        copy=False,
    )
    payout_request_count = fields.Integer(string="Richieste payout", compute="_compute_payout_traceability")
    payout_allocated_amount = fields.Float(
        string="Importo collegato a payout (€)",
        compute="_compute_payout_traceability",
        digits=(16, 2),
    )

    _settlement_unique_partner_period = models.Constraint(
        "UNIQUE(period_id, partner_id)",
        "Esiste gia un settlement per questo consulente e periodo.",
    )

    @api.depends("period_id", "partner_id", "state")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "%s · %s · %s" % (
                record.partner_id.display_name or "Consulente",
                record.period_id.display_name or "-",
                dict(record._fields["state"].selection).get(record.state, record.state or ""),
            )

    @api.depends("line_ids.amount_eur")
    def _compute_totals(self):
        for record in self:
            record.gross_amount = sum(record.line_ids.mapped("amount_eur"))
            record.runtime_line_count = len(record.line_ids)

    @api.depends("payout_trace_line_ids.allocated_amount", "payout_trace_line_ids.payout_request_id.state")
    def _compute_payout_traceability(self):
        for record in self:
            active_lines = record.payout_trace_line_ids.filtered(
                lambda line: line.payout_request_id.state not in ("rejected", "cancelled")
            )
            record.payout_request_count = len(active_lines.mapped("payout_request_id"))
            record.payout_allocated_amount = sum(active_lines.mapped("allocated_amount"))

    @api.constrains("gross_amount", "state")
    def _check_posted_amount(self):
        for record in self:
            if record.state in ("confirmed", "posted") and record.gross_amount <= 0:
                raise ValidationError(_("Un settlement confermato deve avere un importo positivo."))

    @api.model
    def _get_runtime_period(self, period=None):
        if period:
            return period
        runtime_model = self.env["lamess.m3.bonus.runtime.line"]
        return runtime_model._get_default_period()

    @api.model
    def _commission_batch_size(self, context_key, default):
        raw_value = self.env.context.get(context_key)
        if raw_value is None:
            raw_value = self.env["ir.config_parameter"].sudo().get_param(
                "lamess_accounting.%s" % context_key,
                default,
            )
        try:
            return max(1, int(raw_value))
        except (TypeError, ValueError):
            return default

    @api.model
    def _iter_commission_batches(self, record_ids, batch_size):
        record_ids = list(record_ids or [])
        for offset in range(0, len(record_ids), batch_size):
            yield record_ids[offset:offset + batch_size]

    @api.model
    def _commission_commit_batch_if_requested(self):
        if (
            self.env.context.get("commission_batch_autocommit")
            and not tools.config["test_enable"]
            and not getattr(odoo_module, "current_test", False)
        ):
            self.env.cr.commit()
            self.env.invalidate_all()

    @api.model
    def _get_runtime_recipient_ids(self, period, partner_ids=None):
        params = [period.id]
        partner_filter = ""
        if partner_ids:
            partner_filter = "AND recipient_id = ANY(%s)"
            params.append(list(set(partner_ids)))
        query = """
            SELECT DISTINCT recipient_id
              FROM lamess_m3_bonus_runtime_line
             WHERE period_id = %s
               AND state = 'generated'
               AND recipient_id IS NOT NULL
               AND amount_eur > 0.0
               {partner_filter}
             ORDER BY recipient_id
            """.format(partner_filter=partner_filter)
        self.env.cr.execute(query, params)
        return [row[0] for row in self.env.cr.fetchall()]

    @api.model
    def generate_from_m3_runtime(self, period=None, partner_ids=None, lock_runtime=True):
        """Crea settlement draft raggruppando le righe runtime M3 generate."""
        period = self._get_runtime_period(period=period)
        if period.state == "closed":
            raise UserError(_("Non puoi generare settlement su un periodo commissionale chiuso."))
        recipient_ids = self._get_runtime_recipient_ids(period, partner_ids=partner_ids)
        batch_size = self._commission_batch_size("commission_settlement_batch_size", 50)
        settlements = self.browse()
        for batch_partner_ids in self._iter_commission_batches(recipient_ids, batch_size):
            settlements |= self._generate_from_m3_runtime_partner_batch(
                period=period,
                partner_ids=batch_partner_ids,
                lock_runtime=lock_runtime,
            )
            self._commission_commit_batch_if_requested()
        return settlements

    @api.model
    def _generate_from_m3_runtime_partner_batch(self, period, partner_ids, lock_runtime=True):
        domain = [
            ("period_id", "=", period.id),
            ("state", "=", "generated"),
            ("recipient_id", "!=", False),
            ("amount_eur", ">", 0.0),
            ("recipient_id", "in", partner_ids),
        ]

        runtime_lines = self.env["lamess.m3.bonus.runtime.line"].search(domain, order="recipient_id, id")
        grouped = defaultdict(lambda: self.env["lamess.m3.bonus.runtime.line"])
        for line in runtime_lines:
            grouped[line.recipient_id.id] |= line

        settlements = self.browse()
        for partner_id, lines in grouped.items():
            partner = self.env["res.partner"].browse(partner_id)
            settlement = self.search([
                ("period_id", "=", period.id),
                ("partner_id", "=", partner.id),
                ("state", "!=", "cancelled"),
            ], limit=1)
            if settlement and settlement.state != "draft":
                continue

            line_commands = [(5, 0, 0)]
            line_commands.extend((0, 0, {
                "runtime_line_id": line.id,
                "bonus_type": line.bonus_type,
                "family_id": line.family_id.id,
                "movement_id": line.movement_id.id,
                "origin_runtime_line_id": line.origin_runtime_line_id.id,
                "base_pv": line.base_pv,
                "percentage": line.percentage,
                "amount_eur": line.amount_eur,
                "rule_ref": line.rule_ref,
                "calculation_note": line.calculation_note,
            }) for line in lines)

            vals = {
                "period_id": period.id,
                "partner_id": partner.id,
                "company_id": partner.company_id.id or self.env.company.id,
                "line_ids": line_commands,
            }
            settlement = settlement.write(vals) and settlement if settlement else self.create(vals)
            settlements |= settlement
            if lock_runtime:
                lines.write({"state": "locked"})

        return settlements

    def action_confirm(self):
        for record in self.filtered(lambda item: item.state == "draft"):
            if not record.line_ids:
                raise UserError(_("Non puoi confermare un settlement senza righe bonus."))
            record.write({
                "state": "confirmed",
                "confirmed_at": fields.Datetime.now(),
            })
        return True

    def action_post_to_wallet(self):
        batch_size = self._commission_batch_size("commission_wallet_post_batch_size", 50)
        if len(self) > batch_size and not self.env.context.get("commission_wallet_skip_batch"):
            return self.action_post_to_wallet_batched(batch_size=batch_size)
        for record in self:
            if record.period_id.state == "closed":
                raise UserError(_("Non puoi accreditare wallet su un periodo commissionale chiuso."))
            if record.state == "draft":
                record.action_confirm()
            if record.state != "confirmed":
                raise UserError(_("Solo un settlement confermato puo essere accreditato al wallet."))
            record.partner_id.write({
                "x_wallet_balance": record.partner_id.x_wallet_balance + record.gross_amount,
            })
            record.write({
                "state": "posted",
                "posted_at": fields.Datetime.now(),
                "posted_by_id": self.env.user.id,
            })
        return True

    def action_post_to_wallet_batched(self, batch_size=None):
        batch_size = batch_size or self._commission_batch_size("commission_wallet_post_batch_size", 50)
        for batch_ids in self._iter_commission_batches(self.ids, batch_size):
            self.browse(batch_ids).with_context(commission_wallet_skip_batch=True).action_post_to_wallet()
            self._commission_commit_batch_if_requested()
        return True

    def action_cancel(self):
        for record in self.filtered(lambda item: item.state in ("draft", "confirmed")):
            runtime_lines = record.line_ids.mapped("runtime_line_id").filtered(lambda line: line.state == "locked")
            runtime_lines.write({"state": "generated"})
            record.write({"state": "cancelled"})
        return True

    def action_open_payout_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Richieste payout collegate",
            "res_model": "lamess.payout.request",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payout_trace_line_ids.mapped("payout_request_id").ids)],
            "target": "current",
        }


class LamessCommissionSettlementLine(models.Model):
    _name = "lamess.commission.settlement.line"
    _description = "Lamess Commission Settlement Line"
    _order = "settlement_id, bonus_type, id"

    settlement_id = fields.Many2one(
        "lamess.commission.settlement",
        string="Settlement",
        required=True,
        ondelete="cascade",
        index=True,
    )
    period_id = fields.Many2one(related="settlement_id.period_id", store=True, readonly=True)
    partner_id = fields.Many2one(related="settlement_id.partner_id", store=True, readonly=True)
    runtime_line_id = fields.Many2one(
        "lamess.m3.bonus.runtime.line",
        string="Riga runtime M3",
        required=True,
        ondelete="restrict",
        index=True,
    )
    family_id = fields.Many2one("lamess.m3.bonus.family", string="Famiglia bonus", ondelete="restrict")
    movement_id = fields.Many2one("lamess.pv.movement", string="Movimento PV", ondelete="set null")
    origin_runtime_line_id = fields.Many2one(
        "lamess.m3.bonus.runtime.line",
        string="Riga bonus origine",
        ondelete="set null",
    )
    bonus_type = fields.Selection([
        ("direct", "Direct Bonus"),
        ("team", "Team Bonus"),
        ("matching", "Matching Bonus"),
        ("rank", "Rank Bonus"),
        ("fast_start", "Fast Start Bonus"),
    ], string="Tipo bonus", required=True, index=True)
    base_pv = fields.Float(string="Base PV", digits=(16, 4))
    percentage = fields.Float(string="% applicata", digits=(16, 4))
    amount_eur = fields.Float(string="Importo €", required=True, digits=(16, 2))
    rule_ref = fields.Char(string="Regola / step")
    calculation_note = fields.Char(string="Nota calcolo")

    _settlement_runtime_line_unique = models.Constraint(
        "UNIQUE(runtime_line_id)",
        "Una riga runtime M3 puo appartenere a un solo settlement.",
    )
