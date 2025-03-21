from odoo import _, fields, models
from odoo.exceptions import UserError


class HrWorkweekWizard(models.TransientModel):
    _name = "hr.workweek.wizard"
    _description = "Wizard for compensation"

    compensation_description = fields.Text(string="Description", required=False)

    compensation_type = fields.Selection(
        string="Compensation type",
        selection=[("economic", "Economic"), ("leave", "Leave days")],
        required=True,
    )

    def _default_compensation_amount(self):
        employee_id = self.env["hr.employee"].browse(self.env.context.get("active_id"))
        hours_difference = sum(employee_id.hr_workweek_ids.mapped("hours_difference"))
        hours_compensated = sum(employee_id.hr_workweek_ids.mapped("hours_compensated"))
        return (
            abs(hours_difference + hours_compensated)
            if hours_difference + hours_compensated < 0
            else 0.0
        )

    compensation_amount = fields.Float(
        string="Hours to compensate",
        required=True,
        default=_default_compensation_amount,
    )

    compensation_amount_max = fields.Float(
        string="Hours to compensate",
        default=_default_compensation_amount,
        readonly=True,
    )

    def _default_responsible_id(self):
        employee_id = self.env["hr.employee"].browse(self.env.context.get("active_id"))
        return employee_id.parent_id.id or employee_id.id

    responsible_id = fields.Many2one(
        string="Responsible",
        comodel_name="hr.employee",
        required=True,
        default=_default_responsible_id,
    )

    def action_confirm(self):
        employee = self.env["hr.employee"].browse([self._context.get("active_id")])
        if self.compensation_amount <= 0:
            raise UserError(_("The number of hours must be greater than 0."))
        elif self.compensation_amount > self.compensation_amount_max:
            raise UserError(
                _(
                    f"You can't compensate more than {self.compensation_amount_max} hours"
                )
            )
        else:
            compensation_id = employee._action_compensate(
                self.compensation_amount,
                self.compensation_type,
                self.compensation_description,
                self.responsible_id,
            )
            return {
                "name": compensation_id.name,
                "view_type": "form",
                "view_mode": "form",
                "res_model": "hr.compensation",
                "type": "ir.actions.act_window",
                "res_id": compensation_id.id,
                "context": self.env.context,
            }
