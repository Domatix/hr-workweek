from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hr_workweek_ids = fields.One2many(
        comodel_name="hr.workweek",
        inverse_name="employee_id",
        string="Workweeks",
    )

    workweek_ids_count = fields.Integer(
        string="workweeks",
        compute="_compute_workweek_ids_count",
    )

    hours_difference = fields.Float(
        string="Total hours difference",
        help="If positive, you still have some work hours to do. "
        "If negative, you've worked beyond what you should've",
        compute="_compute_hours_difference",
        store=True,
    )

    hr_compensation_ids = fields.One2many(
        comodel_name="hr.compensation",
        inverse_name="employee_id",
        string="Compensations",
    )

    compensation_ids_count = fields.Integer(
        string="Compensations", compute="_compute_compensation_count"
    )

    current_workweek = fields.Many2one(comodel_name="hr.workweek")

    def _compute_workweek_ids_count(self):
        for record in self:
            record.workweek_ids_count = len(record.hr_workweek_ids)

    @api.depends(
        "hr_workweek_ids.hours_difference", "hr_workweek_ids.hours_compensated"
    )
    def _compute_hours_difference(self):
        for record in self:
            hours_difference = sum(record.hr_workweek_ids.mapped("hours_difference"))
            hours_compensated = sum(record.hr_workweek_ids.mapped("hours_compensated"))
            record.hours_difference = hours_difference + hours_compensated

    def _compute_compensation_count(self):
        for record in self:
            record.compensation_ids_count = len(record.hr_compensation_ids)

    @property
    def _hours_difference_without_last_week(self):
        monday = self.env["hr.workweek"]._get_limit_dates(datetime.today().date())[0]
        return sum(
            self.hr_workweek_ids.sorted("date_start")
            .filtered(lambda x: x.date_end <= monday)
            .mapped("hours_difference")
        )

    def action_view_workweek_ids(self):
        return {
            "name": _("{}'s workweeks").format(self.name),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "hr.workweek",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.hr_workweek_ids.ids)],
            "context": self.env.context,
        }

    def action_view_compensation_ids(self):
        return {
            "name": _("{}'s compensations").format(self.name),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "hr.compensation",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.hr_compensation_ids.ids)],
            "context": self.env.context,
        }

    def _action_compensate(
        self, amount, compensation_type, description, responsible_id
    ):
        vals = {
            "employee_id": self.id,
            "state": "draft",
            "description": description or f"Compensation of {amount} hours",
            "petition_date": fields.Datetime.now().date(),
            "type": compensation_type,
            "responsible_id": responsible_id.id,
        }
        for compensable_workweek_id in self.hr_workweek_ids.filtered(
            lambda x: (x.hours_difference + x.hours_compensated) < 0
            and (
                x.date_start.year == datetime.today().year
                or x.date_end.year == datetime.today().year
            )
        ):
            vals.update(
                {
                    "workweek_id": compensable_workweek_id.id,
                    "unit_amount": amount,
                    "type": compensation_type,
                }
            )
        compensation_id = self.env["hr.compensation"].create(vals)
        compensation_id.create_leave_allocation()
        template = self.env.ref("hr_workweek.assignment_email_template")
        self.message_post_with_template(
            template.id,
            composition_mode="comment",
            model="hr.compensation",
            res_id=compensation_id.id,
        )
        return compensation_id

    def action_compensate(self):
        """
         Public method which summons the user-level wizard,
        the actual compensation is done via the private method below,
        `_action_compensate`
        :return:
        """
        ir_default = self.env["ir.default"].sudo()
        leave_type = self.env["hr.leave.type"].search(
            [("id", "=", ir_default.get("res.config.settings", "hr_leave_type"))]
        )
        if leave_type:
            return {
                "type": "ir.actions.act_window",
                "res_model": "hr.workweek.wizard",
                "name": "Ask for compensation",
                "view_mode": "form",
                "target": "new",
                "context": dict(
                    self.env.context,
                    leave_type=leave_type.id,
                    wizard_model="hr.workweek.wizard",
                ),
            }
        else:
            raise UserError(
                _(
                    "A default compensation leave type has not been set. "
                    "Please contact your HR Manager about this error."
                )
            )

    @api.model
    def create_current_workweek(self):
        ir_default = self.env["ir.default"].sudo()
        excluded_calendars = (
            ir_default.get("res.config.settings", "excluded_calendar_ids") or []
        )
        date_start, date_end = self.get_workweek_dates()
        for record in self.env[self._name].search(
            [("resource_calendar_id", "not in", excluded_calendars)]
        ):
            workweek = self.env["hr.workweek"].create(
                {
                    "employee_id": record.id,
                    "date_start": date_start,
                    "date_end": date_end,
                }
            )
            record.current_workweek = workweek.id

    def get_workweek_dates(self, dateweek=False):
        now = dateweek or datetime.now().date()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week


class HrEmployeeCalendar(models.Model):
    _inherit = "hr.employee.calendar"

    name = fields.Char()
    is_active = fields.Boolean(string="Active", default=True)
