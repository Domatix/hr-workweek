/** @odoo-module **/
import { progressBarField, ProgressBarField } from "@web/views/fields/progress_bar/progress_bar_field";
import { registry } from "@web/core/registry";


export class HrWorkweekProgressBarField extends ProgressBarField {
    get progressBarColorClass() {
        const widthComplete = this.currentValue;
        if (widthComplete <= 99) {
            return "o_hr_workweek_progress_red";
        } else if (widthComplete >= 100) {
            return "o_hr_workweek_progress_green";
        }
        return "bg-primary";
    }
}

export const hrWorkweekProgressBarField = {
    ...progressBarField,
    component: HrWorkweekProgressBarField,
};

registry.category("fields").add("hr_workweek_progressbar", hrWorkweekProgressBarField);
