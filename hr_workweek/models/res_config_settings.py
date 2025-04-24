from odoo import api, fields, models
from datetime import datetime


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Leave type for compensations",
        default=lambda self: self.env.ref("hr_holidays.holiday_status_comp", False),
    )

    send_mail_notification = fields.Boolean(
        default=True, string="Send mail"
    )

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
        ir_config = self.env["ir.config_parameter"].sudo()
        leave_type = self.hr_leave_type or self.env.ref(
            "hr_holidays.holiday_status_comp", False
        )
        ir_config.set_param(
            "res.config.settings.hr_leave_type",
            leave_type.id or ""
        )
        ir_config.set_param(
            "res.config.settings.summary_notification_recipient_ids",
            ",".join(map(str, self.summary_notification_recipient_ids.ids)),
        )
        ir_config.set_param(
            "res.config.settings.excluded_calendar_ids",
            ",".join(map(str, self.excluded_calendar_ids.ids)),
        )
        ir_config.set_param(
            "res.config.settings.send_mail_notification",
            str(self.send_mail_notification)
        )
        ir_config.set_param(
            "res.config.settings.send_from_employee_id",
            self.send_from_employee_id.id or ""
        )
        ir_config.set_param(
            "res.config.settings.invoiced_hours_start_date",
            fields.Date.to_string(self.invoiced_hours_start_date) if self.invoiced_hours_start_date else ""
        )
        self.env['hr.employee'].search([])._compute_efficiency()
        return True

    def get_values(self):
        res = super().get_values()
        ir_config = self.env["ir.config_parameter"].sudo()

        excluded_calendar_ids = ir_config.get_param(
            "res.config.settings.excluded_calendar_ids", default=""
        )
        summary_recipient_ids = ir_config.get_param(
            "res.config.settings.summary_notification_recipient_ids", default=""
        )
        res.update(
            {
                "hr_leave_type": int(ir_config.get_param("res.config.settings.hr_leave_type", default=0)) or False,
                "summary_notification_recipient_ids": [(6, 0, [
                    int(id) for id in summary_recipient_ids.split(",") if id.isdigit()
                ])],
                "excluded_calendar_ids": [(6, 0, [
                    int(id) for id in excluded_calendar_ids.split(",") if id.isdigit()
                ])],
                "send_mail_notification": ir_config.get_param(
                    "res.config.settings.send_mail_notification", default="False"
                ) == "True",
                "send_from_employee_id": int(
                    ir_config.get_param("res.config.settings.send_from_employee_id", default=0)
                ) or False,
                "invoiced_hours_start_date": fields.Date.to_date(
                    ir_config.get_param("res.config.settings.invoiced_hours_start_date")
                ) if ir_config.get_param("res.config.settings.invoiced_hours_start_date") else False
            }
        )
        return res
