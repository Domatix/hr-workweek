from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    hours_difference = fields.Float(readonly=True)
    current_workweek = fields.Many2one(
        comodel_name="hr.workweek",
        readonly=True,
    )
    total_hours_worked = fields.Float(readonly=True)
    total_hours_invoiced = fields.Float(readonly=True)
    work_efficiency = fields.Float(readonly=True)