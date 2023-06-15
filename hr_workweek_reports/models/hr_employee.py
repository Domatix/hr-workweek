from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def send_weekly_report_email(self):
        ir_default = self.env["ir.default"].sudo()
        fields = [
            "subject",
            "body_html",
            "email_from",
            "email_to",
            "partner_to",
            "email_cc",
            "reply_to",
            "scheduled_date",
        ]
        if ir_default.get("res.config.settings", "send_mail_notification"):
            excluded_calendars = (
                ir_default.get("res.config.settings", "excluded_calendar_ids") or []
            )
            template = self.env.ref("hr_workweek_reports.hours_worked_email_template")
            if template:
                for employee in self.env["hr.employee"].search(
                    [("resource_calendar_id", "not in", excluded_calendars)]
                ):
                    mail = template.generate_email([employee.id], fields)
                    self.env["mail.mail"].create(mail.values()).send()

    @api.model
    def send_weekly_summary_report_email(self):
        ir_default = self.env["ir.default"].sudo()
        fields = [
            "subject",
            "body_html",
            "email_from",
            "email_to",
            "partner_to",
            "email_cc",
            "reply_to",
            "scheduled_date",
        ]
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
                    mail = template.with_context(
                        **{
                            "employee": self.env["hr.employee"],
                            "calendars": allowed_calendars,
                        }
                    ).generate_email(allowed_employee.id, fields)

                    mail["email_from"] = (
                        self.env["hr.employee"]
                        .browse(
                            [
                                ir_default.get(
                                    "res.config.settings", "send_from_employee_id"
                                )
                            ]
                        )
                        .work_email
                    )
                    mail["email_to"] = allowed_employee.work_email
                    self.env["mail.mail"].create(mail).send()
