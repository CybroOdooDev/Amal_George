# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestResConfigSettings(TransactionCase):
    """Test suite for res.config.settings model extensions."""

    def test_set_values_project_category(self):
        """Test that enabling/disabling is_project_category modifies user group membership."""
        user = self.env.ref('base.user_admin')
        group = self.env.ref('advanced_project_management_system.group_project_category')

        # Ensure starting state
        if user in group.users:
            group.write({'users': [(3, user.id)]})

        self.assertNotIn(user, group.users)

        # Create settings and set project category to True
        config = self.env['res.config.settings'].with_user(user).create({
            'is_project_category': True,
        })
        config.execute()
        self.assertIn(user, group.users)

        # Set to False and execute
        config_off = self.env['res.config.settings'].with_user(user).create({
            'is_project_category': False,
        })
        config_off.execute()
        self.assertNotIn(user, group.users)
