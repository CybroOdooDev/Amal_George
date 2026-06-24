# -*- coding: utf-8 -*-
"""Configurazione contabile payout Lamess."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class LamessConfig(models.Model):
    _inherit = 'lamess.config'

    payout_journal_id = fields.Many2one(
        'account.journal',
        string='Payout journal',
        domain="[('company_id', '=', company_id)]",
        help='Journal used to post payout accounting entries.',
    )
    payout_payable_account_id = fields.Many2one(
        'account.account',
        string='Payout payable account',
        domain="[('company_ids', 'in', company_id), ('account_type', '=', 'liability_payable')]",
        help='Payable or clearing account debited for the gross payout amount.',
    )
    payout_liquidity_account_id = fields.Many2one(
        'account.account',
        string='Payout liquidity account',
        domain="[('company_ids', 'in', company_id), ('account_type', '=', 'asset_cash')]",
        help='Cash or bank account credited for the net payout amount.',
    )
    payout_withholding_account_id = fields.Many2one(
        'account.account',
        string='Payout withholding account',
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ['liability_current', 'liability_non_current'])]",
        help='Liability account credited with payout withholding tax.',
    )
    payout_fee_account_id = fields.Many2one(
        'account.account',
        string='Payout fee account',
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ['income', 'income_other', 'expense', 'expense_direct_cost'])]",
        help='Account credited with the administrative payout fee.',
    )

    # ── Autofattura (self-invoice) configuration ───────────────────────────
    # Le ritenute IRPEF, l'IVA e la cassa INPS sono record account.tax che
    # l'admin configura con le aliquote corrette (es. ritenuta su base 78%);
    # qui referenziamo i record da applicare alla bozza di autofattura.
    autoinv_purchase_journal_id = fields.Many2one(
        'account.journal',
        string='Self-invoice purchase journal',
        domain="[('company_id', '=', company_id), ('type', '=', 'purchase')]",
        help=(
            'Single shared purchase journal used for ALL consultant self-invoices. '
            'Never create one journal per consultant.'
        ),
    )
    autoinv_expense_account_id = fields.Many2one(
        'account.account',
        string='Self-invoice expense account',
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        help='Account used on the self-invoice line (taxable base).',
    )
    autoinv_vat_tax_id = fields.Many2one(
        'account.tax',
        string='Self-invoice VAT',
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
        help='VAT tax (default 22%) applied on Scenario B self-invoices.',
    )
    autoinv_withholding_tax_id = fields.Many2one(
        'account.tax',
        string='Self-invoice withholding (IRPEF)',
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
        help='IRPEF withholding tax (23% on 78% taxable base) applied on both scenarios.',
    )
    autoinv_inps_tax_id = fields.Many2one(
        'account.tax',
        string='Self-invoice INPS (cassa)',
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
        help='INPS pension contribution tax applied on Scenario B above the gross threshold.',
    )
    autoinv_gross_threshold = fields.Float(
        string='Self-invoice gross threshold (€)',
        default=6410.0,
        help=(
            'Annual gross ceiling for occasional collaborators (€6.410). Crossing it '
            'requires a P.IVA and triggers INPS on the slice above. Resets every 1 Jan.'
        ),
    )
    autoinv_inps_ceiling = fields.Float(
        string='INPS ceiling (€)',
        default=120607.0,
        help='Annual gross ceiling (€120.607). INPS contribution is zero above it.',
    )

    def _autoinv_is_configured(self):
        """True quando i campi minimi per emettere l'autofattura sono valorizzati.

        Permette di attivare la generazione della bozza solo dopo che l'admin ha
        completato la configurazione, lasciando intatto il flusso payout esistente
        sugli ambienti non ancora configurati.
        """
        self.ensure_one()
        return bool(
            self.autoinv_purchase_journal_id
            and self.autoinv_expense_account_id
            and self.autoinv_withholding_tax_id
        )

    def _check_autoinv_configuration(self):
        for config in self:
            missing = []
            required_fields = [
                ('autoinv_purchase_journal_id', _('self-invoice purchase journal')),
                ('autoinv_expense_account_id', _('self-invoice expense account')),
                ('autoinv_withholding_tax_id', _('self-invoice withholding (IRPEF)')),
            ]
            for field_name, label in required_fields:
                if not config[field_name]:
                    missing.append(label)
            if missing:
                raise UserError(_(
                    "Configura l'autofattura Lamess prima di emettere: %s."
                ) % ', '.join(missing))
            if config.autoinv_purchase_journal_id.company_id != config.company_id:
                raise UserError(_(
                    "Il journal autofattura deve appartenere alla stessa azienda della configurazione Lamess."
                ))
        return True

    def _check_payout_accounting_configuration(self):
        for config in self:
            missing = []
            required_fields = [
                ('payout_journal_id', _('payout journal')),
                ('payout_payable_account_id', _('payout payable account')),
                ('payout_liquidity_account_id', _('payout liquidity account')),
                ('payout_withholding_account_id', _('payout withholding account')),
                ('payout_fee_account_id', _('payout fee account')),
            ]
            for field_name, label in required_fields:
                if not config[field_name]:
                    missing.append(label)
            if missing:
                raise UserError(_(
                    "Configura la contabilita' payout Lamess prima di liquidare: %s."
                ) % ', '.join(missing))

            if config.payout_journal_id.company_id != config.company_id:
                raise UserError(_("Il journal payout deve appartenere alla stessa azienda della configurazione Lamess."))

            account_fields = [
                ('payout_payable_account_id', _('payout payable account')),
                ('payout_liquidity_account_id', _('payout liquidity account')),
                ('payout_withholding_account_id', _('payout withholding account')),
                ('payout_fee_account_id', _('payout fee account')),
            ]
            for field_name, label in account_fields:
                account = config[field_name]
                if config.company_id not in account.company_ids:
                    raise UserError(_(
                        "Il conto %s deve essere disponibile per l'azienda %s."
                    ) % (label, config.company_id.display_name))
                if 'deprecated' in account._fields and account.deprecated:
                    raise UserError(_("Il conto %s non puo' essere deprecato.") % label)
        return True

    def action_check_payout_accounting_configuration(self):
        self._check_payout_accounting_configuration()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Payout accounting'),
                'message': _("Configurazione contabile payout completa."),
                'sticky': False,
            },
        }
