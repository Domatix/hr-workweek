from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def send_weekly_report_email(self):
        ir_config = self.env["ir.config_parameter"].sudo()
        send_mail_notification = ir_config.get_param("res.config.settings.send_mail_notification", default=False)
        if send_mail_notification:
            excluded_calendar_ids = ir_config.get_param("res.config.settings.excluded_calendar_ids", default="").split(",")
            excluded_calendars = [int(id) for id in excluded_calendar_ids if id.isdigit()]
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
        ir_config = self.env["ir.config_parameter"].sudo()
        send_mail_notification = ir_config.get_param("res.config.settings.send_mail_notification", default=False)
        if send_mail_notification:
            excluded_calendar_ids = ir_config.get_param("res.config.settings.excluded_calendar_ids", default="").split(",")
            excluded_calendars = [int(id) for id in excluded_calendar_ids if id.isdigit()]
            template = self.env.ref("hr_workweek_reports.hours_worked_summary_email_template")
            if template:
                allowed_calendars = self.env["resource.calendar"].search(
                    [("id","not in",excluded_calendars)]
                )
                employees_by_calendar = {
                    calendar.id: self.env["hr.employee"].sudo().search(
                        [("resource_calendar_id", "=", calendar.id)]
                    )
                    for calendar in allowed_calendars
                }
                recipient_ids = ir_config.get_param("res.config.settings.summary_notification_recipient_ids", default="").split(",")
                allowed_employees = self.env["hr.employee"].search(
                    [("id", "in", [int(id) for id in recipient_ids if id.isdigit()])]
                )
                send_from_employee_id = int(ir_config.get_param("res.config.settings.send_from_employee_id", default=0))
                send_from_employee = self.env["hr.employee"].browse(send_from_employee_id)
                for allowed_employee in allowed_employees:
                    template.with_context(
                        calendars=allowed_calendars,
                        employees_by_calendar=employees_by_calendar,
                    ).send_mail(
                        allowed_employee.id,
                        force_send=True,
                        email_values={
                            "email_to": allowed_employee.work_email,
                            "email_from": send_from_employee.work_email,
                        },
                    )
