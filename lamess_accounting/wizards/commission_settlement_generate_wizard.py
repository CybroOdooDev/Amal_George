# -*- coding: utf-8 -*-
"""Wizard di generazione settlement dalle righe runtime M3."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LamessCommissionSettlementGenerateWizard(models.TransientModel):
    _name = "lamess.commission.settlement.generate.wizard"
    _description = "Generate Lamess Commission Settlements"

    period_id = fields.Many2one(
        "lamess.commission.period",
        string="Periodo",
        required=True,
        default=lambda self: self.env["lamess.m3.bonus.runtime.line"]._get_default_period(),
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Consulenti",
        domain=[("x_is_networker", "=", True)],
        help="Lascia vuoto per generare i settlement di tutti i consulenti con righe M3 generate.",
    )
    lock_runtime = fields.Boolean(
        string="Blocca righe runtime",
        default=True,
        help="Impedisce che le stesse righe bonus vengano riutilizzate in un altro settlement.",
    )
    eligible_runtime_line_count = fields.Integer(
        string="Righe generabili",
        compute="_compute_eligible_runtime",
    )
    eligible_amount = fields.Float(
        string="Importo generabile (€)",
        compute="_compute_eligible_runtime",
        digits=(16, 2),
    )

    def _get_runtime_domain(self):
        self.ensure_one()
        domain = [
            ("period_id", "=", self.period_id.id),
            ("state", "=", "generated"),
            ("recipient_id", "!=", False),
            ("amount_eur", ">", 0.0),
        ]
        if self.partner_ids:
            domain.append(("recipient_id", "in", self.partner_ids.ids))
        return domain

    @api.depends("period_id", "partner_ids")
    def _compute_eligible_runtime(self):
        for wizard in self:
            if not wizard.period_id:
                wizard.eligible_runtime_line_count = 0
                wizard.eligible_amount = 0.0
                continue
            params = [wizard.period_id.id]
            partner_filter = ""
            if wizard.partner_ids:
                partner_filter = "AND recipient_id = ANY(%s)"
                params.append(wizard.partner_ids.ids)
            query = """
                SELECT COUNT(*), COALESCE(SUM(amount_eur), 0.0)
                  FROM lamess_m3_bonus_runtime_line
                 WHERE period_id = %s
                   AND state = 'generated'
                   AND recipient_id IS NOT NULL
                   AND amount_eur > 0.0
                   {partner_filter}
            """.format(partner_filter=partner_filter)
            self.env.cr.execute(query, params)
            count, amount = self.env.cr.fetchone()
            wizard.eligible_runtime_line_count = count
            wizard.eligible_amount = amount

    def action_generate(self):
        self.ensure_one()
        if not self.eligible_runtime_line_count:
            raise UserError(_("Non ci sono righe runtime M3 generate per il periodo e i filtri selezionati."))

        settlements = self.env["lamess.commission.settlement"].with_context(
            commission_batch_autocommit=True,
        ).generate_from_m3_runtime(
            period=self.period_id,
            partner_ids=self.partner_ids.ids or None,
            lock_runtime=self.lock_runtime,
        )
        if not settlements:
            raise UserError(_("Nessun settlement e stato generato. Verifica se esistono gia settlement confermati."))

        action = self.env.ref("lamess_accounting.action_lamess_commission_settlement").read()[0]
        action["domain"] = [("id", "in", settlements.ids)]
        action["context"] = {
            "default_period_id": self.period_id.id,
            "search_default_group_partner": 1,
        }
        return action


class LamessCommissionWalletPostWizard(models.TransientModel):
    _name = "lamess.commission.wallet.post.wizard"
    _description = "Accredita settlement commissioni al wallet"

    period_id = fields.Many2one(
        "lamess.commission.period",
        string="Periodo",
        required=True,
        default=lambda self: self.env["lamess.m3.bonus.runtime.line"]._get_default_period(),
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Consulenti",
        domain=[("x_is_networker", "=", True)],
        help="Lascia vuoto per accreditare tutti i settlement pronti del periodo.",
    )
    settlement_count = fields.Integer(
        string="Settlement da accreditare",
        compute="_compute_postable_settlements",
    )
    settlement_amount = fields.Float(
        string="Importo da accreditare (€)",
        compute="_compute_postable_settlements",
        digits=(16, 2),
    )

    def _get_postable_settlement_domain(self):
        self.ensure_one()
        domain = [
            ("period_id", "=", self.period_id.id),
            ("state", "in", ("draft", "confirmed")),
            ("gross_amount", ">", 0.0),
        ]
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        return domain

    @api.depends("period_id", "partner_ids")
    def _compute_postable_settlements(self):
        settlement_model = self.env["lamess.commission.settlement"]
        for wizard in self:
            if not wizard.period_id:
                wizard.settlement_count = 0
                wizard.settlement_amount = 0.0
                continue
            settlements = settlement_model.search(wizard._get_postable_settlement_domain())
            wizard.settlement_count = len(settlements)
            wizard.settlement_amount = sum(settlements.mapped("gross_amount"))

    def action_post_wallet(self):
        self.ensure_one()
        settlements = self.env["lamess.commission.settlement"].search(
            self._get_postable_settlement_domain(),
            order="partner_id, id",
        )
        if not settlements:
            raise UserError(_("Non ci sono settlement pronti da accreditare per il periodo e i filtri selezionati."))

        amount = sum(settlements.mapped("gross_amount"))
        count = len(settlements)
        settlements.with_context(
            commission_batch_autocommit=True,
        ).action_post_to_wallet_batched()

        action = self.env.ref("lamess_accounting.action_lamess_commission_settlement").read()[0]
        action["domain"] = [("id", "in", settlements.ids)]
        action["context"] = {
            "default_period_id": self.period_id.id,
            "search_default_posted": 1,
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Wallet accreditati"),
                "message": _("%s settlement accreditati al wallet per un totale di %.2f €.") % (count, amount),
                "type": "success",
                "sticky": False,
                "next": action,
            },
        }


class LamessCommissionFullCycleWizard(models.TransientModel):
    _name = "lamess.commission.full.cycle.wizard"
    _description = "Esegui ciclo completo commissioni"

    period_id = fields.Many2one(
        "lamess.commission.period",
        string="Periodo",
        required=True,
        default=lambda self: self.env["lamess.m3.bonus.runtime.line"]._get_default_period(),
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Consulenti",
        domain=[("x_is_networker", "=", True)],
        help="Lascia vuoto per elaborare tutti i consulenti del periodo.",
    )
    regenerate_runtime = fields.Boolean(
        string="Rigenera runtime M3",
        default=True,
        help="Ricalcola le righe runtime M3 prima di creare settlement e wallet.",
    )
    generate_settlement = fields.Boolean(
        string="Genera settlement",
        default=True,
        help="Crea i settlement dalle righe runtime M3 generate.",
    )
    post_wallet = fields.Boolean(
        string="Accredita wallet",
        default=True,
        help="Accredita al wallet i settlement in bozza o confermati.",
    )
    lock_runtime = fields.Boolean(
        string="Blocca righe runtime",
        default=True,
        help="Impedisce che le stesse righe bonus vengano riutilizzate in un altro settlement.",
    )
    existing_generated_runtime_count = fields.Integer(
        string="Runtime generati disponibili",
        compute="_compute_preview",
    )
    existing_postable_settlement_count = fields.Integer(
        string="Settlement accreditabili",
        compute="_compute_preview",
    )
    existing_postable_settlement_amount = fields.Float(
        string="Importo accreditabile (€)",
        compute="_compute_preview",
        digits=(16, 2),
    )

    def _partner_domain_filter(self, partner_field):
        self.ensure_one()
        if self.partner_ids:
            return [(partner_field, "in", self.partner_ids.ids)]
        return []

    @api.depends("period_id", "partner_ids")
    def _compute_preview(self):
        runtime_model = self.env["lamess.m3.bonus.runtime.line"]
        settlement_model = self.env["lamess.commission.settlement"]
        for wizard in self:
            if not wizard.period_id:
                wizard.existing_generated_runtime_count = 0
                wizard.existing_postable_settlement_count = 0
                wizard.existing_postable_settlement_amount = 0.0
                continue
            runtime_domain = [
                ("period_id", "=", wizard.period_id.id),
                ("state", "=", "generated"),
                ("recipient_id", "!=", False),
                ("amount_eur", ">", 0.0),
            ] + wizard._partner_domain_filter("recipient_id")
            settlement_domain = [
                ("period_id", "=", wizard.period_id.id),
                ("state", "in", ("draft", "confirmed")),
                ("gross_amount", ">", 0.0),
            ] + wizard._partner_domain_filter("partner_id")
            wizard.existing_generated_runtime_count = runtime_model.search_count(runtime_domain)
            settlements = settlement_model.search(settlement_domain)
            wizard.existing_postable_settlement_count = len(settlements)
            wizard.existing_postable_settlement_amount = sum(settlements.mapped("gross_amount"))

    def action_run_full_cycle(self):
        self.ensure_one()
        if not any((self.regenerate_runtime, self.generate_settlement, self.post_wallet)):
            raise UserError(_("Seleziona almeno una operazione da eseguire."))

        runtime_lines = self.env["lamess.m3.bonus.runtime.line"]
        settlements = self.env["lamess.commission.settlement"]
        runtime_count = 0
        settlement_count = 0
        wallet_count = 0
        wallet_amount = 0.0

        if self.regenerate_runtime:
            runtime_lines = runtime_lines.with_context(
                m3_runtime_autocommit=True,
                m3_runtime_today=self.period_id.date_end,
                m3_enable_startup_activity_grace=True,
                m3_force_rank_snapshot_refresh=True,
            ).generate_all_runtime_for_period(period=self.period_id)
            if self.partner_ids:
                runtime_lines = runtime_lines.filtered(lambda line: line.recipient_id in self.partner_ids)
            runtime_count = len(runtime_lines)

        if self.generate_settlement:
            settlements = settlements.with_context(
                commission_batch_autocommit=True,
            ).generate_from_m3_runtime(
                period=self.period_id,
                partner_ids=self.partner_ids.ids or None,
                lock_runtime=self.lock_runtime,
            )
            settlement_count = len(settlements)

        if self.post_wallet:
            post_domain = [
                ("period_id", "=", self.period_id.id),
                ("state", "in", ("draft", "confirmed")),
                ("gross_amount", ">", 0.0),
            ] + self._partner_domain_filter("partner_id")
            wallet_settlements = self.env["lamess.commission.settlement"].search(post_domain, order="partner_id, id")
            wallet_count = len(wallet_settlements)
            wallet_amount = sum(wallet_settlements.mapped("gross_amount"))
            if wallet_settlements:
                wallet_settlements.with_context(
                    commission_batch_autocommit=True,
                ).action_post_to_wallet_batched()

        action = self.env.ref("lamess_accounting.action_lamess_commission_settlement").read()[0]
        action["domain"] = [("period_id", "=", self.period_id.id)]
        action["context"] = {
            "default_period_id": self.period_id.id,
            "search_default_posted": 1 if self.post_wallet else 0,
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Ciclo commissioni completato"),
                "message": _(
                    "Periodo %(period)s: %(runtime)s righe runtime, %(settlements)s settlement generati, "
                    "%(wallets)s wallet accreditati per %(amount).2f €."
                ) % {
                    "period": self.period_id.display_name,
                    "runtime": runtime_count,
                    "settlements": settlement_count,
                    "wallets": wallet_count,
                    "amount": wallet_amount,
                },
                "type": "success",
                "sticky": True,
                "next": action,
            },
        }
