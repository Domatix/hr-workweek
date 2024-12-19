from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    hr_workweek_id = fields.Many2one(
        comodel_name="hr.workweek",
        string="Workweek",
    )

    holiday_id = fields.Many2one(
        comodel_name="hr.leave",
        string='Time Off Request'
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        workweek = self.env["hr.workweek"].get_current_workweek(
            res.employee_id, res.date
        )
        if res.holiday_id:
            return res
        if workweek:
            res.hr_workweek_id = workweek.id
        return res

    def write(self, vals):
        if "date" in vals:
            if not self.hr_workweek_id and not self.holiday_id:
                workweek = self.env["hr.workweek"].get_current_workweek(
                    self.employee_id, self.date
                )
                if workweek:
                    vals["hr_workweek_id"] = workweek.id

        res = super().write(vals)
        return res
