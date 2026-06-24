# -*- coding: utf-8 -*-
"""Vista di audit tra runtime M3, settlement e wallet."""

from odoo import fields, models, tools


class LamessCommissionSettlementAudit(models.Model):
    _name = "lamess.commission.settlement.audit"
    _description = "Lamess Commission Settlement Audit"
    _auto = False
    _rec_name = "display_name"
    _order = "period_id desc, issue_level, partner_id"

    display_name = fields.Char(string="Riferimento", compute="_compute_display_name")
    period_id = fields.Many2one("lamess.commission.period", string="Periodo", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Consulente", readonly=True)
    settlement_id = fields.Many2one("lamess.commission.settlement", string="Settlement", readonly=True)
    settlement_state = fields.Selection([
        ("draft", "Bozza"),
        ("confirmed", "Confermato"),
        ("posted", "Accreditato wallet"),
        ("cancelled", "Annullato"),
    ], string="Stato settlement", readonly=True)
    issue_level = fields.Selection([
        ("pending_runtime", "Runtime da liquidare"),
        ("locked_without_settlement", "Locked senza settlement"),
        ("draft", "Settlement in bozza"),
        ("ready_wallet", "Pronto per wallet"),
        ("posted", "Accreditato"),
        ("ok", "OK"),
    ], string="Esito controllo", readonly=True)
    runtime_generated_line_count = fields.Integer(string="Runtime generati", readonly=True)
    runtime_generated_amount = fields.Float(string="Importo runtime generato (€)", digits=(16, 2), readonly=True)
    runtime_locked_line_count = fields.Integer(string="Runtime bloccati", readonly=True)
    runtime_locked_amount = fields.Float(string="Importo runtime bloccato (€)", digits=(16, 2), readonly=True)
    runtime_cancelled_line_count = fields.Integer(string="Runtime annullati", readonly=True)
    settlement_line_count = fields.Integer(string="Righe settlement", readonly=True)
    settlement_amount = fields.Float(string="Importo settlement (€)", digits=(16, 2), readonly=True)
    locked_without_settlement_count = fields.Integer(string="Locked non collegati", readonly=True)
    locked_without_settlement_amount = fields.Float(string="Importo locked non collegato (€)", digits=(16, 2), readonly=True)
    amount_delta = fields.Float(string="Delta locked/settlement (€)", digits=(16, 2), readonly=True)
    wallet_balance = fields.Float(string="Saldo wallet attuale (€)", digits=(16, 2), readonly=True)

    def _compute_display_name(self):
        issue_labels = dict(self._fields["issue_level"].selection)
        for record in self:
            record.display_name = "%s · %s · %s" % (
                record.partner_id.display_name or "Consulente",
                record.period_id.display_name or "-",
                issue_labels.get(record.issue_level, record.issue_level or "-"),
            )

    def action_open_runtime_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Righe runtime M3",
            "res_model": "lamess.m3.bonus.runtime.line",
            "view_mode": "list,form",
            "domain": [
                ("period_id", "=", self.period_id.id),
                ("recipient_id", "=", self.partner_id.id),
            ],
            "context": {"search_default_group_bonus_type": 1},
        }

    def action_open_settlement(self):
        self.ensure_one()
        if not self.settlement_id:
            return {
                "type": "ir.actions.act_window",
                "name": "Settlement commissioni",
                "res_model": "lamess.commission.settlement",
                "view_mode": "list,form",
                "domain": [
                    ("period_id", "=", self.period_id.id),
                    ("partner_id", "=", self.partner_id.id),
                ],
                "context": {
                    "default_period_id": self.period_id.id,
                    "default_partner_id": self.partner_id.id,
                },
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Settlement commissioni",
            "res_model": "lamess.commission.settlement",
            "view_mode": "form",
            "res_id": self.settlement_id.id,
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH runtime_group AS (
                    SELECT
                        line.period_id,
                        line.recipient_id AS partner_id,
                        COUNT(*) FILTER (WHERE line.state = 'generated') AS runtime_generated_line_count,
                        COALESCE(SUM(line.amount_eur) FILTER (WHERE line.state = 'generated'), 0.0) AS runtime_generated_amount,
                        COUNT(*) FILTER (WHERE line.state = 'locked') AS runtime_locked_line_count,
                        COALESCE(SUM(line.amount_eur) FILTER (WHERE line.state = 'locked'), 0.0) AS runtime_locked_amount,
                        COUNT(*) FILTER (WHERE line.state = 'cancelled') AS runtime_cancelled_line_count
                    FROM lamess_m3_bonus_runtime_line line
                    WHERE line.recipient_id IS NOT NULL
                    GROUP BY line.period_id, line.recipient_id
                ),
                settlement_group AS (
                    SELECT
                        settlement.period_id,
                        settlement.partner_id,
                        settlement.id AS settlement_id,
                        settlement.state AS settlement_state,
                        settlement.gross_amount AS settlement_amount,
                        COUNT(settlement_line.id) AS settlement_line_count
                    FROM lamess_commission_settlement settlement
                    LEFT JOIN lamess_commission_settlement_line settlement_line
                        ON settlement_line.settlement_id = settlement.id
                    GROUP BY
                        settlement.period_id,
                        settlement.partner_id,
                        settlement.id,
                        settlement.state,
                        settlement.gross_amount
                ),
                unmatched_locked AS (
                    SELECT
                        line.period_id,
                        line.recipient_id AS partner_id,
                        COUNT(*) AS locked_without_settlement_count,
                        COALESCE(SUM(line.amount_eur), 0.0) AS locked_without_settlement_amount
                    FROM lamess_m3_bonus_runtime_line line
                    LEFT JOIN lamess_commission_settlement_line settlement_line
                        ON settlement_line.runtime_line_id = line.id
                    WHERE line.state = 'locked'
                      AND line.recipient_id IS NOT NULL
                      AND settlement_line.id IS NULL
                    GROUP BY line.period_id, line.recipient_id
                ),
                audit_keys AS (
                    SELECT period_id, partner_id FROM runtime_group
                    UNION
                    SELECT period_id, partner_id FROM settlement_group
                )
                SELECT
                    row_number() OVER (ORDER BY key.period_id DESC, key.partner_id) AS id,
                    key.period_id,
                    key.partner_id,
                    settlement.settlement_id,
                    settlement.settlement_state,
                    CASE
                        WHEN COALESCE(unmatched.locked_without_settlement_count, 0) > 0 THEN 'locked_without_settlement'
                        WHEN COALESCE(runtime.runtime_generated_line_count, 0) > 0 THEN 'pending_runtime'
                        WHEN settlement.settlement_state = 'draft' THEN 'draft'
                        WHEN settlement.settlement_state = 'confirmed' THEN 'ready_wallet'
                        WHEN settlement.settlement_state = 'posted' THEN 'posted'
                        ELSE 'ok'
                    END AS issue_level,
                    COALESCE(runtime.runtime_generated_line_count, 0) AS runtime_generated_line_count,
                    COALESCE(runtime.runtime_generated_amount, 0.0) AS runtime_generated_amount,
                    COALESCE(runtime.runtime_locked_line_count, 0) AS runtime_locked_line_count,
                    COALESCE(runtime.runtime_locked_amount, 0.0) AS runtime_locked_amount,
                    COALESCE(runtime.runtime_cancelled_line_count, 0) AS runtime_cancelled_line_count,
                    COALESCE(settlement.settlement_line_count, 0) AS settlement_line_count,
                    COALESCE(settlement.settlement_amount, 0.0) AS settlement_amount,
                    COALESCE(unmatched.locked_without_settlement_count, 0) AS locked_without_settlement_count,
                    COALESCE(unmatched.locked_without_settlement_amount, 0.0) AS locked_without_settlement_amount,
                    COALESCE(runtime.runtime_locked_amount, 0.0) - COALESCE(settlement.settlement_amount, 0.0) AS amount_delta,
                    COALESCE(partner.x_wallet_balance, 0.0) AS wallet_balance
                FROM audit_keys key
                LEFT JOIN runtime_group runtime
                    ON runtime.period_id = key.period_id
                   AND runtime.partner_id = key.partner_id
                LEFT JOIN settlement_group settlement
                    ON settlement.period_id = key.period_id
                   AND settlement.partner_id = key.partner_id
                LEFT JOIN unmatched_locked unmatched
                    ON unmatched.period_id = key.period_id
                   AND unmatched.partner_id = key.partner_id
                LEFT JOIN res_partner partner
                    ON partner.id = key.partner_id
            )
        """)
