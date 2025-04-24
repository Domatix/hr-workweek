from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


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
        today = fields.Date.context_today(self)
        date_val = vals.get('date_imputable')
        import pdb; pdb.set_trace()
        if isinstance(date_val, str):
            date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
        if date_val != today:
            if not self.env.user.has_group('hr_workweek.group_timesheet_modified_date'):
                raise UserError(_("You can only record hours for today."))
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
