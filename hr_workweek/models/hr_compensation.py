from odoo import _, api, fields, models


class HrCompensation(models.Model):
    _name = "hr.compensation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "HR Compensations"

    @api.depends("description", "employee_id")
    def _compute_workweek_name(self):
        for record in self:
            record.name = "{} {} ".format(record.employee_id.name, record.description)

    @api.depends("hr_allocation_id")
    def _compute_allocation_count(self):
        for record in self:
            record.allocation_count = len(record.hr_allocation_id)

    name = fields.Char(store=True, compute="_compute_workweek_name")

    description = fields.Text(required=False)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("refused", "Refused"),
        ],
        string="Status",
        readonly=True,
        default="draft",
        tracking=True
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee", string="Employee", required=True
    )

    petition_date = fields.Date(string="Petition date", required=True)

    hr_allocation_id = fields.Many2one(
        comodel_name="hr.leave.allocation", string="Allocation"
    )

    unit_amount = fields.Float(
        string="Hours to compensate",
        default=0.0,
        store=True,
    )

    type = fields.Selection(
        selection=[("economic", "Economic"), ("leave", "Leave days")]
    )

    allocation_count = fields.Integer(
        string="Allocations", compute=_compute_allocation_count
    )

    responsible_id = fields.Many2one(string="Responsible", comodel_name="hr.employee")

    workweek_id = fields.Many2one(
        comodel_name="hr.workweek", string="Workweek", required=True
    )

    def unlink(self):
        for record in self:
            record.hr_allocation_id.unlink()
            record.employee_id.hr_workweek_ids._compute_hours_compensated()
        return super().unlink()

    def action_approve(self):
        for record in self:
            if record.type == "leave":
                if record.hr_allocation_id:
                    record.hr_allocation_id.action_validate()
            record.write({"state": "approved"})

    def action_refuse(self):
        for record in self:
            if record.type == "leave":
                if record.hr_allocation_id:
                    record.hr_allocation_id.action_refuse()
            record.write({"state": "refused"})

    def action_draft(self):
        for record in self:
            if record.type == "leave":
                if record.hr_allocation_id:
                    if record.hr_allocation_id.state != "refuse":
                        record.hr_allocation_id.action_refuse()
                    record.hr_allocation_id.action_draft()
                    record.hr_allocation_id.action_confirm()
            record.write({"state": "draft"})

    def create_leave_allocation(self):
        ir_config = self.env["ir.config_parameter"].sudo()
        hr_leave_type = int(ir_config.get_param("res.config.settings.hr_leave_type", default=0))
        self.hr_allocation_id = self.env["hr.leave.allocation"].create(
            {
                "name": self.description or self.name,
                "holiday_status_id": hr_leave_type,
                "number_of_days": self.unit_amount
                / self.employee_id.resource_calendar_id.hours_per_day,
                "holiday_type": "employee",
                "number_of_hours_display": self.unit_amount,
                "employee_id": self.employee_id.id,
                "state": "confirm",
            }
        )

    def action_view_allocation(self):
        return {
            "name": _("Allocations"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "hr.leave.allocation",
            "type": "ir.actions.act_window",
            "res_id": self.hr_allocation_id.id,
            "context": self.env.context,
        }
