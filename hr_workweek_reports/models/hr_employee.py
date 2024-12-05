from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def send_weekly_report_email(self):
        ir_default = self.env["ir.default"].sudo()
        if ir_default.get("res.config.settings", "send_mail_notification"):
            excluded_calendars = (
                ir_default.get("res.config.settings", "excluded_calendar_ids") or []
            )
            template = self.env.ref("hr_workweek_reports.hours_worked_email_template")
            if template:
                for employee in self.env["hr.employee"].search(
                    [("resource_calendar_id", "not in", excluded_calendars)]
                ):
                    context = {
                        'hours_difference': getattr(employee.current_workweek, 'hours_difference', 0),
                        'hours_difference_str': str(getattr(employee.current_workweek, 'hours_difference', 0)),
                        'current_workweek_hours_to_work': getattr(employee.current_workweek, 'hours_to_work', 0),
                        'current_workweek_hours_to_work_str': str(getattr(employee.current_workweek, 'hours_to_work', 0)),
                        'current_workweek_hours_worked_str': str(getattr(employee.current_workweek, 'hours_worked', 0)),
                    }
                    template.with_context(context).send_mail(employee.id, force_send=True)

    @api.model
    def send_weekly_summary_report_email(self):
        ir_default = self.env["ir.default"].sudo()
        if ir_default.get("res.config.settings", "send_mail_notification"):
            excluded_calendars = (
                ir_default.get("res.config.settings", "excluded_calendar_ids") or []
            )
            template = self.env.ref(
                "hr_workweek_reports.hours_worked_summary_email_template"
            )
            if template:
                allowed_calendars = self.env["resource.calendar"].search(
                    [
                        (
                            "id",
                            "not in",
                            excluded_calendars,
                        )
                    ]
                )
                allowed_employees = self.env["hr.employee"].search(
                    [
                        (
                            "id",
                            "in",
                            ir_default.get(
                                "res.config.settings",
                                "summary_notification_recipient_ids",
                            ),
                        )
                    ]
                )
                for allowed_employee in allowed_employees:
                    template.with_context(calendars=allowed_calendars).send_mail(allowed_employee.id, force_send=True, email_values={
                        'email_to': allowed_employee.work_email,
                        'email_from': self.env["hr.employee"]
                        .browse(
                            [
                                ir_default.get(
                                    "res.config.settings", "send_from_employee_id"
                                )
                            ]
                        )
                        .work_email,
                    })
