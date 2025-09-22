/** @odoo-module **/
import { progressBarField, ProgressBarField } from "@web/views/fields/progress_bar/progress_bar_field";
import { patch } from "@web/core/utils/patch";


patch(ProgressBarField.prototype, {
    setup() {
        super.setup(...arguments);
    },
    get progressBarColorClass() {
        const widthComplete = this.currentValue;
        if (widthComplete <= 99) {
            return "o_progress_red";
        } else if (widthComplete >= 100) {
            return "o_progress_green";
        }
        return "bg-primary";
    }
});