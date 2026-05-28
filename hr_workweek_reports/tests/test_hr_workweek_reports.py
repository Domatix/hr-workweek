from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.models.mail_template import MailTemplate
from odoo.tests.common import TransactionCase


class TestHrWorkweekReports(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env["hr.employee"]
        cls.Workweek = cls.env["hr.workweek"]
        cls.Config = cls.env["ir.config_parameter"].sudo()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "Workweek Reports Calendar"}
        )
        cls.employee = cls.Employee.create(
            {
                "name": "Report Employee",
                "work_email": "report.employee@example.com",
                "resource_calendar_id": cls.calendar.id,
            }
        )
        cls.employee_without_workweek = cls.Employee.create(
            {
                "name": "Report Employee Without Workweek",
                "work_email": "report.no.week@example.com",
                "resource_calendar_id": cls.calendar.id,
            }
        )
        cls.recipient = cls.Employee.create(
            {
                "name": "Report Recipient",
                "work_email": "report.recipient@example.com",
                "resource_calendar_id": cls.calendar.id,
            }
        )
        cls.sender = cls.Employee.create(
            {
                "name": "Report Sender",
                "work_email": "report.sender@example.com",
                "resource_calendar_id": cls.calendar.id,
            }
        )
        cls.date_start, cls.date_end = cls.Employee.get_workweek_dates(
            fields.Date.context_today(cls.Employee)
        )
        cls.workweek = cls.Workweek.create(
            {
                "employee_id": cls.employee.id,
                "date_start": cls.date_start,
                "date_end": cls.date_end,
            }
        )

    def setUp(self):
        super().setUp()
        self.Config.set_param("res.config.settings.send_mail_notification", "False")
        self.Config.set_param("res.config.settings.summary_notification_recipient_ids", "")
        self.Config.set_param("res.config.settings.send_from_employee_id", "")
        self._allow_only_calendar(self.calendar)

    def _allow_only_calendar(self, calendar):
        excluded_calendars = self.env["resource.calendar"].search(
            [("id", "!=", calendar.id)]
        )
        self.Config.set_param(
            "res.config.settings.excluded_calendar_ids",
            ",".join(map(str, excluded_calendars.ids)),
        )

    def _capture_sent_mails(self):
        sent_mails = []
        def send_mail(template, res_id, force_send=False, email_values=None, **kwargs):
            sent_mails.append(
                {
                    "res_id": res_id,
                    "force_send": force_send,
                    "email_values": email_values or {},
                    "context": dict(template.env.context),
                }
            )
            return True
        return sent_mails, patch.object(MailTemplate, "send_mail", send_mail)

    def test_get_report_workweek_sets_current_workweek(self):
        self.employee.current_workweek = False
        workweek = self.Employee._get_report_workweek(
            self.employee,
            fields.Date.context_today(self.Employee),
        )
        self.assertEqual(workweek, self.workweek)
        self.assertEqual(self.employee.current_workweek, self.workweek)

    def test_get_report_workweek_returns_empty_without_matching_week(self):
        workweek = self.Employee._get_report_workweek(
            self.employee_without_workweek,
            fields.Date.context_today(self.Employee),
        )
        self.assertFalse(workweek)

    def test_weekly_report_does_not_send_when_notification_is_false_string(self):
        sent_mails, mail_patch = self._capture_sent_mails()
        with mail_patch:
            self.Employee.send_weekly_report_email()
            self.Employee.send_weekly_summary_report_email()
        self.assertFalse(sent_mails)

    def test_weekly_report_sends_only_employees_with_current_week(self):
        self.Config.set_param("res.config.settings.send_mail_notification", "True")
        sent_mails, mail_patch = self._capture_sent_mails()
        with mail_patch:
            self.Employee.send_weekly_report_email()
        sent_res_ids = [mail["res_id"] for mail in sent_mails]
        self.assertIn(self.employee.id, sent_res_ids)
        self.assertNotIn(self.employee_without_workweek.id, sent_res_ids)

    def test_weekly_summary_supports_empty_sender_and_filters_missing_weeks(self):
        self.Config.set_param("res.config.settings.send_mail_notification", "True")
        self.Config.set_param(
            "res.config.settings.summary_notification_recipient_ids",
            str(self.recipient.id),
        )
        self.Config.set_param("res.config.settings.send_from_employee_id", "")
        sent_mails, mail_patch = self._capture_sent_mails()
        with mail_patch:
            self.Employee.send_weekly_summary_report_email()
        self.assertEqual(len(sent_mails), 1)
        self.assertEqual(sent_mails[0]["res_id"], self.recipient.id)
        self.assertEqual(sent_mails[0]["email_values"]["email_to"], self.recipient.work_email)
        employees_by_calendar = sent_mails[0]["context"]["employees_by_calendar"]
        calendar_employees = employees_by_calendar[self.calendar.id]
        self.assertIn(self.employee, calendar_employees)
        self.assertNotIn(self.employee_without_workweek, calendar_employees)

    def test_weekly_summary_uses_configured_sender_email(self):
        self.Config.set_param("res.config.settings.send_mail_notification", "True")
        self.Config.set_param(
            "res.config.settings.summary_notification_recipient_ids",
            str(self.recipient.id),
        )
        self.Config.set_param("res.config.settings.send_from_employee_id", str(self.sender.id))
        sent_mails, mail_patch = self._capture_sent_mails()
        with mail_patch:
            self.Employee.send_weekly_summary_report_email()
        self.assertEqual(sent_mails[0]["email_values"]["email_from"], self.sender.work_email)
