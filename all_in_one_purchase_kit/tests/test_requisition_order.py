# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestRequisitionOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Requisition Order Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Requisition Order Product',
            'type': 'consu',
        })
        cls.dept = cls.env['hr.department'].create({'name': 'Requisition Dept'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Requisition Employee',
            'department_id': cls.dept.id,
        })
        cls.requisition = cls.env['employee.purchase.requisition'].create({
            'employee_id': cls.employee.id,
            'user_id': cls.env.user.id,
        })

    def test_requisition_order_fields_and_computes(self):
        """Test compute description and field assignments on requisition order."""
        req_order = self.env['requisition.order'].create({
            'requisition_product_id': self.requisition.id,
            'product_id': self.product.id,
            'quantity': 15,
            'requisition_type': 'purchase_order',
            'partner_id': self.partner.id,
        })
        
        # Test description computation
        req_order._compute_product_id()
        self.assertIn('Requisition Order Product', req_order.description)
