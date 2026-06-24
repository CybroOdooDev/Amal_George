# -*- coding: utf-8 -*-
"""Test wallet e payout base sul partner."""

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAccountingPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.general_journal = self.env['account.journal'].search([
            ('company_id', '=', self.company.id),
            ('type', '=', 'general'),
        ], limit=1)

        self.payable_account = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
            ('account_type', '=', 'liability_payable'),
        ], limit=1) or self.env['account.account'].create({
            'name': 'Test Payable',
            'code': 'TPAYOUT',
            'account_type': 'liability_payable',
            'reconcile': True,
            'company_ids': [(6, 0, [self.company.id])],
        })
        self.liquidity_account = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
            ('account_type', '=', 'asset_cash'),
        ], limit=1) or self.env['account.account'].create({
            'name': 'Test Liquidity',
            'code': 'TLIQPD',
            'account_type': 'asset_cash',
            'company_ids': [(6, 0, [self.company.id])],
        })
        self.withholding_account = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
            ('account_type', '=', 'liability_current'),
            ('id', '!=', self.payable_account.id),
        ], limit=1) or self.env['account.account'].create({
            'name': 'Test Withholding',
            'code': 'TWITHH',
            'account_type': 'liability_current',
            'company_ids': [(6, 0, [self.company.id])],
        })
        self.fee_account = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
            ('account_type', '=', 'income'),
        ], limit=1) or self.env['account.account'].create({
            'name': 'Test Fee Income',
            'code': 'TFEEIN',
            'account_type': 'income',
            'company_ids': [(6, 0, [self.company.id])],
        })
        if not self.general_journal:
            self.general_journal = self.env['account.journal'].create({
                'name': 'Test Payout Journal',
                'code': 'TPJO',
                'type': 'general',
                'company_id': self.company.id,
                'default_account_id': self.liquidity_account.id,
            })
        elif not self.general_journal.default_account_id:
            self.general_journal.default_account_id = self.liquidity_account
        self.payout_config = self.env['lamess.config'].get_config(company=self.company)
        self.payout_config.write({
            'payout_journal_id': self.general_journal.id,
            'payout_payable_account_id': self.payable_account.id,
            'payout_liquidity_account_id': self.liquidity_account.id,
            'payout_withholding_account_id': self.withholding_account.id,
            'payout_fee_account_id': self.fee_account.id,
        })

    def _create_networker_partner(self, **vals):
        default_vals = {
            'x_is_networker': True,
            'x_join_date': fields.Date.today(),
            'property_account_payable_id': self.payable_account.id,
        }
        default_vals.update(vals)
        return self.env['res.partner'].create(default_vals)

    def _create_official_rank_snapshot(self, partner, period, rank_code):
        period_month = "%s-%02d" % (period.year, period.month)
        snapshot_model = self.env['lamess.partner.rank.snapshot'].sudo()
        snapshot = snapshot_model.search([
            ('partner_id', '=', partner.id),
            ('period_month', '=', period_month),
            ('snapshot_type', '=', 'monthly'),
        ], limit=1)
        values = {
            'partner_id': partner.id,
            'period_id': period.id,
            'period_month': period_month,
            'snapshot_type': 'monthly',
            'is_official': True,
            'is_dirty': False,
            'calc_state': 'ready',
            'rank_code': rank_code,
            'activity_status': 'active',
        }
        if snapshot:
            snapshot.write(values)
            return snapshot
        return snapshot_model.create(values)

    def _prepare_m3_runtime_context(self, period=None):
        workspace = self.env['lamess.m3.workspace'].search([], limit=1)
        if not workspace:
            workspace = self.env['lamess.m3.workspace'].create({'name': 'M3 Test Workspace'})
        self.env['lamess.m3.plan.version'].search([]).write({'state': 'archived'})
        plan = self.env['lamess.m3.plan.version'].create({
            'workspace_id': workspace.id,
            'name': 'v settlement test',
            'state': 'published',
            'validation_status': 'passed',
            'valid_from': fields.Date.today(),
        })
        family = self.env['lamess.m3.bonus.family'].search([('code', '=', 'DIRECT')], limit=1)
        if not family:
            family = self.env['lamess.m3.bonus.family'].create({
                'name': 'Direct Bonus',
                'code': 'DIRECT',
                'state': 'active',
            })
        else:
            family.write({'state': 'active'})
        period = period or self.env['lamess.m3.bonus.runtime.line']._get_or_create_period_for_date(fields.Date.today())
        return plan, family, period

    def _create_runtime_line(self, partner, amount, bonus_type='direct', period=None):
        plan, family, period = self._prepare_m3_runtime_context(period=period)
        return self.env['lamess.m3.bonus.runtime.line'].create({
            'period_id': period.id,
            'plan_version_id': plan.id,
            'family_id': family.id,
            'recipient_id': partner.id,
            'bonus_type': bonus_type,
            'level': 1,
            'base_pv': 100.0,
            'previous_percentage': 0.0,
            'recipient_percentage': amount,
            'percentage': amount,
            'amount_eur': amount,
            'recipient_rank_code': partner.x_rank_current or 'none',
            'source_rank_code': partner.x_rank_current or 'none',
        })

    def _prepare_direct_runtime_engine(self, period=None):
        self.env['lamess.m3.rank'].seed_client_career_matrix()
        plan, direct_family, period = self._prepare_m3_runtime_context(period=period)
        self.env['lamess.m3.bonus.rate'].seed_default_family_matrix(direct_family)
        team_family = self.env['lamess.m3.bonus.family'].search([('code', '=', 'TEAM')], limit=1)
        if team_family:
            team_family.write({'state': 'active'})
        return plan, direct_family, period

    def _create_sale_origin_for_pv(self, seller, customer, pv_amount=100.0):
        product_vals = {
            'name': 'E2E Commission Product',
            'type': 'consu',
            'list_price': pv_amount,
        }
        if 'x_pv_value' in self.env['product.product']._fields:
            product_vals['x_pv_value'] = pv_amount
        product = self.env['product.product'].create(product_vals)
        if hasattr(product, 'product_tmpl_id') and product.product_tmpl_id:
            product.product_tmpl_id.property_account_income_id = self.fee_account

        order_vals = {
            'partner_id': customer.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1.0,
                'price_unit': pv_amount,
            })],
        }
        if 'x_networker_id' in self.env['sale.order']._fields:
            order_vals['x_networker_id'] = seller.id
        order = self.env['sale.order'].create(order_vals)
        order.action_confirm()

        movement = self.env['lamess.pv.movement'].search([
            ('sale_order_id', '=', order.id),
            ('move_type', '=', 'sale'),
        ], limit=1)
        movement_vals = {
            'partner_id': customer.id,
            'networker_id': seller.id,
            'sale_order_id': order.id,
            'origin_order_line_id': order.order_line[:1].id,
            'product_id': product.id,
            'pv_amount': pv_amount,
            'move_type': 'sale',
            'state': 'confirmed',
            'date': fields.Date.today(),
        }
        if movement:
            movement.write(movement_vals)
        else:
            movement = self.env['lamess.pv.movement'].create(movement_vals)
        return order, movement

    def test_wallet_balance_default_zero(self):
        partner = self.env['res.partner'].create({'name': 'Wallet Partner'})
        self.assertAlmostEqual(partner.x_wallet_balance, 0.0)

    def test_request_payout_creates_open_request(self):
        partner = self._create_networker_partner(**{
            'name': 'Payout Eligible',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 120.0,
        })

        action = partner.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])

        self.assertTrue(request)
        self.assertEqual(request.partner_id, partner)
        self.assertEqual(request.state, 'requested')
        self.assertEqual(request.gross_amount, 120.0)

    def test_request_payout_requires_eligibility(self):
        partner = self._create_networker_partner(**{
            'name': 'Payout Blocked',
            'x_networker_state': 'active',
            'x_kyc_state': 'submitted',
            'x_wallet_balance': 120.0,
        })

        with self.assertRaises(UserError):
            partner.action_request_payout()

    def test_draft_kyc_generates_direct_runtime_but_blocks_payout(self):
        partner = self._create_networker_partner(**{
            'name': 'Draft KYC Runtime Sponsor',
            'email': 'draft_kyc_runtime_sponsor@test.com',
            'x_networker_state': 'active',
            'x_kyc_state': 'draft',
            'x_rank_current': 'pearl',
            'x_rank_highest': 'pearl',
            'x_wallet_balance': 120.0,
        })
        if 'x_incarico_sign_state' in partner._fields:
            partner.write({'x_incarico_sign_state': 'signed'})
        customer = self.env['res.partner'].create({
            'name': 'Draft KYC Runtime Customer',
            'email': 'draft_kyc_runtime_customer@test.com',
            'x_sponsor_id': partner.id,
        })
        _plan, _direct_family, period = self._prepare_direct_runtime_engine()
        team_family = self.env['lamess.m3.bonus.family'].search([('code', '=', 'TEAM')], limit=1)
        if team_family:
            team_family.write({'state': 'active'})
        else:
            self.env['lamess.m3.bonus.family'].create({
                'name': 'Team Bonus',
                'code': 'TEAM',
                'state': 'active',
            })
        product = self.env['product.product'].search([], limit=1)
        if not product:
            template = self.env['product.template'].create({
                'name': 'Draft KYC Runtime Product',
                'type': 'consu',
            })
            product = template.product_variant_id
        movement = self.env['lamess.pv.movement'].create({
            'partner_id': customer.id,
            'networker_id': partner.id,
            'product_id': product.id,
            'pv_amount': 1000.0,
            'move_type': 'sale',
            'state': 'confirmed',
            'date': fields.Date.today(),
        })

        lines = movement._generate_m3_direct_team_bonus_lines(period)
        direct = lines.filtered(lambda line: line.bonus_type == 'direct')

        self.assertEqual(direct.recipient_id, partner)
        self.assertFalse(partner.can_request_payout())
        with self.assertRaises(UserError):
            partner.action_request_payout()

    def test_request_payout_requires_minimum_wallet(self):
        partner = self._create_networker_partner(**{
            'name': 'Payout Too Small',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 10.0,
        })

        with self.assertRaises(UserError):
            partner.action_request_payout()

    def test_mark_paid_reduces_wallet_balance(self):
        partner = self._create_networker_partner(**{
            'name': 'Liquidation Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 120.0,
        })
        request = self.env['lamess.payout.request'].create({
            'partner_id': partner.id,
            'gross_amount': 50.0,
            'state': 'requested',
        })

        request.action_approve()
        request.action_mark_paid()

        self.assertEqual(request.state, 'paid')
        self.assertAlmostEqual(partner.x_wallet_balance, 70.0)
        self.assertTrue(request.accounting_move_id)
        self.assertEqual(request.accounting_move_id.state, 'posted')
        move_lines_by_account = {
            line.account_id.id: line for line in request.accounting_move_id.line_ids
        }
        self.assertAlmostEqual(move_lines_by_account[self.payable_account.id].debit, 50.0)
        self.assertAlmostEqual(move_lines_by_account[self.liquidity_account.id].credit, request.net_amount)
        self.assertAlmostEqual(move_lines_by_account[self.withholding_account.id].credit, request.withholding_amount)
        self.assertAlmostEqual(move_lines_by_account[self.fee_account.id].credit, request.administrative_fee_amount)
        self.assertAlmostEqual(
            sum(request.accounting_move_id.line_ids.mapped('debit')),
            sum(request.accounting_move_id.line_ids.mapped('credit')),
        )

    def test_mark_paid_requires_explicit_payout_accounting_config(self):
        partner = self._create_networker_partner(**{
            'name': 'Missing Config Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 120.0,
        })
        request = self.env['lamess.payout.request'].create({
            'partner_id': partner.id,
            'gross_amount': 50.0,
            'state': 'requested',
        })

        request.action_approve()
        self.payout_config.payout_liquidity_account_id = False

        with self.assertRaises(UserError):
            request.action_mark_paid()

        self.assertEqual(request.state, 'approved')
        self.assertAlmostEqual(partner.x_wallet_balance, 120.0)
        self.assertFalse(request.accounting_move_id)

    def test_sale_bonus_wallet_payout_end_to_end(self):
        seller = self._create_networker_partner(**{
            'name': 'E2E Seller',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 0.0,
            'x_rank_current': 'pearl',
            'x_rank_highest': 'pearl',
        })
        customer = self.env['res.partner'].create({
            'name': 'E2E Customer',
            'x_sponsor_id': seller.id,
        })
        period = self.env['lamess.m3.bonus.runtime.line']._get_or_create_period_for_date(fields.Date.today())
        self._prepare_direct_runtime_engine(period=period)
        self._create_official_rank_snapshot(seller, period, 'pearl')
        order, movement = self._create_sale_origin_for_pv(seller, customer, pv_amount=100.0)

        runtime_lines = self.env['lamess.m3.bonus.runtime.line'].generate_direct_team_for_period(period=period)
        direct_line = runtime_lines.filtered(
            lambda line: line.movement_id == movement
            and line.recipient_id == seller
            and line.bonus_type == 'direct'
        )

        self.assertEqual(len(direct_line), 1)
        self.assertEqual(movement.sale_order_id, order)
        self.assertAlmostEqual(direct_line.amount_eur, 18.0)

        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            period=period,
            partner_ids=[seller.id],
        )
        self.assertEqual(len(settlement), 1)
        self.assertEqual(settlement.partner_id, seller)
        self.assertAlmostEqual(settlement.gross_amount, 18.0)
        self.assertEqual(direct_line.state, 'locked')

        settlement.action_post_to_wallet()
        self.assertEqual(settlement.state, 'posted')
        self.assertAlmostEqual(seller.x_wallet_balance, 18.0)

        action = seller.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])
        self.assertEqual(request.partner_id, seller)
        self.assertAlmostEqual(request.gross_amount, 18.0)
        self.assertEqual(request.settlement_trace_line_ids.settlement_id, settlement)

        request.action_approve()
        request.action_mark_paid()

        self.assertEqual(request.state, 'paid')
        self.assertAlmostEqual(seller.x_wallet_balance, 0.0)
        self.assertTrue(request.accounting_move_id)
        self.assertEqual(request.accounting_move_id.state, 'posted')
        self.assertAlmostEqual(
            sum(request.accounting_move_id.line_ids.mapped('debit')),
            sum(request.accounting_move_id.line_ids.mapped('credit')),
        )

    def test_generate_settlement_from_m3_runtime_locks_lines(self):
        partner = self._create_networker_partner(**{
            'name': 'Settlement Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 0.0,
            'x_rank_current': 'opal',
        })
        line_a = self._create_runtime_line(partner, 18.0, bonus_type='direct')
        line_b = self._create_runtime_line(partner, 6.0, bonus_type='team')

        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            partner_ids=[partner.id],
        )

        self.assertEqual(len(settlement), 1)
        self.assertEqual(settlement.partner_id, partner)
        self.assertAlmostEqual(settlement.gross_amount, 24.0)
        self.assertEqual(settlement.runtime_line_count, 2)
        line_a.invalidate_recordset()
        line_b.invalidate_recordset()
        self.assertEqual(line_a.state, 'locked')
        self.assertEqual(line_b.state, 'locked')

    def test_post_settlement_to_wallet_once(self):
        partner = self._create_networker_partner(**{
            'name': 'Wallet Settlement Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 10.0,
            'x_rank_current': 'opal',
        })
        self._create_runtime_line(partner, 18.0)
        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            partner_ids=[partner.id],
        )

        settlement.action_post_to_wallet()

        self.assertEqual(settlement.state, 'posted')
        self.assertAlmostEqual(partner.x_wallet_balance, 28.0)
        with self.assertRaises(UserError):
            settlement.action_post_to_wallet()

    def test_generate_settlement_wizard_filters_period_and_partner(self):
        partner = self._create_networker_partner(**{
            'name': 'Wizard Settlement Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 0.0,
            'x_rank_current': 'opal',
        })
        runtime_line = self._create_runtime_line(partner, 12.5)
        wizard = self.env['lamess.commission.settlement.generate.wizard'].create({
            'period_id': runtime_line.period_id.id,
            'partner_ids': [(6, 0, [partner.id])],
        })

        self.assertEqual(wizard.eligible_runtime_line_count, 1)
        self.assertAlmostEqual(wizard.eligible_amount, 12.5)

        action = wizard.action_generate()
        settlement = self.env['lamess.commission.settlement'].search([
            ('period_id', '=', runtime_line.period_id.id),
            ('partner_id', '=', partner.id),
        ])

        self.assertEqual(action['res_model'], 'lamess.commission.settlement')
        self.assertEqual(settlement.partner_id, partner)
        self.assertAlmostEqual(settlement.gross_amount, 12.5)
        runtime_line.invalidate_recordset()
        self.assertEqual(runtime_line.state, 'locked')

    def test_settlement_audit_tracks_runtime_settlement_and_wallet(self):
        partner = self._create_networker_partner(**{
            'name': 'Audit Settlement Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 5.0,
            'x_rank_current': 'opal',
        })
        runtime_line = self._create_runtime_line(partner, 22.0)
        audit_model = self.env['lamess.commission.settlement.audit']

        pending_audit = audit_model.search([
            ('period_id', '=', runtime_line.period_id.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        self.assertEqual(pending_audit.issue_level, 'pending_runtime')
        self.assertEqual(pending_audit.runtime_generated_line_count, 1)
        self.assertAlmostEqual(pending_audit.runtime_generated_amount, 22.0)
        self.assertFalse(pending_audit.settlement_id)

        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            period=runtime_line.period_id,
            partner_ids=[partner.id],
        )
        self.env.invalidate_all()
        draft_audit = audit_model.search([
            ('period_id', '=', runtime_line.period_id.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        self.assertEqual(draft_audit.issue_level, 'draft')
        self.assertEqual(draft_audit.runtime_locked_line_count, 1)
        self.assertEqual(draft_audit.settlement_id, settlement)
        self.assertAlmostEqual(draft_audit.amount_delta, 0.0)

        settlement.action_post_to_wallet()
        self.env.invalidate_all()
        posted_audit = audit_model.search([
            ('period_id', '=', runtime_line.period_id.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        self.assertEqual(posted_audit.issue_level, 'posted')
        self.assertAlmostEqual(posted_audit.wallet_balance, 27.0)

    def test_period_close_requires_posted_settlements_and_blocks_regeneration(self):
        partner = self._create_networker_partner(**{
            'name': 'Close Guard Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 0.0,
            'x_rank_current': 'opal',
        })
        period = self.env['lamess.commission.period'].create({
            'year': 2098,
            'month': 12,
        })
        runtime_line = self._create_runtime_line(partner, 31.0, period=period)

        with self.assertRaises(UserError):
            period.action_mark_closed()

        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            period=period,
            partner_ids=[partner.id],
        )
        with self.assertRaises(UserError):
            period.action_mark_closed()

        settlement.action_post_to_wallet()
        period.action_mark_closed()
        self.assertEqual(period.state, 'closed')

        with self.assertRaises(UserError):
            self.env['lamess.m3.bonus.runtime.line'].generate_all_runtime_for_period(period=period)
        with self.assertRaises(UserError):
            self.env['lamess.commission.settlement'].generate_from_m3_runtime(
                period=period,
                partner_ids=[partner.id],
            )

    def test_payout_request_traces_posted_settlement_origin(self):
        partner = self._create_networker_partner(**{
            'name': 'Traceable Payout Partner',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
            'x_wallet_balance': 0.0,
            'x_rank_current': 'opal',
        })
        runtime_line = self._create_runtime_line(partner, 20.0)
        settlement = self.env['lamess.commission.settlement'].generate_from_m3_runtime(
            period=runtime_line.period_id,
            partner_ids=[partner.id],
        )
        settlement.action_post_to_wallet()
        partner.write({'x_wallet_balance': partner.x_wallet_balance + 5.0})

        action = partner.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])
        settlement.invalidate_recordset()

        self.assertAlmostEqual(request.gross_amount, 25.0)
        self.assertAlmostEqual(request.withholding_amount, 4.49)
        self.assertAlmostEqual(request.administrative_fee_amount, 2.5)
        self.assertAlmostEqual(request.net_amount, 18.01)
        self.assertEqual(len(request.settlement_trace_line_ids), 1)
        self.assertEqual(request.settlement_trace_line_ids.settlement_id, settlement)
        self.assertAlmostEqual(request.traced_settlement_amount, 20.0)
        self.assertAlmostEqual(request.untraced_amount, 5.0)
        self.assertAlmostEqual(settlement.payout_allocated_amount, 20.0)
        self.assertEqual(settlement.payout_request_count, 1)

        request.action_approve()
        request.action_mark_paid()

        self.assertEqual(request.state, 'paid')
        self.assertAlmostEqual(partner.x_wallet_balance, 0.0)
        self.assertEqual(request.settlement_trace_line_ids.settlement_id, settlement)
        self.assertAlmostEqual(
            sum(request.accounting_move_id.line_ids.mapped('debit')),
            sum(request.accounting_move_id.line_ids.mapped('credit')),
        )


class TestSelfInvoicePayout(TestAccountingPartner):
    """Generazione bozza autofattura alla richiesta di prelievo."""

    def setUp(self):
        super().setUp()
        self.purchase_journal = self.env['account.journal'].search([
            ('company_id', '=', self.company.id),
            ('type', '=', 'purchase'),
        ], limit=1) or self.env['account.journal'].create({
            'name': 'Test Self-invoice Purchase',
            'code': 'TAINV',
            'type': 'purchase',
            'company_id': self.company.id,
        })
        self.expense_account = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
            ('account_type', '=', 'expense'),
        ], limit=1) or self.env['account.account'].create({
            'name': 'Test Self-invoice Expense',
            'code': 'TAINVE',
            'account_type': 'expense',
            'company_ids': [(6, 0, [self.company.id])],
        })
        self.wh_tax = self.env['account.tax'].create({
            'name': 'IRPEF 23 test',
            'amount': 23.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'company_id': self.company.id,
        })
        self.vat_tax = self.env['account.tax'].create({
            'name': 'IVA 22 test',
            'amount': 22.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'company_id': self.company.id,
        })
        self.inps_tax = self.env['account.tax'].create({
            'name': 'INPS test',
            'amount': 24.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'company_id': self.company.id,
        })
        self.payout_config.write({
            'autoinv_purchase_journal_id': self.purchase_journal.id,
            'autoinv_expense_account_id': self.expense_account.id,
            'autoinv_withholding_tax_id': self.wh_tax.id,
            'autoinv_vat_tax_id': self.vat_tax.id,
            'autoinv_inps_tax_id': self.inps_tax.id,
            'autoinv_gross_threshold': 6410.0,
            'autoinv_inps_ceiling': 120607.0,
        })

    def _eligible(self, **vals):
        base = {
            'name': 'Self-invoice consultant',
            'x_networker_state': 'active',
            'x_kyc_state': 'verified',
        }
        base.update(vals)
        return self._create_networker_partner(**base)

    def test_scenario_a_under_threshold_creates_draft_bill(self):
        partner = self._eligible(x_wallet_balance=100.0, x_fiscal_profile='occasional')
        action = partner.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])

        bill = request.vendor_bill_id
        self.assertTrue(bill, "deve generare una bozza autofattura")
        self.assertEqual(bill.move_type, 'in_invoice')
        self.assertEqual(bill.state, 'draft')
        self.assertEqual(request.self_invoice_scenario, 'A')
        self.assertAlmostEqual(request.vat_amount, 0.0)
        self.assertAlmostEqual(request.inps_total_amount, 0.0)
        # Solo ritenuta IRPEF in scenario A.
        line_taxes = bill.invoice_line_ids.tax_ids
        self.assertEqual(line_taxes, self.wh_tax)
        self.assertEqual(bill.ref, "01/%02dA" % (fields.Date.today().year % 100))

    def test_scenario_a_over_threshold_blocks(self):
        partner = self._eligible(x_wallet_balance=7000.0, x_fiscal_profile='occasional')
        with self.assertRaises(UserError):
            partner.action_request_payout()

    def test_scenario_b_applies_vat_irpef_inps(self):
        partner = self._eligible(
            x_wallet_balance=7000.0,
            x_fiscal_profile='vat_registered',
            x_vat_number='IT12345678901',
            x_inps_rate_pct='24',
        )
        action = partner.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])

        self.assertEqual(request.self_invoice_scenario, 'B')
        # INPS solo sulla quota sopra 6410: slice = 590, base 78% = 460.2, INPS 24%.
        self.assertAlmostEqual(request.inps_total_amount, round(460.2 * 0.24, 2), places=2)
        self.assertAlmostEqual(request.inps_withheld_amount, round((460.2 * 0.24) / 3.0, 2), places=2)
        self.assertAlmostEqual(request.vat_amount, round(7000.0 * 0.22, 2), places=2)
        line_taxes = request.vendor_bill_id.invoice_line_ids.tax_ids
        self.assertIn(self.vat_tax, line_taxes)
        self.assertIn(self.wh_tax, line_taxes)
        self.assertIn(self.inps_tax, line_taxes)

    def test_scenario_b_below_threshold_no_inps(self):
        partner = self._eligible(
            x_wallet_balance=100.0,
            x_fiscal_profile='vat_registered',
            x_vat_number='IT12345678901',
            x_inps_rate_pct='24',
        )
        action = partner.action_request_payout()
        request = self.env['lamess.payout.request'].browse(action['res_id'])

        self.assertEqual(request.self_invoice_scenario, 'B')
        self.assertAlmostEqual(request.inps_total_amount, 0.0)
        self.assertNotIn(self.inps_tax, request.vendor_bill_id.invoice_line_ids.tax_ids)

    def test_numbering_resets_on_year_change(self):
        partner = self._eligible(x_wallet_balance=100.0, x_fiscal_profile='occasional')
        year2 = fields.Date.today().year % 100
        first = partner._next_autoinv_number()
        self.assertEqual(first, "01/%02dA" % year2)
        second = partner._next_autoinv_number()
        self.assertEqual(second, "02/%02dA" % year2)
        # Simuliamo il cambio anno: la progressione riparte da 01.
        partner.x_autoinv_last_seq_year = fields.Date.today().year - 1
        third = partner._next_autoinv_number()
        self.assertEqual(third, "01/%02dA" % year2)
