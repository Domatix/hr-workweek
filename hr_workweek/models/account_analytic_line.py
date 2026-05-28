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

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if vals.get('holiday_id') or vals.get('global_leave_id'):
                continue
            date_val = vals.get('date_imputable') or vals.get('date')
            if date_val:
                if isinstance(date_val, str):
                    date_val = fields.Date.to_date(date_val)
                elif isinstance(date_val, datetime):
                    date_val = date_val.date()
                if date_val != today and not self.env.user.has_group('hr_workweek.group_timesheet_modified_date'):
                    raise UserError(_("You can only record hours for today."))
        records = super().create(vals_list)
        for rec in records:
            if rec.holiday_id or ("global_leave_id" in rec._fields and rec.global_leave_id):
                continue
            workweek = self.env["hr.workweek"].get_current_workweek(rec.employee_id, rec.date)
            if workweek:
                rec.hr_workweek_id = workweek.id
        return records

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
