import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantBooking extends Base {
    static pythonModel = "restaurant.booking";

    setup(vals) {
        super.setup(vals);
        this.name = vals.name;
        this.partner_id = vals.partner_id;
        this.phone = vals.phone;
        this.booking_date = vals.booking_date;
        this.table_id = vals.table_id;
        this.guests = vals.guests || 2;
    }
}
registry.category("pos_available_models").add(RestaurantBooking.pythonModel, RestaurantBooking);
