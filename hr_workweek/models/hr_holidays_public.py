from odoo import fields, models


class HrHolidaysPublicLine(models.Model):
    _inherit = "hr.holidays.public.line"

    hr_workweek_id = fields.Many2one(
        comodel_name="hr.workweek",
        string="Workweek",
    )
