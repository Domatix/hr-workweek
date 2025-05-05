from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    total_hours_invoiced = fields.Float(
        string="Total Invoiced",
        compute="_compute_efficiency",
        store=True,
        recursive=True,
        help="Sum of all unit_amount_invoiced from timesheets including subtasks"
    )

    work_efficiency = fields.Float(
        string="Billing Efficiency",
        compute="_compute_efficiency",
        store=True,
        recursive=True,
        help="Percentage of worked hours that are billable (unit_amount_invoiced / unit_amount * 100)"
    )

    @api.depends('timesheet_ids.unit_amount', 'timesheet_ids.unit_amount_invoiced', 'child_ids.total_hours_invoiced', 'child_ids.work_efficiency')
    def _compute_efficiency(self):
        for task in self.sorted(key=lambda t: str(t.id), reverse=True):
            subtasks = task._get_all_subtasks()
            all_tasks = task | subtasks
            all_timesheets = all_tasks.mapped('timesheet_ids')
            total_invoiced = sum(all_timesheets.mapped('unit_amount_invoiced'))
            total_worked = sum(all_timesheets.mapped('unit_amount'))
            task.total_hours_invoiced = total_invoiced
            task.work_efficiency = ((total_invoiced / total_worked) * 100 if total_worked > 0 else 0.0)