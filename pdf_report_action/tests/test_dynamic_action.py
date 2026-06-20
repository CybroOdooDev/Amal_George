# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestDynamicAction(TransactionCase):
    """Test suite for the dynamic.action wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set up a customer/vendor
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })

        # Set up a product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'consu',
        })

        # Set up Sale Orders (one draft, one confirmed)
        cls.sale_order_draft = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        cls.sale_order_confirmed = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        cls.sale_order_confirmed.action_confirm()

        # Set up Purchase Orders (one draft, one confirmed)
        cls.purchase_order_draft = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_qty': 1,
                'price_unit': 80.0,
            })],
        })
        cls.purchase_order_confirmed = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_qty': 1,
                'price_unit': 80.0,
            })],
        })
        cls.purchase_order_confirmed.button_confirm()

        # Set up Stock Picking
        cls.picking_type = cls.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        cls.location = cls.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
        cls.location_dest = cls.env['stock.location'].search([('usage', '=', 'customer')], limit=1)

        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.picking_type.id,
            'location_id': cls.location.id,
            'location_dest_id': cls.location_dest.id,
            'partner_id': cls.partner.id,
        })

        # Set up Account Moves (one customer invoice, one customer credit note/refund)
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date': '2026-06-20',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        cls.invoice.action_post()

        cls.credit_note = cls.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': cls.partner.id,
            'invoice_date': '2026-06-20',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        cls.credit_note.action_post()

    def test_selection_target_model(self):
        """Test selection target models includes expected models."""
        wizard = self.env['dynamic.action'].create({})
        selection = wizard._selection_target_model()
        selection_models = [sel[0] for sel in selection]
        expected_models = ['account.move', 'sale.order', 'purchase.order', 'stock.picking']
        for model in expected_models:
            self.assertIn(model, selection_models)

    def test_resource_ref_inverse(self):
        """Test that setting resource_ref correctly updates res_id and res_model."""
        wizard = self.env['dynamic.action'].create({
            'resource_ref': f'sale.order,{self.sale_order_draft.id}',
        })
        self.assertEqual(wizard.res_model, 'sale.order')
        self.assertEqual(wizard.res_id, self.sale_order_draft.id)

        # Change it to purchase order
        wizard.resource_ref = f'purchase.order,{self.purchase_order_draft.id}'
        self.assertEqual(wizard.res_model, 'purchase.order')
        self.assertEqual(wizard.res_id, self.purchase_order_draft.id)

    def test_action_print_report(self):
        """Test print report generation for supported models and failure cases."""
        server_address = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Sale Order
        wizard = self.env['dynamic.action'].create({
            'resource_ref': f'sale.order,{self.sale_order_draft.id}',
        })
        res = wizard.action_print_report()
        self.assertEqual(res['type'], 'ir.actions.report')
        self.assertEqual(res['report_type'], 'xlsx')
        self.assertEqual(res['data'], f"{server_address}/report/pdf/sale.report_saleorder/{self.sale_order_draft.id}")

        # Purchase Order
        wizard.resource_ref = f'purchase.order,{self.purchase_order_draft.id}'
        res = wizard.action_print_report()
        self.assertEqual(res['data'], f"{server_address}/report/pdf/purchase.report_purchaseorder/{self.purchase_order_draft.id}")

        # Stock Picking
        wizard.resource_ref = f'stock.picking,{self.picking.id}'
        res = wizard.action_print_report()
        self.assertEqual(res['data'], f"{server_address}/report/pdf/stock.report_picking/{self.picking.id}")

        # Account Move
        wizard.resource_ref = f'account.move,{self.invoice.id}'
        res = wizard.action_print_report()
        self.assertEqual(res['data'], f"{server_address}/report/pdf/account.report_invoice/{self.invoice.id}")

        # Unsupported Model / ValidationError
        wizard_unsupported = self.env['dynamic.action'].create({
            'res_model': 'res.partner',
            'res_id': self.partner.id,
        })
        with self.assertRaises(ValidationError):
            wizard_unsupported.action_print_report()

    def test_action_open_report(self):
        """Test open report action generates correct URLs and fails when unsupported."""
        server_address = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or wizard.get_base_url()

        # Sale Order
        wizard = self.env['dynamic.action'].create({
            'resource_ref': f'sale.order,{self.sale_order_draft.id}',
        })
        res = wizard.action_open_report()
        self.assertEqual(res['type'], 'ir.actions.act_url')
        self.assertEqual(res['target'], 'new')
        self.assertEqual(res['url'], f"{wizard.get_base_url()}/report/pdf/sale.report_saleorder/{self.sale_order_draft.id}")

        # Purchase Order
        wizard.resource_ref = f'purchase.order,{self.purchase_order_draft.id}'
        res = wizard.action_open_report()
        self.assertEqual(res['url'], f"{wizard.get_base_url()}/report/pdf/purchase.report_purchaseorder/{self.purchase_order_draft.id}")

        # Stock Picking
        wizard.resource_ref = f'stock.picking,{self.picking.id}'
        res = wizard.action_open_report()
        self.assertEqual(res['url'], f"{wizard.get_base_url()}/report/pdf/stock.report_picking/{self.picking.id}")

        # Account Move
        wizard.resource_ref = f'account.move,{self.invoice.id}'
        res = wizard.action_open_report()
        self.assertEqual(res['url'], f"{wizard.get_base_url()}/report/pdf/account.report_invoice/{self.invoice.id}")

        # Unsupported Model / ValidationError
        wizard_unsupported = self.env['dynamic.action'].create({
            'res_model': 'res.partner',
            'res_id': self.partner.id,
        })
        with self.assertRaises(ValidationError):
            wizard_unsupported.action_open_report()

    def test_action_download_report(self):
        """Test download report actions mock pdf render and verify attachments creation."""
        dummy_pdf_content = b'dummy_pdf_content'

        with patch.object(type(self.env['ir.actions.report']), '_render_qweb_pdf', return_value=(dummy_pdf_content, 'pdf')) as mock_render:
            # Sale Order
            wizard = self.env['dynamic.action'].create({
                'resource_ref': f'sale.order,{self.sale_order_draft.id}',
            })
            res = wizard.action_download_report()
            mock_render.assert_called_with('sale.report_saleorder', self.sale_order_draft.id)
            attachment = self.env['ir.attachment'].search([('res_model', '=', 'sale.order'), ('res_id', '=', self.sale_order_draft.id)], limit=1)
            self.assertTrue(attachment)
            self.assertEqual(res['type'], 'ir.actions.act_url')
            self.assertEqual(res['url'], f"/web/content/{attachment.id}?download=true")

            # Purchase Order
            wizard.resource_ref = f'purchase.order,{self.purchase_order_draft.id}'
            res = wizard.action_download_report()
            mock_render.assert_called_with('purchase.report_purchaseorder', self.purchase_order_draft.id)
            attachment_po = self.env['ir.attachment'].search([('res_model', '=', 'purchase.order'), ('res_id', '=', self.purchase_order_draft.id)], limit=1)
            self.assertTrue(attachment_po)

            # Stock Picking
            wizard.resource_ref = f'stock.picking,{self.picking.id}'
            res = wizard.action_download_report()
            mock_render.assert_called_with('stock.report_picking', self.picking.id)
            attachment_sp = self.env['ir.attachment'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', self.picking.id)], limit=1)
            self.assertTrue(attachment_sp)

            # Account Move
            wizard.resource_ref = f'account.move,{self.invoice.id}'
            res = wizard.action_download_report()
            mock_render.assert_called_with('account.report_invoice', self.invoice.id)
            attachment_inv = self.env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', self.invoice.id)], limit=1)
            self.assertTrue(attachment_inv)

        # Unsupported Model / ValidationError
        wizard_unsupported = self.env['dynamic.action'].create({
            'res_model': 'res.partner',
            'res_id': self.partner.id,
        })
        with self.assertRaises(ValidationError):
            wizard_unsupported.action_download_report()

    def test_action_share_email(self):
        """Test action_share_email template selection and email compose action structure."""
        # Sale Order Draft -> sale.email_template_edi_sale
        wizard = self.env['dynamic.action'].create({
            'resource_ref': f'sale.order,{self.sale_order_draft.id}',
        })
        res = wizard.action_share_email()
        self.assertEqual(res['res_model'], 'mail.compose.message')
        expected_template = self.env.ref('sale.email_template_edi_sale')
        self.assertEqual(res['context']['default_template_id'], expected_template.id)

        # Sale Order Confirmed -> sale.mail_template_sale_confirmation
        wizard.resource_ref = f'sale.order,{self.sale_order_confirmed.id}'
        res = wizard.action_share_email()
        expected_template_conf = self.env.ref('sale.mail_template_sale_confirmation')
        self.assertEqual(res['context']['default_template_id'], expected_template_conf.id)

        # Purchase Order Draft -> purchase.email_template_edi_purchase
        wizard.resource_ref = f'purchase.order,{self.purchase_order_draft.id}'
        res = wizard.action_share_email()
        expected_template_po = self.env.ref('purchase.email_template_edi_purchase')
        self.assertEqual(res['context']['default_template_id'], expected_template_po.id)

        # Purchase Order Confirmed -> purchase.email_template_edi_purchase_done
        wizard.resource_ref = f'purchase.order,{self.purchase_order_confirmed.id}'
        res = wizard.action_share_email()
        expected_template_po_done = self.env.ref('purchase.email_template_edi_purchase_done')
        self.assertEqual(res['context']['default_template_id'], expected_template_po_done.id)

        # Invoice -> account.email_template_edi_invoice
        wizard.resource_ref = f'account.move,{self.invoice.id}'
        res = wizard.action_share_email()
        expected_template_inv = self.env.ref('account.email_template_edi_invoice')
        self.assertEqual(res['context']['default_template_id'], expected_template_inv.id)

        # Credit Note -> account.email_template_edi_credit_note
        wizard.resource_ref = f'account.move,{self.credit_note.id}'
        res = wizard.action_share_email()
        expected_template_cn = self.env.ref('account.email_template_edi_credit_note')
        self.assertEqual(res['context']['default_template_id'], expected_template_cn.id)

        # Unsupported Model / ValidationError (e.g. stock.picking)
        wizard.resource_ref = f'stock.picking,{self.picking.id}'
        with self.assertRaises(ValidationError):
            wizard.action_share_email()
