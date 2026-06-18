# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestResUsersFilters(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestResUsersFilters, cls).setUpClass()

        # Sanitize account_account table constraints for third-party modules (e.g. account_asset)
        cls.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'account_account' AND column_name = 'create_asset'
        """)
        if cls.env.cr.fetchone():
            cls.env.cr.execute("ALTER TABLE account_account ALTER COLUMN create_asset DROP NOT NULL")

        # Create a user to test filters
        cls.test_user = cls.env['res.users'].create({
            'name': 'Filter Test User',
            'login': 'filter_test_user@example.com',
        })

    def test_user_get_views_filters(self):
        """ Verify get_views sets module-user boolean flags correctly based on user groups """
        categories = {
            'base.module_category_sales_sales': 'sales_user',
            'base.module_category_accounting_accounting': 'invoice_user',
            'base.module_category_inventory_purchase': 'purchase_user',
            'base.module_category_website_website': 'website_user',
            'base.module_category_inventory_inventory': 'inventory_user',
            'base.module_category_sales_point_of_sale': 'pos_user',
            'base.module_category_services_project': 'project_user',
            'base.module_category_manufacturing_manufacturing': 'manufacturing_user',
        }

        # Clear any existing groups from test_user
        self.test_user.write({'groups_id': [(5, 0, 0)]})

        # Call get_views and verify all flags are False
        self.env['res.users'].get_views(views=[[False, 'list']])
        for field in categories.values():
            self.assertFalse(self.test_user[field], f"Field {field} should be False initially")

        # Test each category flag by assigning a group belonging to it
        for category_xml_id, field in categories.items():
            category = self.env.ref(category_xml_id, raise_if_not_found=False)
            if not category:
                continue

            # Find a group for this category
            group = self.env['res.groups'].search([('category_id', '=', category.id)], limit=1)
            if not group:
                continue

            # Assign group to user
            self.test_user.write({'groups_id': [(4, group.id)]})

            # Call get_views
            self.env['res.users'].get_views(views=[[False, 'list']])

            # Verify the corresponding field is now True
            self.assertTrue(self.test_user[field], f"Field {field} should be True after assigning group in {category_xml_id}")

            # Remove group
            self.test_user.write({'groups_id': [(3, group.id)]})
