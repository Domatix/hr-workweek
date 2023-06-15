{
    "name": "HR Workweek",
    "summary": "Per-employee workweek entries with compensation"
    " capabilities for due and overtime hours",
    "author": "Domatix",
    "website": "https://www.domatix.com",
    "category": "Human Resources",
    "version": "15.0.1.0.0",
    "depends": [
        "hr_timesheet",
        "hr_employee_calendar_planning",
        "hr_holidays_public",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/hr_workweek_wizard_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_workweek_views.xml",
        "views/res_config_settings.xml",
        "views/hr_compensation_views.xml",
        "data/ir_sequence_data.xml",
        "data/workweek_data.xml",
        "data/ir_cron.xml",
    ],
    "application": True,
    "installable": True,
    "license": "AGPL-3",
}
