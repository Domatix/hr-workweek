from datetime import datetime, time, timedelta

import pytz

from odoo import fields
from odoo.exceptions import UserError
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
        # A full Monday-to-Sunday week used by several tests.
        cls.week_start = fields.Date.to_date("2020-06-29")
        cls.week_end = fields.Date.to_date("2020-07-05")

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "res.config.settings.excluded_calendar_ids", ""
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_employee(self, name):
        return self.Employee.create(
            {
                "name": name,
                "resource_calendar_id": self.calendar.id,
            }
        )

    def _calendar_hours(self, date_start, date_end):
        """Plain calendar attendance hours for the given range (no leaves)."""
        return self.calendar.get_work_hours_count(
            datetime.combine(date_start, time.min),
            datetime.combine(date_end, time.max),
            compute_leaves=False,
        )

    # ------------------------------------------------------------------
    # Dates / helpers
    # ------------------------------------------------------------------
    def test_get_workweek_dates(self):
        monday = fields.Date.to_date("2020-06-29")
        start, end = self.Employee.get_workweek_dates(monday)
        self.assertEqual(start, monday)
        self.assertEqual(end, monday + timedelta(days=6))
        tuesday = fields.Date.to_date("2019-09-03")
        start, end = self.Employee.get_workweek_dates(tuesday)
        self.assertEqual(start, fields.Date.to_date("2019-09-02"))
        self.assertEqual(end, fields.Date.to_date("2019-09-08"))

    def test_date_is_working_day(self):
        self.assertTrue(
            self.Workweek.date_is_working_day(fields.Date.to_date("2020-06-29"))
        )  # Monday
        self.assertFalse(
            self.Workweek.date_is_working_day(fields.Date.to_date("2020-07-04"))
        )  # Saturday

    def test_get_current_workweek(self):
        workweek = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        found = self.Workweek.get_current_workweek(
            self.employee, fields.Date.to_date("2020-07-01")
        )
        self.assertEqual(found, workweek)
        self.assertFalse(
            self.Workweek.get_current_workweek(
                self.employee, fields.Date.to_date("2020-07-20")
            )
        )

    # ------------------------------------------------------------------
    # Workweek creation (cron)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # hours_to_work / hours_leave / hours_difference
    # ------------------------------------------------------------------
    def test_hours_to_work_full_week(self):
        """A regular employee gets the calendar hours, no leave, and the
        difference equals the hours still to do."""
        workweek = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        expected = self._calendar_hours(self.week_start, self.week_end)
        self.assertEqual(workweek.hours_to_work, expected)
        self.assertEqual(workweek.hours_leave, 0.0)
        self.assertEqual(workweek.hours_worked, 0.0)
        self.assertEqual(workweek.hours_difference, expected)

    def test_flexible_resource_does_not_span_whole_period(self):
        """Regression: since 19.0 the working schedule lives on the contract
        version, leaving ``resource_id.calendar_id`` empty (a "fully flexible"
        resource). Passing such a resource to ``_work_intervals_batch`` makes
        ``resource.calendar`` return the whole 7x24 period (168h) -- the bug
        behind the inflated "hours to work". ``_compute_hours_to_work`` now reads
        the calendar attendances WITHOUT the resource, which keeps the real
        schedule."""
        employee = self._create_employee("Flexible Resource Employee")
        employee.resource_id.calendar_id = False
        self.assertTrue(employee.resource_id._is_fully_flexible())

        tz = pytz.timezone(self.calendar.tz or "UTC")
        start = tz.localize(datetime.combine(self.week_start, time.min))
        end = tz.localize(datetime.combine(self.week_end, time.max))

        # The trap the module used to fall into: passing the flexible resource
        # returns the whole period.
        trapped = self.calendar._work_intervals_batch(start, end, employee.resource_id)
        trapped_hours = sum(
            (stop - begin).total_seconds() / 3600
            for begin, stop, _meta in trapped[employee.resource_id.id]
        )
        self.assertAlmostEqual(trapped_hours, 168.0, delta=0.01)

        # The approach used by the fix keeps the real schedule.
        attendances = self.calendar._attendance_intervals_batch(start, end, tz=tz)[False]
        real_hours = sum(
            (stop - begin).total_seconds() / 3600 for begin, stop, _meta in attendances
        )
        self.assertNotEqual(real_hours, 168.0)
        self.assertAlmostEqual(
            real_hours, self._calendar_hours(self.week_start, self.week_end), delta=0.01
        )

    def test_hours_to_work_uses_employee_planned_calendar(self):
        empty_calendar = self.env["resource.calendar"].create(
            {
                "name": "Workweek Empty Calendar",
                "attendance_ids": [(5, 0, 0)],
            }
        )
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
                            "date_start": self.week_start,
                            "date_end": self.week_end,
                        },
                    )
                ],
            }
        )
        workweek = self.Workweek.create(
            {
                "employee_id": employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )

        self.assertEqual(workweek.hours_to_work, 0.0)

    def test_hours_to_work_excludes_public_holidays(self):
        """A public holiday on a working day reduces the hours to work and is
        accounted as leave/absence hours."""
        public_holiday = self.env["calendar.public.holiday"].create({"year": 2020})
        holiday_date = fields.Date.to_date("2020-06-30")  # Tuesday
        self.env["calendar.public.holiday.line"].create(
            {
                "name": "Workweek Public Holiday",
                "date": holiday_date,
                "public_holiday_id": public_holiday.id,
            }
        )
        workweek = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        full = self._calendar_hours(self.week_start, self.week_end)
        holiday_hours = self._calendar_hours(holiday_date, holiday_date)
        self.assertTrue(holiday_hours > 0)
        self.assertEqual(workweek.hr_holidays_public_lines_count, 1)
        self.assertAlmostEqual(workweek.hours_to_work, full - holiday_hours)
        self.assertAlmostEqual(workweek.hours_leave, holiday_hours)

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

    # ------------------------------------------------------------------
    # Timesheets (account.analytic.line)
    # ------------------------------------------------------------------
    def test_timesheet_restricted_to_today_and_linked_to_workweek(self):
        """Timesheets can only be recorded for the current day, and a valid one
        is linked to the running workweek and counted as worked hours."""
        AnalyticLine = self.env["account.analytic.line"]
        employee = self._create_employee("Timesheet Employee")
        project = self.env["project.project"].create({"name": "Workweek Project"})

        with self.assertRaises(UserError):
            AnalyticLine.create(
                {
                    "name": "Past timesheet",
                    "project_id": project.id,
                    "account_id": project.account_id.id,
                    "employee_id": employee.id,
                    "date": self.week_start,
                    "unit_amount": 1.0,
                }
            )

        today = fields.Date.context_today(self.Employee)
        date_start, date_end = self.Employee.get_workweek_dates(today)
        workweek = self.Workweek.create(
            {
                "employee_id": employee.id,
                "date_start": date_start,
                "date_end": date_end,
            }
        )
        line = AnalyticLine.create(
            {
                "name": "Today timesheet",
                "project_id": project.id,
                "account_id": project.account_id.id,
                "employee_id": employee.id,
                "date": today,
                "unit_amount": 3.0,
            }
        )
        self.assertEqual(line.hr_workweek_id, workweek)
        self.assertEqual(workweek.hours_worked, 3.0)
        self.assertEqual(workweek.hours_difference, workweek.hours_to_work - 3.0)

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

    # ------------------------------------------------------------------
    # Compensations
    # ------------------------------------------------------------------
    def test_hours_compensated_sums_compensations(self):
        workweek = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        self.env["hr.compensation"].create(
            {
                "employee_id": self.employee.id,
                "workweek_id": workweek.id,
                "petition_date": fields.Date.context_today(self.Employee),
                "unit_amount": 4.0,
                "type": "economic",
            }
        )
        # ``compensation_count`` is a non-stored compute without depends, so the
        # value cached when the workweek was created must be invalidated first.
        workweek.invalidate_recordset()
        self.assertEqual(workweek.compensation_count, 1)
        self.assertEqual(workweek.hours_compensated, 4.0)

    def test_employee_hours_difference_aggregates_workweeks(self):
        employee = self._create_employee("Aggregate Employee")
        workweek = self.Workweek.create(
            {
                "employee_id": employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        self.assertEqual(
            employee.hours_difference,
            workweek.hours_difference + workweek.hours_compensated,
        )

    # ------------------------------------------------------------------
    # Leaves
    # ------------------------------------------------------------------
    def test_leave_overlapping_workweeks(self):
        workweek = self.Workweek.create(
            {
                "employee_id": self.employee.id,
                "date_start": self.week_start,
                "date_end": self.week_end,
            }
        )
        # A leave overlapping the week resolves and maps to the workweek.
        overlapping_leave = self.env["hr.leave"].new(
            {
                "employee_id": self.employee.id,
                "request_date_from": fields.Date.to_date("2020-06-30"),
                "request_date_to": fields.Date.to_date("2020-06-30"),
            }
        )
        self.assertIn(workweek, overlapping_leave._get_overlapping_workweeks())
        self.assertEqual(
            self.env["hr.leave"]._assign_workweeks(overlapping_leave),
            [(4, workweek.id)],
        )
        # A leave outside the week resolves to nothing.
        outside_leave = self.env["hr.leave"].new(
            {
                "employee_id": self.employee.id,
                "request_date_from": fields.Date.to_date("2020-08-01"),
                "request_date_to": fields.Date.to_date("2020-08-02"),
            }
        )
        self.assertFalse(outside_leave._get_overlapping_workweeks())
