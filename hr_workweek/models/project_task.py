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
        help="Imputable duration vs worked hours (unit_amount_imputable / unit_amount * 100), "
             "excluding time off requests, closed-budget and non-billable tasks."
    )

    @api.depends('timesheet_ids.unit_amount', 'timesheet_ids.unit_amount_invoiced', 'timesheet_ids.unit_amount_imputable', 'timesheet_ids.holiday_id', 'closed_budget', 'non_invoiceable', 'child_ids.total_hours_invoiced', 'child_ids.work_efficiency')
    def _compute_efficiency(self):
        has_global_leave = 'global_leave_id' in self.env['account.analytic.line']._fields
        for task in self.sorted(key=lambda t: str(t.id), reverse=True):
            subtasks = task._get_all_subtasks()
            all_tasks = task | subtasks
            all_timesheets = all_tasks.mapped('timesheet_ids').filtered(
                lambda line: not (line.holiday_id or (has_global_leave and line.global_leave_id))
            )
            task.total_hours_invoiced = sum(all_timesheets.mapped('unit_amount_invoiced'))
            if task.closed_budget or task.non_invoiceable:
                task.work_efficiency = 0.0
                continue
            eff_timesheets = all_timesheets.filtered(lambda line: not (line.task_id.closed_budget or line.task_id.non_invoiceable))
            eff_imputable = sum(eff_timesheets.mapped('unit_amount_imputable'))
            eff_worked = sum(eff_timesheets.mapped('unit_amount'))
            task.work_efficiency = ((eff_imputable / eff_worked) * 100 if eff_worked > 0 else 0.0)