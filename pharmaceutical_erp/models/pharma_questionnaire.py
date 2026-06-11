# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PharmaQuestionnaireTemplate(models.Model):
    _name = 'pharma.questionnaire.template'
    _description = 'Questionnaire Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(default=True, help="Set to False to hide this template without removing it.")
    
    question_ids = fields.One2many(
        comodel_name='pharma.questionnaire.question',
        inverse_name='template_id',
        string='Questions',
        copy=True
    )


class PharmaQuestionnaireQuestion(models.Model):
    _name = 'pharma.questionnaire.question'
    _description = 'Questionnaire Question'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        comodel_name='pharma.questionnaire.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    section = fields.Char(
        string='Section',
        help='Used to group questions together (e.g., "Quality Management", "Facilities").',
        translate=True
    )
    
    question_text = fields.Char(string='Question', required=True, translate=True)
    
    answer_type = fields.Selection(
        selection=[
            ('yes_no', 'Yes / No'),
            ('text', 'Text'),
            ('number', 'Number'),
        ],
        string='Answer Type',
        required=True,
        default='yes_no'
    )


class PharmaVendorQualificationResponse(models.Model):
    _name = 'pharma.vendor.qualification.response'
    _description = 'Vendor Qualification Response'
    _order = 'sequence, id'

    qualification_id = fields.Many2one(
        comodel_name='pharma.vendor.qualification',
        string='Vendor Qualification',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    question_id = fields.Many2one(
        comodel_name='pharma.questionnaire.question',
        string='Question Reference',
        required=True,
        ondelete='restrict'
    )
    
    # Display fields related to the question
    section = fields.Char(related='question_id.section', string='Section', readonly=True)
    sequence = fields.Integer(related='question_id.sequence', string='Sequence', readonly=True)
    question_text = fields.Char(related='question_id.question_text', string='Question', readonly=True)
    answer_type = fields.Selection(related='question_id.answer_type', string='Answer Type', readonly=True)
    
    # Answer fields
    answer_yes_no = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Yes/No Answer'
    )
    answer_text = fields.Text(string='Text Answer')
    answer_number = fields.Float(string='Number Answer')

