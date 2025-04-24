from odoo import api, fields, models
from datetime import datetime


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Leave type for compensations",
        default=lambda self: self.env.ref("hr_holidays.holiday_status_comp", False),
    )

    send_mail_notification = fields.Boolean(default=True, string="Send mail")

    summary_notification_recipient_ids = fields.Many2many(
        comodel_name="hr.employee", string="Summary destination emails"
    )

    excluded_calendar_ids = fields.Many2many(
        comodel_name="resource.calendar", string="Excluded calendars"
    )

    send_from_employee_id = fields.Many2one(
        comodel_name="hr.employee", string="Send from", required=False
    )

    invoiced_hours_start_date = fields.Date(
        string="Invoiced Hours Start Date",
        help="Date from which to calculate invoiced hours and efficiency"
    )

    def set_values(self):
        super().set_values()
        ir_default = self.env["ir.default"].sudo()
        leave_type = self.hr_leave_type or self.env.ref(
            "hr_holidays.holiday_status_comp"
        )
        ir_default.set(
            "res.config.settings", "hr_leave_type",
            leave_type.id
        )
        ir_default.set(
            "res.config.settings",
            "summary_notification_recipient_ids",
            self.summary_notification_recipient_ids.ids,
        )
        ir_default.set(
            "res.config.settings", "send_mail_notification",
            self.send_mail_notification
        )
        ir_default.set(
            "res.config.settings",
            "excluded_calendar_ids",
            self.excluded_calendar_ids.ids,
        )
        ir_default.set(
            "res.config.settings",
            "send_from_employee_id",
            self.send_from_employee_id.id,
        )
        ir_default.set(
            "res.config.settings",
            "invoiced_hours_start_date",
            fields.Date.to_string(self.invoiced_hours_start_date) if self.invoiced_hours_start_date else ""
        )
        return True

    @api.model
    def get_values(self):
        res = super().get_values()
        ir_default = self.env["ir.default"].sudo()
        res.update(
            {
                "hr_leave_type": ir_default.get("res.config.settings", "hr_leave_type"),
                "summary_notification_recipient_ids": ir_default.get(
                    "res.config.settings", "summary_notification_recipient_ids"
                ),
                "send_mail_notification": ir_default.get(
                    "res.config.settings", "send_mail_notification"
                ),
                "excluded_calendar_ids": ir_default.get(
                    "res.config.settings", "excluded_calendar_ids"
                ),
                "send_from_employee_id": ir_default.get(
                    "res.config.settings", "send_from_employee_id"
                ),
                "invoiced_hours_start_date": fields.Date.to_date(ir_default.get(
                    "res.config.settings", "invoiced_hours_start_date"
                )) if ir_default.get("res.config.settings", "invoiced_hours_start_date") else ""
            },
        )
        return res
