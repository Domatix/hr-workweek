from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _get_report_workweek(self, employee, dateweek=None):
        dateweek = dateweek or fields.Date.context_today(self)
        workweek = employee.current_workweek
        if not workweek or not (workweek.date_start <= dateweek <= workweek.date_end):
            workweek = self.env["hr.workweek"].get_current_workweek(employee, dateweek)
            if workweek:
                employee.current_workweek = workweek.id
        return workweek

    def _get_excluded_calendars(self, ir_config):
        excluded_calendar_ids = ir_config.get_param(
            "res.config.settings.excluded_calendar_ids", default=""
        ).split(",")
        return [int(id) for id in excluded_calendar_ids if id.isdigit()]

    @api.model
    def send_weekly_report_email(self):
        ir_config = self.env["ir.config_parameter"].sudo()
        send_mail_notification = ir_config.get_param("res.config.settings.send_mail_notification", default="False") == "True"
        if send_mail_notification:
            excluded_calendars = self._get_excluded_calendars(ir_config)
            template = self.env.ref("hr_workweek_reports.hours_worked_email_template", raise_if_not_found=False)
            if template:
                dateweek = fields.Date.context_today(self)
                for employee in self.env["hr.employee"].sudo().search([]):
                    calendars = employee._get_workweek_exclusion_calendar_ids(dateweek)
                    if not calendars or calendars.filtered(lambda calendar: calendar.id in excluded_calendars):
                        continue
                    if not self._get_report_workweek(employee, dateweek):
                        continue
                    context = {
                        'hours_difference': getattr(employee.current_workweek, 'hours_difference', 0),
                        'hours_difference_str': str(getattr(employee.current_workweek, 'hours_difference', 0)),
                        'current_workweek_hours_to_work': getattr(employee.current_workweek, 'hours_to_work', 0),
                        'current_workweek_hours_to_work_str': str(getattr(employee.current_workweek, 'hours_to_work', 0)),
                        'current_workweek_hours_worked_str': str(getattr(employee.current_workweek, 'hours_worked', 0)),
                    }
                    template.with_context(
                        context
                    ).send_mail(
                        employee.id, force_send=True
                    )

    @api.model
    def send_weekly_summary_report_email(self):
        ir_config = self.env["ir.config_parameter"].sudo()
        send_mail_notification = ir_config.get_param("res.config.settings.send_mail_notification", default="False") == "True"
        if send_mail_notification:
            excluded_calendars = self._get_excluded_calendars(ir_config)
            template = self.env.ref("hr_workweek_reports.hours_worked_summary_email_template", raise_if_not_found=False)
            if template:
                Calendar = self.env["resource.calendar"].sudo()
                Employee = self.env["hr.employee"].sudo()
                allowed_calendars = Calendar.search([("id", "not in", excluded_calendars)])
                employees_by_calendar = {calendar.id: Employee.browse() for calendar in allowed_calendars}
                dateweek = fields.Date.context_today(self)
                for employee in Employee.search([]):
                    calendars = employee._get_workweek_exclusion_calendar_ids(dateweek)
                    if not calendars or calendars.filtered(lambda calendar: calendar.id in excluded_calendars):
                        continue
                    if not self._get_report_workweek(employee, dateweek):
                        continue
                    calendar = calendars[:1]
                    if calendar.id not in employees_by_calendar:
                        allowed_calendars |= calendar
                        employees_by_calendar[calendar.id] = Employee.browse()
                    employees_by_calendar[calendar.id] |= employee
                recipient_ids = ir_config.get_param("res.config.settings.summary_notification_recipient_ids", default="").split(",")
                allowed_employees = self.env["hr.employee"].search(
                    [("id", "in", [int(id) for id in recipient_ids if id.isdigit()])]
                )
                send_from_employee_id = int(ir_config.get_param("res.config.settings.send_from_employee_id", default=0) or 0)
                send_from_employee = self.env["hr.employee"].browse(send_from_employee_id).exists()
                email_from = send_from_employee.work_email or self.env.company.email or self.env.company.partner_id.email
                 # Log del contexto completo
                # _logger.info("Contexto que se pasará al template: calendars = %s", allowed_calendars)
                # _logger.info("Contexto employees_by_calendar keys: %s", list(employees_by_calendar.values()))
                for allowed_employee in allowed_employees:
                    if not allowed_employee.work_email:
                        continue
                    email_values = {"email_to": allowed_employee.work_email}
                    if email_from:
                        email_values["email_from"] = email_from
                    template.with_context(
                        calendars=allowed_calendars,
                        employees_by_calendar=employees_by_calendar,
                    ).send_mail(
                        allowed_employee.id,
                        force_send=True,
                        email_values=email_values,
                    )
