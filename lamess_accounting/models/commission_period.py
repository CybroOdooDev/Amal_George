# -*- coding: utf-8 -*-
"""Estensioni contabili del periodo commissionale."""

from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LamessCommissionPeriod(models.Model):
    _inherit = "lamess.commission.period"

    sale_order_count = fields.Integer(string="Ordini vendita", compute="_compute_month_panel")
    invoice_count = fields.Integer(string="Fatture", compute="_compute_month_panel")
    invoice_paid_count = fields.Integer(string="Fatture pagate", compute="_compute_month_panel")
    invoice_pending_count = fields.Integer(string="Fatture non pagate", compute="_compute_month_panel")
    sales_total_amount = fields.Float(string="Totale fatturato mese", compute="_compute_month_panel", digits=(16, 2))
    paid_total_amount = fields.Float(string="Totale pagato mese", compute="_compute_month_panel", digits=(16, 2))
    residual_total_amount = fields.Float(string="Residuo da incassare", compute="_compute_month_panel", digits=(16, 2))
    pv_movement_count = fields.Integer(string="Movimenti PV", compute="_compute_month_panel")
    pv_confirmed_count = fields.Integer(string="Movimenti PV confermati", compute="_compute_month_panel")
    pv_pending_count = fields.Integer(string="Movimenti PV in attesa", compute="_compute_month_panel")
    pv_confirmed_amount = fields.Float(string="PV confermati", compute="_compute_month_panel", digits=(16, 0))
    pv_pending_amount = fields.Float(string="PV in attesa", compute="_compute_month_panel", digits=(16, 0))
    pv_antifraud_amount = fields.Float(string="PV antifrode", compute="_compute_month_panel", digits=(16, 0))
    consultant_with_pv_count = fields.Integer(string="Consulenti con PV", compute="_compute_month_panel")
    pc_month_total = fields.Float(string="PR mese totale", compute="_compute_month_panel", digits=(16, 0))
    pc_consultant_count = fields.Integer(string="Consulenti con PR", compute="_compute_month_panel")
    pc_career_updated_count = fields.Integer(string="PR carriera aggiornati", compute="_compute_month_panel")
    pc_live_snapshot_count = fields.Integer(string="Snapshot live", compute="_compute_month_panel")
    pc_official_snapshot_count = fields.Integer(string="Snapshot ufficiali", compute="_compute_month_panel")
    pc_rank_calculated_count = fields.Integer(string="Rank calcolati", compute="_compute_month_panel")
    runtime_line_count = fields.Integer(string="Righe runtime", compute="_compute_month_panel")
    runtime_recipient_count = fields.Integer(string="Beneficiari runtime", compute="_compute_month_panel")
    bonus_direct_amount = fields.Float(string="Direct bonus", compute="_compute_month_panel", digits=(16, 2))
    bonus_team_amount = fields.Float(string="Team bonus", compute="_compute_month_panel", digits=(16, 2))
    bonus_matching_amount = fields.Float(string="Matching bonus", compute="_compute_month_panel", digits=(16, 2))
    bonus_rank_amount = fields.Float(string="Rank bonus", compute="_compute_month_panel", digits=(16, 2))
    bonus_fast_start_amount = fields.Float(string="Fast Start", compute="_compute_month_panel", digits=(16, 2))
    bonus_total_amount = fields.Float(string="Totale bonus stimati", compute="_compute_month_panel", digits=(16, 2))

    def _month_datetime_bounds(self):
        self.ensure_one()
        date_start = fields.Date.to_date(self.date_start)
        date_end = fields.Date.to_date(self.date_end)
        if not date_start or not date_end:
            return False, False
        return datetime.combine(date_start, time.min), datetime.combine(date_end, time.max)

    def _period_pv_domain(self):
        self.ensure_one()
        return [
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
        ]

    def _compute_invoice_panel_stats(self, datetime_start, datetime_end):
        """Legge solo le colonne fattura necessarie al pannello mese.

        Usare recordset `account.move.filtered(...)` qui prefetcha tutte le
        colonne della fattura e su Odoo.sh puo' restare bloccato fino al timeout.
        """
        self.ensure_one()
        self.env.cr.execute("""
            WITH candidate_invoice AS (
                SELECT DISTINCT movement.invoice_id AS id
                  FROM lamess_pv_movement movement
                 WHERE movement.invoice_id IS NOT NULL
                   AND movement.date >= %s
                   AND movement.date <= %s
                UNION
                SELECT DISTINCT move_line.move_id AS id
                  FROM sale_order sale
                  JOIN sale_order_line sale_line
                    ON sale_line.order_id = sale.id
                  JOIN sale_order_line_invoice_rel invoice_rel
                    ON invoice_rel.order_line_id = sale_line.id
                  JOIN account_move_line move_line
                    ON move_line.id = invoice_rel.invoice_line_id
                 WHERE sale.date_order >= %s
                   AND sale.date_order <= %s
                   AND sale.state != 'cancel'
            )
            SELECT
                COUNT(move.id),
                COUNT(move.id) FILTER (WHERE move.payment_state = 'paid'),
                COALESCE(SUM(move.amount_total), 0.0),
                COALESCE(SUM(move.amount_total) FILTER (WHERE move.payment_state = 'paid'), 0.0),
                COALESCE(SUM(move.amount_residual), 0.0)
              FROM account_move move
              JOIN candidate_invoice candidate
                ON candidate.id = move.id
             WHERE move.move_type = 'out_invoice'
               AND move.state = 'posted'
               AND COALESCE(move.invoice_date, move.date) >= %s
               AND COALESCE(move.invoice_date, move.date) <= %s
        """, [
            self.date_start,
            self.date_end,
            datetime_start,
            datetime_end,
            self.date_start,
            self.date_end,
        ])
        row = self.env.cr.fetchone() or (0, 0, 0.0, 0.0, 0.0)
        invoice_count, paid_count, total_amount, paid_amount, residual_amount = row
        return {
            "invoice_count": invoice_count or 0,
            "invoice_paid_count": paid_count or 0,
            "invoice_pending_count": (invoice_count or 0) - (paid_count or 0),
            "sales_total_amount": total_amount or 0.0,
            "paid_total_amount": paid_amount or 0.0,
            "residual_total_amount": residual_amount or 0.0,
        }

    @api.depends("date_start", "date_end")
    def _compute_month_panel(self):
        sale_model = self.env["sale.order"].sudo()
        movement_model = self.env["lamess.pv.movement"].sudo()
        runtime_model = self.env["lamess.m3.bonus.runtime.line"].sudo()
        period_volume_model = self.env["lamess.network.period.volume"].sudo()
        snapshot_model = self.env["lamess.partner.rank.snapshot"].sudo()
        for period in self:
            period.sale_order_count = 0
            period.invoice_count = 0
            period.invoice_paid_count = 0
            period.invoice_pending_count = 0
            period.sales_total_amount = 0.0
            period.paid_total_amount = 0.0
            period.residual_total_amount = 0.0
            period.pv_movement_count = 0
            period.pv_confirmed_count = 0
            period.pv_pending_count = 0
            period.pv_confirmed_amount = 0.0
            period.pv_pending_amount = 0.0
            period.pv_antifraud_amount = 0.0
            period.consultant_with_pv_count = 0
            period.pc_month_total = 0.0
            period.pc_consultant_count = 0
            period.pc_career_updated_count = 0
            period.pc_live_snapshot_count = 0
            period.pc_official_snapshot_count = 0
            period.pc_rank_calculated_count = 0
            period.runtime_line_count = 0
            period.runtime_recipient_count = 0
            period.bonus_direct_amount = 0.0
            period.bonus_team_amount = 0.0
            period.bonus_matching_amount = 0.0
            period.bonus_rank_amount = 0.0
            period.bonus_fast_start_amount = 0.0
            period.bonus_total_amount = 0.0

            if not period.date_start or not period.date_end:
                continue

            datetime_start, datetime_end = period._month_datetime_bounds()
            sale_order_count = sale_model.search_count([
                ("date_order", ">=", datetime_start),
                ("date_order", "<=", datetime_end),
                ("state", "!=", "cancel"),
            ])
            movements = movement_model.search(period._period_pv_domain())
            invoice_stats = period._compute_invoice_panel_stats(datetime_start, datetime_end)
            runtime_lines = runtime_model.search([
                ("period_id", "=", period.id),
                ("state", "!=", "cancelled"),
            ])
            period_month = "%s-%02d" % (period.year, period.month)
            period_volumes = period_volume_model.search([
                ("period_month", "=", period_month),
                ("network_cv", ">", 0.0),
            ])
            period_snapshots = snapshot_model.search([
                ("period_month", "=", period_month),
                ("calc_state", "=", "ready"),
            ])

            confirmed_movements = movements.filtered(lambda movement: movement.state == "confirmed")
            pending_movements = movements.filtered(lambda movement: movement.state != "confirmed")
            pc_movements = confirmed_movements.filtered(lambda movement: not movement.x_antifraud_flag)

            period.sale_order_count = sale_order_count
            period.invoice_count = invoice_stats["invoice_count"]
            period.invoice_paid_count = invoice_stats["invoice_paid_count"]
            period.invoice_pending_count = invoice_stats["invoice_pending_count"]
            period.sales_total_amount = invoice_stats["sales_total_amount"]
            period.paid_total_amount = invoice_stats["paid_total_amount"]
            period.residual_total_amount = invoice_stats["residual_total_amount"]
            period.pv_movement_count = len(movements)
            period.pv_confirmed_count = len(confirmed_movements)
            period.pv_pending_count = len(pending_movements)
            period.pv_confirmed_amount = sum(confirmed_movements.mapped("pv_amount"))
            period.pv_pending_amount = sum(pending_movements.mapped("pv_amount"))
            period.pv_antifraud_amount = sum(movements.filtered("x_antifraud_flag").mapped("pv_amount"))
            period.consultant_with_pv_count = len(set(confirmed_movements.mapped("networker_id").ids))
            period.pc_month_total = sum(pc_movements.mapped("cv_amount"))
            period.pc_consultant_count = len(set(period_volumes.mapped("partner_id").ids))
            period.pc_career_updated_count = len(period_snapshots)
            period.pc_live_snapshot_count = len(period_snapshots.filtered(lambda snapshot: snapshot.snapshot_type == "live"))
            period.pc_official_snapshot_count = len(period_snapshots.filtered(lambda snapshot: snapshot.is_official))
            period.pc_rank_calculated_count = len(period_snapshots.filtered(lambda snapshot: snapshot.rank_code and snapshot.rank_code != "none"))
            period.runtime_line_count = len(runtime_lines)
            period.runtime_recipient_count = len(set(runtime_lines.mapped("recipient_id").ids))
            period.bonus_direct_amount = sum(runtime_lines.filtered(lambda line: line.bonus_type == "direct").mapped("amount_eur"))
            period.bonus_team_amount = sum(runtime_lines.filtered(lambda line: line.bonus_type == "team").mapped("amount_eur"))
            period.bonus_matching_amount = sum(runtime_lines.filtered(lambda line: line.bonus_type == "matching").mapped("amount_eur"))
            period.bonus_rank_amount = sum(runtime_lines.filtered(lambda line: line.bonus_type == "rank").mapped("amount_eur"))
            period.bonus_fast_start_amount = sum(runtime_lines.filtered(lambda line: line.bonus_type == "fast_start").mapped("amount_eur"))
            period.bonus_total_amount = sum(runtime_lines.mapped("amount_eur"))

    def action_open_m3_bonus_preview(self):
        self.ensure_one()
        # L'anteprima compensi e' il runtime M3 filtrato per periodo: il totale
        # del pannello mensile e le righe aperte qui leggono la stessa fonte.
        return {
            "type": "ir.actions.act_window",
            "name": _("Anteprima compensi - %s") % self.display_name,
            "res_model": "lamess.m3.bonus.runtime.line",
            "view_mode": "list",
            "domain": [
                ("period_id", "=", self.id),
                ("state", "!=", "cancelled"),
            ],
            "context": {
                "default_period_id": self.id,
                "search_default_group_recipient": 1,
                "search_default_group_bonus_type": 1,
            },
        }

    def _confirmed_movements_for_close(self):
        self.ensure_one()
        return self.env["lamess.pv.movement"].sudo().search([
            ("state", "=", "confirmed"),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
            ("x_antifraud_flag", "=", False),
            ("networker_id", "!=", False),
            ("pv_amount", "!=", 0.0),
        ], order="date asc, id asc")

    def _partners_in_period_scope(self, movements):
        partner_ids = set()
        for movement in movements:
            chain = movement.networker_id.get_raw_commission_chain(max_depth=200)
            partner_ids.update(chain.ids)
        return list(partner_ids)

    def _partners_for_pc_rank_regeneration(self, movements):
        """Return the snapshot scope for a monthly PR/rank regeneration.

        Career PR and rank are cumulative up to the period cut-off. If the
        period has ledger, only the touched sponsor chains need fresh snapshots;
        quiet months fall back to all networkers so historical dashboards still
        get an official monthly picture.
        """
        partner_model = self.env["res.partner"].sudo().with_context(active_test=False)
        partner_ids = self._partners_in_period_scope(movements)
        if partner_ids:
            return partner_model.browse(partner_ids).filtered("x_is_networker")
        return partner_model.search([("x_is_networker", "=", True)])

    def action_regenerate_pc_rank(self):
        snapshot_model = self.env["lamess.partner.rank.snapshot"].sudo()
        today = fields.Date.context_today(self)
        notifications = []
        for period in self.sudo():
            if not period.date_start or not period.date_end:
                continue
            period_month = "%s-%02d" % (period.year, period.month)
            movements = period._confirmed_movements_for_close()
            partners = period._partners_for_pc_rank_regeneration(movements)
            snapshot_model.search([
                ("period_month", "=", period_month),
                ("snapshot_type", "in", ("live", "monthly")),
                ("partner_id", "in", partners.ids),
            ]).unlink()

            refresh_model = snapshot_model.with_context(skip_commission_projection_sync=True)
            # Il ricalcolo storico deve essere bottom-up sulla catena sponsor
            # reale: x_network_depth deriva da x_parent_path e puo essere stale.
            for partner in partners._sorted_by_real_sponsor_depth_desc():
                refresh_model._refresh_snapshot(
                    partner,
                    period_month,
                    snapshot_type="monthly",
                    is_official=True,
                    force=True,
                )

            if hasattr(partners, "_sync_commission_career_rank_cache"):
                # Il reset storico azzera i cache globali del contatto.
                # Dopo avere ricreato gli snapshot ufficiali del mese,
                # riallineiamo carriera e rank dalla vista unica senza
                # sovrascrivere il PV mensile live del consulente.
                partners._sync_commission_career_rank_cache()

            if period.date_start <= today <= period.date_end:
                for partner in partners._sorted_by_real_sponsor_depth_desc():
                    snapshot_model._refresh_snapshot(
                        partner,
                        period_month,
                        snapshot_type="live",
                        is_official=False,
                        force=True,
                    )

            notifications.append(_("%(period)s: %(partners)s consulenti ricalcolati.") % {
                "period": period.display_name,
                "partners": len(partners),
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("PR e rank rigenerati"),
                "message": "\n".join(notifications) if notifications else _("Nessun periodo elaborato."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_pv_ledger_state(self):
        """Aggiorna lo stato del PV Ledger partendo da pagamenti, refund e fatture."""
        movement_model = self.env["lamess.pv.movement"].sudo()
        invoice_model = self.env["account.move"].sudo()
        payment_model = self.env["account.payment"].sudo()
        transaction_model = self.env["payment.transaction"].sudo()
        notifications = []

        # Prima chiudiamo i ponti PSP/manuali: se un pagamento o refund e'
        # confermato, il ledger deve leggerlo senza aspettare azioni manuali.
        close_done_payments = getattr(transaction_model, "_cron_lamess_close_done_payment_bridge", None)
        sync_done_refunds = getattr(transaction_model, "_cron_lamess_sync_done_refunds", None)
        close_confirmed_payments = getattr(payment_model, "_cron_lamess_close_confirmed_payments", None)
        if callable(close_done_payments):
            close_done_payments(limit=500)
        if callable(sync_done_refunds):
            sync_done_refunds(limit=500)
        if callable(close_confirmed_payments):
            close_confirmed_payments(limit=500)

        autosync = getattr(movement_model, "_autosync_commission_engine", None)
        autosync_stats = autosync(limit=2000) if callable(autosync) else {}

        for period in self.sudo():
            if not period.date_start or not period.date_end:
                continue
            dated_invoices = invoice_model.search([
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_date", ">=", period.date_start),
                ("invoice_date", "<=", period.date_end),
            ])
            undated_invoices = invoice_model.search([
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_date", "=", False),
                ("date", ">=", period.date_start),
                ("date", "<=", period.date_end),
            ])
            invoices = dated_invoices | undated_invoices
            sync_invoice_ledger = getattr(invoices, "_sync_pv_movements_from_billing_state", None)
            if callable(sync_invoice_ledger):
                # Le fatture storiche create a mano non passano da sale.order:
                # prima di leggere il periodo assicuriamo il ledger dalla data fattura.
                sync_invoice_ledger()
            movements = movement_model.search(period._period_pv_domain())
            movements._sync_from_billing_data()
            confirmed = movements.filtered(lambda movement: movement.state == "confirmed")
            pending = movements - confirmed
            notifications.append(_(
                "%(period)s: %(invoices)s fatture controllate, %(total)s movimenti aggiornati, %(confirmed)s confermati, %(pending)s in attesa."
            ) % {
                "period": period.display_name,
                "invoices": len(invoices),
                "total": len(movements),
                "confirmed": len(confirmed),
                "pending": len(pending),
            })

        if autosync_stats:
            notifications.append(_("Autosync globale: %(synced)s movimenti riallineati, %(created)s creati.") % {
                "synced": autosync_stats.get("movements_synced", 0),
                "created": autosync_stats.get("movements_created", 0),
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("PV Ledger aggiornato"),
                "message": "\n".join(notifications) if notifications else _("Nessun periodo elaborato."),
                "type": "success",
                "sticky": True,
            },
        }

    def _get_accounting_close_blockers(self):
        self.ensure_one()
        runtime_model = self.env["lamess.m3.bonus.runtime.line"].sudo()
        settlement_model = self.env["lamess.commission.settlement"].sudo()
        settlement_line_model = self.env["lamess.commission.settlement.line"].sudo()

        blockers = []
        pending_runtime_count = runtime_model.search_count([
            ("period_id", "=", self.id),
            ("state", "=", "generated"),
            ("recipient_id", "!=", False),
            ("amount_eur", ">", 0.0),
        ])
        if pending_runtime_count:
            blockers.append(_("%s righe runtime M3 sono ancora generate e non liquidate.") % pending_runtime_count)

        unposted_settlement_count = settlement_model.search_count([
            ("period_id", "=", self.id),
            ("state", "in", ("draft", "confirmed")),
        ])
        if unposted_settlement_count:
            blockers.append(_("%s settlement sono ancora in bozza o confermati ma non accreditati.") % unposted_settlement_count)

        locked_lines = runtime_model.search([
            ("period_id", "=", self.id),
            ("state", "=", "locked"),
        ])
        if locked_lines:
            linked_runtime_ids = set(settlement_line_model.search([
                ("runtime_line_id", "in", locked_lines.ids),
            ]).mapped("runtime_line_id").ids)
            unmatched_locked_count = len([line for line in locked_lines if line.id not in linked_runtime_ids])
            if unmatched_locked_count:
                blockers.append(_("%s righe runtime bloccate non sono collegate a nessun settlement.") % unmatched_locked_count)

        return blockers

    def action_mark_closed(self):
        if self.env.context.get("lamess_period_finalizing_snapshots"):
            return super().action_mark_closed()

        closed_periods = self.filtered(lambda period: period.state == "closed")
        if closed_periods:
            raise UserError(_("Il periodo %s e gia chiuso.") % closed_periods[:1].display_name)

        notifications = []
        for period in self:
            blockers = period._get_accounting_close_blockers()
            if blockers:
                raise UserError("\n".join(blockers))

            movements = period._confirmed_movements_for_close()
            if movements:
                movements.write({"period_id": period.id})
            period.action_mark_processing()
            partner_ids = period._partners_in_period_scope(movements)
            snapshot_count = self.env["lamess.partner.rank.snapshot"].sudo().with_context(
                lamess_period_finalizing_snapshots=True,
                lamess_skip_period_close=True,
            ).finalize_period_snapshots(
                period_month="%s-%02d" % (period.year, period.month),
                partner_ids=partner_ids or None,
            )
            runtime_lines = self.env["lamess.m3.bonus.runtime.line"].sudo().with_context(
                m3_runtime_autocommit=True,
                m3_runtime_today=period.date_end,
                m3_enable_startup_activity_grace=True,
                m3_skip_rank_snapshot_refresh=True,
            ).generate_all_runtime_for_period(period=period, reset_generated=True)
            blockers = period._get_accounting_close_blockers()
            if blockers:
                raise UserError("\n".join(blockers))
            period.with_context(lamess_period_finalizing_snapshots=True).action_mark_closed()
            notifications.append(_(
                "%(period)s: %(movements)s movimenti PV, %(runtime)s righe runtime, %(snapshots)s snapshot ufficiali."
            ) % {
                "period": period.display_name,
                "movements": len(movements),
                "runtime": len(runtime_lines),
                "snapshots": snapshot_count,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Periodo chiuso"),
                "message": "\n".join(notifications),
                "type": "success",
                "sticky": True,
            },
        }


class LamessM3BonusRuntimeLine(models.Model):
    _inherit = "lamess.m3.bonus.runtime.line"

    @api.model
    def _ensure_period_can_receive_runtime_generation(self, period):
        if (
            period
            and period.state == "closed"
            and not self.env.context.get("lamess_allow_closed_period_runtime")
        ):
            raise UserError(_("Non puoi generare righe runtime M3 su un periodo commissionale chiuso."))

    @api.model_create_multi
    def create(self, vals_list):
        period_ids = {vals.get("period_id") for vals in vals_list if vals.get("period_id")}
        if period_ids and not self.env.context.get("lamess_allow_closed_period_runtime"):
            closed_period = self.env["lamess.commission.period"].browse(period_ids).filtered(
                lambda period: period.state == "closed"
            )[:1]
            if closed_period:
                raise UserError(_("Non puoi creare righe runtime M3 sul periodo chiuso %s.") % closed_period.display_name)
        return super().create(vals_list)

    @api.model
    def generate_direct_team_for_period(self, period=None, reset_generated=True):
        period = period or self._get_default_period()
        self._ensure_period_can_receive_runtime_generation(period)
        return super().generate_direct_team_for_period(period=period, reset_generated=reset_generated)

    @api.model
    def generate_matching_for_period(self, period=None, reset_generated=True):
        period = period or self._get_default_period()
        self._ensure_period_can_receive_runtime_generation(period)
        return super().generate_matching_for_period(period=period, reset_generated=reset_generated)

    @api.model
    def generate_rank_bonus_for_period(self, period=None, reset_generated=True):
        period = period or self._get_default_period()
        self._ensure_period_can_receive_runtime_generation(period)
        return super().generate_rank_bonus_for_period(period=period, reset_generated=reset_generated)

    @api.model
    def generate_fast_start_for_period(self, period=None, reset_generated=True):
        period = period or self._get_default_period()
        self._ensure_period_can_receive_runtime_generation(period)
        return super().generate_fast_start_for_period(period=period, reset_generated=reset_generated)

    @api.model
    def generate_all_runtime_for_period(self, period=None, reset_generated=True):
        period = period or self._get_default_period()
        self._ensure_period_can_receive_runtime_generation(period)
        return super().generate_all_runtime_for_period(period=period, reset_generated=reset_generated)
