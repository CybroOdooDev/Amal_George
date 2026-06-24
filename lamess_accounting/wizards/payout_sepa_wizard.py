# -*- coding: utf-8 -*-
"""Wizard di disposizione bonifici SEPA (CBI) per le richieste payout approvate.

Accessibile dall'elenco delle richieste prelievo: filtra le richieste approvate
con autofattura registrata (documento validato), mostra il netto da bonificare
(Lordo + IVA - Ritenuta - Costo amministrativo) e genera in blocco il file SEPA
Credit Transfer (pain.001 / CBI) usando lo standard Odoo (account.batch.payment +
account_iso20022). Alla generazione i pagamenti vengono marcati come inviati,
abilitando la riconciliazione automatica all'import dell'estratto conto.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LamessPayoutSepaWizard(models.TransientModel):
    _name = 'lamess.payout.sepa.wizard'
    _description = 'Lamess Payout SEPA Batch Wizard'

    journal_id = fields.Many2one(
        'account.journal',
        string='Banca (giornale)',
        required=True,
        domain="[('type', '=', 'bank')]",
        default=lambda self: self._default_journal(),
        help='Giornale bancario da cui parte il bonifico SEPA. Deve avere il metodo '
             'di pagamento "SEPA Credit Transfer" e un conto IBAN valido.',
    )
    payment_date = fields.Date(
        string='Data esecuzione',
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    line_ids = fields.One2many(
        'lamess.payout.sepa.wizard.line',
        'wizard_id',
        string='Richieste da bonificare',
    )
    total_net = fields.Monetary(
        string='Totale netto da bonificare',
        compute='_compute_total_net',
        currency_field='currency_id',
    )

    @api.model
    def _default_journal(self):
        # Preferiamo un giornale bancario che esponga gia' il metodo SEPA Credit
        # Transfer, cosi l'admin non deve sceglierlo a mano nei casi standard.
        journals = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id),
        ])
        for journal in journals:
            if journal._get_available_payment_method_lines('outbound').filtered(
                lambda line: line.code == 'sepa_ct'
            ):
                return journal.id
        return journals[:1].id

    @api.depends('line_ids.net_amount')
    def _compute_total_net(self):
        for wizard in self:
            wizard.total_net = sum(wizard.line_ids.mapped('net_amount'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        if active_model != 'lamess.payout.request' or not active_ids:
            return res
        requests = self.env['lamess.payout.request'].browse(active_ids)
        # Solo richieste approvate con autofattura registrata (documento validato).
        eligible = requests.filtered(
            lambda r: r.state == 'approved'
            and r.vendor_bill_id
            and r.vendor_bill_id.state == 'posted'
        )
        if not eligible:
            raise UserError(_(
                "Nessuna richiesta selezionata e' bonificabile: servono stato "
                "Approvato e autofattura registrata (documento validato)."
            ))
        line_vals = []
        for request in eligible:
            partner_bank = request.partner_id.bank_ids[:1]
            line_vals.append((0, 0, {
                'payout_request_id': request.id,
                'partner_bank_id': partner_bank.id,
            }))
        res['line_ids'] = line_vals
        return res

    def _get_sepa_payment_method_line(self):
        self.ensure_one()
        method_line = self.journal_id._get_available_payment_method_lines('outbound').filtered(
            lambda line: line.code == 'sepa_ct'
        )[:1]
        if not method_line:
            raise UserError(_(
                "Il giornale '%s' non espone il metodo di pagamento 'SEPA Credit "
                "Transfer'. Configuralo nelle impostazioni del giornale bancario."
            ) % self.journal_id.display_name)
        return method_line

    def action_generate_sepa(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Nessuna richiesta da bonificare."))
        method_line = self._get_sepa_payment_method_line()

        payment_by_request = {}
        for line in self.line_ids:
            request = line.payout_request_id
            if request.state != 'approved':
                raise UserError(_(
                    "La richiesta %s non e' piu' in stato Approvato."
                ) % request.display_name)
            bill = request.vendor_bill_id
            if not bill or bill.state != 'posted':
                raise UserError(_(
                    "La richiesta %s non ha un'autofattura registrata."
                ) % request.display_name)
            if not line.partner_bank_id:
                raise UserError(_(
                    "Manca l'IBAN del consulente %s: impostalo nel profilo per il bonifico SEPA."
                ) % request.partner_id.display_name)
            if request.gross_amount > request.partner_id.x_wallet_balance:
                raise UserError(_(
                    "Saldo wallet insufficiente per liquidare la richiesta %s."
                ) % request.display_name)
            # Registriamo il pagamento sull'autofattura cosi il debito verso il
            # consulente viene riconciliato secondo lo standard Odoo.
            register = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=bill.ids,
            ).create({
                'journal_id': self.journal_id.id,
                'payment_date': self.payment_date,
                'payment_method_line_id': method_line.id,
                'amount': line.net_amount,
                'partner_bank_id': line.partner_bank_id.id,
            })
            payments = register._create_payments()
            payment_by_request[request] = payments[:1]

        all_payments = self.env['account.payment']
        for payment in payment_by_request.values():
            all_payments |= payment

        # Raggruppiamo i pagamenti in un'unica disposizione SEPA Credit Transfer.
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.journal_id.id,
            'batch_type': 'outbound',
            'date': self.payment_date,
            'payment_method_id': method_line.payment_method_id.id,
            'payment_ids': [(6, 0, all_payments.ids)],
        })
        # validate_batch genera il file pain.001/CBI e marca i pagamenti come
        # inviati. Se la validazione trova errori restituisce il wizard errori:
        # in tal caso lo propaghiamo senza chiudere le richieste.
        validation = batch.validate_batch()
        if isinstance(validation, dict) and validation.get('res_model') == 'account.batch.error.wizard':
            return validation

        now = fields.Datetime.now()
        for request, payment in payment_by_request.items():
            request._sync_settlement_traceability()
            request.partner_id.write({
                'x_wallet_balance': request.partner_id.x_wallet_balance - request.gross_amount,
            })
            request.write({
                'state': 'paid',
                'paid_at': now,
                'paid_by_id': self.env.user.id,
                'accounting_move_id': payment.move_id.id,
            })
            if hasattr(request, 'message_post'):
                request.message_post(body=_(
                    "Bonifico SEPA disposto (disposizione %s) per %.2f €."
                ) % (batch.name, payment.amount))

        return {
            'name': _('Disposizione bonifici SEPA'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.batch.payment',
            'view_mode': 'form',
            'res_id': batch.id,
            'target': 'current',
        }


class LamessPayoutSepaWizardLine(models.TransientModel):
    _name = 'lamess.payout.sepa.wizard.line'
    _description = 'Lamess Payout SEPA Batch Wizard Line'

    wizard_id = fields.Many2one(
        'lamess.payout.sepa.wizard',
        required=True,
        ondelete='cascade',
    )
    payout_request_id = fields.Many2one(
        'lamess.payout.request',
        string='Richiesta',
        required=True,
    )
    partner_id = fields.Many2one(
        related='payout_request_id.partner_id',
        string='Consulente',
        readonly=True,
    )
    vendor_bill_id = fields.Many2one(
        related='payout_request_id.vendor_bill_id',
        string='Autofattura',
        readonly=True,
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='IBAN consulente',
        domain="[('partner_id', '=', partner_id)]",
    )
    currency_id = fields.Many2one(
        related='wizard_id.currency_id',
        readonly=True,
    )
    gross_amount = fields.Float(
        related='payout_request_id.gross_amount',
        string='Lordo',
        currency_field='currency_id',
        readonly=True,
    )
    vat_amount = fields.Float(
        related='payout_request_id.vat_amount',
        string='IVA',
        currency_field='currency_id',
        readonly=True,
    )
    withholding_amount = fields.Float(
        related='payout_request_id.withholding_amount',
        string='Ritenuta',
        currency_field='currency_id',
        readonly=True,
    )
    administrative_fee_amount = fields.Float(
        related='payout_request_id.administrative_fee_amount',
        string='Costo amm.',
        currency_field='currency_id',
        readonly=True,
    )
    net_amount = fields.Monetary(
        string='Netto da bonificare',
        compute='_compute_net_amount',
        currency_field='currency_id',
    )

    @api.depends('gross_amount', 'vat_amount', 'withholding_amount', 'administrative_fee_amount')
    def _compute_net_amount(self):
        # Netto da bonificare = Lordo + IVA - Ritenuta - Costo amministrativo.
        for line in self:
            line.net_amount = (
                line.gross_amount
                + line.vat_amount
                - line.withholding_amount
                - line.administrative_fee_amount
            )
