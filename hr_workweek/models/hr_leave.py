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
        if self.env.context.get("skip_workweek_leave_sync"):
            return super().write(vals)
        affected_workweeks = self.mapped("hr_workweek_ids")
        res = super().write(vals)
        sync_fields = {"employee_id", "request_date_from", "request_date_to", "date_from", "date_to", "state"}
        if sync_fields.intersection(vals) and vals.get("state") != "validate":
            affected_workweeks |= self._sync_workweeks()
            affected_workweeks._refresh_workweek_data()
        return res

    def _validate_leave_request(self):
        res = super()._validate_leave_request()
        affected_workweeks = self._sync_workweeks()
        affected_workweeks._refresh_workweek_data()
        return res

    def _post_leave_cancel(self):
        affected_workweeks = self.mapped("hr_workweek_ids")
        res = super()._post_leave_cancel()
        self.with_context(skip_workweek_leave_sync=True).write({"hr_workweek_ids": [(5, 0, 0)]})
        affected_workweeks._refresh_workweek_data()
        return res

    def _sync_workweeks(self):
        affected_workweeks = self.mapped("hr_workweek_ids")
        for leave in self:
            workweeks = leave._get_overlapping_workweeks() if leave.state in ["validate", "validate1"] else self.env["hr.workweek"]
            affected_workweeks |= workweeks
            leave.with_context(skip_workweek_leave_sync=True).write(
                {"hr_workweek_ids": [(6, 0, workweeks.ids)]}
            )
        return affected_workweeks

    def _get_overlapping_workweeks(self):
        self.ensure_one()
        if not self.employee_id or not self.request_date_from or not self.request_date_to:
            return self.env["hr.workweek"]
        return self.env["hr.workweek"].search(
            [
                "&",
                ("employee_id", "=", self.employee_id.id),
                "|",
                "|",
                "&",
                ("date_start", "<=", self.request_date_from),
                ("date_end", ">=", self.request_date_from),
                "&",
                ("date_start", "<=", self.request_date_to),
                ("date_end", ">=", self.request_date_to),
                "&",
                ("date_start", ">=", self.request_date_from),
                ("date_end", "<=", self.request_date_to),
            ]
        )

    @api.model
    def _assign_workweeks(self, leave) -> list:
        workweeks = leave._get_overlapping_workweeks()
        values = []
        for workweek in workweeks:
            if leave.id not in workweek.hr_leave_ids.ids:
                values.append((4, workweek.id))
        return values
