{
    "name": "HR Workweek",
    "summary": "Per-employee workweek entries with compensation"
    " capabilities for due and overtime hours",
    "author": "Domatix",
    "website": "https://www.domatix.com",
    "category": "Human Resources",
    "version": "18.0.1.0.0",
    "depends": [
        "hr_timesheet",
        "hr_employee_calendar_planning",
        "hr_holidays_public",
        "calendar_public_holiday",
        "task_hr_timesheet_report"
    ],
    "data": [
        "security/ir.model.access.csv",
        'security/security_groups.xml',
        "wizard/hr_workweek_wizard_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_workweek_views.xml",
        "views/res_config_settings.xml",
        "views/project_task_views.xml",
        "views/hr_compensation_views.xml",
        "data/ir_sequence_data.xml",
        "data/workweek_data.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_workweek/static/src/js/efficiency_color.js",
            "hr_workweek/static/src/css/efficiency_color.css",
        ],
    },
    "application": True,
    "installable": True,
    "license": "AGPL-3",
}
