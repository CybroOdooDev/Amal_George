# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jigin K (odoo@cybrosys.com)
#
#    This program is under the terms of Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
################################################################################
from odoo import api, models, _
from odoo.exceptions import UserError


class AccountCashBookReport(models.TransientModel):
	"""
	This transient model represents a dynamic cash book report in the accounting
	module.
	"""
	_name = 'account.cash.book.report'
	_inherit = 'account.cash.book.report'

	def action_view_report(self):
		"""
        Generate and display the Cash Book Reports.
		"""
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
		display_account = 'movement'
		if data['form'].get('journal_ids', False):
			codes = [journal.code for journal in
			         self.env['account.journal'].search(
				         [('id', 'in', data['form']['journal_ids'])])]
		account_ids = data['form']['account_ids']
		accounts = self.env['account.account'].search(
			[('id', 'in', account_ids)])
		if not accounts:
			raise UserError(_("You must choose an account"))
		accounts_res = self.with_context(
			data['form'].get('used_context', {}))._get_dynamic_move_entry(
			accounts,
			init_balance,
			sortby,
			display_account)
		acc_name = []
		for i in accounts:
			acc_name.append({
				'acc_name': i.code + ' ' + i.name,
			})
		currency = self._get_currency()
		data['type'] = 'cash_account'
		if accounts_res:
			return {
				'name': "Cash Book Reports",
				'type': 'ir.actions.client',
				'tag': 'report_cashbook',
				'params': {
					'form': data['form'],
					'acc_name': acc_name,
					'account_res': accounts_res,
					'currency': currency,
					'init_balance': init_balance,
				}
			}
		else:
			raise UserError("No report for the selected credentials")

	def _get_dynamic_move_entry(self, accounts, init_balance, sortby,
	                            display_account):
		"""
		Retrieve dynamic move entries for the specified accounts based on
		provided parameters.
		"""
		cr = self.env.cr
		moveline = self.env['account.move.line']
		move_lines = {x: [] for x in accounts.ids}
		# Prepare initial sql query and Get the initial move lines
		if init_balance:
			init_tables, init_where_clause, init_where_params = moveline.with_context(
				date_from=self.env.context.get('date_from'), date_to=False,
				initial_bal=True)._query_get()
			init_wheres = [""]
			if init_where_clause.strip():
				init_wheres.append(init_where_clause.strip())
			init_filters = " AND ".join(init_wheres)
			filters = init_filters.replace('account_move_line__move_id',
			                               'm').replace('account_move_line',
			                                            'l')
			sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                    '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                    NULL AS currency_id,\
                    '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                    '' AS partner_name\
                    FROM account_move_line l\
                    LEFT JOIN account_move m ON (l.move_id=m.id)\
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                    JOIN account_journal j ON (l.journal_id=j.id)\
                    WHERE l.account_id IN %s""" + filters + ' GROUP BY l.account_id')
			params = (tuple(accounts.ids),) + tuple(init_where_params)
			cr.execute(sql, params)
			for row in cr.dictfetchall():
				move_lines[row.pop('account_id')].append(row)
		sql_sort = 'l.date, l.move_id'
		if sortby == 'sort_journal_partner':
			sql_sort = 'j.code, p.name, l.move_id'
		# Prepare sql query base on selected parameters from wizard
		tables, where_clause, where_params = moveline._query_get()
		wheres = [""]
		if where_clause.strip():
			wheres.append(where_clause.strip())
		filters = " AND ".join(wheres)
		filters = filters.replace('account_move_line__move_id', 'm').replace(
			'account_move_line', 'l')
		# Get move lines base on sql query and Calculate the total balance of move lines
		sql = ('''SELECT l.id AS lid,m.id as m_id, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
                m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
                FROM account_move_line l\
                JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                JOIN account_account acc ON (l.account_id = acc.id) \
                WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id,m.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)
		params = (tuple(accounts.ids),) + tuple(where_params)
		cr.execute(sql, params)
		for row in cr.dictfetchall():
			balance = 0
			for line in move_lines.get(row['account_id']):
				balance += line['debit'] - line['credit']
			row['balance'] += balance
			move_lines[row.pop('account_id')].append(row)
		# Calculate the debit, credit and balance for Accounts
		account_res = []
		for account in accounts:
			currency = (account.currency_id and account.currency_id or
			            account.company_ids[0].currency_id)
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

	@api.model
	def _get_currency(self):
		"""
		Get the currency information based on the default journal.
		"""
		journal = self.env['account.journal'].browse(
			self.env.context.get('default_journal_id', False))
		if journal.currency_id:
			return journal.currency_id.id
		currency_array = [self.env.user.company_id.currency_id.symbol,
		                  self.env.user.company_id.currency_id.position]
		return currency_array
