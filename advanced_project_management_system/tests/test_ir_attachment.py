# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestIrAttachment(TransactionCase):
    """Test suite for ir.attachment extensions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Attachment Test Partner',
            'email': 'partner@example.com'
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Attachment Test Project',
            'partner_id': cls.partner.id,
        })
        # Set config parameters for notifications
        cls.env['ir.config_parameter'].sudo().set_param(
            'res.config.settings.notify_customer', True
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'res.config.settings.email', 'internal@example.com'
        )

    def test_onchange_res_id(self):
        """Test that _onchange_res_id correctly sets partner_id from project."""
        attachment = self.env['ir.attachment'].create({
            'name': 'Test Attachment',
            'res_model': 'project.project',
            'res_id': self.project.id,
        })
        attachment._onchange_res_id()
        self.assertEqual(attachment.partner_id, self.partner)

    def test_document_expire_notification(self):
        """Test document_expire_notification sends emails for expired attachments."""
        # Create an expired attachment with expiry_notification = True
        expired_attachment = self.env['ir.attachment'].create({
            'name': 'Expired Attachment',
            'res_model': 'project.project',
            'res_id': self.project.id,
            'expiry_date': fields.Date.subtract(fields.Date.today(), days=2),
            'expiry_notification': True,
        })
        # Create an active attachment (not expired)
        active_attachment = self.env['ir.attachment'].create({
            'name': 'Active Attachment',
            'res_model': 'project.project',
            'res_id': self.project.id,
            'expiry_date': fields.Date.add(fields.Date.today(), days=2),
            'expiry_notification': True,
        })

        # Clear mail queue/messages
        self.env['mail.mail'].search([]).unlink()

        # Run notification method
        self.env['ir.attachment'].document_expire_notification()

        # Verify that emails were created in the mail queue
        # Since notify_customer is True and expiry_notification is True, emails should be sent
        mails = self.env['mail.mail'].search([])
        # We expect mails to be generated. Let's inspect them.
        self.assertTrue(len(mails) >= 1, "At least one mail should have been generated")
