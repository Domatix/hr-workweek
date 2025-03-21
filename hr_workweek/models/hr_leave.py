from odoo import api, fields, models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    hr_workweek_ids = fields.Many2many(
        comodel_name="hr.workweek",
        string="Workweeks",
        column1="leave_id",
        column2="workweek_id",
        relation="leave_workweek_rel",
    )

    def write(self, vals):
        if vals.get("state") in ["validate", "validate1"]:
            workweek_vals = self._assign_workweeks(self)
            if workweek_vals:
                vals["hr_workweek_ids"] = workweek_vals
        return super().write(vals)

    @api.model
    def _assign_workweeks(self, leave) -> list:
        """
        Given an 'hr.leave' record will compute a [(4, ID)] operation
        :param leave:
        :return: list
        """
        workweeks = self.env["hr.workweek"].search(
            [
                "&",
                ("employee_id", "=", leave.employee_id.id),
                "|",
                "|",
                "&",
                ("date_start", "<=", leave.request_date_from),
                ("date_end", ">=", leave.request_date_from),
                "&",
                ("date_start", "<=", leave.request_date_to),
                ("date_end", ">=", leave.request_date_to),
                "&",
                ("date_start", ">=", leave.request_date_from),
                ("date_end", "<=", leave.request_date_to),
            ]
        )
        values = []
        for workweek in workweeks:
            if leave.id not in workweek.hr_leave_ids.ids:
                values.append((4, workweek.id))
        return values
