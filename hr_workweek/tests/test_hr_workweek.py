from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestHrWorkweek(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env["hr.employee"]
        cls.Workweek = cls.env["hr.workweek"]
        cls.calendar = cls.env.ref("resource.resource_calendar_std")
        cls.employee = cls.Employee.create(
            {
                "name": "Workweek Employee",
                "resource_calendar_id": cls.calendar.id,
            }
        )

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "res.config.settings.excluded_calendar_ids", ""
        )

    def test_get_workweek_dates(self):
        monday = fields.Date.to_date("2020-06-29")
        start, end = self.Employee.get_workweek_dates(monday)
        self.assertEqual(start, monday)
        self.assertEqual(end, monday + timedelta(days=6))
        tuesday = fields.Date.to_date("2019-09-03")
        start, end = self.Employee.get_workweek_dates(tuesday)
        self.assertEqual(start, fields.Date.to_date("2019-09-02"))
        self.assertEqual(end, fields.Date.to_date("2019-09-08"))

    def test_create_current_workweek_is_idempotent(self):
        date_start, date_end = self.Employee.get_workweek_dates(fields.Date.context_today(self.Employee))
        domain = [
            ("employee_id", "=", self.employee.id),
            ("date_start", "=", date_start),
            ("date_end", "=", date_end),
        ]
        self.Employee.create_current_workweek()
        workweek = self.Workweek.search(domain)
        self.assertEqual(len(workweek), 1)
        self.assertEqual(self.employee.current_workweek, workweek)
        self.Employee.create_current_workweek()
        self.assertEqual(self.Workweek.search_count(domain), 1)

    def test_create_current_workweek_respects_excluded_calendar(self):
        employee = self.Employee.create(
            {
                "name": "Excluded Calendar Employee",
                "resource_calendar_id": self.calendar.id,
            }
        )
        date_start, date_end = self.Employee.get_workweek_dates(fields.Date.context_today(self.Employee))
        excluded_calendars = employee._get_workweek_exclusion_calendar_ids(date_start)
        self.assertTrue(excluded_calendars)
        self.env["ir.config_parameter"].sudo().set_param(
            "res.config.settings.excluded_calendar_ids", ",".join(map(str, excluded_calendars.ids))
        )
        self.Employee.create_current_workweek()
        self.assertFalse(
            self.Workweek.search(
                [
                    ("employee_id", "=", employee.id),
                    ("date_start", "=", date_start),
                    ("date_end", "=", date_end),
                ]
            )
        )

    def test_hours_to_work_uses_employee_planned_calendar(self):
        empty_calendar = self.env["resource.calendar"].create(
            {
                "name": "Workweek Empty Calendar",
                "attendance_ids": [(5, 0, 0)],
            }
        )
        date_start = fields.Date.to_date("2020-06-29")
        date_end = fields.Date.to_date("2020-07-05")
        employee = self.Employee.create(
            {
                "name": "Planned Calendar Employee",
                "resource_calendar_id": self.calendar.id,
                "calendar_ids": [
                    (
                        0,
                        0,
                        {
                            "calendar_id": empty_calendar.id,
                            "date_start": date_start,
                            "date_end": date_end,
                        },
                    )
                ],
            }
        )
        workweek = self.Workweek.create(
            {
                "employee_id": employee.id,
                "date_start": date_start,
                "date_end": date_end,
            }
        )

        self.assertEqual(workweek.hours_to_work, 0.0)

    def test_compute_holidays_lines_supports_multiple_records(self):
        week_1 = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": fields.Date.to_date("2020-06-29"),
                "date_end": fields.Date.to_date("2020-07-05"),
            }
        )
        week_2 = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": fields.Date.to_date("2020-07-06"),
                "date_end": fields.Date.to_date("2020-07-12"),
            }
        )
        (week_1 | week_2)._compute_holidays_lines()

    def test_global_leave_timesheet_can_be_created_outside_today(self):
        AnalyticLine = self.env["account.analytic.line"]
        if "global_leave_id" not in AnalyticLine._fields:
            self.skipTest("project_timesheet_holidays is not installed")
        project = self.env["project.project"].create({"name": "Global Leave Project"})
        leave = self.env["resource.calendar.leaves"].create(
            {
                "name": "Global Leave",
                "date_from": "2020-06-29 00:00:00",
                "date_to": "2020-06-29 23:59:59",
            }
        )

        line = AnalyticLine.create(
            {
                "name": "Global leave timesheet",
                "project_id": project.id,
                "account_id": project.account_id.id,
                "employee_id": self.employee.id,
                "date": fields.Date.to_date("2020-06-29"),
                "unit_amount": 1.0,
                "global_leave_id": leave.id,
            }
        )

        self.assertFalse(line.hr_workweek_id)
