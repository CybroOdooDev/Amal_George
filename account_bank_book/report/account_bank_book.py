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
import io
from datetime import datetime
from odoo import models
from odoo.exceptions import UserError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class ReportBankBook(models.AbstractModel):
    """Inheriting report bank book model to get account move entries"""
    _inherit = 'report.base_accounting_kit.report_bank_book'
    _description = 'Bank Book Report'

    def _get_account_move_entry(self, accounts, init_balance, sortby,
                                display_account):
        """Function to fetch the values for the report using accounts and
        values"""
        cr = self.env.cr
        move_line = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}
        if init_balance:
            init_tables, init_where_clause, init_where_params = \
                move_line.with_context(
                    date_from=self.env.context.get('date_from'), date_to=False,
                    initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id',
                                           'm').replace('account_move_line',
                                                        'l')
            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, 
            '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' 
            AS lname, COALESCE(SUM(l.debit),0.0) AS debit, 
            COALESCE(SUM(l.credit),0.0) AS credit, 
            COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, 
            '' AS lpartner_id,\
                    '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                    NULL AS currency_id,\
                    '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                    '' AS partner_name\
                    FROM account_move_line l\
                    LEFT JOIN account_move m ON (l.move_id=m.id)\
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                    JOIN account_journal j ON (l.journal_id=j.id)\
                    WHERE l.account_id IN %s""" + filters +
                   ' GROUP BY l.account_id')
            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)
        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'
        tables, where_clause, where_params = move_line._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace(
            'account_move_line', 'l')
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date 
        AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref 
        AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, 
        COALESCE(l.credit,0) AS credit, 
        COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
                m.name AS move_name, c.symbol AS currency_code, p.name 
                AS partner_name\
                FROM account_move_line l\
                JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                JOIN account_account acc ON (l.account_id = acc.id) \
                WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, 
                l.account_id, l.date, j.code, l.currency_id, l.amount_currency, 
                l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)
        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)
        account_res = []
        for account in accounts:
            company = self.env.user.company_id
            currency = company.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
        return account_res

    def get_xlsx_report(self, options, response):
        """Excel report format for the Excel report"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        options = options
        if not options['form']:
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        init_balance = options['form'].get('initial_balance', True)
        sortby = options['form'].get('sortby', 'sort_date')
        display_account = options['form']['display_account']
        account_ids = options['form']['account_ids']
        accounts = self.env['account.account'].search(
            [('id', 'in', account_ids)])
        if not accounts:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = []
            for journal in journals:
                accounts.append(
                    journal.company_id.
                    account_journal_payment_credit_account_id.id)
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts)])
        report_obj = self.with_context(
            options['form'].get('used_context', {}))._get_account_move_entry(
            accounts,
            init_balance,
            sortby,
            display_account)
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format(
            {'font_size': 16, 'align': 'center', 'bg_color': '#D3D3D3',
             'bold': True})
        format2 = workbook.add_format(
            {'font_size': 12, 'bold': True, 'bg_color': '#D3D3D3'})
        format3 = workbook.add_format({'font_size': 10, 'bold': True})
        format4 = workbook.add_format({'font_size': 10})
        format6 = workbook.add_format({'font_size': 10, 'bold': True})
        format5 = workbook.add_format({'font_size': 10, 'align': 'right'})
        format1.set_align('center')
        format2.set_align('center')
        format3.set_align('right')
        format4.set_align('left')
        sheet.set_column('C:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 42)
        codes = [journal.code for journal in
                 self.env['account.journal'].search(
                     [('id', 'in', options['form']['journal_ids'])])]
        logged_users = self.env.company
        report_date = datetime.now().strftime("%Y-%m-%d")
        sheet.merge_range(0, 5, 0, 8, logged_users.name, format3)
        sheet.merge_range(0, 0, 0, 4, "Report Date : " + report_date, format6)
        sheet.merge_range(1, 0, 2, 8, "Bank Book Report", format1)
        journal_codes = ''
        for code in codes:
            journal_codes += code
            if journal_codes:
                journal_codes += ', '
        sheet.write('A4', "Journals : ", format6)
        sheet.merge_range(3, 1, 3, 8, journal_codes, format4)
        if options['form']['target_move'] == 'all':
            target_moves = 'All entries'
        else:
            target_moves = 'All posted entries'
        if options['form']['sortby'] == 'sort_date':
            sortby = 'Date'
        else:
            sortby = 'Journal and partners'
        if options['form']['date_from']:
            date_start = options['form']['date_from']
        else:
            date_start = ""
        if options['form']['date_to']:
            date_end = options['form']['date_to']
        else:
            date_end = ""
        if sortby == 'Date':
            sheet.write('G5', "Start Date", format3)
            sheet.write('G6', date_start, format4)
            sheet.write('I5', "End Date", format3)
            sheet.write('I6', date_end, format4)
        sheet.write('A5', "Sorted By", format6)
        sheet.write('A6', sortby, format4)
        sheet.write('C5', "Target Moves", format6)
        sheet.write('C6', target_moves, format4)
        sheet.write('A8', "Date ", format2)
        sheet.write('B8', "JRNL", format2)
        sheet.write('C8', "Partner", format2)
        sheet.write('D8', "Ref", format2)
        sheet.write('E8', "Move", format2)
        sheet.write('F8', "Entry Label", format2)
        sheet.write('G8', "Debit", format2)
        sheet.write('H8', "Credit", format2)
        sheet.write('I8', "Balance", format2)
        row_number = 8
        col_number = 0
        if report_obj:
            for datas in accounts:
                for values in report_obj:
                    if datas['name'] == values['name']:
                        sheet.write(row_number, col_number,
                                    datas['code'] + ' ' + datas['name'],
                                    format6)
                        sheet.write(row_number, col_number + 6, values['debit'],
                                    format3)
                        sheet.write(row_number, col_number + 7,
                                    values['credit'], format3)
                        sheet.write(row_number, col_number + 8,
                                    values['balance'], format3)
                        row_number += 1
                        for lines in values['move_lines']:
                            sheet.write(row_number, col_number, lines['ldate'],
                                        format4)
                            sheet.write(row_number, col_number + 1,
                                        lines['lcode'], format4)
                            sheet.write(row_number, col_number + 2,
                                        lines['partner_name'], format4)
                            sheet.write(row_number, col_number + 3,
                                        lines['lref'], format4)
                            sheet.write(row_number, col_number + 4,
                                        lines['move_name'], format4)
                            sheet.write(row_number, col_number + 5,
                                        lines['lname'], format4)
                            sheet.write(row_number, col_number + 6,
                                        lines['debit'], format5)
                            sheet.write(row_number, col_number + 7,
                                        lines['credit'], format5)
                            sheet.write(row_number, col_number + 8,
                                        lines['balance'], format5)
                            row_number += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
