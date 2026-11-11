# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
import json
from odoo import models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import json_default
from datetime import date


class BankBookWizard(models.TransientModel):
    """Inheriting account bank book report model to overirde excel and pdf
    reports"""
    _inherit = "account.bank.book.report"

    def report_xlsx(self):
        """Overriding excel report for account bank book report"""
        self.ensure_one()
        data = {'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'),
                'form': self.read(
                    ['date_from', 'date_to', 'sortby', 'account_ids',
                     'display_account', 'journal_ids', 'target_move'])[0]}
        if isinstance(data['form'].get('date_from'), date):
            data['form']['date_from'] = data['form']['date_from'].isoformat()

        if isinstance(data['form'].get('date_to'), date):
            data['form']['date_to'] = data['form']['date_to'].isoformat()
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')
        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = data['form']['display_account']
        account_ids = data['form']['account_ids']
        if account_ids == []:
            raise UserError(
                _("You need to add at least one account to print the bank book report."))
        accounts = self.env['account.account'].search(
            [('id', 'in', account_ids)])
        if not accounts:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = []
            for journal in journals: accounts.append(
                journal.company_id.account_journal_payment_credit_account_id.id)
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts)])
        report_model = self.env['report.base_accounting_kit.report_bank_book']
        report_obj = report_model.with_context(
            data['form'].get('used_context', {}))._get_account_move_entry(
            accounts,
            init_balance,
            sortby,
            display_account
        )
        if len(report_obj) > 0:
            return {
                'type': 'ir.actions.report',
                'data': {'model': 'report.base_accounting_kit.report_bank_book',
                         'options': json.dumps(data, default=json_default),
                         'output_format': 'xlsx',
                         'report_name': 'Bank Book Report',
                         },
                'report_type': 'bank_book_xlsx'
            }
        else:
            raise ValidationError("No records found for the given criteria!")

    def check_report(self):
        """Overriding the function to fetch values for printing pdf report"""
        self.ensure_one()
        if self.initial_balance and not self.date_from:
            raise UserError(_("You must choose a Start Date"))
        data = {'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'),
                'form': self.read(
                    ['date_from', 'date_to', 'journal_ids', 'target_move',
                     'display_account',
                     'account_ids', 'sortby', 'initial_balance'])[0]}
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')
        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = data['form']['display_account']
        account_ids = data['form']['account_ids']
        if account_ids == []:
            raise UserError(
                _("You need to add at least one account to print the bank book report."))
        accounts = self.env['account.account'].search(
            [('id', 'in', account_ids)])
        if not accounts:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = []
            for journal in journals: accounts.append(
                journal.company_id.account_journal_payment_credit_account_id.id)
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts)])
        report_model = self.env['report.base_accounting_kit.report_bank_book']
        report_obj = report_model.with_context(
            data['form'].get('used_context', {}))._get_account_move_entry(
            accounts,
            init_balance,
            sortby,
            display_account
        )
        if len(report_obj) > 0:
            return self.env.ref(
                'base_accounting_kit.action_report_bank_book').report_action(
                self,
                data=data)
        else:
            raise ValidationError("No records found for the given criteria!")
