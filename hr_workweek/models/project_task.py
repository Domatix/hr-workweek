from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    total_hours_invoiced = fields.Float(
        string="Total Invoiced",
        compute="_compute_efficiency",
        store=True,
        help="Sum of all unit_amount_invoiced from timesheets including subtasks"
    )

    work_efficiency = fields.Float(
        string="Billing Efficiency",
        compute="_compute_efficiency",
        store=True,
        help="Percentage of worked hours that are billable (unit_amount_invoiced / unit_amount * 100)"
    )

    @api.depends('timesheet_ids.unit_amount', 'timesheet_ids.unit_amount_invoiced', 'child_ids.timesheet_ids.unit_amount', 'child_ids.timesheet_ids.unit_amount_invoiced')
    def _compute_efficiency(self):
        for task in self:
            all_timesheets = task.timesheet_ids + task.child_ids.timesheet_ids
            total_worked = sum(all_timesheets.mapped('unit_amount'))
            total_invoiced = sum(all_timesheets.mapped('unit_amount_invoiced'))
            task.total_hours_invoiced = total_invoiced
            task.work_efficiency = ((total_invoiced / total_worked) * 100 if total_worked > 0 else 0.0)