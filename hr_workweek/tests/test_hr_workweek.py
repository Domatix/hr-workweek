from datetime import date, datetime, timedelta

from odoo.tests.common import SavepointCase

from ..models.hr_workweek import ODOO_DATE_FORMAT


class TestHrTimesheetSheet(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.workweek_obj = cls.env["hr.workweek"]
        cls.calendar_obj = cls.env["hr.employee.calendar"]
        cls.employee_obj = cls.env["hr.employee"]
        cls.compensation_obj = cls.env["hr.compensation"]
        cls.weekday_1: date = datetime.strptime(
            "2020-06-29", ODOO_DATE_FORMAT
        ).date()  # M
        cls.weekday_2: date = datetime.strptime(
            "2019-09-03", ODOO_DATE_FORMAT
        ).date()  # T
        cls.weekday_3: date = datetime.strptime(
            "2023-02-05", ODOO_DATE_FORMAT
        ).date()  # S
        cls.employee_1 = cls.employee_obj.create({"name": "Employee 1"})
        cls.user_1 = cls.env.ref("base.user_demo")
        cls.employee_al = cls.env.ref("hr.employee_al")
        cls.employee_mit = cls.env.ref("hr.employee_mit")
        cls.default_resource_calendar = cls.env.ref("resource.resource_calendar_std")
        cls.calendar_1 = cls.calendar_obj.create(
            {
                "date_start": datetime.strptime("2020-06-01", ODOO_DATE_FORMAT).date(),
                "date_end": datetime.strptime("2020-08-01", ODOO_DATE_FORMAT).date(),
                "employee_id": cls.employee_1.id,
                "calendar_id": cls.default_resource_calendar.id,
            }
        )
        cls.calendar_2 = cls.calendar_obj.create(
            {
                "date_start": datetime.strptime("2020-06-28", ODOO_DATE_FORMAT).date(),
                "employee_id": cls.employee_1.id,
                "calendar_id": cls.default_resource_calendar.id,
            }
        )
        cls.calendar_3 = cls.calendar_obj.create(
            {
                "employee_id": cls.employee_1.id,
                "calendar_id": cls.default_resource_calendar.id,
            }
        )
        cls.workweek_1 = cls.env.ref("hr_workweek.workweek_1")
        cls.workweek_2 = cls.env.ref("hr_workweek.workweek_2")
        cls.project_1 = cls.env.ref("project.project_project_1")
        cls.task_1 = cls.env.ref("project.project_task_1")
        cls.compensation = cls.compensation_obj.create(
            {
                "state": "draft",
                "employee_id": cls.employee_1.id,
                "petition_date": datetime.strptime(
                    "2020-11-20", ODOO_DATE_FORMAT
                ).date(),
                "unit_amount": 8,
            }
        )

    def test_static_methods(self):
        # Test week 2020-06-2 -> 2020-07-05
        true_sunday_1: date = datetime.strptime("2020-07-05", ODOO_DATE_FORMAT).date()
        monday, sunday = self.workweek_obj._get_limit_dates(self.weekday_1)

        self.assertEqual(monday, self.weekday_1)
        self.assertEqual(sunday, true_sunday_1)
        self.assertEqual(sunday - monday, timedelta(days=6))

        # Test week 2019-09-02 -> 2019-09-03 -> 2019-09-08
        true_monday_2: date = datetime.strptime("2019-09-02", ODOO_DATE_FORMAT).date()
        true_sunday_2: date = datetime.strptime("2019-09-08", ODOO_DATE_FORMAT).date()
        monday, sunday = self.workweek_obj._get_limit_dates(self.weekday_2)

        self.assertEqual(monday, true_monday_2)
        self.assertEqual(sunday, true_sunday_2)
        self.assertLess(monday, self.weekday_2)
        self.assertGreater(sunday, self.weekday_2)
        self.assertEqual(sunday - monday, timedelta(days=6))

        # Test hours to work
        week_start = self.weekday_1
        week_end = self.weekday_1 + timedelta(days=4)

        self.assertEqual(
            40,
            self.workweek_obj._get_hours_to_work(
                calendars=self.calendar_1, date_start=week_start, date_end=week_end
            ),
        )
        self.assertEqual(
            40,
            self.workweek_obj._get_hours_to_work(
                calendars=self.calendar_2, date_start=week_start, date_end=week_end
            ),
        )
        self.assertEqual(
            40,
            self.workweek_obj._get_hours_to_work(
                calendars=self.calendar_3, date_start=week_start, date_end=week_end
            ),
        )

        # Test defaults
        monday, sunday = self.workweek_obj._get_default_limit_dates()
        self.assertEqual(sunday - monday, timedelta(days=6))

    def test_workweeks(self):
        monday_1 = self.workweek_obj._string2date("2020-10-26")
        sunday_1 = self.workweek_obj._string2date("2020-11-01")

        self.assertEqual(self.workweek_1.date_start, monday_1)
        self.assertEqual(self.workweek_1.date_end, sunday_1)
        self.assertFalse(self.workweek_1.account_analytic_line_ids)
        self.assertEqual(self.workweek_1.hours_to_work, 40)
        self.assertEqual(self.workweek_1.hours_worked, 0)
        self.assertEqual(self.workweek_1.progress, 0)
        self.assertEqual(self.workweek_1.hours_leave, 0)

        account_analytic_line_values = [
            (
                0,
                0,
                {
                    "user_id": self.user_1.id,
                    "employee_id": self.employee_al.id,
                    "date": monday_1 + timedelta(days=i),
                    "name": f"Workweek 1 timesheet test {i}",
                    "project_id": self.project_1.id,
                    "task_id": self.task_1.id,
                    "unit_amount": 3.5 * i,
                },
            )
            for i in range(5)
        ]
        self.workweek_1.account_analytic_line_ids = account_analytic_line_values
        self.assertEqual(len(self.workweek_1.account_analytic_line_ids), 5)
        self.assertEqual(self.workweek_1.hours_to_work, 40)
        self.assertEqual(self.workweek_1.hours_worked, 35.0)
        self.assertEqual(self.workweek_1.progress, 35.0 / 40 * 100)

        # TODO
        # 1. compute leave hours
        # 2. check `hours_worked` after changing the `account.analytic.line` records

        monday_2 = self.workweek_obj._string2date("2020-01-04")
        sunday_2 = self.workweek_obj._string2date("2020-01-10")
        self.assertEqual(self.workweek_2.date_start, monday_2)
        self.assertEqual(self.workweek_2.date_end, sunday_2)
