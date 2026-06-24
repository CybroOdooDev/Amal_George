# -*- coding: utf-8 -*-
"""Workflow visibile di richiesta/revisione/liquidazione prelievi."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class LamessPayoutRequest(models.Model):
    _name = 'lamess.payout.request'
    _description = 'Lamess Payout Request'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    display_name = fields.Char(
        string='Riferimento',
        compute='_compute_display_name',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Consulente',
        required=True,
        ondelete='restrict',
        index=True,
        domain=[('x_is_networker', '=', True)],
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Azienda',
        required=True,
        default=lambda self: self.env.company,
        ondelete='restrict',
        index=True,
    )
    state = fields.Selection([
        ('requested', 'Richiesto'),
        ('review', 'In revisione'),
        ('approved', 'Approvato'),
        ('paid', 'Liquidato'),
        ('rejected', 'Rifiutato'),
        ('cancelled', 'Annullato'),
    ], string='Stato', required=True, default='requested', tracking=True, index=True)
    gross_amount = fields.Float(
        string='Importo lordo richiesto (€)',
        required=True,
        digits=(16, 2),
        tracking=True,
    )
    x_amount_is_net = fields.Boolean(
        string='Importo gia\' al netto',
        default=False,
        help=(
            "Se attivo, l'importo richiesto e' gia' il netto da liquidare "
            "(la ritenuta e' stata applicata a monte nel portale): nessuna "
            "ritenuta o costo amministrativo viene riapplicato qui."
        ),
    )
    taxable_base_amount = fields.Float(
        string='Base imponibile (€)',
        digits=(16, 2),
        compute='_compute_amount_breakdown',
        store=True,
    )
    withholding_amount = fields.Float(
        string='Ritenuta (€)',
        digits=(16, 2),
        compute='_compute_amount_breakdown',
        store=True,
    )
    administrative_fee_amount = fields.Float(
        string='Costo amministrativo (€)',
        digits=(16, 2),
        compute='_compute_amount_breakdown',
        store=True,
    )
    net_amount = fields.Float(
        string='Netto liquidabile (€)',
        digits=(16, 2),
        compute='_compute_amount_breakdown',
        store=True,
    )
    requested_at = fields.Datetime(
        string='Data richiesta',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
    )
    reviewed_at = fields.Datetime(
        string='Data revisione',
        readonly=True,
        tracking=True,
    )
    paid_at = fields.Datetime(
        string='Data liquidazione',
        readonly=True,
        tracking=True,
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Richiesto da',
        default=lambda self: self.env.user,
        readonly=True,
    )
    reviewed_by_id = fields.Many2one(
        'res.users',
        string='Revisionato da',
        readonly=True,
    )
    paid_by_id = fields.Many2one(
        'res.users',
        string='Liquidato da',
        readonly=True,
    )
    accounting_move_id = fields.Many2one(
        'account.move',
        string='Registrazione contabile',
        readonly=True,
        copy=False,
        ondelete='set null',
    )
    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Autofattura (bozza)',
        readonly=True,
        copy=False,
        ondelete='set null',
        help='Fattura fornitore self-invoice generata in bozza alla richiesta.',
    )
    self_invoice_scenario = fields.Selection([
        ('A', 'A — Occasionale (ricevuta)'),
        ('B', 'B — P.IVA (autofattura)'),
    ], string='Scenario fiscale', compute='_compute_self_invoice_breakdown', store=True)
    vat_amount = fields.Float(
        string='IVA (€)',
        digits=(16, 2),
        compute='_compute_self_invoice_breakdown',
        store=True,
    )
    inps_total_amount = fields.Float(
        string='INPS totale (€)',
        digits=(16, 2),
        compute='_compute_self_invoice_breakdown',
        store=True,
    )
    inps_withheld_amount = fields.Float(
        string='INPS a carico agente 1/3 (€)',
        digits=(16, 2),
        compute='_compute_self_invoice_breakdown',
        store=True,
    )
    settlement_trace_line_ids = fields.One2many(
        'lamess.payout.request.settlement.line',
        'payout_request_id',
        string='Origine commissioni',
        copy=False,
    )
    traced_settlement_amount = fields.Float(
        string='Importo tracciato da settlement (€)',
        compute='_compute_traceability_amounts',
        store=True,
        digits=(16, 2),
    )
    untraced_amount = fields.Float(
        string='Importo non tracciato (€)',
        compute='_compute_traceability_amounts',
        store=True,
        digits=(16, 2),
    )
    review_note = fields.Text(string='Nota revisione')
    payment_note = fields.Text(string='Nota liquidazione')

    @api.model
    def _get_lamess_payout_config_values(self, company=False):
        company = company or self.env.company
        config_model = self.env.get('lamess.config')
        if config_model:
            # Riutilizziamo il record canonico di configurazione Lamess quando
            # disponibile, cosi payout, ritenuta e fee restano centralizzati.
            config = config_model.get_config(company=company)
            return {
                'minimum_payout': config.minimum_payout,
                'administrative_fee': config.administrative_fee,
                'withholding_tax_base_pct': config.withholding_tax_base_pct,
                'withholding_tax_rate_pct': config.withholding_tax_rate_pct,
            }
        icp = self.env['ir.config_parameter'].sudo()
        # Fallback utile nelle finestre di installazione o upgrade in cui il
        # modello singleton non e' ancora accessibile ma i parametri esistono gia'.
        return {
            'minimum_payout': float(icp.get_param('lamess_base.minimum_payout', 15.0) or 15.0),
            'administrative_fee': float(icp.get_param('lamess_base.administrative_fee', 2.5) or 2.5),
            'withholding_tax_base_pct': float(icp.get_param('lamess_base.withholding_tax_base_pct', 78.0) or 78.0),
            'withholding_tax_rate_pct': float(icp.get_param('lamess_base.withholding_tax_rate_pct', 23.0) or 23.0),
        }

    @api.model
    def _round_payout_amount(self, amount, company=False):
        company = company or self.env.company
        currency = company.currency_id or self.env.company.currency_id
        return currency.round(amount or 0.0) if currency else round(amount or 0.0, 2)

    @api.model
    def _compute_net_payout_breakdown(self, gross_amount, company=False):
        company = company or self.env.company
        config_vals = self._get_lamess_payout_config_values(company=company)
        gross_amount = self._round_payout_amount(gross_amount or 0.0, company=company)
        # Teniamo la formula fiscale in un helper unico cosi campi calcolati,
        # validazioni e scritture contabili derivano dagli stessi numeri. Ogni
        # componente viene arrotondato alla valuta prima della scrittura, mentre
        # il netto resta il residuo: cosi le righe contabili non si sbilanciano
        # sui mezzi centesimi.
        taxable_base = self._round_payout_amount(
            gross_amount * (config_vals['withholding_tax_base_pct'] / 100.0),
            company=company,
        )
        withholding = self._round_payout_amount(
            taxable_base * (config_vals['withholding_tax_rate_pct'] / 100.0),
            company=company,
        )
        administrative_fee = self._round_payout_amount(config_vals['administrative_fee'], company=company)
        net_amount = self._round_payout_amount(
            gross_amount - withholding - administrative_fee,
            company=company,
        )
        return {
            'taxable_base': taxable_base,
            'withholding': withholding,
            'administrative_fee': administrative_fee,
            'net_payout': net_amount,
            'minimum_payout': config_vals['minimum_payout'],
        }

    @api.depends('partner_id', 'gross_amount', 'state')
    def _compute_display_name(self):
        for record in self:
            partner_name = record.partner_id.name or 'Consulente'
            record.display_name = "%s · %.2f € · %s" % (
                partner_name,
                record.gross_amount or 0.0,
                dict(record._fields['state'].selection).get(record.state, record.state or ''),
            )

    @api.depends('gross_amount', 'company_id', 'x_amount_is_net')
    def _compute_amount_breakdown(self):
        for record in self:
            if record.x_amount_is_net:
                # Importo gia' al netto: nessuna ritenuta/fee, il netto coincide
                # con l'importo richiesto (la ritenuta e' gia' stata applicata
                # nel calcolo del prelevabile a portale).
                net = record._round_payout_amount(
                    record.gross_amount or 0.0,
                    company=record.company_id or self.env.company,
                )
                record.taxable_base_amount = 0.0
                record.withholding_amount = 0.0
                record.administrative_fee_amount = 0.0
                record.net_amount = net
                continue
            breakdown = self._compute_net_payout_breakdown(
                record.gross_amount or 0.0,
                company=record.company_id or self.env.company,
            )
            # Salviamo esplicitamente il dettaglio cosi chi revisiona puo'
            # controllare il calcolo della liquidazione senza rifarlo a mano.
            record.taxable_base_amount = breakdown['taxable_base']
            record.withholding_amount = breakdown['withholding']
            record.administrative_fee_amount = breakdown['administrative_fee']
            record.net_amount = breakdown['net_payout']

    @api.model
    def _partner_has_vat(self, partner):
        # Scenario B scatta quando il consulente ha una posizione IVA: P.IVA
        # presente (campo core o Lamess) oppure profilo fiscale registrato.
        return bool(
            partner.vat
            or partner.x_vat_number
            or partner.x_fiscal_profile == 'vat_registered'
        )

    @api.depends('gross_amount', 'company_id', 'partner_id',
                 'partner_id.vat', 'partner_id.x_vat_number',
                 'partner_id.x_fiscal_profile', 'partner_id.x_vat_exempt',
                 'partner_id.x_inps_rate_pct')
    def _compute_self_invoice_breakdown(self):
        # Calcoliamo i componenti dell'autofattura in Python a scopo informativo
        # e di validazione; gli importi contabili effettivi derivano dai record
        # account.tax configurati e applicati alla riga della bozza.
        for record in self:
            breakdown = record._get_self_invoice_breakdown(
                record.gross_amount or 0.0,
                record.partner_id,
                company=record.company_id or self.env.company,
            )
            record.self_invoice_scenario = breakdown['scenario']
            record.vat_amount = breakdown['vat']
            record.inps_total_amount = breakdown['inps_total']
            record.inps_withheld_amount = breakdown['inps_withheld']

    @api.model
    def _get_self_invoice_breakdown(self, gross_amount, partner, company=False):
        """Ripartizione fiscale dell'autofattura (informativa).

        - Scenario A (occasionale senza P.IVA): solo ritenuta IRPEF (23% sul 78%).
        - Scenario B (con P.IVA): IVA 22% (salvo esenzione), ritenuta IRPEF e INPS
          sulla quota lorda eccedente la soglia annua, azzerata oltre il massimale.
          La ritenuta INPS in fattura e' 1/3 (quota a carico dell'agente).
        """
        company = company or self.env.company
        gross_amount = self._round_payout_amount(gross_amount or 0.0, company=company)
        config_vals = self._get_lamess_payout_config_values(company=company)
        base = self._round_payout_amount(
            gross_amount * (config_vals['withholding_tax_base_pct'] / 100.0),
            company=company,
        )
        irpef = self._round_payout_amount(
            base * (config_vals['withholding_tax_rate_pct'] / 100.0),
            company=company,
        )
        result = {
            'scenario': 'A',
            'taxable_base': base,
            'irpef': irpef,
            'vat': 0.0,
            'inps_total': 0.0,
            'inps_withheld': 0.0,
        }
        if not partner or not self._partner_has_vat(partner):
            return result

        result['scenario'] = 'B'
        # IVA
        if not partner.x_vat_exempt:
            result['vat'] = self._round_payout_amount(gross_amount * 0.22, company=company)
        # INPS: solo sulla quota di questo prelievo compresa tra la soglia annua
        # e il massimale, calcolata sul 78% e ridotta a 1/3 in fattura.
        inps_rate = float(partner.x_inps_rate_pct or '0') / 100.0
        if inps_rate:
            config = self.env['lamess.config'].get_config(company=company)
            threshold = config.scn_threshold or 0.0
            ceiling = config.autoinv_inps_ceiling or 0.0
            ytd = partner.x_ytd_gross_withdrawals or 0.0
            upper = min(ytd + gross_amount, ceiling) if ceiling else (ytd + gross_amount)
            slice_gross = max(0.0, upper - max(threshold, ytd))
            if slice_gross > 0:
                inps_base = self._round_payout_amount(slice_gross * 0.78, company=company)
                inps_total = self._round_payout_amount(inps_base * inps_rate, company=company)
                result['inps_total'] = inps_total
                result['inps_withheld'] = self._round_payout_amount(inps_total / 3.0, company=company)
        return result

    @api.depends('gross_amount', 'settlement_trace_line_ids.allocated_amount')
    def _compute_traceability_amounts(self):
        for record in self:
            traced_amount = sum(record.settlement_trace_line_ids.mapped('allocated_amount'))
            record.traced_settlement_amount = traced_amount
            record.untraced_amount = max((record.gross_amount or 0.0) - traced_amount, 0.0)

    @api.constrains('gross_amount')
    def _check_positive_amount(self):
        for record in self:
            if record.gross_amount <= 0:
                raise ValidationError(_("L'importo richiesto deve essere positivo."))

    @api.constrains('partner_id', 'state')
    def _check_single_open_request(self):
        for record in self:
            if record.state not in ('requested', 'review', 'approved'):
                continue
            duplicate = self.search([
                ('id', '!=', record.id),
                ('partner_id', '=', record.partner_id.id),
                ('state', 'in', ['requested', 'review', 'approved']),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Esiste gia' una richiesta di prelievo aperta per questo consulente."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._validate_business_rules()
            record._sync_settlement_traceability()
        return records

    def write(self, vals):
        result = super().write(vals)
        tracked = {'partner_id', 'gross_amount', 'state'}
        if tracked.intersection(vals.keys()):
            self._validate_business_rules()
        if tracked.intersection(vals.keys()) and not self.env.context.get('skip_settlement_traceability_sync'):
            for record in self:
                if record.state in ('requested', 'review', 'approved'):
                    record._sync_settlement_traceability()
                elif record.state in ('rejected', 'cancelled'):
                    record.settlement_trace_line_ids.unlink()
        return result

    def _validate_business_rules(self):
        for record in self:
            if not record.partner_id:
                continue
            breakdown = self._compute_net_payout_breakdown(
                record.gross_amount or 0.0,
                company=record.company_id or self.env.company,
            )
            # Validiamo contro il wallet corrente solo finche la richiesta e'
            # aperta; i record storici pagati o rifiutati devono restare validi.
            if record.gross_amount < breakdown['minimum_payout']:
                raise ValidationError(_(
                    "L'importo richiesto e' inferiore al minimo payout configurato (%.2f €)."
                ) % breakdown['minimum_payout'])
            if record.gross_amount > record.partner_id.x_wallet_balance and record.state in ('requested', 'review', 'approved'):
                raise ValidationError(_(
                    "L'importo richiesto supera il saldo wallet disponibile del consulente."
                ))
            if record.state in ('requested', 'review', 'approved') and not record.partner_id.can_request_payout():
                raise ValidationError(_(
                    "Il consulente non e' eleggibile per richiedere un prelievo."
                ))

    def _get_active_settlement_trace_domain(self):
        return [
            ('payout_request_id.state', 'not in', ['rejected', 'cancelled']),
        ]

    def _get_settlement_already_allocated_amount(self, settlement):
        self.ensure_one()
        domain = self._get_active_settlement_trace_domain() + [
            ('settlement_id', '=', settlement.id),
            ('payout_request_id', '!=', self.id),
        ]
        lines = self.env['lamess.payout.request.settlement.line'].search(domain)
        return sum(lines.mapped('allocated_amount'))

    def _get_available_posted_settlements(self):
        self.ensure_one()
        return self.env['lamess.commission.settlement'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('gross_amount', '>', 0.0),
        ], order='period_id asc, id asc')

    def _sync_settlement_traceability(self):
        for record in self:
            if not record.partner_id or record.state not in ('requested', 'review', 'approved'):
                continue
            remaining_amount = record.gross_amount or 0.0
            record.with_context(skip_settlement_traceability_sync=True).settlement_trace_line_ids.unlink()
            line_commands = []
            for settlement in record._get_available_posted_settlements():
                if remaining_amount <= 0:
                    break
                already_allocated = record._get_settlement_already_allocated_amount(settlement)
                residual_amount = max((settlement.gross_amount or 0.0) - already_allocated, 0.0)
                if not residual_amount:
                    continue
                allocated_amount = min(residual_amount, remaining_amount)
                line_commands.append((0, 0, {
                    'settlement_id': settlement.id,
                    'allocated_amount': allocated_amount,
                }))
                remaining_amount -= allocated_amount
            if line_commands:
                record.with_context(skip_settlement_traceability_sync=True).write({
                    'settlement_trace_line_ids': line_commands,
                })

    def action_mark_in_review(self):
        for record in self.filtered(lambda rec: rec.state == 'requested'):
            record.write({
                'state': 'review',
                'reviewed_at': fields.Datetime.now(),
                'reviewed_by_id': self.env.user.id,
            })
        return True

    def action_approve(self):
        for record in self.filtered(lambda rec: rec.state in ('requested', 'review')):
            record._validate_business_rules()
            if record.gross_amount > record.partner_id.x_wallet_balance:
                raise UserError(_("Il saldo wallet non e' sufficiente per approvare questa richiesta."))
            # All'approvazione l'importo richiesto viene subito dedotto dal wallet
            # del consulente; la scrittura contabile avviene poi in liquidazione.
            record.partner_id.write({
                'x_wallet_balance': record.partner_id.x_wallet_balance - record.gross_amount,
            })
            record.write({
                'state': 'approved',
                'reviewed_at': fields.Datetime.now(),
                'reviewed_by_id': self.env.user.id,
            })
        return True

    def action_reject(self):
        for record in self.filtered(lambda rec: rec.state in ('requested', 'review', 'approved')):
            # Se era gia' approvata il wallet era stato dedotto: lo ripristiniamo.
            if record.state == 'approved':
                record.partner_id.write({
                    'x_wallet_balance': record.partner_id.x_wallet_balance + record.gross_amount,
                })
            record.write({
                'state': 'rejected',
                'reviewed_at': fields.Datetime.now(),
                'reviewed_by_id': self.env.user.id,
            })
        return True

    def action_cancel(self):
        for record in self.filtered(lambda rec: rec.state in ('requested', 'review', 'approved')):
            # Se era gia' approvata il wallet era stato dedotto: lo ripristiniamo.
            if record.state == 'approved':
                record.partner_id.write({
                    'x_wallet_balance': record.partner_id.x_wallet_balance + record.gross_amount,
                })
            record.write({'state': 'cancelled'})
        return True

    def action_mark_paid(self):
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Solo una richiesta approvata puo' essere liquidata."))
            if record.gross_amount > record.partner_id.x_wallet_balance:
                raise UserError(_("Il saldo wallet non e' sufficiente per liquidare questa richiesta."))
            record._sync_settlement_traceability()
            move = record._create_accounting_move()
            # Il wallet viene ridotto del lordo richiesto perche' ritenuta e
            # costo amministrativo fanno parte della stessa liquidazione payout.
            record.partner_id.write({
                'x_wallet_balance': record.partner_id.x_wallet_balance - record.gross_amount,
            })
            record.write({
                'state': 'paid',
                'paid_at': fields.Datetime.now(),
                'paid_by_id': self.env.user.id,
                'accounting_move_id': move.id,
            })
        return True

    def _get_settlement_journal(self):
        self.ensure_one()
        return self._get_payout_accounting_config().payout_journal_id

    def _get_payout_accounting_config(self):
        self.ensure_one()
        config = self.env['lamess.config'].get_config(company=self.company_id or self.env.company)
        config._check_payout_accounting_configuration()
        return config

    def _get_liquidity_account(self, journal):
        self.ensure_one()
        return self._get_payout_accounting_config().payout_liquidity_account_id

    def _get_withholding_account(self):
        self.ensure_one()
        return self._get_payout_accounting_config().payout_withholding_account_id

    def _get_fee_account(self):
        self.ensure_one()
        return self._get_payout_accounting_config().payout_fee_account_id

    def _prepare_move_lines(self, journal):
        self.ensure_one()
        config = self._get_payout_accounting_config()
        payable_account = config.payout_payable_account_id
        liquidity_account = self._get_liquidity_account(journal)
        # Struttura della scrittura:
        # 1. dare sul conto payout configurato per il debito lordo da chiudere
        # 2. avere sul conto di liquidita' per il netto effettivamente pagato
        # 3. avere sul conto ritenute se la trattenuta fiscale e' presente
        # 4. avere sul conto fee per la trattenuta amministrativa
        lines = [
            (0, 0, {
                'name': _("Liquidazione prelievo %s") % self.display_name,
                'partner_id': self.partner_id.id,
                'account_id': payable_account.id,
                'debit': self.gross_amount,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': _("Pagamento netto prelievo %s") % self.display_name,
                'partner_id': self.partner_id.id,
                'account_id': liquidity_account.id,
                'debit': 0.0,
                'credit': self.net_amount,
            }),
        ]

        if self.withholding_amount:
            withholding_account = self._get_withholding_account()
            lines.append((0, 0, {
                'name': _("Ritenuta prelievo %s") % self.display_name,
                'partner_id': self.partner_id.id,
                'account_id': withholding_account.id,
                'debit': 0.0,
                'credit': self.withholding_amount,
            }))

        if self.administrative_fee_amount:
            fee_account = self._get_fee_account()
            lines.append((0, 0, {
                'name': _("Costo amministrativo prelievo %s") % self.display_name,
                'partner_id': self.partner_id.id,
                'account_id': fee_account.id,
                'debit': 0.0,
                'credit': self.administrative_fee_amount,
            }))
        return lines

    def _create_accounting_move(self):
        self.ensure_one()
        if self.accounting_move_id:
            return self.accounting_move_id

        journal = self._get_settlement_journal()
        # Riutilizziamo la stessa scrittura se il pagamento viene ritentato
        # dalla UI dopo un problema parziale, evitando duplicazioni contabili.
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': (self.company_id or self.env.company).id,
            'date': fields.Date.context_today(self),
            'ref': _("Prelievo %s") % self.display_name,
            'line_ids': self._prepare_move_lines(journal),
        })
        move.action_post()
        return move

    def _get_self_invoice_taxes(self, config, breakdown, partner):
        """Record account.tax da applicare alla riga della bozza, per scenario."""
        self.ensure_one()
        taxes = self.env['account.tax']
        if config.autoinv_withholding_tax_id:
            taxes |= config.autoinv_withholding_tax_id
        if breakdown['scenario'] == 'B':
            if not partner.x_vat_exempt and config.autoinv_vat_tax_id:
                taxes |= config.autoinv_vat_tax_id
            if breakdown['inps_total'] and config.autoinv_inps_tax_id:
                taxes |= config.autoinv_inps_tax_id
        return taxes

    def _prepare_self_invoice_lines(self, config, breakdown, partner, company=False):
        """Righe della bozza autofattura, con split sulla soglia annua.

        Se il prelievo, sommato al lordo gia' prelevato nell'anno (YTD), supera
        la soglia lorda annua (``autoinv_gross_threshold``, es. 6.410,26 €), la
        riga viene divisa in due:

        - quota SOTTO soglia -> solo ritenuta IRPEF (+ IVA se scenario B);
        - quota OLTRE soglia -> ritenuta IRPEF + contributo INPS (+ IVA).

        Lo split scatta per i consulenti con P.IVA (scenario B) che superano la
        soglia. L'INPS sulla quota oltre soglia e' applicata solo se dovuta.
        Sotto soglia, o senza P.IVA, resta una riga unica.
        """
        self.ensure_one()
        company = company or self.company_id or self.env.company
        gross = self.gross_amount or 0.0
        expense_account = config.autoinv_expense_account_id.id

        # IRPEF sempre presente; IVA solo in scenario B per consulente non esente.
        irpef_tax = config.autoinv_withholding_tax_id
        vat_tax = self.env['account.tax']
        if breakdown['scenario'] == 'B' and not partner.x_vat_exempt and config.autoinv_vat_tax_id:
            vat_tax = config.autoinv_vat_tax_id
        inps_tax = config.autoinv_inps_tax_id
        common_taxes = irpef_tax | vat_tax

        # Quota di questo prelievo ancora sotto la soglia annua: la soglia tiene
        # conto del lordo gia' prelevato nell'anno (Total Withdrawn YTD).
        threshold = config.scn_threshold or 0.0
        ytd = partner.x_ytd_gross_withdrawals or 0.0
        if threshold:
            below_slice = max(0.0, min(gross, threshold - ytd))
        else:
            below_slice = gross
        below_slice = self._round_payout_amount(below_slice, company=company)
        above_slice = self._round_payout_amount(gross - below_slice, company=company)

        # Split per consulente con P.IVA (scenario B) quando il prelievo supera
        # la soglia annua. INPS sulla quota oltre soglia solo se effettivamente
        # dovuta; altrimenti la riga oltre soglia porta IRPEF (+ IVA) come quella
        # sotto soglia, ma la riga resta separata come richiesto.
        split = breakdown['scenario'] == 'B' and above_slice > 0
        if not split:
            return [(0, 0, {
                'name': _("Autofattura prelievo %s") % self.display_name,
                'account_id': expense_account,
                'quantity': 1.0,
                'price_unit': gross,
                'tax_ids': [(6, 0, common_taxes.ids)],
            })]

        above_taxes = common_taxes
        if inps_tax and breakdown['inps_total'] > 0:
            above_taxes = common_taxes | inps_tax

        lines = []
        if below_slice > 0:
            lines.append((0, 0, {
                'name': _("Autofattura prelievo %s - quota sotto soglia") % self.display_name,
                'account_id': expense_account,
                'quantity': 1.0,
                'price_unit': below_slice,
                'tax_ids': [(6, 0, common_taxes.ids)],
            }))
        lines.append((0, 0, {
            'name': _("Autofattura prelievo %s - quota oltre soglia") % self.display_name,
            'account_id': expense_account,
            'quantity': 1.0,
            'price_unit': above_slice,
            'tax_ids': [(6, 0, above_taxes.ids)],
        }))
        return lines

    def _create_vendor_bill(self):
        """Genera la bozza del documento (account.move) alla richiesta.

        - Consulente con P.IVA -> autofattura (``in_invoice``).
        - Privato senza P.IVA -> ricevuta (``in_receipt``).

        Idempotente: se la richiesta ha gia' un documento collegato lo
        restituisce senza crearne uno nuovo.
        """
        self.ensure_one()
        if self.vendor_bill_id:
            return self.vendor_bill_id
        company = self.company_id or self.env.company
        config = self.env['lamess.config'].get_config(company=company)
        config._check_autoinv_configuration()
        breakdown = self._get_self_invoice_breakdown(
            self.gross_amount or 0.0, self.partner_id, company=company,
        )
        # Righe della bozza: split automatico sulla soglia annua quando il
        # prelievo (+ YTD) la supera (IRPEF sotto soglia, IRPEF + INPS sopra).
        invoice_lines = self._prepare_self_invoice_lines(
            config, breakdown, self.partner_id, company=company,
        )
        # Numero progressivo per consulente, riparte ogni anno solare.
        ref = self.partner_id._next_autoinv_number()
        # Consulente con posizione IVA -> fattura (in_invoice). Privato senza
        # P.IVA (scenario A) -> ricevuta (in_receipt).
        move_type = 'in_invoice' if self._partner_has_vat(self.partner_id) else 'in_receipt'
        move = self.env['account.move'].create({
            'move_type': move_type,
            'company_id': company.id,
            'journal_id': config.autoinv_purchase_journal_id.id,
            'partner_id': self.partner_id.id,
            'ref': ref,
            # Nessuna invoice_date: la registrazione resta in bozza ed editabile.
            'invoice_line_ids': invoice_lines,
        })
        self.vendor_bill_id = move.id
        if hasattr(self, 'message_post'):
            self.message_post(body=_(
                "Generata bozza autofattura %s (scenario %s)."
            ) % (ref, breakdown['scenario']))
        return move

    def action_open_vendor_bill(self):
        self.ensure_one()
        if not self.vendor_bill_id:
            return False
        return {
            'name': 'Autofattura',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.vendor_bill_id.id,
            'target': 'current',
        }

    def action_open_traced_settlements(self):
        self.ensure_one()
        return {
            'name': 'Settlement collegati',
            'type': 'ir.actions.act_window',
            'res_model': 'lamess.commission.settlement',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.settlement_trace_line_ids.mapped('settlement_id').ids)],
            'target': 'current',
        }


class LamessPayoutRequestSettlementLine(models.Model):
    _name = 'lamess.payout.request.settlement.line'
    _description = 'Lamess Payout Request Settlement Trace Line'
    _order = 'payout_request_id, period_id, settlement_id'

    payout_request_id = fields.Many2one(
        'lamess.payout.request',
        string='Richiesta prelievo',
        required=True,
        ondelete='cascade',
        index=True,
    )
    settlement_id = fields.Many2one(
        'lamess.commission.settlement',
        string='Settlement',
        required=True,
        ondelete='restrict',
        index=True,
    )
    partner_id = fields.Many2one(related='payout_request_id.partner_id', store=True, readonly=True)
    period_id = fields.Many2one(related='settlement_id.period_id', store=True, readonly=True)
    settlement_state = fields.Selection(related='settlement_id.state', store=True, readonly=True)
    settlement_amount = fields.Float(
        related='settlement_id.gross_amount',
        string='Importo settlement (€)',
        store=True,
        readonly=True,
    )
    allocated_amount = fields.Float(string='Importo collegato (€)', required=True, digits=(16, 2))

    _payout_settlement_unique = models.Constraint(
        'UNIQUE(payout_request_id, settlement_id)',
        'Lo stesso settlement puo comparire una sola volta nella stessa richiesta payout.',
    )

    @api.constrains('payout_request_id', 'settlement_id', 'allocated_amount')
    def _check_traceability_consistency(self):
        for line in self:
            if line.allocated_amount <= 0:
                raise ValidationError(_("L'importo collegato deve essere positivo."))
            if line.settlement_id.partner_id != line.payout_request_id.partner_id:
                raise ValidationError(_("Il settlement collegato deve appartenere allo stesso consulente del payout."))
            if line.settlement_id.state != 'posted':
                raise ValidationError(_("Puoi collegare al payout solo settlement gia accreditati al wallet."))
            active_lines = self.search(line.payout_request_id._get_active_settlement_trace_domain() + [
                ('settlement_id', '=', line.settlement_id.id),
            ])
            allocated_total = sum(active_lines.mapped('allocated_amount'))
            if allocated_total - (line.settlement_id.gross_amount or 0.0) > 0.0001:
                raise ValidationError(_("L'importo collegato supera il totale del settlement."))
            payout_allocated_total = sum(line.payout_request_id.settlement_trace_line_ids.mapped('allocated_amount'))
            if payout_allocated_total - (line.payout_request_id.gross_amount or 0.0) > 0.0001:
                raise ValidationError(_("L'importo collegato supera il lordo richiesto nel payout."))
