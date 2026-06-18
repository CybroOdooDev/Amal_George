# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestResPartnerRelatedUser(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestResPartnerRelatedUser, cls).setUpClass()

        # Sanitize account_account table constraints for third-party modules (e.g. account_asset)
        cls.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'account_account' AND column_name = 'create_asset'
        """)
        if cls.env.cr.fetchone():
            cls.env.cr.execute("ALTER TABLE account_account ALTER COLUMN create_asset DROP NOT NULL")

        # Create a partner who has a related user
        cls.partner_with_user = cls.env['res.partner'].create({
            'name': 'Partner with User',
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user_related@example.com',
            'partner_id': cls.partner_with_user.id,
        })

        # Create a partner who has no related user
        cls.partner_without_user = cls.env['res.partner'].create({
            'name': 'Partner without User',
        })

    def test_partner_get_views(self):
        """ Verify get_views correctly assigns related users to partners """
        # Verify initial state is empty / False
        self.assertFalse(self.partner_with_user.is_have_user)
        self.assertFalse(self.partner_with_user.related_user_id)

        # Call get_views
        self.env['res.partner'].get_views(views=[[False, 'list']])

        # Check that the partner with an associated user is updated
        self.assertTrue(self.partner_with_user.is_have_user)
        self.assertEqual(self.partner_with_user.related_user_id, self.user)

        # Check that the partner without an associated user remains unchanged
        self.assertFalse(self.partner_without_user.is_have_user)
        self.assertFalse(self.partner_without_user.related_user_id)
