# -*- coding: utf-8 -*-
"""Estensioni contabili del partner Lamess."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_lamess_payout_config_values(self, company=False):
        company = company or self.env.company
        config_model = self.env.get('lamess.config')
        if config_model:
            # Preferiamo il singleton di configurazione business quando
            # lamess_base e' caricato, cosi le regole payout restano allineate.
            config = config_model.get_config(company=company)
            return {
                'minimum_payout': config.minimum_payout,
            }
        icp = self.env['ir.config_parameter'].sudo()
        # Manteniamo il fallback per sicurezza durante upgrade o caricamenti
        # parziali del registry, quando il modello puo' non essere disponibile.
        return {
            'minimum_payout': float(icp.get_param('lamess_base.minimum_payout', 15.0) or 15.0),
        }

    x_wallet_balance = fields.Float(
        string='Wallet Balance (€)',
        digits=(16, 2),
        default=0.0,
        help="Saldo wallet disponibile per payout e consultazione dashboard.",
    )

    x_payout_request_count = fields.Integer(
        string='Richieste prelievo',
        compute='_compute_payout_request_count',
    )

    # ── Fiscal profile for self-invoicing ──────────────────────────────────
    x_inps_rate_pct = fields.Selection(
        selection=[
            ('0', 'Nessuna (0%)'),
            ('24', 'Ridotta (24%)'),
            ('33.72', 'Piena (33,72%)'),
        ],
        string='Aliquota INPS',
        default='0',
        help='Aliquota cassa INPS del consulente, applicata in Scenario B (con P.IVA).',
    )
    x_vat_exempt = fields.Boolean(
        string='Esente IVA',
        default=False,
        help='Se attivo, le autofatture del consulente non applicano IVA.',
    )

    # ── Per-consultant self-invoice numbering ──────────────────────────────
    # Vietato un journal per consulente: la progressione e' tracciata sul
    # partner e ripartita ogni anno solare.
    x_autoinv_letter = fields.Char(
        string='Serie autofattura',
        default='A',
        help='Lettera di serie usata nel numero progressivo delle autofatture del consulente.',
    )
    x_autoinv_last_seq_year = fields.Integer(
        string='Anno ultima autofattura',
        default=0,
        copy=False,
    )
    x_autoinv_last_seq_number = fields.Integer(
        string='Ultimo progressivo autofattura',
        default=0,
        copy=False,
    )
    x_ytd_gross_withdrawals = fields.Float(
        string='Prelievi lordi YTD (€)',
        digits=(16, 2),
        compute='_compute_ytd_gross_withdrawals',
        help='Somma dei prelievi lordi autofatturati nell\'anno solare corrente.',
    )

    def _compute_ytd_gross_withdrawals(self):
        # Il contatore considera solo le richieste effettivamente autofatturate
        # (vendor_bill_id valorizzato) e non annullate/rifiutate dell'anno corrente.
        year_start = fields.Date.context_today(self).replace(month=1, day=1)
        grouped = self.env['lamess.payout.request']._read_group(
            [
                ('partner_id', 'in', self.ids),
                ('vendor_bill_id', '!=', False),
                ('state', 'not in', ['rejected', 'cancelled']),
                ('requested_at', '>=', fields.Datetime.to_datetime(year_start)),
            ],
            ['partner_id'],
            ['gross_amount:sum'],
        )
        totals = {partner.id: total for partner, total in grouped if partner}
        for partner in self:
            partner.x_ytd_gross_withdrawals = totals.get(partner.id, 0.0)

    def _next_autoinv_number_ref(self):
        """Restituisce il prossimo numero autofattura del consulente.

        La progressione riparte da 1 a ogni cambio di anno solare. Usiamo un
        lock di riga sul partner cosi due richieste concorrenti non ottengono
        lo stesso numero.
        """
        self.ensure_one()
        partner = self.with_context(active_test=False)
        # Lock pessimistico sulla riga partner per serializzare la numerazione.
        self.env.cr.execute("SELECT id FROM res_partner WHERE id = %s FOR UPDATE", (self.id,))
        current_year = fields.Date.context_today(self).year
        if partner.x_autoinv_last_seq_year != current_year:
            next_number = 1
            partner.write({
                'x_autoinv_last_seq_year': current_year,
                'x_autoinv_last_seq_number': next_number,
            })
        else:
            next_number = (partner.x_autoinv_last_seq_number or 0) + 1
            partner.write({'x_autoinv_last_seq_number': next_number})
        letter = (partner.x_autoinv_letter or 'A').strip() or 'A'
        # Formato richiesto dalle specifiche: progressivo/anno-a-due-cifre + lettera serie (es. 01/26L).
        return "%02d/%02d%s" % (next_number, current_year % 100, letter)

    def _next_autoinv_number(self):
        self.ensure_one()

        self.env.cr.execute(
            "SELECT id FROM res_partner WHERE id = %s FOR UPDATE",
            (self.id,)
        )

        current_year = fields.Date.context_today(self).year

        if self.x_autoinv_last_seq_year != current_year:
            next_number = 1
            self.write({
                'x_autoinv_last_seq_year': current_year,
                'x_autoinv_last_seq_number': next_number,
            })
        else:
            next_number = self.x_autoinv_last_seq_number + 1
            self.write({
                'x_autoinv_last_seq_number': next_number,
            })

        letter = (self.x_autoinv_letter or 'A').strip().upper()

        return "%s%02d/%02d" % (
            letter,
            next_number,
            current_year % 100,
        )

    def _compute_payout_request_count(self):
        # Aggreghiamo una sola volta per tutto il batch cosi il bottone
        # statistico resta leggero anche con molti partner caricati.
        grouped = self.env['lamess.payout.request']._read_group(
            [('partner_id', 'in', self.ids)],
            ['partner_id'],
            ['__count'],
        )
        counts = {
            partner.id: count
            for partner, count in grouped
            if partner
        }
        for partner in self:
            partner.x_payout_request_count = counts.get(partner.id, 0)

    def _get_open_payout_request_domain(self):
        self.ensure_one()
        # Per ogni consulente e' ammesso un solo workflow payout aperto alla volta.
        return [
            ('partner_id', '=', self.id),
            ('state', 'in', ['requested', 'review', 'approved']),
        ]

    def action_open_payout_requests(self):
        self.ensure_one()
        return {
            'name': 'Richieste prelievo',
            'type': 'ir.actions.act_window',
            'res_model': 'lamess.payout.request',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            },
            'target': 'current',
        }

    def action_request_payout(self):
        self.ensure_one()
        config_vals = self._get_lamess_payout_config_values(company=self.company_id or self.env.company)
        if not self.can_request_payout():
            raise UserError(_(
                "Questo consulente non puo' richiedere il prelievo: servono stato Attivo e KYC verificato."
            ))
        if self.x_wallet_balance < config_vals['minimum_payout']:
            raise UserError(_(
                "Il saldo wallet e' inferiore al minimo configurato per il prelievo (%.2f €)."
            ) % config_vals['minimum_payout'])
        existing = self.env['lamess.payout.request'].search(self._get_open_payout_request_domain(), limit=1)
        if existing:
            raise UserError(_(
                "Esiste gia' una richiesta di prelievo aperta per questo consulente."
            ))
        company = self.company_id or self.env.company
        # La bozza autofattura si attiva solo quando l'admin ha completato la
        # configurazione fiscale; il blocco soglia invece resta sempre attivo,
        # perche' e' un limite di legge indipendente dalla configurazione contabile.
        config = self.env['lamess.config'].get_config(company=company)
        autoinv_on = config._autoinv_is_configured()
        # Scenario A (occasionale senza P.IVA): se il prelievo, sommato ai
        # prelievi lordi YTD, supera la soglia annua, blocchiamo e invitiamo
        # il consulente a inserire la partita IVA nel profilo.
        if not self.env['lamess.payout.request']._partner_has_vat(self):
            threshold = config.autoinv_gross_threshold or 0.0
            if threshold and (self.x_ytd_gross_withdrawals + self.x_wallet_balance) > threshold:
                raise UserError(_(
                    "Il prelievo supererebbe la soglia annua di %.2f € per i collaboratori "
                    "occasionali. Aggiorna il profilo inserendo la partita IVA per continuare."
                ) % threshold)
        # La richiesta iniziale usa sempre il saldo wallet corrente come lordo.
        # I passaggi successivi gestiscono revisione, approvazione e liquidazione.
        request = self.env['lamess.payout.request'].create({
            'partner_id': self.id,
            'company_id': company.id,
            'gross_amount': self.x_wallet_balance,
            'state': 'requested',
        })
        # Bozza autofattura generata nella stessa transazione: un errore di
        # configurazione fiscale annulla anche la creazione della richiesta.
        if autoinv_on:
            request._create_vendor_bill()
        if hasattr(self, 'message_post'):
            self.message_post(body=_(
                "Creata richiesta di prelievo di %.2f €."
            ) % request.gross_amount)
        return {
            'name': 'Richiesta prelievo',
            'type': 'ir.actions.act_window',
            'res_model': 'lamess.payout.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }
